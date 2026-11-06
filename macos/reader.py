"""Screen-only reader for the MapleStory Classic World bitmap HUD.

Glyphs originate from the user-supplied meter. Capture, scale search and validation
are separate from the UI, so recognition can be reproduced with image fixtures.
"""
import json
from pathlib import Path
import re
import time
import numpy as np
from PIL import Image

GLYPHS = json.loads(Path(__file__).with_name('glyphs.json').read_text())
G = dict(zip('0123456789/.%,', GLYPHS[:14]))
def bitmap(s):
    return np.array([[v == '#' for v in row] for row in s.split()], dtype=bool)
def trim(a):
    cols = np.flatnonzero(a.any(axis=0))
    return a[:, cols[0]:cols[-1]+1]
T = [(ch, trim(bitmap(s))) for ch, s in G.items()]
PAD = {ch: (min(row.find('#') for row in s.split() if '#' in row),
            min(len(row)-1-row.rfind('#') for row in s.split() if '#' in row)) for ch,s in G.items()}

def ink(a, threshold=180):
    a = a.astype(np.int16)
    return (a.min(axis=2) >= threshold) & (a.max(axis=2)-a.min(axis=2) < 65)

def decode(band):
    width = band.shape[1]
    col = band.any(axis=0)
    out, c, last, prev = '', 0, -1, None
    while c < width:
        if not col[c]:
            c += 1
            continue
        e = c
        while e+1 < width and col[e+1]:
            e += 1
        if e-c > 40:
            c = e+1
            continue
        blob = band[:,c:e+1]
        bw, i, covered, got = e-c+1, 0, 0, []
        while i < bw:
            pick = None
            for ch,t in T:
                tw = t.shape[1]
                if tw > bw-i:
                    continue
                d = int(np.count_nonzero(blob[:,i:i+tw] != t))
                if d <= max(1, int(tw*7*.08)) and (pick is None or (d,-tw)<(pick[2],-pick[1])):
                    pick = ch,tw,d
            if pick is None:
                i += 1
                continue
            got.append((c+i,pick[0],pick[1]))
            covered += pick[1]
            i += pick[1]
        if got and covered >= bw-1:
            for at,ch,w in got:
                if last>=0 and at-last-PAD[prev][1]-PAD[ch][0]>3 and out and not out.endswith('['):
                    out += '['
                out += ch
                last,prev = at+w,ch
        c=e+1
    return out

def parse_exp(text):
    text = re.sub(r'\[?,\[?', ',', text)
    # Thousands separators can appear as a dot when the comma descender is dim.
    matches = re.findall(r'(?<![\d.,])(\d{1,3}(?:[,.]\d{3})+|\d+)\[(\d{1,3}\.\d{1,2})%', text)
    if not matches:
        return None
    n,pct = matches[-1]
    n,pct = int(n.replace(',','').replace('.','')),float(pct)
    if 0<=pct<100 and 0<=n<10**12:
        return n,pct

def read_hud(a, fixed=None):
    h,w=a.shape[:2]
    candidates = [fixed] if fixed is not None else range(max(0,h-95),h-6)
    for threshold in (165,155,180,195):
        m=ink(a,threshold)
        for top in candidates:
            if top<0 or top+7>h:
                continue
            band=m[top:top+7]
            if band.sum()<20:
                continue
            text=decode(band)
            value=parse_exp(text)
            if value and (infer_level(*value) is not None or value[1]<.5):
                return value,top,text
    return None

CELLS={ch:(np.pad(bitmap(s),((0,0),(1,2))) if ch=='1' else bitmap(s)) for ch,s in zip('0123456789',GLYPHS[14:24])}
PLUS=bitmap(GLYPHS[24])
CLOSE=bitmap(GLYPHS[25])
OPEN=CLOSE[:,::-1]
LETTER_M=bitmap('#.......# ##.....## ##.....## #.#...#.# #.#...#.# #..#.#..# #..#.#..# #...#...# #...#...# #.......#')
LETTER_E=bitmap('####### #...... #...... #...... #...... ######. #...... #...... #...... #######')

def pick_mask(a):
    a=a.astype(np.int16)
    lum=a.mean(axis=2)
    c=(a.max(axis=2)-a.min(axis=2)<=35)&(lum>=130)
    end=np.zeros_like(c)
    end[:-1,:-1]=c[:-1,:-1]&((lum[1:,1:]<=50)|(lum[:-1,:-1]-lum[1:,1:]>=100))
    ok=end
    for _ in range(16):
        nxt=end.copy()
        nxt[:-1,:-1]|=c[:-1,:-1]&ok[1:,1:]
        if np.array_equal(nxt,ok):
            break
        ok=nxt
    return ok

def fit(w,t):
    return float((w&t).sum())/max(1,int(t.sum())),int((w&~t).sum())

def stem(b,x):
    return x>=2 and int(b[:10,max(0,x-2):x+3].sum(axis=0).max())>=8

def pickup_line(b,x):
    for n in range(1,9):
        xp=x-6*(n+1)
        if xp-5-125<0:
            return None
        hit,extra=fit(b[3:8,xp:xp+5],PLUS)
        if hit<.75 or extra>6:
            continue
        hit,extra=fit(b[:,xp-5:xp-2],OPEN)
        if hit<.75 or extra>6:
            continue
        digits=''
        for k in range(n,0,-1):
            cell=b[:10,x-6*k:x-6*k+5]
            scores=[]
            for ch,t in CELLS.items():
                hit,extra=fit(cell,t)
                scores.append((hit-.04*extra,ch,hit,extra))
            best=max(scores)
            if best[2]<.8 or best[3]>9:
                digits=''
                break
            digits+=best[1]
        if not digits:
            continue
        o=xp-5
        mh,me=fit(b[:10,o-119:o-110],LETTER_M)
        eh,ee=fit(b[:10,o-104:o-97],LETTER_E)
        if mh>=.85 and me<=12:
            return 'meso',int(digits)
        if eh>=.85 and ee<=10:
            return 'exp',int(digits)
    return None

def contrast_masks(t):
    on=np.pad(t,((0,1),(0,1)))
    shadow=np.pad(t,((1,0),(1,0)))&~on
    return on,shadow

CONTRAST={id(t):contrast_masks(t) for t in [CLOSE,OPEN,PLUS,LETTER_M,LETTER_E,*CELLS.values()]}

def contrast(lum,y,x,t):
    on,shadow=CONTRAST[id(t)]
    h,w=on.shape
    if y<0 or x<0 or y+h>lum.shape[0] or x+w>lum.shape[1]:
        return -255.
    patch=lum[y:y+h,x:x+w]
    return float(patch[on].mean()-patch[shadow].mean())

def read_pickups(a, threshold=None, details=False):
    """Correlate white glyphs AND their dark shadows, independent of background.

    Plain white thresholding turns clouds and shop bubbles into extra strokes.
    Paired foreground/shadow contrast also works as the messages fade.
    """
    lum=a.mean(axis=2).astype(np.float32)
    H,W=lum.shape
    if H<12 or W<150:return ([],0) if details else []
    on,shadow=CONTRAST[id(CLOSE)]
    h,w=H-on.shape[0]+1,W-on.shape[1]+1
    # The system pickup feed is right aligned. Keep a little margin for themes.
    x0=max(140,w-35)
    score=np.zeros((h,w-x0),np.float32)
    for r,c in zip(*np.nonzero(on)):
        score+=lum[r:r+h,x0+c:w+c]/on.sum()
    for r,c in zip(*np.nonzero(shadow)):
        score-=lum[r:r+h,x0+c:w+c]/shadow.sum()
    ys,xs=np.nonzero(score>85)
    candidates=sorted(zip(ys.tolist(),(xs+x0).tolist()),key=lambda p:-score[p[0],p[1]-x0])
    out=[];strengths=[]
    for y,x in candidates:
        if any(abs(y-oy)<7 for oy,_,_,_ in out):continue
        for n in range(1,9):
            xp=x-6*(n+1);o=xp-5
            plus=contrast(lum,y+3,xp,PLUS)
            opening=contrast(lum,y,o,OPEN)
            if min(plus,opening)<85:continue
            meso=contrast(lum,y,o-119,LETTER_M)
            exp=contrast(lum,y,o-104,LETTER_E)
            if meso>95 and meso>exp+30:kind='meso'
            elif exp>95 and exp>meso+30:kind='exp'
            else:continue
            digits='';strength=min(plus,opening,max(meso,exp))
            for k in range(n,0,-1):
                scores=sorted([(contrast(lum,y,x-6*k,t),ch) for ch,t in CELLS.items()],reverse=True)
                # Reject ambiguous digits rather than silently inventing income.
                if scores[0][0]<90 or scores[0][0]-scores[1][0]<10:
                    digits='';break
                digits+=scores[0][1]
                strength=min(strength,scores[0][0])
            if digits:
                out.append((y,x,kind,int(digits)));strengths.append(strength);break
    return (sorted(out),sum(strengths)/len(strengths) if strengths else 0) if details else sorted(out)

def exp_for_level(level):
    if not 1<=level<200:
        return 0
    if level<=5:
        return (level*level//2+15)*level
    if level<=50:
        n=level*level//3
        return (n+19)*n
    n=exp_for_level(50)
    for _ in range(51,level+1):
        n=int(n*1.0548)
    return n

def infer_level(n,pct):
    if pct<.5 or n<=0:
        return None
    need=n*100/pct
    lv=min(range(1,200),key=lambda x:abs(exp_for_level(x)-need)/exp_for_level(x))
    # Require agreement at the displayed two-decimal precision, not a 3% guess.
    return lv if abs(n*100/exp_for_level(lv)-pct)<=.016 else None

def undo_axis(a, n, axis):
    """Least-squares inversion of the client's bilinear screen enlargement."""
    a=np.moveaxis(a,axis,0).astype(np.float32)
    m=a.shape[0]
    if m==n:
        return np.moveaxis(a,0,axis)
    u=(np.arange(m)+.5)*n/m-.5
    u=np.clip(u,0,n-1)
    left=np.floor(u).astype(int)
    right=np.minimum(left+1,n-1)
    t=(u-left).astype(np.float32)
    lo,hi=1-t,t
    diag=np.zeros(n,np.float32)
    upper=np.zeros(n,np.float32)
    rhs=np.zeros((n,)+a.shape[1:],np.float32)
    np.add.at(diag,left,lo*lo)
    np.add.at(diag,right,hi*hi)
    np.add.at(upper,left,lo*hi)
    np.add.at(rhs,left,a*lo.reshape((-1,)+(1,)*(a.ndim-1)))
    np.add.at(rhs,right,a*hi.reshape((-1,)+(1,)*(a.ndim-1)))
    for i in range(1,n):
        factor=upper[i-1]/max(diag[i-1],1e-6)
        diag[i]-=factor*upper[i-1]
        rhs[i]-=factor*rhs[i-1]
    rhs[-1]/=max(diag[-1],1e-6)
    for i in range(n-2,-1,-1):
        rhs[i]=(rhs[i]-upper[i]*rhs[i+1])/max(diag[i],1e-6)
    return np.moveaxis(rhs,0,axis)

def normalize(image,size):
    if image.size==size:
        return np.asarray(image)
    if size[0]<=image.width and size[1]<=image.height:
        a=undo_axis(np.asarray(image),size[0],1)
        a=undo_axis(a,size[1],0)
        return np.clip(a+.5,0,255).astype(np.uint8)
    return np.asarray(image.resize(size,Image.Resampling.LANCZOS))

class Reader:
    def __init__(self):
        self.scale=None
        self.row=None
        self.size=None
        self.last_text=''
        self.crop=None

    def read_image(self,image):
        w,h=image.size
        if self.size!=(w,h):
            self.scale=self.row=None
            self.crop=None
            self.size=(w,h)
        if self.scale:
            a=normalize(image.crop(self.crop) if self.crop else image,self.scale)
            result=read_hud(a,self.row)
            if result:
                self.last_text=result[2]
                return result[0],self.pickup_image(image,a)
        # Search windowed upscaling as well as full screen. Original only tried
        # alternate game sizes when the client rectangle filled a monitor.
        views=[]
        for native_h in (768,720,600,900,1080,h):
            cw=round(800*h/native_h)
            if cw>w:continue
            left=round((w-cw)/2)
            views.append(((800,native_h),(left,0,left+cw,h)))
        views.append(((w,h),None))
        for size,crop in views:
            a=normalize(image.crop(crop) if crop else image,size)
            result=read_hud(a)
            if result:
                self.scale,self.row,self.last_text=size,result[1],result[2]
                self.crop=crop
                return result[0],self.pickup_image(image,a)
        return None,None

    def pickup_image(self,image,hud):
        if not self.crop:return hud
        cw=self.crop[2]-self.crop[0]
        return normalize(image.crop((image.width-cw,0,image.width,image.height)),self.scale)

class PickupReader:
    """Calibrate pickup font separately from HUD and window dimensions.

    Resolution changes can leave the HUD scaled and the pickup font at 1:1, or
    stretch both differently. Never reuse a HUD scale as a mandatory pickup
    scale. A valid prefix, parentheses, plus and unambiguous digits must agree.
    """
    def __init__(self):
        self.factor=None;self.size=None;self.changed=False
        self.scan_index=0;self.last_rescan=0;self.prior=[]

    def at_scale(self,image,factor):
        width=min(image.width,round(280*factor))
        target=(max(1,round(width/factor)),max(1,round(image.height/factor)))
        if target[0]<150 or target[1]>3000:return [],0
        a=normalize(image.crop((image.width-width,0,image.width,image.height)),target)
        top=int(len(a)*.32)
        lines,score=read_pickups(a[top:int(len(a)*.98)],details=True)
        return [(y+top,x,k,v) for y,x,k,v in lines],score

    def read(self,image,hint=None,exhaustive=False):
        w,h=image.size
        self.changed=self.size is not None and self.size!=image.size
        if self.changed:
            self.prior=[self.factor,self.factor*h/self.size[1]] if self.factor else []
            self.factor=None;self.scan_index=0;self.last_rescan=0
        self.size=image.size
        if self.factor:
            lines,confidence=self.at_scale(image,self.factor)
            if lines:return lines
        now=time.monotonic()
        # A quiet screen is normal. Do a bounded search every second, keeping
        # the UI responsive while no pickup messages are present.
        if not exhaustive and self.factor and now-self.last_rescan<1:return []
        self.last_rescan=now
        seeds=[hint,1.0,*self.prior,h/768,h/720,h/600,h/900,h/1080,h/1050,
               1.25,1.5,1.75,2.0,2.5,3.0,.875]
        bank=[]
        for factor in seeds:
            if factor and .7<=factor<=4.5 and all(abs(factor-x)>.002 for x in bank):bank.append(factor)
        if exhaustive:
            candidates=bank
        else:
            candidates=[bank[(self.scan_index+i)%len(bank)] for i in range(min(5,len(bank)))]
            self.scan_index=(self.scan_index+5)%len(bank)
        best=(0,None,[])
        for factor in candidates:
            if factor==self.factor:continue
            lines,score=self.at_scale(image,factor)
            if lines and score>best[0]:best=score,factor,lines
        if best[1] is not None:
            self.factor=best[1];return best[2]
        return []
