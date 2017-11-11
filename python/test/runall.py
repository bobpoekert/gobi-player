#!/usr/bin/env python2.7

import unittest
import sys, os


if __name__ == '__main__':

    here = '/'.join(__file__.split('/')[:-1])
    sys.path.insert(0, here)
    sys.path.insert(0, '%s/../src' % here)

    test_loader = unittest.defaultTestLoader
    test_runner = unittest.TextTestRunner()
    test_suite = test_loader.discover(here)
    test_runner.run(test_suite)
