"""Maple meter checker 2.1 — screen-only game statistics."""
import ctypes
import copy
from ctypes import wintypes
import json
import logging
import os
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk,messagebox
from reader import Reader,PickupReader,capture,find_game,client_box,infer_level,U
from session import Session,Reading,PickupCounter
from presentation import METRICS,DEFAULT_KEYS,KEY_LABELS,validate_hotkeys,format_value,selected_metrics
from overlay import Overlay
from theme import BG,TEXT,MUTED,ORANGE,PANEL,RAISED,LINE,GREEN
from ui import build
from hotkeys import Hotkeys
from typography import load_fonts,apply_icons

BASE=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
ASSETS=Path(__file__).parent
DATA=BASE/'checker-data'
try:DATA.mkdir(exist_ok=True)
except OSError:
    DATA=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'MapleMeterChecker';DATA.mkdir(parents=True,exist_ok=True)
logging.basicConfig(filename=DATA/'diagnostics.log',level=logging.INFO,encoding='utf-8',
                    format='%(asctime)s %(levelname)s %(message)s')
VERSION='2.1.2'

def own_foreground(hwnd):
    fg=U.GetForegroundWindow();pid=wintypes.DWORD();U.GetWindowThreadProcessId(fg,ctypes.byref(pid))
    return fg==hwnd or pid.value==os.getpid()

class App:
    def __init__(self):
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('MapleMeterChecker.Desktop.2')
        load_fonts()
        self.root=tk.Tk();self.root.title('Maple meter checker · 설정');self.root.configure(bg=BG)
        self.root.geometry('960x820');self.root.minsize(920,720)
        self.root.protocol('WM_DELETE_WINDOW',self.close)
        try:apply_icons(self.root)
        except tk.TclError:pass
        try:self.conf=json.loads((DATA/'settings.json').read_text(encoding='utf-8'))
        except (OSError,ValueError):self.conf={}
        self.keymap={**DEFAULT_KEYS,**self.conf.get('hotkeys',{})}
        try:validate_hotkeys(self.keymap)
        except ValueError:self.keymap=dict(DEFAULT_KEYS)
        self.session=Session();self.pickups=PickupCounter();self.reading=None;self.hwnd=None
        self.read_ok=False;self.last_good=0;self.capture_after=0;self.toast_until=0;self.toast=''
        self.exp_status='게임 화면을 확인하는 중…';self.meso_status='메소 획득 메시지 대기'
        self.selected={k:tk.BooleanVar(value=k in selected_metrics(self.conf)) for k in METRICS}
        self.font_size=tk.IntVar(value=max(8,min(26,int(self.conf.get('font_size',16)))))
        self.bg_opacity=tk.IntVar(value=max(0,min(100,int(self.conf.get('background_opacity',85)))))
        self.text_opacity=tk.IntVar(value=max(10,min(100,int(self.conf.get('text_opacity',100)))))
        self.text_outline=tk.BooleanVar(value=self.conf.get('text_outline',True))
        self.free_position=tk.BooleanVar(value=self.conf.get('free_position',True))
        self.percent=tk.BooleanVar(value=bool(self.conf.get('percent',False)))
        self.show_overlay=tk.BooleanVar(value=self.conf.get('show_overlay',True));self.lock_var=tk.BooleanVar(value=self.conf.get('locked',False))
        self.preview=tk.BooleanVar(value=False)
        self.status_var=tk.StringVar(value=self.exp_status);self.meso_var=tk.StringVar(value=self.meso_status)
        self.scale_var=tk.StringVar(value='화면 크기가 바뀌면 자동으로 다시 보정합니다.')
        self.summary_var=tk.StringVar(value='표시 항목을 고르고 측정을 시작하세요.')
        self.key_status=tk.StringVar(value='')
        self.undo_state=None;self.undo_until=0;self.help_window=None
        self.queue=queue.Queue(maxsize=3);self.stop=threading.Event()
        build(self);self.overlay=Overlay(self);self.overlay.set_lock(self.lock_var.get());self.hotkeys=Hotkeys(self.keymap)
        self.thread=threading.Thread(target=self.worker,daemon=True);self.thread.start()
        self.root.after(120,self.tick)

    def label(self,p,text='',**kw):
        return tk.Label(p,text=text,bg=kw.pop('bg',BG),fg=kw.pop('fg',TEXT),
                        font=kw.pop('font',('Malgun Gothic',10)),**kw)

    def button(self,p,text,cmd,primary=False):
        return tk.Button(p,text=text,command=cmd,bg=ORANGE if primary else RAISED,fg=BG if primary else TEXT,
                         relief='flat',bd=0,disabledforeground='#68737A',activebackground='#F0BB93' if primary else LINE,padx=15,pady=9,cursor='hand2',font=('Malgun Gothic',10,'bold'))

    def check(self,p,text,var,cmd=None):
        return tk.Checkbutton(p,text=text,variable=var,command=cmd or self.save_config,bg=BG,fg=TEXT,selectcolor=PANEL,
                              activebackground=BG,activeforeground=TEXT,font=('Malgun Gothic',10),anchor='w')

    def save_config(self):
        conf={'metrics_revision':2,'metrics':[k for k,v in self.selected.items() if v.get()], 'font_size':self.font_size.get(),
              'background_opacity':self.bg_opacity.get(),'text_opacity':self.text_opacity.get(),
              'percent':self.percent.get(),'hotkeys':self.keymap,'show_overlay':self.show_overlay.get(),'locked':self.lock_var.get(),
              'text_outline':self.text_outline.get(),'free_position':self.free_position.get()}
        if hasattr(self,'overlay'):
            conf['position']=self.overlay.offset;conf['desktop_position']=self.overlay.desktop
        try:
            tmp=DATA/'settings.tmp';tmp.write_text(json.dumps(conf,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(DATA/'settings.json')
        except OSError:logging.exception('Settings write failed')

    def apply_keys(self):
        mapping={k:f'{m.get()}+{v.get()}' for k,(m,v) in self.key_vars.items()}
        try:validate_hotkeys(mapping)
        except ValueError as e:messagebox.showerror('단축키 확인',str(e),parent=self.root);return
        self.keymap=mapping;self.hotkeys.update(mapping);self.save_config()

    def lock_changed(self):self.overlay.set_lock(self.lock_var.get());self.save_config()
    def toggle_lock(self):self.lock_var.set(not self.lock_var.get());self.lock_changed()
    def toggle_units(self):self.percent.set(not self.percent.get());self.save_config()

    def worker(self):
        reader=Reader();pickup=PickupReader()
        while not self.stop.is_set():
            at=time.monotonic()
            try:
                hwnd=find_game();p={'hwnd':hwnd,'at':at}
                if not hwnd:p['status']='게임 창 대기 · 최소화를 해제해 주세요'
                elif not own_foreground(hwnd):p['status']='게임 화면 확인 대기'
                else:
                    image=capture(hwnd);value,_=reader.read_image(image)
                    if value:p.update(value=value,scale=reader.scale)
                    else:p['status']='EXP 인식 대기 · 상태바가 가리지 않게 해 주세요'
                    # Meso recognition has its own calibration and keeps working
                    # even while HUD calibration is temporarily unavailable.
                    hint=(image.height/reader.scale[1]) if reader.scale else None
                    p['lines']=pickup.read(image,hint)
                    p['meso_scale']=pickup.factor;p['resized']=pickup.changed
                p['ms']=round((time.monotonic()-at)*1000)
                try:self.queue.put_nowait(p)
                except queue.Full:
                    try:self.queue.get_nowait()
                    except queue.Empty:pass
                    self.queue.put_nowait(p)
            except Exception as e:
                logging.exception('Reader error')
                try:self.queue.put_nowait({'hwnd':None,'at':at,'status':f'화면 읽기 오류 · {type(e).__name__}'})
                except queue.Full:pass
            self.stop.wait(max(.05,.5-(time.monotonic()-at)))

    def process(self,p,now):
        if self.session.running and p['at']<self.capture_after:return
        self.hwnd=p['hwnd']
        if 'value' in p:
            n,pct=p['value'];lv=infer_level(n,pct) or (self.reading.level if self.reading else None)
            self.reading=Reading(n,pct,lv);self.read_ok=True;self.last_good=now;self.session.feed(now,self.reading)
            self.exp_status=f'EXP {n:,}  ·  {pct:.2f}%  ·  '+(f'Lv.{lv}' if lv else '레벨 확인 중')
        else:self.read_ok=False;self.exp_status=p.get('status','인식 대기')
        if 'lines' in p:
            if p.get('resized'):
                # Reset positional alignment, retaining recent identities. A
                # visible pre-resize message must not become new income.
                self.pickups.rebaseline(p['lines'],now)
                amount=0;seen=any(k=='meso' for _,_,k,_ in p['lines'])
            else:amount,seen=self.pickups.feed(p['lines'],now,self.session.running)
            self.session.meso+=amount
            if seen:self.session.meso_seen=True
            self.meso_status=(f'메소 인식 확인 · 누적 {self.session.meso:,} +α' if self.session.meso_seen else '메소 획득 메시지 대기')
            if self.pickups.uncertain:self.meso_status+=' · 메시지 누락 가능'
            factor=p.get('meso_scale')
            self.scale_var.set(f'자동 배율 보정  ·  메소 {factor:.3f}배  ·  읽기 {p["ms"]} ms' if factor else f'메소 배율 탐색 중  ·  읽기 {p["ms"]} ms')
        elif self.session.running:self.meso_status='화면 확인 대기 · 메소 메시지 누락 가능'

    def tick(self):
        now=time.monotonic()
        while True:
            try:self.process(self.queue.get_nowait(),now)
            except queue.Empty:break
        while True:
            try:kind,value=self.hotkeys.events.get_nowait()
            except queue.Empty:break
            if kind=='ready':
                self.key_status.set('다른 프로그램과 충돌: '+', '.join(KEY_LABELS[k] for k in value) if value else '모든 단축키가 적용되었습니다.')
                self.shortcut_hint.set('단축키 충돌 · 단축키 탭에서 확인하세요' if value else self.keymap['toggle']+' · 시작 / 일시정지')
            else:{'toggle':self.toggle,'settings':self.show_settings,'lock':self.toggle_lock,'reset':self.reset_with_undo,'units':self.toggle_units}[value]()
        if now-self.last_good>3:self.read_ok=False
        self.status_var.set(self.exp_status);self.meso_var.set(self.meso_status)
        self.exp_label.configure(fg=GREEN if self.read_ok else MUTED)
        self.connection_var.set('게임 연결됨' if self.read_ok else ('화면 확인 대기' if self.hwnd else '게임 연결 대기'))
        self.phase_var.set('측정 중' if self.session.running else ('일시정지' if self.session.started else '준비'))
        self.count_var.set(f'{sum(v.get() for v in self.selected.values())} / {len(METRICS)}')
        self.start_btn.configure(text='일시정지' if self.session.running else ('계속 측정' if self.session.started else '측정 시작'),
             state='normal' if self.session.running or (any(v.get() for v in self.selected.values()) and self.read_ok and self.reading and self.reading.level) else 'disabled')
        stats=self.session.stats(now,self.percent.get())
        if not self.read_ok:stats['level_eta']=None
        if self.session.started:self.summary_var.set(f'{"측정 중" if self.session.running else "일시정지"}  ·  {format_value("elapsed",stats["elapsed"])}  ·  EXP {format_value("exp_total",stats["exp_total"],self.percent.get())}  ·  메소 {self.session.meso:,} +α')
        if not self.session.started:self.summary_var.set('표시 항목을 하나 이상 선택하세요.' if not any(v.get() for v in self.selected.values()) else '준비되면 측정 시작을 누르세요. 설정은 자동 저장됩니다.')
        status=self.session.warning or ('일시정지' if not self.session.running else ('측정 중 · 인식 정상' if self.read_ok else '화면 인식 대기'))
        if not self.session.meso_seen:status+=' · 메소 대기'
        elif self.pickups.uncertain:status+=' · 메소 누락 가능'
        if now<self.toast_until:status=self.toast
        foreground=U.GetForegroundWindow()
        panel_focused=any(foreground==U.GetAncestor(w.winfo_id(),2) for w in (self.overlay.win,self.overlay.back))
        visible=(foreground==self.hwnd or panel_focused or (self.free_position.get() and not own_foreground(self.hwnd))) and self.show_overlay.get() and self.session.started
        if not self.free_position.get():visible=visible and self.hwnd and not U.IsIconic(self.hwnd)
        self.overlay.paint(stats,'미리보기 · 측정 시작 전' if not self.session.started else status,visible)
        self.panel_preview.render()
        if self.undo_state and now<self.undo_until:
            if not self.undo_btn.winfo_manager():self.undo_btn.pack(side='left',padx=(8,0),before=self.start_btn)
        else:
            self.undo_state=None;self.undo_btn.pack_forget()
        self.root.after(120,self.tick)

    def toggle(self):
        if self.session.running:self.session.pause(time.monotonic());return
        if not any(v.get() for v in self.selected.values()):self.show_settings();messagebox.showinfo('표시 항목','항목을 하나 이상 선택하세요.',parent=self.root);return
        if not self.read_ok or not self.reading or not self.reading.level:return
        self.capture_after=time.monotonic();self.session.start(self.capture_after,self.reading)
        self.save_config();self.to_game()

    def reset(self):
        running=self.session.running;started=self.session.started;now=time.monotonic()
        self.session=Session();self.session.current=self.reading;self.session.started=started
        self.pickups.uncertain=False;self.capture_after=now
        if running and self.reading:self.session.start(now,self.reading)
        self.toast='초기화 완료 · 0부터 새로 측정';self.toast_until=now+3
        self.meso_status='메소 획득 메시지 대기';self.summary_var.set('초기화 완료')

    def select_preset(self,mode):
        compact={'exp_hour','meso_hour','level_eta','elapsed'}
        for key,var in self.selected.items():var.set(mode=='all' or key in compact)
        self.save_config()

    def restore_appearance(self):
        self.font_size.set(16);self.bg_opacity.set(85);self.text_opacity.set(100)
        self.text_outline.set(True)
        self.save_config()

    def position_changed(self):
        self.overlay.origin=None;self.overlay.placement=None;self.save_config()

    def restore_position(self):
        self.overlay.offset=[370,100];self.overlay.desktop=None;self.overlay.placement=None
        self.lock_var.set(False);self.lock_changed();self.save_config()

    def reset_with_undo(self):
        self.undo_state=copy.deepcopy(self.session);self.undo_until=time.monotonic()+8
        self.reset()
        self.toast='초기화 완료 · 설정에서 8초 안에 취소 가능'

    def undo_reset(self):
        if self.undo_state is None or time.monotonic()>=self.undo_until:return
        previous=self.undo_state;self.undo_state=None
        if previous.running:
            previous.meso+=self.session.meso
            previous.meso_seen=previous.meso_seen or self.session.meso_seen
            if self.reading:previous.feed(time.monotonic(),self.reading)
        self.session=previous;self.toast='초기화를 취소했습니다.';self.toast_until=time.monotonic()+3

    def show_help(self):
        if self.help_window and self.help_window.winfo_exists():self.help_window.lift();return
        w=tk.Toplevel(self.root);self.help_window=w;w.title('Maple meter checker · 사용 안내')
        w.configure(bg=BG);w.geometry('570x600');w.minsize(520,520)
        apply_icons(w)
        body=tk.Text(w,bg=BG,fg=TEXT,wrap='word',relief='flat',font=('Malgun Gothic',10),padx=25,pady=22,
                     spacing1=5,spacing3=8,selectbackground=LINE)
        body.pack(fill='both',expand=True)
        body.insert('1.0','Maple meter checker 2.1\n메이플스토리 클래식 월드 · Windows 64비트\n\n'
            '1. 게임을 켜고 경험치 상태바가 보이게 합니다.\n2. 표시 항목과 패널 모양을 고릅니다.\n3. 측정 시작을 누르면 게임 위에 패널이 나타납니다.\n\n'
            '경험치 양 / %\n설정 또는 패널의 EXP ↔ % 버튼으로 바꿉니다. 레벨업 전후의 비율도 이어서 합산합니다.\n\n'
            '메소 +α와 레벨업 예상 시간\n+α는 빠르게 사라져 읽지 못한 메소가 있을 수 있다는 뜻입니다. 누락량을 임의로 더하지 않습니다. 레벨업까지는 남은 경험치 ÷ 측정 중 평균 순 경험치 속도이며, 속도가 없거나 인식이 안 되면 —로 표시합니다.\n\n예상치와 실제 기록\n분당·30분·1시간은 현재 평균 속도 기준입니다. 설정 미리보기의 수치는 예시이며 기록되지 않습니다.\n\n'
            '패널 조작\n드래그로 이동하고 우클릭으로 설정을 엽니다. 위치 잠금은 클릭을 게임으로 통과시킵니다. 잠금 중에는 단축키를 사용하세요.\n\n'
            '자유 이동과 투명 배경\n패널 모양에서 화면 어디든 이동을 켜면 바탕화면과 다른 모니터로 옮길 수 있습니다. 다른 앱 위에도 표시됩니다. 끄면 게임 안에 고정됩니다. 패널 위치 되돌리기로 위치를 복구할 수 있습니다. 글자 테두리는 배경을 투명하게 해도 가독성을 유지합니다.\n\n'
            '인식이 멈추면\n게임 최소화를 해제하고 경험치 상태바와 오른쪽 획득 메시지를 가리는 창을 치우세요. 해상도 변경은 자동 보정합니다. 사라진 메소 메시지는 복구할 수 없습니다.\n\n'
            '개인정보와 저장\n측정 수치는 PC에서 처리하며 서버로 전송하지 않습니다. 스크린샷이나 사냥 기록을 자동 저장하지 않습니다. 설정과 오류 기록만 checker-data 폴더에 저장합니다.\n\n'
            '설치 없이 ZIP을 모두 풀고 실행하세요. 게임과 미터는 같은 Windows 사용자로 실행하세요. 다른 버전의 미터는 먼저 닫아 주세요.\n\n'
            '독립 제작 도구이며 Nexon의 공식 프로그램이 아닙니다.\n')
        body.configure(state='disabled')
        self.button(w,'닫기',w.destroy).pack(pady=(0,20))

    def show_settings(self):self.root.deiconify();self.root.lift();self.root.focus_force()
    def to_game(self):
        if self.hwnd:self.root.iconify();U.SetForegroundWindow(self.hwnd)
    def close(self):
        self.save_config();self.stop.set();self.hotkeys.close();self.overlay.destroy();self.root.destroy()

if __name__=='__main__':
    from instance import acquire_instance
    instance=acquire_instance()
    if instance is None:sys.exit(0)
    try:App().root.mainloop()
    except Exception:logging.exception('Application failure');raise
