"""Settings UI; measurement logic remains in app/session/reader."""
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from theme import *
from presentation import METRICS,DEFAULT_KEYS,KEY_LABELS
from preview import PanelPreview

class TabDeck(tk.Frame):
    def __init__(self,parent):
        super().__init__(parent,bg=BG)
        self.nav=tk.Frame(self,bg=BG);self.nav.pack(fill='x')
        self.pages=[];self.buttons=[];self.marks=[]
    def add(self,page,text):
        index=len(self.pages);self.pages.append(page)
        holder=tk.Frame(self.nav,bg=BG);holder.pack(side='left')
        button=tk.Button(holder,text=text,command=lambda:self.select(index),bg=BG,fg=MUTED,
            activebackground=PANEL,activeforeground=TEXT,relief='flat',bd=0,padx=18,pady=12,
            font=('Malgun Gothic',10),cursor='hand2')
        button.pack();mark=tk.Frame(holder,bg=BG,height=2);mark.pack(fill='x')
        self.buttons.append(button);self.marks.append(mark)
        if index==0:self.select(0)
    def select(self,index):
        for i,page in enumerate(self.pages):
            page.pack_forget();self.buttons[i].configure(bg=PANEL if i==index else BG,fg=TEXT if i==index else MUTED)
            self.marks[i].configure(bg=ORANGE if i==index else BG)
        self.pages[index].pack(fill='both',expand=True)

class ScrollTab(tk.Frame):
    def __init__(self,parent):
        super().__init__(parent,bg=PANEL)
        self.canvas=tk.Canvas(self,bg=PANEL,highlightthickness=0,bd=0)
        self.bar=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side='left',fill='both',expand=True)
        self.content=tk.Frame(self.canvas,bg=PANEL,padx=18,pady=18)
        self.item=self.canvas.create_window(0,0,window=self.content,anchor='nw')
        self.canvas.bind('<Configure>',self.layout)
        self.content.bind('<Configure>',self.layout)
    def layout(self,event=None):
        self.canvas.itemconfigure(self.item,width=self.canvas.winfo_width())
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        if self.content.winfo_reqheight()>self.canvas.winfo_height()+2:
            if not self.bar.winfo_manager():self.bar.pack(side='right',fill='y')
        else:
            self.bar.pack_forget();self.canvas.yview_moveto(0)

def build(a):
    a.root.option_add('*Font',('Malgun Gothic',10))
    style=ttk.Style();style.theme_use('clam')
    style.configure('TNotebook',background=BG,borderwidth=0)
    style.configure('TNotebook.Tab',background=BG,foreground=MUTED,padding=(16,12),borderwidth=0)
    style.map('TNotebook.Tab',background=[('selected',PANEL)],foreground=[('selected',TEXT)])
    style.configure('TCombobox',fieldbackground=RAISED,background=RAISED,foreground=TEXT,
                    arrowcolor=TEXT,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE,padding=5)
    style.map('TCombobox',fieldbackground=[('readonly',RAISED)],foreground=[('readonly',TEXT)],selectbackground=[('readonly',RAISED)])
    style.configure('Horizontal.TScale',background=PANEL,troughcolor=LINE,bordercolor=PANEL)
    style.configure('Vertical.TScrollbar',background=LINE,troughcolor=PANEL,bordercolor=PANEL,
                    lightcolor=PANEL,darkcolor=PANEL,arrowcolor=MUTED,width=8)
    style.layout('Vertical.TScrollbar',[('Vertical.Scrollbar.trough',{'sticky':'ns','children':[
        ('Vertical.Scrollbar.thumb',{'expand':'1','sticky':'nswe'})]})])
    a.root.option_add('*TCombobox*Listbox.background',RAISED)
    a.root.option_add('*TCombobox*Listbox.foreground',TEXT)
    a.root.option_add('*TCombobox*Listbox.selectBackground',LINE)

    def label(p,text='',**kw):return a.label(p,text,bg=kw.pop('bg',p.cget('bg')),**kw)
    def check(p,text,var,command=None):
        return tk.Checkbutton(p,text=text,variable=var,command=command or a.save_config,bg=p.cget('bg'),fg=TEXT,
            activebackground=p.cget('bg'),activeforeground=ORANGE,selectcolor=RAISED,bd=0,
            highlightthickness=0,padx=0,pady=5,cursor='hand2',anchor='w')
    def section(p,title,subtitle=''):
        label(p,title,font=('Malgun Gothic',12,'bold')).pack(anchor='w')
        if subtitle:label(p,subtitle,fg=MUTED,font=('Malgun Gothic',9),justify='left').pack(anchor='w',pady=(5,15))
    shell=tk.Frame(a.root,bg=BG,padx=26,pady=22);shell.pack(fill='both',expand=True)
    header=tk.Frame(shell,bg=BG);header.pack(fill='x')
    a.logo=tk.PhotoImage(file=str(Path(__file__).with_name('brand-mark.png')))
    tk.Label(header,image=a.logo,bg=BG).pack(side='left',padx=(0,14))
    brand=tk.Frame(header,bg=BG);brand.pack(side='left')
    label(brand,'Maple meter',font=('Segoe UI Semibold',23)).pack(anchor='w')
    label(brand,'C H E C K E R   /   2.1',fg=ORANGE,font=('Segoe UI',9)).pack(anchor='w',pady=(1,0))
    a.button(header,'사용 안내',a.show_help).pack(side='right')
    label(header,'CLASSIC WORLD',fg=MUTED,font=('Segoe UI',9)).pack(side='right',padx=18)

    status=tk.Frame(shell,bg=PANEL,padx=18,pady=12);status.pack(fill='x',pady=(20,20))
    info=tk.Frame(status,bg=PANEL);info.pack(side='left',fill='x',expand=True)
    a.connection_var=tk.StringVar(value='게임 연결 대기')
    a.exp_label=label(info,textvariable=a.connection_var,fg=GREEN,font=('Malgun Gothic',10,'bold'))
    a.exp_label.pack(anchor='w')
    label(info,textvariable=a.status_var,fg=MUTED,font=('Malgun Gothic',9)).pack(anchor='w',pady=(3,0))
    label(info,textvariable=a.meso_var,fg=MUTED,font=('Malgun Gothic',9)).pack(anchor='w',pady=(3,0))
    a.phase_var=tk.StringVar(value='준비')
    label(status,textvariable=a.phase_var,fg=ORANGE,font=('Malgun Gothic',11,'bold')).pack(side='right',padx=(12,0))

    footer=tk.Frame(shell,bg=BG);footer.pack(side='bottom',fill='x',pady=(16,0))
    tk.Frame(footer,bg=LINE,height=1).pack(fill='x',pady=(0,12))
    label(footer,textvariable=a.summary_var,fg=MUTED,font=('Malgun Gothic',9)).pack(anchor='w',pady=(0,10))
    actions=tk.Frame(footer,bg=BG);actions.pack(fill='x')
    a.start_btn=a.button(actions,'측정 시작',a.toggle,True);a.start_btn.pack(side='right',padx=(10,0),ipadx=35)
    a.button(actions,'게임으로',a.to_game).pack(side='right')
    a.button(actions,'초기화',a.reset_with_undo).pack(side='left')
    a.undo_btn=a.button(actions,'초기화 취소',a.undo_reset)
    a.shortcut_hint=tk.StringVar(value=a.keymap['toggle']+' · 시작 / 일시정지')
    label(actions,textvariable=a.shortcut_hint,fg=MUTED,font=('Malgun Gothic',9)).pack(side='left',padx=14)

    body=tk.Frame(shell,bg=BG);body.pack(fill='both',expand=True)
    body.columnconfigure(0,weight=1);body.columnconfigure(1,weight=0,minsize=340);body.rowconfigure(0,weight=1)
    tabs=TabDeck(body);tabs.grid(row=0,column=0,sticky='nsew',padx=(0,22))
    scroll_tabs=[ScrollTab(tabs) for _ in range(3)]
    metrics,appearance,keys=[t.content for t in scroll_tabs]
    for page,title in zip(scroll_tabs,['표시 항목','패널 모양','단축키']):tabs.add(page,text=title)
    def wheel(event):
        if isinstance(event.widget,(tk.Scale,ttk.Combobox)):return
        node=event.widget
        while node is not None:
            for page in scroll_tabs:
                if node==page.content:
                    page.canvas.yview_scroll(-int(event.delta/120),'units');return 'break'
            node=getattr(node,'master',None)
    a.root.bind('<MouseWheel>',wheel)

    section(metrics,'보고 싶은 기록만 골라 보세요.','분당 · 30분 · 1시간은 평균 속도로 계산한 예상치입니다.')
    presets=tk.Frame(metrics,bg=PANEL);presets.pack(fill='x',pady=(0,12))
    for title,mode in [('전체 보기','all'),('간단히 보기','compact')]:
        a.button(presets,title,lambda m=mode:a.select_preset(m)).pack(side='left',padx=(0,8))
    a.count_var=tk.StringVar()
    label(presets,textvariable=a.count_var,fg=MUTED,font=('Segoe UI',9)).pack(side='right')
    groups=tk.Frame(metrics,bg=PANEL);groups.pack(fill='x')
    for index,(title,prefix,color) in enumerate([('경험치','exp',ORANGE),('메소 +α','meso',GOLD)]):
        group=tk.Frame(groups,bg=PANEL);group.grid(row=0,column=index,sticky='nw',padx=(0,24))
        groups.columnconfigure(index,weight=1)
        label(group,title,fg=color,font=('Malgun Gothic',10,'bold')).pack(anchor='w',pady=(0,5))
        for suffix,name in [('total','누적'),('min','분당'),('30min','30분'),('hour','1시간')]:
            check(group,name,a.selected[f'{prefix}_{suffix}']).pack(anchor='w')
    tk.Frame(metrics,bg=LINE,height=1).pack(fill='x',pady=(12,8))
    check(metrics,'레벨업까지 남은 시간 (예상)',a.selected['level_eta']).pack(anchor='w')
    label(metrics,'메소 +α: 빠르게 사라져 읽지 못한 획득량이 있을 수 있습니다.',fg=MUTED,font=('Malgun Gothic',8),wraplength=390,justify='left').pack(anchor='w',pady=(3,6))
    check(metrics,'측정 시간',a.selected['elapsed']).pack(anchor='w')
    unit=tk.Frame(metrics,bg=PANEL);unit.pack(fill='x',pady=(10,0))
    label(unit,'경험치 단위',fg=MUTED,font=('Malgun Gothic',9)).pack(side='left',padx=(0,14))
    for title,value in [('경험치 양',False),('비율 %',True)]:
        tk.Radiobutton(unit,text=title,variable=a.percent,value=value,command=a.save_config,indicatoron=False,
            bg=RAISED,fg=MUTED,selectcolor=LINE,activebackground=LINE,activeforeground=TEXT,
            relief='flat',bd=0,padx=12,pady=7,cursor='hand2').pack(side='left',padx=(0,4))

    section(appearance,'읽기 편한 패널로 조절하세요.','오른쪽 미리보기에 바로 반영됩니다.')
    for title,var,lo,hi,suffix in [('글자 크기',a.font_size,8,26,'px'),('배경 불투명도',a.bg_opacity,0,100,'%'),('글자 불투명도',a.text_opacity,10,100,'%')]:
        group=tk.Frame(appearance,bg=PANEL);group.pack(fill='x',pady=(0,13))
        line=tk.Frame(group,bg=PANEL);line.pack(fill='x')
        label(line,title).pack(side='left')
        value=tk.StringVar(value=f'{var.get()}{suffix}')
        var.trace_add('write',lambda *_,v=var,t=value,s=suffix:t.set(f'{v.get()}{s}'))
        label(line,textvariable=value,fg=ORANGE,font=('Segoe UI',10,'bold')).pack(side='right')
        tk.Scale(group,variable=var,from_=lo,to=hi,orient='horizontal',showvalue=False,command=lambda _:a.save_config(),
            bg=PANEL,fg=TEXT,troughcolor=LINE,highlightthickness=0,bd=0,sliderrelief='flat',sliderlength=22,
            activebackground=ORANGE,width=10).pack(fill='x',pady=(9,0))
    tk.Frame(appearance,bg=LINE,height=1).pack(fill='x',pady=(0,8))
    check(appearance,'글자 테두리 · 투명 배경에서도 또렷하게',a.text_outline).pack(anchor='w')
    check(appearance,'게임 위에 패널 표시',a.show_overlay).pack(anchor='w')
    check(appearance,'화면 어디든 이동 · 다른 모니터에도 표시',a.free_position,a.position_changed).pack(anchor='w')
    check(appearance,'위치 잠금 · 클릭을 게임으로 통과',a.lock_var,a.lock_changed).pack(anchor='w')
    label(appearance,'자유 이동을 끄면 게임 안에 고정됩니다.\n잠금 중에는 단축키로 경험치 단위를 바꿔 주세요.',
          fg=MUTED,font=('Malgun Gothic',9),justify='left').pack(anchor='w',pady=(6,12))
    resets=tk.Frame(appearance,bg=PANEL);resets.pack(fill='x')
    a.button(resets,'모양 기본값',a.restore_appearance).pack(side='left',padx=(0,8))
    a.button(resets,'패널 위치 되돌리기',a.restore_position).pack(side='left')

    section(keys,'손에 익은 단축키로 바꾸세요.','변경한 조합은 적용 버튼을 누르면 저장됩니다.')
    a.key_vars={};kg=tk.Frame(keys,bg=PANEL);kg.pack(fill='x')
    for i,name in enumerate(DEFAULT_KEYS):
        parts=a.keymap[name].split('+');mod=tk.StringVar(value='+'.join(parts[:-1]));key=tk.StringVar(value=parts[-1]);a.key_vars[name]=(mod,key)
        label(kg,KEY_LABELS[name],font=('Malgun Gothic',9)).grid(row=i,column=0,sticky='w',pady=10,padx=(0,8))
        ttk.Combobox(kg,textvariable=mod,state='readonly',values=['Ctrl+Alt','Ctrl+Shift','Alt+Shift','Ctrl','Alt'],width=10).grid(row=i,column=1,padx=4)
        ttk.Combobox(kg,textvariable=key,state='readonly',values=[f'F{x}' for x in range(1,12)]+list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),width=4).grid(row=i,column=2,padx=4)
        mod.trace_add('write',lambda *_:a.key_status.set('변경한 단축키를 적용해 주세요.'))
        key.trace_add('write',lambda *_:a.key_status.set('변경한 단축키를 적용해 주세요.'))
    a.button(keys,'단축키 적용',a.apply_keys,True).pack(anchor='w',pady=(15,12))
    label(keys,textvariable=a.key_status,fg=ORANGE,wraplength=390,justify='left',font=('Malgun Gothic',9)).pack(anchor='w')
    label(keys,'초기화는 즉시 실행되며, 설정에서 8초 동안 취소할 수 있습니다.',fg=MUTED,
        wraplength=390,justify='left',font=('Malgun Gothic',9)).pack(anchor='w',pady=(15,0))

    preview=tk.Frame(body,bg=BG);preview.grid(row=0,column=1,sticky='nsew')
    line=tk.Frame(preview,bg=BG);line.pack(fill='x',pady=(9,13))
    label(line,'패널 미리보기',font=('Malgun Gothic',10,'bold')).pack(side='left')
    label(line,'실시간 반영',fg=ORANGE,font=('Malgun Gothic',9)).pack(side='right')
    a.panel_preview=PanelPreview(preview,a);a.panel_preview.pack(fill='both',expand=True)
    label(preview,'예시 수치 · 실제 측정 기록에는 포함되지 않습니다.',fg=MUTED,font=('Malgun Gothic',8)).pack(anchor='w',pady=(10,0))
