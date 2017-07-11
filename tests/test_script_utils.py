# pylint: disable=missing-docstring

import unittest
import sys

from scripts.utils import read_config_file, generate_payload

class UtilsTestCase(unittest.TestCase):
    """Test cases for read_config_file"""
    def test_read_config_file(self):
        """read_config_file returns a dict"""
        sys.argv = ['tests/test_script_utils.py', '--conf', 'config.yaml.example']
        x = read_config_file()
        self.assertTrue(isinstance(x, dict))

    def test_payload_structure(self):
        payload = generate_payload([])
        for required in ('id', 'session', 'data'):
            self.assertIn(required, payload)

        self.assertEqual(payload['data'], [])
