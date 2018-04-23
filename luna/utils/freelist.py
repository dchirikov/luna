'''
Written by Dmitry Chirikov <dmitry@chirikov.ru>
This file is part of Luna, cluster provisioning tool
https://github.com/dchirikov/luna

This file is part of Luna.

Luna is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Luna is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Luna.  If not, see <http://www.gnu.org/licenses/>.

'''

import re
import socket
import struct
import logging


log = logging.getLogger(__name__)


"""
This file handles lists of free ranges representing unoccupied
relative IPv4 addresses (in binary form obtained using ip.aton
and relative to their subnet address).

e.g. flist = [{'start': 1, 'end': 80},
                 {'start': 100, 'end': 65652}]

Note: a freelist's lower boundary is always '1' due to the elements
      being relative
"""


def next_free(flist):
    """
    Get the next free element from a freelist then remove it from
    the list
    """

    # Return None if the freelist is empty

    if not bool(flist):
        log.error("Cannot get next IP. No free IPs available")
        return (flist, None)

    first_range = flist[0]

    if first_range['start'] == first_range['end']:
        flist.pop(0)

    else:
        flist[0] = {'start': first_range['start'] + 1,
                       'end': first_range['end']}

    return (flist, first_range['start'])


def unfree_range(flist, start, end=None):
    """
    Remove a range from a freelist
    """

    if end is None:
        end = start

    # Return None if the freelist is empty

    if not bool(flist):
        log.info("Cannot get next IP. No free IPs available")
        return (flist, None)

    # Make sure the requested range does fit into the freelist's
    # boundaries

    first_free = flist[0]['start']
    last_free = flist[-1]['end']

    if not (first_free <= start <= last_free):
        log.error("Requested IP '{}' is out of range".format(start))
        return (flist, None)

    if not (first_free <= end <= last_free):
        log.error("Requested IP '{}' is out of range".format(end))
        return (flist, None)

    # Find the range that containes the subrange [start, end]
    # and update it. if none found then it means that some requested
    # elements are already reserved

    new_list = []
    index = -1
    for i, frange in enumerate(flist):

        if ((frange['start'] <= start <= frange['end']) and
                (frange['start'] <= end <= frange['end'])):

            index = i

            if frange['end'] == end and frange['start'] == start:
                continue

            elif frange['start'] == start:
                new_list.append({'start': start + 1, 'end': frange['end']})

            elif frange['end'] == end:
                new_list.append({'start': frange['start'], 'end': start - 1})

            elif frange['end'] != frange['start']:
                new_list.append({'start': frange['start'], 'end': start - 1})
                new_list.append({'start': end + 1, 'end': frange['end']})

        else:
            new_list.append(frange)

    if index == -1:
        log.error("Some IPs in the requested range are not available")
        return (flist, None)

    if end == start:
        return (new_list, start)
    else:
        return (new_list, [start, end])


def free_range(flist, start, end=None):
    """
    Mark a range as free in a freelist. This range may include elements
    that are already free.
    """

    if end is None:
        end = start

    # Add the range to the end of the freelist

    tmp_list = flist[:]
    tmp_list.append({'start': start, 'end': end})

    # Sort the freelist based on each free range's 'start' attribute
    # This will allow us to merge overlapping free ranges

    tmp_list.sort(key=lambda free_range: free_range['start'])

    # Merge overlapping ranges

    new_list = []
    skip = 0

    for i in range(0, len(tmp_list)):
        if skip > 0:
            skip -= 1
            continue

        if i == len(tmp_list) - 1:
            new_list.append(tmp_list[i])

        elif (tmp_list[i]['start']
                <= tmp_list[i + 1]['start']
                <= tmp_list[i]['end'] + 1):
            s = tmp_list[i]['start']
            e = tmp_list[i]['end']

            # Check next free ranges for overlaps or continuations

            for j in range(i + 1, len(tmp_list)):
                if tmp_list[j]['end'] >= e and tmp_list[j]['start'] <= e + 1:
                    e = tmp_list[j]['end']
                    skip += 1

                elif tmp_list[j]['end'] <= e and tmp_list[j]['start'] >= s:
                    skip += 1

                else:
                    break

            new_list.append({'start': s, 'end': e})

        else:
            new_list.append(tmp_list[i])

    if end == start:
        return (new_list, start)
    else:
        return (new_list, [start, end])


def set_upper_limit(flist, end, prev_end):
    """
    Update a freelists's uppper end. We assume that a freelist is always
    sorted since the only operation that might alter the order (free_range)
    does perform a sort on the freelist.
    """

    last_ip = flist[-1]['start'] - 1 # last occupied ip
    if flist[-1]['end'] != prev_end:
        last_ip = prev_end

    # Make sure the new 'end' does not exclude some non-free elements

    if last_ip > end:
        err_msg = ("Cannot update freelist upper limit. " +
                   "This new limit excludes some already nonfree elements")
        log.error(err_msg)
        raise RuntimeError, err_msg
    last_range = flist[-1]
    flist[-1] = {'start': last_range['start'], 'end': end}

    return flist


def get_nonfree(flist, limit=None):
    """
    Return an array of the elements that do not belong to the freelist
    and that are in the range delimited by the freelist's boundaries
    """

    if not bool(flist) and (limit is None):
        err_msg = ("freelist is empty. " +
                   "You must provide a boundary (network prefix)")
        log.error(err_msg)
        raise RuntimeError, err_msg

    elif not bool(flist):
        return range(1, limit)

    else:
        last_nonfree = flist[-1]['start']

    nonfree_list = []

    i = 0
    while i < last_nonfree:
        i += 1
        if (flist[0]['start'] <= i <= flist[0]['end']):
            continue

        if i > flist[0]['end']:
            flist.pop(0)

        nonfree_list.append(i)

    return nonfree_list
