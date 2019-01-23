/*
* Written by Dmitry Chirikov <dmitry@chirikov.ru>
* This file is part of Luna, cluster provisioning tool
* https://github.com/dchirikov/luna
*
* This file is part of Luna.
*
* Luna is free software: you can redistribute it and/or modify
* it under the terms of the GNU General Public License as published by
* the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.

* Luna is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with Luna.  If not, see <http://www.gnu.org/licenses/>.
*/

#pragma once

#define ENV_LTORRENT_HOMEDIR          "LTORRENT_HOMEDIR"
#define DEFAULT_LTORRENT_HOMEDIR      "~luna/torrents"
#define ENV_LTORRENT_USER             "LTORRENT_USER"
#define DEFAULT_LTORRENT_USER         "luna"
#define DEFAULT_LOGGER_NAME           "default"
#define ENV_LTORRENT_LOGFILE          "LTORRENT_LOGFILE"
#define DEFAULT_LTORRENT_LOGFILE      "/var/log/luna/ltorrent.log"
#define ENV_LTORRENT_PIDFILE          "LTORRENT_PIDFILE"
#define DEFAULT_LTORRENT_PIDFILE      "/var/run/luna/ltorrent.pid"
#define ENV_LTORRENT_KILLTIMEOUT      "LTORRENT_KILLTIMEOUT"
#define DEFAULT_LTORRENT_KILLTIMEOUT  5
#define TORRENT_FILE_EXTENSION        ".torrent"
#define DEFAULT_HARD_TIMEOUT_FOR_TORRENTS_FILES 3600
#define DEFAULT_LTORRENT_GET_OSIMAGES_CMD "/usr/bin/python", \
  "-c", \
  "import luna; \
      print chr(10).join( \
          [luna.OsImage(n).get('torrent') \
            for n in luna.list('osimage') if luna.OsImage(n).get('torrent')] \
      )"
