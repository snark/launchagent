#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_launchagent
----------------------------------

Tests for `launchagent` module.
"""

import unittest

from launchagent import launchagent


class TestLaunchagent(unittest.TestCase):

    def setUp(self):
        pass

    def test_class_is_present(self):
        self.assertTrue(isinstance(launchagent.LaunchAgent, type))

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()
