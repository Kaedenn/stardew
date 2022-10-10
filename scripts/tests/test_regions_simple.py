#!/usr/bin/env python3

"""
Test suite for Regions: simple cases
"""

import logging

# pylint: disable=import-error
from regions import RegionNode
# pylint: enable=import-error
from testutil import assert_raises, dump_region

logger = logging.getLogger(__name__)

def test_simple():
  "Trivial test cases with asserts"
  logger.info("test_basic_asserts")
  root = RegionNode("root", 1, invariant_assert=True)
  rfoo = root.push_region("foo", 2)
  assert root.open
  assert rfoo.open
  assert root.last_open() is rfoo
  assert_raises(root.end_region, 1) # end line too small
  root.end_region(4) # ends rfoo
  dump_region(root, msg="root with no open children\n")
  rbar = root.push_region("bar", 4)
  dump_region(root, msg="root with rfoo closed and rbar open\n", with_opath=True)
  assert root.last_open() is rbar, f"{root.last_open()} not {rbar}"

  rbar.end_region(5)
  assert_raises(rbar.end_region, 6)
  assert_raises(rbar.push_region, "baz", 6)
  root.end_region(5)

  dump_region(root, msg="after all tests\n")

# vim: set ts=2 sts=2 sw=2:
