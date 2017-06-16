# pylint: disable=missing-docstring
# this fails on Python 2.6 but Slurm environment is 2.7

import unittest
from datetime import datetime
from reporting.plugins.slurm import SlurmInput


class SlurmTestCase(unittest.TestCase):
    """Test cases for slurm module"""
    def test_all_heros(self):
        """no user other than hero should be in test/sacct-with-start-end.txt"""
        slurm_input = SlurmInput(path='tests/sacct-with-start-end.txt')
        data = slurm_input.get_data()
        for job in data['jobs']:
            self.assertTrue(job['user'].startswith('hero'))

    def test_get_data(self):
        """get_data should return a message in correct structure"""
        slurm_input = SlurmInput(path='tests/sacct-with-start-end.txt')
        data = slurm_input.get_data()
        self.assertIn('hostname', data)
        self.assertIn('timestamp', data)
        self.assertIn('jobs', data)
        self.assertTrue(isinstance(data['jobs'], list))
        job = data['jobs'][0]
        for required_key in ('job_id', 'partition', 'user', 'start', 'end', 'cpu_seconds'):
            self.assertIn(required_key, job)

    def test_read_data(self):
        """_read_data should only return job summary not steps, those do not have User value"""
        data = SlurmInput._read_data('tests/sacct-with-start-end.txt')
        qualified_count = len(data)
        for message in data:
            if 'user' in message and len(message['user'].strip()):
                qualified_count -= 1
        self.assertEqual(qualified_count, 0)

    def test_convert_to_timestamp(self):
        """_convert_to_timestamp should convert iso datetime to timestamp string correctly"""
        ISO_FORMAT = '%Y-%m-%dT%H:%M:%S'
        reference = datetime.utcnow().strftime(ISO_FORMAT)
        converted = datetime.utcfromtimestamp(
            SlurmInput._convert_to_timestamp(reference)).strftime(ISO_FORMAT)
        self.assertEqual(reference, converted)
