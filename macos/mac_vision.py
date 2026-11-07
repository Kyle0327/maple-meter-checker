"""On-device Apple Vision fallback for the EXP HUD; no screen uploads."""
import io
import re
import time
from reader import infer_level

PATTERN=re.compile(r'\bEXP[\s.:]*([0-9]{1,3}(?:[,.][0-9]{3})+|[0-9]+)(?:\s*[\[(]\s*|\s+)([0-9]{1,2}[.,][0-9]{1,2})\s*%',re.I)


def parse_exp_line(text):
    values=set()
    for number,percentage in PATTERN.findall(text):
        value=(int(number.replace(',','').replace('.','')),float(percentage.replace(',','.')))
        if value[0]<10**12 and 0<value[1]<100 and infer_level(*value) is not None:values.add(value)
    return values.pop() if len(values)==1 else None


def text_rows(records):
    """Join only neighboring OCR boxes on the same HUD baseline."""
    rows=[]
    for text,confidence,box in sorted(records,key=lambda item:item[2][0]):
        if confidence<.35:continue
        x,y,w,h=box
        # The lower half of our bottom strip contains the HUD, not trade chat.
        if y>.55:continue
        center=y+h/2
        for row in rows:
            if abs(center-row['center'])<=max(h,row['height'])*.55 and x-row['end']<.15:
                row['text']+=' '+text;row['end']=x+w;break
        else:rows.append(dict(text=text,center=center,height=h,end=x+w))
    return [row['text'] for row in rows]


class VisionReader:
    def __init__(self):self.pending=None;self.last_attempt=-float('inf');self.note=''

    def confirm(self,value,now):
        old=self.pending;self.pending=(value,now) if value else None
        if value is None or old is None or now-old[1]>5:return None
        old_level=infer_level(*old[0]);level=infer_level(*value)
        if level==old_level or (level==old_level+1 and old[0][1]>80 and value[1]<20):return value
        return None

    def read(self,image):
        now=time.monotonic()
        if now-self.last_attempt<.8:return None
        self.last_attempt=now
        records=recognize(image)
        rows=text_rows(records)
        candidates={value for row in rows if (value:=parse_exp_line(row)) is not None}
        value=next(iter(candidates)) if len(candidates)==1 else None
        self.note=' / '.join(row for row in rows if 'exp' in row.lower())[:140] or '하단 EXP 문구를 찾는 중'
        return self.confirm(value,now)


def recognize(image):
    import objc
    import Foundation
    import Vision
    from PIL import Image
    height=min(image.height,max(100,round(image.height*.18)))
    strip=image.crop((0,image.height-height,image.width,image.height))
    # Enlarge tiny bitmap text for Vision while bounding memory on Retina.
    scale=min(3.,4096/strip.width)
    if scale>1:strip=strip.resize((round(strip.width*scale),round(strip.height*scale)),Image.Resampling.LANCZOS)
    stream=io.BytesIO();strip.save(stream,format='PNG');data=stream.getvalue()
    with objc.autorelease_pool():
        request=Vision.VNRecognizeTextRequest.alloc().init()
        request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        request.setUsesLanguageCorrection_(False)
        request.setRecognitionLanguages_(['en-US'])
        request.setMinimumTextHeight_(.005)
        nsdata=Foundation.NSData.dataWithBytes_length_(data,len(data))
        handler=Vision.VNImageRequestHandler.alloc().initWithData_options_(nsdata,{})
        ok,error=handler.performRequests_error_([request],None)
        if not ok:raise RuntimeError(str(error.localizedDescription()) if error else 'Apple 문자 인식 실패')
        records=[]
        for observation in request.results() or []:
            choices=observation.topCandidates_(1)
            if not choices:continue
            candidate=choices[0];rect=observation.boundingBox()
            records.append((str(candidate.string()),float(candidate.confidence()),
                (float(rect.origin.x),float(rect.origin.y),float(rect.size.width),float(rect.size.height))))
        return records
