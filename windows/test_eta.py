import unittest
from session import Session,Reading
from reader import exp_for_level
from presentation import format_value,selected_metrics,METRICS

def reading(n,level=47):
    return Reading(n,int(n*10000/exp_for_level(level))/100,level)

class LevelEtaTests(unittest.TestCase):
    def measured(self):
        s=Session();s.start(0,reading(1000));s.feed(60,reading(7000));return s

    def test_remaining_divided_by_net_exp_speed(self):
        s=self.measured();self.assertAlmostEqual(s.stats(60)['level_eta'],(exp_for_level(47)-7000)/100)
    def test_percent_display_does_not_change_eta(self):
        s=self.measured();self.assertEqual(s.stats(60)['level_eta'],s.stats(60,True)['level_eta'])
    def test_pause_does_not_grow_elapsed_or_eta(self):
        s=self.measured();s.pause(60);self.assertEqual(s.stats(60)['level_eta'],s.stats(600)['level_eta'])
    def test_resume_excludes_pause_gains(self):
        s=self.measured();s.pause(60);s.feed(300,reading(9000));s.start(300,reading(9000));s.feed(360,reading(15000))
        self.assertAlmostEqual(s.stats(360)['level_eta'],(exp_for_level(47)-15000)/100)
    def test_level_up_uses_new_level_remaining(self):
        s=Session();s.start(0,reading(exp_for_level(47)-50));s.feed(10,reading(100,48))
        self.assertAlmostEqual(s.stats(10)['level_eta'],(exp_for_level(48)-100)/15)
    def test_zero_or_negative_net_speed_is_unknown(self):
        s=Session();s.start(0,reading(5000));self.assertIsNone(s.stats(10)['level_eta'])
        s.feed(10,reading(4000));self.assertIsNone(s.stats(10)['level_eta'])
    def test_first_second_and_reset_are_unknown(self):
        s=Session();s.start(0,reading(1000));s.feed(.1,reading(1100));self.assertIsNone(s.stats(.1)['level_eta'])
        self.assertIsNone(Session().stats(20)['level_eta'])
    def test_bad_reading_does_not_produce_eta(self):
        s=self.measured();s.feed(61,Reading(8000,99,47));self.assertIsNone(s.stats(61)['level_eta'])
    def test_maximum_or_unknown_level_is_unknown(self):
        for level in (None,200):
            s=self.measured();s.current=Reading(0,0,level);self.assertIsNone(s.stats(60)['level_eta'])
    def test_time_format_rounds_eta_up_without_wrapping_days(self):
        self.assertEqual(format_value('level_eta',3661.1),'01:01:02')
        self.assertEqual(format_value('level_eta',90000),'25:00:00')
        self.assertEqual(format_value('level_eta',None),'—')
    def test_new_metric_migrates_once_without_overriding_choices(self):
        self.assertEqual(selected_metrics({'metrics':['elapsed']}),{'elapsed','level_eta'})
        self.assertEqual(selected_metrics({'metrics':['elapsed'],'metrics_revision':2}),{'elapsed'})
    def test_meso_alpha_is_label_only(self):
        self.assertTrue(all('+α' in METRICS[k] for k in METRICS if k.startswith('meso_')))
        self.assertEqual(format_value('meso_total',1250),'1,250')

if __name__=='__main__':unittest.main()
