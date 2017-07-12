# pylint: disable=missing-docstring

import unittest
import sys

from scripts.utils import read_config_file, generate_payload, create_logger

class UtilsTestCase(unittest.TestCase):
    """Test cases for read_config_file"""
    def test_read_config_file(self):
        """read_config_file returns a dict"""
        sys.argv = ['tests/test_script_utils.py', '--conf', 'config.runonce.yaml.example']
        config = read_config_file()
        self.assertTrue(isinstance(config, dict))

    def test_payload_structure(self):
        payload = generate_payload([])
        for required in ('id', 'session', 'data'):
            self.assertIn(required, payload)

        self.assertEqual(payload['data'], [])

    def test_default_logger(self):
        log = create_logger(__name__, {})
        self.assertTrue(log.isEnabledFor(10))  # logging.DEBUG
        self.assertTrue(hasattr(log.handlers[0], 'stream'))

    def test_overwrite_config(self):
        """command line argument can overwrite one key-value pair in input"""
        overwritten = 'my_new_path'
        sys.argv = ['tests/test_script_utils.py', '--conf', 'config.runonce.yaml.example',
                    '--key', 'path', '--value', overwritten]
        config = read_config_file()
        self.assertEqual(config['input']['arguments']['path'], overwritten)

    def test_overwrite_config_optional(self):
        """command line argument to overwrite is optional"""
        sys.argv = ['tests/test_script_utils.py', '--conf', 'config.runonce.yaml.example']
        config = read_config_file()
        self.assertEqual(config['input']['arguments']['path'], 'tests/sacct-with-start-end.txt')

    def test_overwrite_config_optional_incomplete(self):
        """command line argument overwrite only works when a pair is set"""
        sys.argv = ['tests/test_script_utils.py', '--conf', 'config.runonce.yaml.example', '--key', 'the_key']
        config = read_config_file()
        self.assertEqual(config['input']['arguments']['path'], 'tests/sacct-with-start-end.txt')
        sys.argv = ['tests/test_script_utils.py', '--conf', 'config.runonce.yaml.example', '--value', 'the_value']
        config = read_config_file()
        self.assertEqual(config['input']['arguments']['path'], 'tests/sacct-with-start-end.txt')
