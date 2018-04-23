import mock
import unittest

import os
from luna.utils import freelist


class UtilsFreelistTests(unittest.TestCase):

    def setUp(self):
        print
        self.flist0 = []
        self.flist1 = [{'start': 1, 'end': 254}]
        self.flist2 = [{'start': 10, 'end': 18}, {'start': 20, 'end': 254}]
        self.flist3 = [{'start': 254, 'end': 254}]
        self.flist4 = [{'start': 10, 'end': 10}, {'start': 12, 'end': 254}]

    def test_next_free(self):

        # Simple freelist

        flist, next_free = freelist.next_free(self.flist1)
        self.assertEqual(flist, [{'start': 2, 'end': 254}])
        self.assertEqual(next_free, 1)

        # Multiple range freelist

        flist, next_free = freelist.next_free(self.flist2)
        self.assertEqual(flist, [{'start': 11, 'end': 18},
                                 {'start': 20, 'end': 254}])
        self.assertEqual(next_free, 10)

        # Empty freelist

        flist, next_free = freelist.next_free(self.flist0)
        self.assertEqual(flist, [])
        self.assertEqual(next_free, None)

        # Single element freelist

        flist, next_free = freelist.next_free(self.flist3)
        self.assertEqual(flist, [])
        self.assertEqual(next_free, 254)

    def test_unfree_range(self):

        # Empty freelist. Reserve single element

        flist, unfreed = freelist.unfree_range(self.flist0, 6)
        self.assertEqual(flist, [])
        self.assertEqual(unfreed, None)

        # Empty freelist. Reserve range

        flist, unfreed = freelist.unfree_range(self.flist0, 6, 8)
        self.assertEqual(flist, [])
        self.assertEqual(unfreed, None)

        # Simple freelist. Reserve last element

        flist, unfreed = freelist.unfree_range(self.flist1, 254)
        self.assertEqual(flist, [{'start': 1, 'end': 253}])
        self.assertEqual(unfreed, 254)

        # Simple freelist. Reserve first element

        flist, unfreed = freelist.unfree_range(self.flist1, 1)
        self.assertEqual(flist, [{'start': 2, 'end': 254}])
        self.assertEqual(unfreed, 1)

        # Simple freelist. Reserve range

        flist, unfreed = freelist.unfree_range(self.flist1, 6, 8)
        self.assertEqual(flist, [{'start': 1, 'end': 5},
                                 {'start': 9, 'end': 254}])
        self.assertEqual(unfreed, [6, 8])

        # Multiple range freelist. Reserve overlapping range

        flist, unfreed = freelist.unfree_range(self.flist2, 5, 12)
        self.assertEqual(flist, self.flist2)
        self.assertEqual(unfreed, None)

        # Multiple range freelist. Reserve non-overlapping range

        flist, unfreed = freelist.unfree_range(self.flist2, 26, 38)
        self.assertEqual(flist, [{'start': 10, 'end': 18},
                                 {'start': 20, 'end': 25},
                                 {'start': 39, 'end': 254}])
        self.assertEqual(unfreed, [26, 38])

        # Single element freelist. Reserve that element

        flist, unfreed = freelist.unfree_range(self.flist3, 254)
        self.assertEqual(flist, [])
        self.assertEqual(unfreed, 254)

        # Single element freelist. Reserve out of bounds range

        flist, unfreed = freelist.unfree_range(self.flist3, 5, 12)
        self.assertEqual(flist, self.flist3)
        self.assertEqual(unfreed, None)

    def test_free_range(self):

        # Empty freelist. Free range

        flist, freed = freelist.free_range(self.flist0, 6, 8)
        self.assertEqual(flist, [{'start': 6, 'end': 8}])
        self.assertEqual(freed, [6, 8])

        # Simple freelist. Free range

        flist, freed = freelist.free_range(self.flist1, 6, 8)
        self.assertEqual(flist, self.flist1)
        self.assertEqual(freed, [6, 8])

        # Simple freelist. free last element

        flist, freed = freelist.free_range(self.flist1, 255)
        self.assertEqual(flist, [{'start': 1, 'end': 255}])
        self.assertEqual(freed, 255)

        # Simple freelist. free first element

        flist, freed = freelist.free_range(self.flist1, 0)
        self.assertEqual(flist, [{'start': 0, 'end': 254}])
        self.assertEqual(freed, 0)

        # Multiple range freelist. Free overlapping range

        flist, freed = freelist.free_range(self.flist2, 15, 19)
        self.assertEqual(flist, [{'start': 10, 'end': 254}])
        self.assertEqual(freed, [15, 19])

        # Multiple range freelist. Free non-overlapping range

        flist, freed = freelist.free_range(self.flist2, 4, 8)
        self.assertEqual(flist, [{'start': 4, 'end': 8},
                                 {'start': 10, 'end': 18},
                                 {'start': 20, 'end': 254}])
        self.assertEqual(freed, [4, 8])

        # Single element freelist. Free other range

        flist, freed = freelist.free_range(self.flist3, 5, 12)
        self.assertEqual(flist, [{'start': 5, 'end': 12},
                                 {'start': 254, 'end': 254}])
        self.assertEqual(freed, [5, 12])

        # freelist with a single element range. Free one element

        flist, freed = freelist.free_range(self.flist4, 9)
        self.assertEqual(flist, [{'start': 9, 'end': 10},
                                 {'start': 12, 'end': 254}])
        self.assertEqual(freed, 9)

    def test_set_upper_limit(self):

        # Update upper limit with no conflicts

        flist = freelist.set_upper_limit(self.flist1, 15, 254)
        self.assertEqual(flist, [{'start': 1, 'end': 15}])

        # Update upper limit with conflicts

        self.assertRaises(RuntimeError,
                          freelist.set_upper_limit, self.flist2, 15, 254)

    def test_get_nonfree(self):

        # Get non free from empty list without boundary

        self.assertRaises(RuntimeError,
                          freelist.get_nonfree, self.flist0)

        # Get non free from empty list with boundary

        nonfree = freelist.get_nonfree(self.flist0, 254)
        self.assertEqual(nonfree, range(1, 254))

        # Get non free form all free list

        nonfree = freelist.get_nonfree(self.flist1)
        self.assertEqual(nonfree, [])

        # Get non free from partially free list

        nonfree = freelist.get_nonfree(self.flist2)
        self.assertEqual(nonfree, [1, 2, 3, 4, 5, 6, 7, 8, 9, 19])


if __name__ == '__main__':
    unittest.main()
