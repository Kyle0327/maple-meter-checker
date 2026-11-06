"""Deterministic counters; no screen or UI dependencies."""
from collections import deque
from dataclasses import dataclass
from reader import exp_for_level, infer_level

@dataclass(frozen=True)
class Reading:
    exp: int
    percent: float
    level: int | None

class Session:
    def __init__(self):
        self.running=False
        self.started=False
        self.seconds=0.0
        self.clock=None
        self.current=None
        self.gained=0
        self.percent_gained=0.0
        self.meso=0
        self.meso_seen=False
        self.history=deque([(0.0,0)])
        self.warning=''
        self.levels=0

    def elapsed(self,now):
        return self.seconds+(max(0,now-self.clock) if self.running else 0)

    def start(self,now,reading):
        self.current=reading
        self.started=True
        self.running=True
        self.clock=now
        self.history.append((self.seconds,self.gained))

    def pause(self,now):
        if self.running:
            self.seconds=self.elapsed(now)
        self.clock=None
        self.running=False

    def feed(self,now,reading):
        if not self.running or self.current is None:
            self.current=reading
            return False
        old=self.current
        lv=reading.level or old.level
        if lv is None:
            self.warning='레벨 확인 대기 · 경험치를 더 얻으면 다시 확인합니다'
            return False
        need=exp_for_level(lv)
        if not need or abs(reading.exp*100/need-reading.percent)>.016:
            self.warning='숫자·퍼센트 불일치 · 이번 값 제외'
            return False
        old_lv=old.level or lv
        if not old_lv<=lv<=old_lv+3:
            self.warning='레벨 변경 확인 필요 · 새 측정을 시작하세요'
            return False
        delta=reading.exp-old.exp
        if lv>old_lv:
            delta+=sum(exp_for_level(x) for x in range(old_lv,lv))
        elif delta < -need*.2:
            self.warning='큰 경험치 감소 · 확인 전 반영 보류'
            return False
        self.current=Reading(reading.exp,reading.percent,lv)
        self.gained+=delta
        self.percent_gained+=100*(lv-old_lv)+reading.exp*100/need-old.exp*100/exp_for_level(old_lv)
        self.levels+=lv-old_lv
        self.warning=''
        t=self.elapsed(now)
        self.history.append((t,self.gained))
        while len(self.history)>2 and self.history[1][0]<t-60:
            self.history.popleft()
        return True

    def level_eta(self,now):
        """Seconds to next level at the measured net EXP/sec, not percent/sec."""
        elapsed=self.elapsed(now)
        reading=self.current
        if not self.started or self.warning or elapsed<1 or self.gained<=0 or reading is None:
            return None
        if reading.level is None or not 1<=reading.level<200:
            return None
        needed=exp_for_level(reading.level)
        if not 0<=reading.exp<needed or abs(reading.exp*100/needed-reading.percent)>.016:
            return None
        return (needed-reading.exp)*elapsed/self.gained

    def stats(self,now,percent=False):
        elapsed=self.elapsed(now)
        total=self.percent_gained if percent else self.gained
        rate=total*60/elapsed if elapsed>=1 else None
        target=max(0,elapsed-60)
        points=list(self.history)
        baseline=points[0][1]
        for (ta,va),(tb,vb) in zip(points,points[1:]):
            if ta<=target<=tb and tb>ta:
                baseline=va+(vb-va)*(target-ta)/(tb-ta)
                break
            if tb<=target:
                baseline=vb
        recent=self.gained-baseline
        meso_min=self.meso*60/elapsed if elapsed>=1 and self.meso_seen else None
        return {'elapsed':elapsed,'level_eta':self.level_eta(now),'exp_total':total,'exp_min':rate,
                'exp_30min':None if rate is None else rate*30,
                'exp_hour':None if rate is None else rate*60,
                'exp_recent':recent if elapsed>=60 else None,
                'meso_total':self.meso if self.meso_seen else None,
                'meso_min':meso_min,'meso_30min':None if meso_min is None else meso_min*30,
                'meso_hour':None if meso_min is None else meso_min*60}

class PickupCounter:
    """Align visible message rows. Uncertain discontinuities never become income."""
    def __init__(self):
        self.previous=[]
        self.last_seen=None
        self.ready=False
        self.uncertain=False
        self.recent={}

    def rebaseline(self,lines,now):
        self.previous=list(lines);self.last_seen=now;self.ready=True
        for _,_,k,v in lines:self.recent[(k,v)]=now

    def feed(self,lines,now,counting):
        # (y,x,kind,value); x varies with digit count, so identity is kind/value.
        lines=list(lines)
        if not lines:
            if self.last_seen is not None and now-self.last_seen>5:
                self.previous=[]
            self.ready=True
            return 0,False
        self.last_seen=now
        self.recent={key:t for key,t in self.recent.items() if now-t<6}
        new=[]
        if not self.ready:
            self.ready=True
        elif not self.previous:
            new=[line for line in lines if (line[2],line[3]) not in self.recent]
        else:
            # Monotone one-to-one match. Favor the least shift to avoid counting
            # a stationary list containing multiple identical amounts again.
            candidates=[]
            for shift in range(0,15):
                dy=shift*14
                matches=[]
                used=set()
                for i,(y,x,k,v) in enumerate(lines):
                    for j,(py,px,pk,pv) in enumerate(self.previous):
                        if j not in used and (k,v)==(pk,pv) and abs(py-dy-y)<=2:
                            used.add(j);matches.append(i);break
                if matches:
                    candidates.append((len(matches),-shift,matches))
            if candidates:
                growth=max(0,len(lines)-len(self.previous))
                _,_,matched=max(candidates,key=lambda x:(x[0],-abs(-x[1]-growth),x[1]))
                new=lines[max(matched)+1:]
            else:
                # Without an overlapping line, missing frames and a completely
                # new batch cannot be distinguished. Rebaseline and disclose.
                self.uncertain=True
                new=[line for line in lines if (line[2],line[3]) not in self.recent]
        self.previous=lines
        for _,_,k,v in lines:self.recent[(k,v)]=now
        amount=sum(v for _,_,k,v in new if k=='meso') if counting else 0
        seen=any(k=='meso' for _,_,k,_ in lines)
        return amount,seen
