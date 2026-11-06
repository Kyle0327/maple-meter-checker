import unittest
from PIL import Image
from mac_model import Model,crop_frame
from mac_hotkeys import parse,DEFAULT_KEYS
from reader import exp_for_level
from session import Reading,Session,PickupCounter
from presentation import format_value


def value(n,lv=47):return n,int(n*10000/exp_for_level(lv))/100


def packet(model,n=143519,at=1,lines=(),**extra):
    return dict(generation=model.generation,at=at,value=value(n),lines=list(lines),**extra)


class CaptureBoundaryTests(unittest.TestCase):
    def test_old_target_result_never_updates_new_target(self):
        m=Model();p=packet(m);m.invalidate()
        self.assertFalse(m.feed(p));self.assertIsNone(m.reading)

    def test_inflight_before_reset_does_not_reappear(self):
        m=Model();m.feed(packet(m));m.toggle(1.1);old=packet(m,143600,at=2)
        m.reset(2.1);self.assertFalse(m.feed(old));self.assertEqual(m.session.gained,0)

    def test_prestart_pickup_is_baseline(self):
        m=Model();m.feed(packet(m));m.toggle(1.1)
        m.feed(packet(m,at=2,lines=[(100,790,'meso',14)]))
        self.assertEqual(m.session.meso,0)
        m.feed(packet(m,at=3,lines=[(86,790,'meso',14),(100,790,'meso',12)]))
        self.assertEqual(m.session.meso,12)

    def test_resized_meso_is_not_counted_twice(self):
        m=Model();m.feed(packet(m));m.toggle(1.1)
        m.feed(packet(m,at=2,lines=[(100,790,'meso',14)]))
        m.feed(packet(m,at=3,lines=[(300,790,'meso',14)],resized=True))
        self.assertEqual(m.session.meso,0)

    def test_stale_reading_cannot_start(self):
        m=Model();m.feed(packet(m))
        with self.assertRaises(ValueError):m.toggle(10)
        self.assertFalse(m.session.running)

    def test_pausing_does_not_add_off_session_experience(self):
        m=Model();m.feed(packet(m,at=1));m.toggle(1.1);m.feed(packet(m,143619,at=2))
        m.toggle(2.1);m.feed(packet(m,144000,at=3));m.toggle(3.1);m.feed(packet(m,144050,at=4))
        self.assertEqual(m.session.gained,150)

    def test_old_capture_timestamp_rejected(self):
        m=Model();m.feed(packet(m));m.toggle(1.1)
        self.assertFalse(m.feed(packet(m,143600,at=1)))

    def test_reset_with_stale_capture_stops(self):
        m=Model();m.feed(packet(m));m.toggle(1.1);m.reset(20)
        self.assertFalse(m.session.running)

    def test_crop_percent_tracks_retina_resolution(self):
        for size,expected in [((800,600),(720,540)),((1600,1200),(1440,1080))]:
            self.assertEqual(crop_frame(Image.new('RGB',size),(5,10,5,0)).size,expected)

    def test_crop_rejects_tiny_game_area(self):
        with self.assertRaises(ValueError):crop_frame(Image.new('RGB',(300,300)),(30,30,30,30))


class MeterTests(unittest.TestCase):
    def test_hour_projection_and_percent(self):
        m=Model();m.feed(packet(m));m.toggle(1.1);m.feed(packet(m,144119,at=61.1))
        self.assertEqual(m.session.stats(61.1)['exp_hour'],36000)
        self.assertAlmostEqual(m.session.stats(61.1,True)['exp_total'],600*100/exp_for_level(47))

    def test_level_up(self):
        s=Session();s.start(0,Reading(*value(exp_for_level(47)-50),47))
        s.feed(1,Reading(*value(100,48),48));self.assertEqual(s.gained,150)

    def test_reject_bad_percentage(self):
        s=Session();s.start(0,Reading(*value(143519),47))
        self.assertFalse(s.feed(1,Reading(14519,25.83,47)));self.assertEqual(s.gained,0)

    def test_shortcuts_are_distinct_and_mac_codes(self):
        self.assertEqual(len({parse(v) for v in DEFAULT_KEYS.values()}),5)
        self.assertEqual(parse('Ctrl+Alt+R'),(15,6144))
        self.assertEqual(parse('Cmd+E'),(14,256))

    def test_invalid_shortcut_rejected(self):
        for value_ in ('R','Shift+R','Ctrl+F12','Ctrl+Space','Meta+E'):
            with self.assertRaises(ValueError):parse(value_)

    def test_format_units(self):
        self.assertEqual(format_value('exp_total',1.25,True),'1.2500%')
        self.assertEqual(format_value('meso_hour',12500,True),'12,500')
        self.assertEqual(format_value('elapsed',3661),'01:01:01')


if __name__=='__main__':unittest.main()
