import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw,ImageFont
from mac_vision import parse_exp_line,text_rows,VisionReader,recognize
from mac_recognition import MacHudReader


class VisionParsingTests(unittest.TestCase):
    def test_photo_reading_and_punctuation_variants(self):
        for text in ('EXP. 413,056[63.04%]','HP 2224/2224 MP 896/896 EXP 413056 (63.04%)',
                     'EXP: 413.056 [63,04%]','EXP 413056 63.04%'):
            with self.subTest(text=text):self.assertEqual(parse_exp_line(text),(413056,63.04))

    def test_inconsistent_and_unrelated_numbers_are_rejected(self):
        for text in ('MESOS 413,056 [63.04%]','413056 [63.04%]','EXP 413056 [99.99%]',
                     'EXP 413056 [100.00%]','EXP 413O56 [63.04%]','EXP 0 [0.00%]'):
            with self.subTest(text=text):self.assertIsNone(parse_exp_line(text))

    def test_split_ocr_boxes_join_but_chat_and_low_confidence_do_not(self):
        rows=text_rows([('EXP.',.9,(.60,.10,.04,.08)),('413,056',.9,(.65,.10,.09,.08)),
            ('[63.04%]',.9,(.75,.10,.10,.08)),('EXP 413056 [63.04%]',.9,(.2,.8,.3,.08)),
            ('1234',.1,(.1,.1,.1,.08))])
        self.assertEqual(len(rows),1);self.assertEqual(parse_exp_line(rows[0]),(413056,63.04))

    def test_confirmation_requires_two_fresh_frames(self):
        r=VisionReader();value=(413056,63.04)
        self.assertIsNone(r.confirm(value,0));self.assertEqual(r.confirm(value,1),value)
        self.assertIsNone(r.confirm(None,2));self.assertIsNone(r.confirm(value,3))
        self.assertIsNone(r.confirm(value,10))

    def test_live_changing_numbers_are_read_from_each_new_frame(self):
        r=VisionReader();image=Image.new('RGB',(800,600))
        frames=[[(text,.95,(.6,.1,.3,.1))] for text in
            ('EXP 413056 [63.04%]','EXP 413156 [63.05%]','EXP 414000 [63.18%]')]
        with patch('mac_vision.recognize',side_effect=frames),patch('mac_vision.time.monotonic',side_effect=[1,2,3]):
            self.assertIsNone(r.read(image))
            self.assertEqual(r.read(image),(413156,63.05))
            self.assertEqual(r.read(image),(414000,63.18))

    def test_fallback_runs_after_bitmap_failure_and_discards_on_resize(self):
        r=MacHudReader(vision=True);image=Image.new('RGB',(800,600));r.size=image.size
        with patch.object(r,'read_bitmap',return_value=None),patch.object(r.vision,'read',return_value=(413056,63.04)):
            self.assertEqual(r.read_image(image),(413056,63.04));self.assertEqual(r.source,'Apple 문자 인식')
        previous=r.vision
        with patch('mac_vision.recognize',return_value=[]):r.read_image(Image.new('RGB',(801,600)))
        self.assertIsNot(r.vision,previous)


@unittest.skipUnless(sys.platform=='darwin','Apple Vision requires macOS')
class NativeVisionTests(unittest.TestCase):
    def test_native_ocr_reads_non_bitmap_font_with_black_margins(self):
        # Independent of the Windows bitmap glyph templates, matching the
        # reported level-49 EXP values. No user photo is uploaded to CI.
        image=Image.new('RGB',(1600,1000),(5,5,5))
        draw=ImageDraw.Draw(image)
        draw.rectangle((260,880,1340,999),fill=(35,50,65))
        font=ImageFont.truetype(str(Path(__file__).with_name('Pretendard-Bold.otf')),30)
        for number,percentage in ((413056,63.04),(414000,63.18)):
            with self.subTest(number=number):
                draw.rectangle((260,880,1340,999),fill=(35,50,65))
                draw.text((800,945),f'EXP. {number:,} [{percentage:.2f}%]',font=font,fill='white',stroke_width=1,stroke_fill='black')
                records=recognize(image)
                values=[parse_exp_line(row) for row in text_rows(records)]
                self.assertIn((number,percentage),values,records)
