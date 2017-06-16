import unittest

from reporting.collectors import CommandRunner, FileReader, HTTPReader


class GenericInputTestCase(unittest.TestCase):
    def test_command_running(self):
        input=CommandRunner(cmd="/bin/df -Pk")
        data=input.get_data()
        #print data
        self.assertTrue(data.split('\n')[0].startswith('Filesystem'))

#     def test_file_reader(self):
#         parser=JsonGrepParser(pattern="chargebackData", list_name="hcp-chargeback")
#         input= '{"chargebackData":["chargebackData1","chargebackData2"]}'
#         output=parser.parse(input)
#         #print output
#         self.assertTrue('timestamp' in output)
#         self.assertTrue('hostname' in output)
#         self.assertTrue('hcp-chargeback' in output)
#         self.assertDictEqual({"hcp-chargeback": output["hcp-chargeback"]}, {"hcp-chargeback": [u'chargebackData1',u'chargebackData2']})
#
#     def test_case3(self):
#         parser=JsonGrepParser(pattern=". chargebackData", list_name="hcp-chargeback")
#         input= '[{"chargebackData": 1}, {"chargebackData": 2}]'
#         output=parser.parse(input)
#         #print output
#         self.assertTrue('timestamp' in output)
#         self.assertTrue('hostname' in output)
#         self.assertTrue('hcp-chargeback' in output)
#         self.assertDictEqual({"hcp-chargeback": output["hcp-chargeback"]}, {"hcp-chargeback": [1, 2]})
