"""Read the HUD at its pixel scale, independent of macOS window decorations."""
from reader import normalize, read_hud
from mac_vision import VisionReader


class MacHudReader:
    def __init__(self,vision=False):
        self.factor=None;self.row=None;self.size=None;self.last_text='';self.scan_index=0;self.anchor='center'
        self.vision=VisionReader() if vision else None;self.source='';self.note=''
        self.prefer_vision=False

    def sample(self,image,factor,anchor='center'):
        # Bottom anchoring keeps title bars and unrelated top padding out of
        # scale estimation. Use an exact 800-pixel HUD width instead of rounding
        # the entire window width, which shifts the bitmap glyph sampling grid.
        height=min(image.height,round(110*factor))
        width=min(image.width,round(800*factor))
        left=round((image.width-width)/2) if anchor=='center' else image.width-width
        strip=image.crop((left,image.height-height,left+width,image.height))
        size=(max(1,round(strip.width/factor)),max(7,round(strip.height/factor)))
        return normalize(strip,size)

    def read_bitmap(self,image):
        if self.size!=image.size:
            self.factor=self.row=None;self.scan_index=0;self.size=image.size
        if self.factor:
            result=read_hud(self.sample(image,self.factor,self.anchor),self.row)
            if result:
                self.last_text=result[2];return result[0]
        # Fixed pixel factors work even when a 28-point title bar changes the
        # capture height. Include game-height ratios for stretched game clients.
        bank=[1.,2.,1.5,1.25,1.75,2.5,3.,.75]
        for native in (768,720,600,900,1080):
            for title in (0,28,56):
                factor=(image.height-title)/native
                if .7<=factor<=4 and all(abs(factor-x)>.003 for x in bank):bank.append(factor)
        # Bound work per frame when the game is blank or the HUD is hidden.
        budget=1 if self.vision else 4
        candidates=[bank[(self.scan_index+i)%len(bank)] for i in range(min(budget,len(bank)))]
        self.scan_index=(self.scan_index+budget)%len(bank)
        for factor in candidates:
            for anchor in ('center','right') if image.width>round(800*factor) else ('center',):
                result=read_hud(self.sample(image,factor,anchor))
                if result:
                    self.factor,self.row,self.last_text=factor,result[1],result[2]
                    self.anchor=anchor
                    return result[0]
        return None

    def read_image(self,image):
        self.source=''
        if self.size!=image.size and self.vision:
            self.vision=VisionReader();self.prefer_vision=False
        if self.prefer_vision:return self.read_vision(image)
        value=self.read_bitmap(image)
        if value:
            self.source='글자 패턴';self.note=''
            if self.vision:self.vision.pending=None
            return value
        if self.vision:return self.read_vision(image)
        return None

    def read_vision(self,image):
        if self.vision:
            try:
                value=self.vision.read(image);self.note=self.vision.note
                if value:self.source='Apple 문자 인식';self.prefer_vision=True
                return value
            except Exception as error:self.note=f'Apple 문자 인식: {error}'
        return None


def hud_preview(image):
    """Return just the bottom HUD area; never persist a captured frame."""
    return image.crop((0,max(0,image.height-round(image.height*.22)),image.width,image.height))
