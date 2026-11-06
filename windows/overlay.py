import ctypes
from ctypes import wintypes
import tkinter as tk
from tkinter import font as tkfont
from presentation import METRICS,format_value,row_layout
from reader import client_box,U
from pathlib import Path
from theme import BG,TEXT,MUTED,ORANGE,GOLD,GREEN,LINE,RAISED
from placement import clamp_desktop,monitor_areas
from typography import apply_icons
import time

KEY='#010203'

class TextCanvas(tk.Canvas):
    def __init__(self,parent,app,**kwargs):
        super().__init__(parent,**kwargs);self.app=app
    def create_text(self,x,y,**kwargs):
        if self.app.text_outline.get():
            if self.app.bg_opacity.get()<35 and kwargs.get('fill')==MUTED:
                kwargs['fill']='#FFFFFF'
            shadow=dict(kwargs);shadow['fill']='#080B0D'
            for dx,dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(1,-1),(-1,1),(1,1)]:
                super().create_text(x+dx,y+dy,**shadow)
        return super().create_text(x,y,**kwargs)

class Overlay:
    def __init__(self,app):
        self.app=app
        self.back=tk.Toplevel(app.root);self.win=tk.Toplevel(app.root)
        for w,title in [(self.back,'Maple meter checker · 배경'),(self.win,'Maple meter checker · 게임 패널')]:
            apply_icons(w)
            w.withdraw();w.overrideredirect(True);w.title(title)
            w.attributes('-topmost',True);w.attributes('-toolwindow',True)
        self.back.configure(bg=BG);self.win.configure(bg=KEY)
        self.win.attributes('-transparentcolor',KEY)
        self.back_canvas=tk.Canvas(self.back,bg=BG,highlightthickness=0)
        self.canvas=TextCanvas(self.win,app,bg=KEY,highlightthickness=0)
        self.back_canvas.pack(fill='both',expand=True);self.canvas.pack(fill='both',expand=True)
        for c in (self.canvas,self.back_canvas):
            c.bind('<ButtonPress-1>',self.down);c.bind('<B1-Motion>',self.drag)
            c.bind('<ButtonRelease-1>',lambda _:app.save_config())
            c.bind('<Button-3>',lambda _:app.show_settings())
        self.offset=list(app.conf.get('position',[370,100]));self.origin=None
        self.desktop=app.conf.get('desktop_position');self.areas=[];self.area_time=0
        self.locked=False;self.shown=False;self.signature=None;self.unit_box=None
        self.fonts={};self.geometry=None;self.last_size=(0,0)
        self.placement=None
        U.SetWindowPos.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.UINT]
        self.mark=tk.PhotoImage(file=str(Path(__file__).with_name('panel-mark.png')))

    def font(self,size,bold=False):
        key=(size,bold)
        if key not in self.fonts:self.fonts[key]=tkfont.Font(family='Pretendard ExtraBold' if bold else 'Pretendard',size=-size,weight='normal' if bold else 'bold')
        return self.fonts[key]

    def down(self,e):
        if self.locked:return
        # Clicking the background raises it; restore the text layer before
        # handling the unit button as well as dragging.
        self.win.lift(self.back)
        if self.unit_box and self.unit_box[0]<=e.x<=self.unit_box[2] and self.unit_box[1]<=e.y<=self.unit_box[3]:
            self.app.toggle_units();self.origin=None;return
        position=self.desktop if self.app.free_position.get() and self.desktop else self.offset
        self.origin=(e.x_root,e.y_root,*position)

    def drag(self,e):
        if self.origin and not self.locked:
            x,y,ox,oy=self.origin;position=[ox+e.x_root-x,oy+e.y_root-y]
            if self.app.free_position.get():self.desktop=position
            else:self.offset=position

    def set_lock(self,locked):
        self.locked=locked
        U.GetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int];U.GetWindowLongPtrW.restype=ctypes.c_ssize_t
        U.SetWindowLongPtrW.argtypes=[wintypes.HWND,ctypes.c_int,ctypes.c_ssize_t];U.SetWindowLongPtrW.restype=ctypes.c_ssize_t
        for w in (self.back,self.win):
            w.update_idletasks();hwnd=U.GetAncestor(w.winfo_id(),2);style=U.GetWindowLongPtrW(hwnd,-20)
            style=(style|0x80000|0x20|0x08000000) if locked else (style&~(0x20|0x08000000))
            U.SetWindowLongPtrW(hwnd,-20,style)
        self.signature=None

    def hide(self):
        if self.shown:
            self.win.withdraw();self.back.withdraw();self.shown=False

    def paint(self,stats,status,visible):
        a=self.app
        if not visible:self.hide();return
        keys=[k for k,v in a.selected.items() if v.get()]
        fs=a.font_size.get();label_font=self.font(max(10,fs-2));value_font=self.font(fs,True)
        small=self.font(10);header=self.font(11,True)
        rows=row_layout(len(keys),label_font.metrics('linespace'),value_font.metrics('linespace'))
        values=[format_value(k,stats.get(k),a.percent.get()) for k in keys]
        width=max(340,max((label_font.measure(METRICS[k])+value_font.measure(v)+70 for k,v in zip(keys,values)),default=0))
        height=(rows[-1][2] if rows else 72)+14
        box=client_box(a.hwnd) if a.hwnd else (0,0,1920,1080)
        if time.monotonic()-self.area_time>3:
            self.areas=monitor_areas();self.area_time=time.monotonic()
        available=max((r[3]-r[1]-25 for r in self.areas),default=box[3]-box[1]-25) if a.free_position.get() else box[3]-box[1]-25
        if height>available:
            # Keep the control and all metrics on screen in a short game window.
            fs=max(8,fs-1)
            while height>available and fs>=8:
                label_font=self.font(max(9,fs-2));value_font=self.font(fs,True)
                rows=row_layout(len(keys),label_font.metrics('linespace'),value_font.metrics('linespace'))
                height=(rows[-1][2] if rows else 72)+14
                if fs==8:break
                fs-=1
        self.offset[0]=max(0,min(self.offset[0],box[2]-box[0]-width))
        self.offset[1]=max(0,min(self.offset[1],box[3]-box[1]-height-15))
        if a.free_position.get():
            if self.desktop is None:self.desktop=[box[0]+self.offset[0],box[1]+self.offset[1]]
            self.desktop=list(clamp_desktop(*self.desktop,width,height,self.areas));x,y=self.desktop
        else:x,y=box[0]+self.offset[0],box[1]+self.offset[1]
        # Tk uses negative geometry offsets relative to screen edges. Place at
        # absolute desktop coordinates with SetWindowPos after sizing instead.
        geometry=f'{width}x{height}'
        if geometry!=self.geometry:
            for w in (self.back,self.win):w.geometry(geometry)
            self.geometry=geometry
        if self.placement!=(x,y,width,height):
            for w in (self.back,self.win):
                w.update_idletasks()
                U.SetWindowPos(U.GetAncestor(w.winfo_id(),2),None,x,y,width,height,0x0014)
            self.placement=(x,y,width,height)
        self.last_size=width,height
        # These are distinct windows; text alpha never multiplies background alpha.
        self.back.attributes('-alpha',a.bg_opacity.get()/100)
        self.win.attributes('-alpha',a.text_opacity.get()/100)
        sig=(tuple(zip(keys,values)),status,fs,width,height,self.locked,a.percent.get(),a.text_outline.get(),a.bg_opacity.get()<35)
        if sig!=self.signature:
            c,b=self.canvas,self.back_canvas;c.delete('all');b.delete('all')
            b.create_rectangle(0,0,width-1,height-1,outline=LINE)
            c.create_image(23,20,image=self.mark)
            c.create_text(43,19,text='Maple meter',fill=TEXT,font=header,anchor='w')
            if a.session.started and not a.session.running:
                c.create_text(153,19,text='일시정지',fill=ORANGE,font=small,anchor='w')
            if self.locked:
                c.create_text(width-14,19,text='잠금',fill=MUTED,font=small,anchor='e')
            else:
                # This lives on the text layer, so the hit area survives a
                # fully transparent background. No invisible drag target.
                c.create_rectangle(width-94,6,width-12,33,fill='#10171C',outline='#596B78')
                for dx in (0,4):
                    for dy in (0,4,8):c.create_rectangle(width-83+dx,15+dy,width-82+dx,16+dy,fill='#FFFFFF',outline='')
                c.create_text(width-45,19,text='이동',fill='#FFFFFF',font=self.font(11,True))
            self.unit_box=(width-112,36,width-14,61)
            b.create_rectangle(*self.unit_box,fill=RAISED,outline='')
            if a.bg_opacity.get()<35:c.create_rectangle(*self.unit_box,fill='#10171C',outline='#596B78')
            c.create_text(width-63,48,text='EXP  ↔  %',fill=ORANGE,font=self.font(11,True))
            c.create_text(15,48,text='경험치 비율 (%)' if a.percent.get() else '경험치 양 (EXP)',fill=MUTED,font=small,anchor='w')
            for i,(k,v,(top,bottom,line)) in enumerate(zip(keys,values,rows)):
                center=(top+bottom)/2
                accent='#FFB45C' if k.startswith('meso') else '#74DCFF'
                if k.startswith(('exp_','meso_')):c.create_rectangle(10,center-3,12,center+3,fill=accent,outline='#071015')
                c.create_text(20,center,text=METRICS[k],fill='#FFFFFF',font=label_font,anchor='w')
                c.create_text(width-15,center,text=v,fill='#FFFFFF',font=value_font,anchor='e')
                if i==len(keys)-1 or keys[i+1].split('_')[0]!=k.split('_')[0]:
                    b.create_line(15,line,width-15,line,fill=LINE)
            self.signature=sig
        if not self.shown:
            self.back.deiconify();self.win.deiconify();self.win.lift(self.back);self.shown=True

    def destroy(self):
        self.win.destroy();self.back.destroy()
