# pylint: disable=missing-docstring
# this fails on Python 2.6 but vms plugin's environment is 2.7

import unittest
from reporting.plugins.vms import VMSInput


class VMSTestCase(unittest.TestCase):
    """Test cases for vms module"""
    def test_get_data(self):
        """VMS plugin: get_data method should return a message in correct structure"""
        vms_input = VMSInput(path='tests/vms_2017_12.xls')
        data = vms_input.get_data()
        self.assertIn('hostname', data)
        self.assertIn('timestamp', data)
        self.assertIn('instances', data)
        self.assertTrue(isinstance(data['instances'], list))
        self.assertEqual(21, len(data['instances']))
        vm = data['instances'][0]
        for required_key in ('span', 'server_id', 'core', 'ram', 'storage', 'os', 'server', 'business_unit', 'month'):
            self.assertIn(required_key, vm)
