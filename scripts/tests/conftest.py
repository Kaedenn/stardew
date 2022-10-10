#!/usr/bin/env python3

"""
Top-level configuration for the Regions test suite
"""

import logging
import os
import shutil

import pytest
import testutil
testutil.provide_module("regions")

pytest_plugins = ["pytester"]

logging.basicConfig(format="%(module)s:%(lineno)s: %(levelname)s: %(message)s",
                    level=logging.INFO)

# vim: set ts=2 sts=2 sw=2:
