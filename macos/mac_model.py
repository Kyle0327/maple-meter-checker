"""Session boundaries shared by the asynchronous macOS capture and UI."""
from session import Session, Reading, PickupCounter
from reader import infer_level


def crop_frame(image, edges):
    left,top,right,bottom=edges
    w,h=image.size
    box=(round(w*left/100),round(h*top/100),round(w*(1-right/100)),round(h*(1-bottom/100)))
    if box[2]-box[0]<200 or box[3]-box[1]<200:
        raise ValueError('게임 영역이 너무 작습니다. 여백 값을 줄여 주세요.')
    return image.crop(box)


class Model:
    def __init__(self):
        self.session=Session();self.pickups=PickupCounter();self.reading=None
        self.generation=0;self.last_good=0;self.after=0

    def invalidate(self):
        self.generation+=1;self.reading=None;self.last_good=0;self.pickups=PickupCounter()

    def feed(self, packet):
        if packet['generation']!=self.generation or packet['at']<self.after:return False
        at=packet['at'];value=packet['value']
        if value:
            n,pct=value
            level=infer_level(n,pct) or (self.reading.level if self.reading else None)
            self.reading=Reading(n,pct,level);self.last_good=at
            self.session.feed(at,self.reading)
        if packet.get('resized'):
            self.pickups.rebaseline(packet['lines'],at);amount=0
            seen=any(row[2]=='meso' for row in packet['lines'])
        else:amount,seen=self.pickups.feed(packet['lines'],at,self.session.running)
        self.session.meso+=amount
        if seen:self.session.meso_seen=True
        return True

    def toggle(self, now):
        self.generation+=1;self.after=now
        if self.session.running:self.session.pause(now);return
        if self.reading is None or self.reading.level is None or now-self.last_good>3:
            raise ValueError('최근 경험치가 정상 인식된 뒤 시작할 수 있습니다.')
        self.pickups=PickupCounter()
        self.session.start(now,self.reading)

    def reset(self, now):
        running=self.session.running and self.reading is not None and now-self.last_good<3
        self.generation+=1;self.after=now;self.session=Session();self.pickups=PickupCounter()
        if running:self.session.start(now,self.reading)
