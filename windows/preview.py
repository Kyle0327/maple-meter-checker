import tkinter as tk
from tkinter import font as tkfont
from theme import *
from presentation import METRICS,format_value,row_layout

def blend(front,back,alpha):
    a=[int(front[i:i+2],16) for i in (1,3,5)];b=[int(back[i:i+2],16) for i in (1,3,5)]
    return '#'+''.join(f'{round(x*alpha+y*(1-alpha)):02x}' for x,y in zip(a,b))

class PanelPreview(tk.Canvas):
    """A labeled example, never inserted into measurement state."""
    def __init__(self,parent,app):
        super().__init__(parent,bg='#28332F',highlightthickness=1,highlightbackground=LINE,width=338,height=420)
        self.app=app;self.signature=None;self.fonts={}
        self.bind('<Configure>',lambda _:self.render())
    def render(self):
        a=self.app;keys=[k for k,v in a.selected.items() if v.get()]
        w,h=self.winfo_width(),self.winfo_height()
        if w<10 or h<10:return
        sig=(w,h,tuple(keys),a.font_size.get(),a.bg_opacity.get(),a.text_opacity.get(),a.percent.get(),a.lock_var.get(),a.text_outline.get())
        if sig==self.signature:return
        self.signature=sig;self.delete('all')
        scene='#28332F'
        # Muted landscape provides a neutral opacity reference.
        self.create_rectangle(0,0,w,h,fill=scene,outline='')
        self.create_oval(-100,h*.45,w*.85,h*1.25,fill='#39463A',outline='')
        self.create_oval(w*.4,h*.25,w*1.6,h*1.15,fill='#45503D',outline='')
        values={'exp_total':23840,'exp_min':4768,'exp_30min':143040,'exp_hour':286080,
                'meso_total':12500,'meso_min':2500,'meso_30min':75000,'meso_hour':150000,'level_eta':4823,'elapsed':300}
        if a.percent.get():
            for k in values:
                if k.startswith('exp'):values[k]/=55560
        fs=a.font_size.get();base=tkfont.Font(family='Pretendard ExtraBold',size=-fs)
        lab=tkfont.Font(family='Pretendard',size=-max(10,fs-2),weight='bold')
        rows=row_layout(len(keys),lab.metrics('linespace'),base.metrics('linespace'))
        natural=(rows[-1][2]+14 if rows else 130)
        natural_width=max(340,max((lab.measure(METRICS[k])+base.measure(format_value(k,values[k],a.percent.get()))+70 for k in keys),default=0))
        scale=min(1,(h-24)/natural,(w-24)/natural_width)
        ph=natural*scale;pw=natural_width*scale;left=(w-pw)/2;top=(h-ph)/2
        panel=blend(BG,scene,a.bg_opacity.get()/100)
        self.create_rectangle(left,top,left+pw,top+ph,fill=panel,outline=blend(LINE,scene,a.bg_opacity.get()/100))
        def f(n,bold=False):
            key=(max(6,round(n*scale)),bold)
            if key not in self.fonts:self.fonts[key]=tkfont.Font(family='Pretendard ExtraBold' if bold else 'Pretendard',size=-key[0],weight='normal' if bold else 'bold')
            return self.fonts[key]
        def txt(x,y,t,size=10,color=TEXT,bold=False,anchor='w'):
            if a.text_outline.get():
                for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    self.create_text(left+x*scale+dx,top+y*scale+dy,text=t,font=f(size,bold),fill=blend('#080B0D',panel,a.text_opacity.get()/100),anchor=anchor)
            self.create_text(left+x*scale,top+y*scale,text=t,font=f(size,bold),fill=blend(color,panel,a.text_opacity.get()/100),anchor=anchor)
        txt(16,20,'Maple meter',12,ORANGE,True)
        if not a.lock_var.get():
            self.create_rectangle(left+(natural_width-94)*scale,top+6*scale,left+(natural_width-12)*scale,top+33*scale,fill='#10171C',outline='#596B78')
            txt(natural_width-53,19,'⠿  이동',10,'#FFFFFF',True,anchor='center')
        else:txt(natural_width-16,20,'잠금',9,MUTED,anchor='e')
        txt(16,49,'경험치 비율 (%)' if a.percent.get() else '경험치 양 (EXP)',9,MUTED)
        txt(natural_width-16,49,'EXP  ↔  %',10,ORANGE,True,anchor='e')
        for i,(k,(start,end,line)) in enumerate(zip(keys,rows)):
            y=(start+end)/2
            if k.startswith(('exp_','meso_')):
                self.create_rectangle(left+10*scale,top+(y-3)*scale,left+12*scale,top+(y+3)*scale,
                    fill=blend('#FFB45C' if k.startswith('meso') else '#74DCFF',panel,a.text_opacity.get()/100),outline='')
            txt(20,y,METRICS[k],max(10,fs-2),'#FFFFFF')
            txt(natural_width-16,y,format_value(k,values[k],a.percent.get()),fs,'#FFFFFF',True,anchor='e')
            if i==len(keys)-1 or keys[i+1].split('_')[0]!=k.split('_')[0]:
                self.create_line(left+16*scale,top+line*scale,left+(natural_width-16)*scale,top+line*scale,fill=blend(LINE,scene,a.bg_opacity.get()/100))
        if not keys:txt(170,90,'표시할 항목을 선택하세요.',10,MUTED,anchor='center')
