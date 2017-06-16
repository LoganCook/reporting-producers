import unittest

from reporting.parsers import JsonGrepParser


class JsonGrepParserTestCase(unittest.TestCase):
    def test_case1(self):
        parser=JsonGrepParser(pattern="chargebackData", list_name="hcp-chargeback")
        input= '{"chargebackData":[{"systemName":"hcp1.s3.ersa.edu.au"}, {"systemName":"hcp2.s3.ersa.edu.au"}]}'
        output=parser.parse(input)
        #print output
        self.assertTrue('timestamp' in output)
        self.assertTrue('hostname' in output)
        self.assertTrue('hcp-chargeback' in output)
        self.assertTrue(isinstance(output["hcp-chargeback"], list))
        self.assertTrue(len(output["hcp-chargeback"])==2)
        self.assertTrue('systemName' in output["hcp-chargeback"][0])
        self.assertTrue(output["hcp-chargeback"][0]['systemName']=='hcp1.s3.ersa.edu.au')
        self.assertTrue('systemName' in output["hcp-chargeback"][1])
        self.assertTrue(output["hcp-chargeback"][1]['systemName']=='hcp2.s3.ersa.edu.au')

    def test_case2(self):
        parser=JsonGrepParser(pattern="chargebackData", list_name="hcp-chargeback")
        input= '{"chargebackData":["chargebackData1","chargebackData2"]}'
        output=parser.parse(input)
        #print output
        self.assertTrue('timestamp' in output)
        self.assertTrue('hostname' in output)
        self.assertTrue('hcp-chargeback' in output)
        self.assertTrue(isinstance(output["hcp-chargeback"], list))
        self.assertTrue(len(output["hcp-chargeback"])==2)
        self.assertTrue(output["hcp-chargeback"][0]=='chargebackData1')
        self.assertTrue(output["hcp-chargeback"][1]=='chargebackData2')

    def test_case3(self):
        parser=JsonGrepParser(pattern=". chargebackData", list_name="hcp-chargeback")
        input= '[{"chargebackData": 1}, {"chargebackData": 2}]'
        output=parser.parse(input)
        #print output
        self.assertTrue('timestamp' in output)
        self.assertTrue('hostname' in output)
        self.assertTrue('hcp-chargeback' in output)
        self.assertTrue(isinstance(output["hcp-chargeback"], list))
        self.assertTrue(len(output["hcp-chargeback"])==2)
        self.assertTrue(output["hcp-chargeback"][0]==1)
        self.assertTrue(output["hcp-chargeback"][1]==2)
