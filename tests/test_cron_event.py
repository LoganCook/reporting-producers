import unittest

from reporting.crontab import CronEvent


class CronEventTestCase(unittest.TestCase):
    def test_cron_event1(self):
        cron1=CronEvent("0 1 * * *")
        #print cron1.numerical_tab
        self.assertTrue(cron1.numerical_tab[0]==set([0]))
        self.assertTrue(cron1.numerical_tab[1]==set([1]))
        self.assertTrue(cron1.numerical_tab[2]==set(xrange(1,32)))
        self.assertTrue(cron1.numerical_tab[3]==set(xrange(1,13)))
        self.assertTrue(cron1.numerical_tab[4]==set(xrange(0,7)))
        self.assertFalse(cron1.check_trigger((2015,6,16,10,0)))

    def test_cron_event2(self):
        cron2=CronEvent("0 */5 * * 0-4")
        #print cron2.numerical_tab
        self.assertTrue(cron2.numerical_tab[0]==set([0]))
        self.assertTrue(cron2.numerical_tab[1]==set([0, 10, 20, 5, 15]))
        self.assertTrue(cron2.numerical_tab[2]==set([]))
        self.assertTrue(cron2.numerical_tab[3]==set(xrange(1,13)))
        self.assertTrue(cron2.numerical_tab[4]==set(xrange(0,5)))
        self.assertTrue(cron2.check_trigger((2015,6,16,10,0)))

    def test_cron_event3(self):
        cron3=CronEvent("*/2 * * * *")
        #print cron1.numerical_tab
        self.assertTrue(cron3.numerical_tab[0]==set([0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58]))
        self.assertTrue(cron3.numerical_tab[1]==set(xrange(0,24)))
        self.assertTrue(cron3.numerical_tab[2]==set(xrange(1,32)))
        self.assertTrue(cron3.numerical_tab[3]==set(xrange(1,13)))
        self.assertTrue(cron3.numerical_tab[4]==set(xrange(0,7)))
        self.assertTrue(cron3.check_trigger((2015,6,17,9,40)))
