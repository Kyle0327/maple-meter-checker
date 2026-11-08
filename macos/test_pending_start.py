import unittest
from unittest.mock import patch
from PIL import Image
from mac_model import Model
from mac_recognition import MacHudReader
from test_mac import packet


class PendingStartTests(unittest.TestCase):
    def test_old_displayed_value_does_not_lock_out_new_start(self):
        m=Model();m.feed(packet(m,at=1));old=packet(m,143600,at=2)
        m.request_toggle(10)
        self.assertTrue(m.start_pending);self.assertFalse(m.session.running)
        self.assertFalse(m.feed(old))
        # Even if recognition finishes four seconds after capture, the frame
        # was captured after the click; measurement starts at capture time.
        self.assertTrue(m.feed(packet(m,143619,at=11)))
        self.assertTrue(m.session.running);self.assertFalse(m.start_pending)
        self.assertEqual(m.session.elapsed(15),4);self.assertEqual(m.session.gained,0)
        m.feed(packet(m,143719,at=16));self.assertEqual(m.session.gained,100)

    def test_no_exp_stays_pending_and_second_click_cancels(self):
        m=Model();m.request_toggle(10)
        p=packet(m,at=11);p['value']=None;m.feed(p)
        self.assertTrue(m.start_pending);self.assertFalse(m.session.running)
        late=packet(m,at=12);m.request_toggle(11.5)
        self.assertFalse(m.start_pending);self.assertFalse(m.feed(late));self.assertFalse(m.session.running)

    def test_reset_and_target_change_cancel_pending_start(self):
        for operation in (lambda m:m.reset(11),lambda m:m.invalidate()):
            m=Model();m.request_toggle(10);late=packet(m,at=10.5);operation(m)
            self.assertFalse(m.start_pending);self.assertFalse(m.feed(late));self.assertFalse(m.session.running)

    def test_start_baseline_does_not_count_old_pickups(self):
        m=Model();m.request_toggle(10)
        m.feed(packet(m,at=11,lines=[(100,790,'meso',14)]))
        self.assertEqual(m.session.meso,0)
        m.feed(packet(m,at=12,lines=[(86,790,'meso',14),(100,790,'meso',12)]))
        self.assertEqual(m.session.meso,12)

    def test_working_vision_reader_skips_expensive_bitmap_search(self):
        r=MacHudReader(vision=True);image=Image.new('RGB',(800,600));r.size=image.size;r.prefer_vision=True
        with patch.object(r,'read_bitmap') as bitmap,patch.object(r.vision,'read',return_value=(413056,63.04)):
            self.assertEqual(r.read_image(image),(413056,63.04));bitmap.assert_not_called()

    def test_vision_failure_never_reuses_old_success(self):
        r=MacHudReader(vision=True);image=Image.new('RGB',(800,600));r.size=image.size;r.prefer_vision=True
        with patch.object(r.vision,'read',side_effect=[(413056,63.04),None]):
            self.assertEqual(r.read_image(image),(413056,63.04));self.assertIsNone(r.read_image(image))
