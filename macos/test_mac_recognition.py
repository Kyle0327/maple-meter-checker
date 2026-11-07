import unittest
import numpy as np
from PIL import Image
from reader import G,bitmap,exp_for_level
from mac_recognition import MacHudReader,hud_preview


def fixture():
    image=Image.new('RGB',(1000,720),(25,40,60))
    n=143519;pct=int(n*10000/exp_for_level(47))/100
    x=680;y=690
    for char in f'{n}    {pct:.2f}%':
        if char==' ':x+=2;continue
        glyph=bitmap(G[char]);pixels=np.zeros((*glyph.shape,3),dtype=np.uint8)
        pixels[:]=[25,40,60];pixels[glyph]=255
        image.paste(Image.fromarray(pixels),(x,y));x+=glyph.shape[1]+1
    return image,(n,pct)


class MacRecognitionTests(unittest.TestCase):
    def test_title_bar_and_retina_do_not_change_exp(self):
        source,expected=fixture()
        for scale,title in ((1,28),(2,56),(1.5,42),(1.25,35)):
            with self.subTest(scale=scale):
                game=source.resize((round(source.width*scale),round(source.height*scale)),Image.Resampling.BILINEAR)
                capture=Image.new('RGB',(game.width,game.height+title),(60,60,60));capture.paste(game,(0,title))
                reader=MacHudReader();value=None
                for _ in range(8):
                    value=reader.read_image(capture)
                    if value:break
                self.assertEqual(value,expected)
                self.assertEqual(reader.read_image(capture),expected)

    def test_blank_frame_never_invents_a_reading(self):
        reader=MacHudReader()
        for _ in range(8):self.assertIsNone(reader.read_image(Image.new('RGB',(800,628))))

    def test_preview_only_contains_bottom_area(self):
        image,_=fixture();self.assertEqual(hud_preview(image).size,(1000,158))
