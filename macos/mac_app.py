"""Maple meter checker macOS preview. Window capture is explicitly opt-in."""
import json
import logging
import os
from pathlib import Path
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QRectF, QLockFile
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QPainter, QPainterPath, QPen, QIcon, QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QSlider, QSpinBox, QDoubleSpinBox, QTabWidget, QFormLayout,
    QLineEdit, QMessageBox, QScrollArea, QFileDialog)
from presentation import METRICS, KEY_LABELS, format_value, selected_metrics
from reader import PickupReader
from mac_recognition import MacHudReader, hud_preview
from mac_model import Model, crop_frame
from mac_hotkeys import DEFAULT_KEYS, Hotkeys

VERSION='2.2.0-mac-preview.6'
ASSETS=Path(__file__).parent
BG='#10171C';PANEL='#1D272E';TEXT='#F6F6F3';ORANGE='#EAB38B'


class Bus(QObject):
    result=Signal(object)
    windows=Signal(object)
    failed=Signal(object)
    hotkey=Signal(str)


class Overlay(QWidget):
    def __init__(self, owner):
        super().__init__(None,Qt.WindowType.Tool|Qt.WindowType.FramelessWindowHint|Qt.WindowType.WindowStaysOnTopHint)
        self.owner=owner;self.drag_origin=None;self.locked=False
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowTitle('Maple meter checker · 패널')
        self.resize(360,420);self.move(80,100)

    def apply_native_flags(self):
        if sys.platform!='darwin':return
        import objc, AppKit
        view=objc.objc_object(c_void_p=int(self.winId()))
        window=view.window()
        window.setLevel_(AppKit.NSFloatingWindowLevel)
        window.setCollectionBehavior_(AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces|
                                      AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary)
        window.setIgnoresMouseEvents_(self.locked)

    def set_locked(self, locked):
        self.locked=locked
        # Native ignoresMouseEvents preserves the transparent surface and works
        # across all child hit regions without recreating the NSWindow.
        if sys.platform=='darwin':self.apply_native_flags()
        else:self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents,locked)
        self.update()

    def selected(self):return [k for k,cb in self.owner.metrics.items() if cb.isChecked()]

    def font_for(self,size):
        font=QFont(self.owner.font_family)
        font.setPixelSize(size);font.setWeight(QFont.Weight.Bold)
        return font

    def dimensions(self):
        size=self.owner.font_size.value();font=self.font_for(size)
        fm=QFontMetrics(font);rh=max(27,fm.height()+14)
        stats=self.owner.model.session.stats(time.monotonic(),self.owner.percent.isChecked())
        if time.monotonic()-self.owner.model.last_good>3:stats['level_eta']=None
        keys=self.selected();width=350
        for key in keys:
            value=format_value(key,stats.get(key),self.owner.percent.isChecked())
            width=max(width,fm.horizontalAdvance(METRICS[key])+fm.horizontalAdvance(value)+58)
        return width,76+rh*len(keys),rh,font,stats

    def refresh(self):
        w,h,*_=self.dimensions()
        if self.size().width()!=w or self.size().height()!=h:self.resize(w,h)
        self.update()

    def outlined(self,p,text,x,baseline,font,color='#FFFFFF',right=False):
        if right:x-=QFontMetrics(font).horizontalAdvance(text)
        path=QPainterPath();path.addText(x,baseline,font,text)
        p.setPen(QPen(QColor('#05070A'),2.4,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin))
        p.setBrush(QColor(color));p.drawPath(path)

    def paintEvent(self,event):
        width,height,rh,font,stats=self.dimensions()
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self.owner.bg_alpha.value()/100)
        p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor(BG));p.drawRoundedRect(self.rect(),10,10)
        p.setPen(QPen(QColor('#52626B'),1))
        keys=self.selected()
        for i,key in enumerate(keys):
            if i==len(keys)-1 or keys[i+1].split('_')[0]!=key.split('_')[0]:
                p.drawLine(14,70+(i+1)*rh,width-14,70+(i+1)*rh)
        # Controls keep a visible, hittable surface even at background opacity 0.
        p.setOpacity(1);p.setPen(QPen(QColor('#6E808C'),1));p.setBrush(QColor(BG))
        if not self.locked:p.drawRoundedRect(QRectF(width-90,7,79,26),4,4)
        p.drawRoundedRect(QRectF(width-112,38,100,25),4,4)
        p.setOpacity(self.owner.text_alpha.value()/100)
        small=self.font_for(12)
        self.outlined(p,'Maple meter',14,25,self.font_for(14),ORANGE)
        self.outlined(p,'잠금' if self.locked else '⠿ 이동',width-50,25,small)
        self.outlined(p,'EXP ↔ %',width-99,55,small,ORANGE)
        title='경험치 비율 (%)' if self.owner.percent.isChecked() else '경험치 양 (EXP)'
        self.outlined(p,title,14,55,self.font_for(11))
        if self.owner.model.session.started and not self.owner.model.session.running:
            self.outlined(p,'일시정지',137,25,self.font_for(11),ORANGE)
        for i,key in enumerate(keys):
            cy=70+i*rh+rh/2;fm=QFontMetrics(font)
            baseline=cy+(fm.ascent()-fm.descent())/2
            if key.startswith(('exp_','meso_')):
                p.setPen(Qt.PenStyle.NoPen);p.setBrush(QColor('#FFB45C' if key.startswith('meso') else '#74DCFF'))
                p.drawRect(QRectF(9,cy-3,3,6))
            self.outlined(p,METRICS[key],20,baseline,font)
            self.outlined(p,format_value(key,stats.get(key),self.owner.percent.isChecked()),width-15,baseline,font,right=True)
        p.end()

    def mousePressEvent(self,event):
        if self.locked:return
        if event.button()==Qt.MouseButton.RightButton:self.owner.show_settings();return
        if event.button()!=Qt.MouseButton.LeftButton:return
        if QRectF(self.width()-112,38,100,25).contains(event.position()):self.owner.percent.toggle();return
        self.drag_origin=event.globalPosition().toPoint()-self.pos()

    def mouseMoveEvent(self,event):
        if self.drag_origin is not None and not self.locked:
            self.move(event.globalPosition().toPoint()-self.drag_origin)

    def mouseReleaseEvent(self,event):
        self.drag_origin=None;self.owner.save()


class Window(QWidget):
    def __init__(self, smoke=False):
        super().__init__();self.smoke=smoke;self.model=Model();self.pool=ThreadPoolExecutor(max_workers=1)
        self.bus=Bus();self.bus.result.connect(self.receive);self.bus.windows.connect(self.received_windows)
        self.bus.failed.connect(self.failed);self.bus.hotkey.connect(self.action)
        self.busy=False;self.closing=False;self.capture=None;self.reader=MacHudReader(vision=True);self.pickup=PickupReader();self.reader_key=None
        self.last_preview=None
        self.frame_size=None;self.conf={};self.hotkeys=None;self.last_undo=None
        self.data=Path(os.environ.get('MMC_TEST_DATA',str(Path.home()/'Library/Application Support/MapleMeterChecker')))
        self.data.mkdir(parents=True,exist_ok=True)
        try:self.conf=json.loads((self.data/'settings.json').read_text())
        except (OSError,ValueError):pass
        if not isinstance(self.conf,dict):self.conf={}
        self.font_family='Helvetica Neue'
        for name in ('Pretendard-Bold.otf','Pretendard-ExtraBold.otf'):
            ident=QFontDatabase.addApplicationFont(str(ASSETS/name))
            if ident>=0:self.font_family=QFontDatabase.applicationFontFamilies(ident)[0]
        self.setWindowTitle('Maple meter checker · Mac 테스트 버전')
        self.setWindowIcon(QIcon(str(ASSETS/'checker.png')));self.resize(760,760)
        self.setStyleSheet('QWidget {background:#10171C;color:#F6F6F3;font-size:13px;} '
            'QPushButton,QComboBox,QLineEdit,QSpinBox {background:#25323C;border:1px solid #43545F;border-radius:5px;padding:7px;} '
            'QPushButton:hover {background:#354955;} QTabWidget::pane {border:1px solid #354955;} '
            'QTabBar::tab {padding:10px 18px;} QTabBar::tab:selected {background:#25323C;} '
            'QCheckBox {padding:5px;} QSlider::groove:horizontal {background:#43545F;height:5px;} '
            'QSlider::handle:horizontal {background:#EAB38B;width:16px;margin:-5px 0;border-radius:5px;}')
        outer=QVBoxLayout(self);outer.setContentsMargins(24,20,24,20);outer.setSpacing(14)
        title=QLabel('Maple meter checker  /  Mac');title.setStyleSheet('font-size:26px;font-weight:bold;color:#EAB38B;');outer.addWidget(title)
        outer.addWidget(QLabel('CrossOver 게임 창을 선택해 경험치와 메소를 확인하세요.  ·  테스트 버전'))
        row=QHBoxLayout();self.permission_button=QPushButton('1. 화면 기록 권한');self.permission_button.clicked.connect(self.permission)
        self.refresh_button=QPushButton('2. 창 목록 새로고침');self.refresh_button.clicked.connect(self.refresh_windows)
        row.addWidget(self.permission_button);row.addWidget(self.refresh_button);outer.addLayout(row)
        self.windows=QComboBox();self.windows.addItem('게임 창을 선택하세요',None);self.windows.currentIndexChanged.connect(self.target_changed);outer.addWidget(self.windows)
        self.status=QLabel('화면 기록 권한을 허용하고 게임 창을 선택하세요.');self.status.setWordWrap(True);outer.addWidget(self.status)
        tabs=QTabWidget();self.tabs=tabs;outer.addWidget(tabs)
        page=QWidget();layout=QVBoxLayout(page);self.metrics={}
        selected=selected_metrics(self.conf)
        for key,label in METRICS.items():
            cb=QCheckBox(label);cb.setChecked(key in selected);cb.toggled.connect(self.changed);self.metrics[key]=cb;layout.addWidget(cb)
        self.percent=QCheckBox('경험치를 %로 표시');self.percent.setChecked(bool(self.conf.get('percent',False)));self.percent.toggled.connect(self.changed);layout.addWidget(self.percent)
        layout.addWidget(QLabel('분당·30분·1시간과 레벨업 시간은 평균 속도 기준 예상치입니다.\n메소 +α는 누락 가능성을 뜻하며 누락량을 임의로 더하지 않습니다.'));layout.addStretch();tabs.addTab(page,'표시 항목')
        page=QWidget();form=QFormLayout(page)
        self.font_size=QSpinBox();self.font_size.setRange(8,26);self.font_size.setValue(self.number('font_size',16,8,26));self.font_size.valueChanged.connect(self.changed);form.addRow('글자 크기',self.font_size)
        self.bg_alpha=self.slider(self.number('background_opacity',80,0,100),0);form.addRow('배경 불투명도',self.bg_alpha)
        self.text_alpha=self.slider(self.number('text_opacity',100,10,100),10);form.addRow('글자 불투명도',self.text_alpha)
        self.show_panel=QCheckBox('패널 표시');self.show_panel.setChecked(True);self.show_panel.toggled.connect(self.changed);form.addRow(self.show_panel)
        self.preview=QCheckBox('시작 전 패널 미리보기');self.preview.toggled.connect(self.changed);form.addRow(self.preview)
        self.locked=QCheckBox('위치 잠금 / 클릭 통과');self.locked.toggled.connect(self.changed);form.addRow(self.locked)
        recover=QPushButton('패널 위치 되돌리기');recover.clicked.connect(self.recover);form.addRow(recover)
        form.addRow(QLabel('패널은 게임 밖과 다른 모니터로 자유롭게 옮길 수 있습니다.'));tabs.addTab(page,'패널 모양')
        page=QWidget();form=QFormLayout(page);self.key_inputs={};mapping=self.conf.get('hotkeys',DEFAULT_KEYS)
        for key,value in DEFAULT_KEYS.items():
            edit=QLineEdit(mapping.get(key,value));self.key_inputs[key]=edit;form.addRow(KEY_LABELS[key],edit)
        apply=QPushButton('단축키 적용');apply.clicked.connect(self.apply_keys);form.addRow(apply)
        self.key_status=QLabel('Ctrl = Control · Alt = Option · Cmd = Command');self.key_status.setWordWrap(True);form.addRow(self.key_status);tabs.addTab(page,'단축키')
        page=QWidget();form=QFormLayout(page);self.edges=[]
        saved_edges=self.conf.get('crop_edges',[0,0,0,0])
        if not isinstance(saved_edges,list) or len(saved_edges)!=4:saved_edges=[0,0,0,0]
        for index,label in enumerate(('왼쪽','위쪽','오른쪽','아래쪽')):
            spin=QDoubleSpinBox();spin.setRange(0,30);spin.setDecimals(2);spin.setSingleStep(.1);spin.setSuffix(' %')
            try:spin.setValue(float(saved_edges[index]))
            except (ValueError,TypeError):pass
            spin.valueChanged.connect(self.target_changed);self.edges.append(spin);form.addRow(label+' 제외 여백',spin)
        helptext=QLabel('우선 여백 0%로 시도하세요. 아래 미리보기에 게임 하단 경험치 숫자가 보여야 합니다.\n검은 여백이 있을 때만 조절하세요. 변경하면 측정이 일시정지됩니다.');helptext.setWordWrap(True);form.addRow(helptext)
        clear_edges=QPushButton('여백 0%로 되돌리기');clear_edges.clicked.connect(self.clear_edges);form.addRow(clear_edges)
        self.capture_preview=QLabel('게임 창을 선택하면 실제로 읽는 하단 화면이 여기에 표시됩니다.')
        self.capture_preview.setMinimumSize(400,90);self.capture_preview.setMaximumHeight(130)
        self.capture_preview.setAlignment(Qt.AlignmentFlag.AlignCenter);self.capture_preview.setWordWrap(True);form.addRow(self.capture_preview)
        self.preview_info=QLabel('미리보기는 이 기기 안에서만 표시됩니다.');self.preview_info.setWordWrap(True);form.addRow(self.preview_info)
        self.save_preview=QPushButton('진단용 하단 화면을 PNG로 저장');self.save_preview.setEnabled(False);self.save_preview.clicked.connect(self.export_preview);form.addRow(self.save_preview)
        crop_scroll=QScrollArea();crop_scroll.setWidgetResizable(True);crop_scroll.setWidget(page);tabs.addTab(crop_scroll,'인식 영역')
        row=QHBoxLayout();self.start=QPushButton('측정 시작');self.start.clicked.connect(lambda:self.action('toggle'))
        reset=QPushButton('초기화');reset.clicked.connect(lambda:self.action('reset'));self.undo=QPushButton('초기화 취소');self.undo.clicked.connect(self.undo_reset);self.undo.setEnabled(False)
        row.addWidget(reset);row.addWidget(self.undo);row.addStretch();row.addWidget(self.start);outer.addLayout(row)
        note=QLabel('화면은 이 기기 안에서만 처리합니다. 진단 PNG는 저장 버튼을 누른 경우에만 저장하며 자동 전송하지 않습니다.');note.setWordWrap(True);outer.addWidget(note)
        self.overlay=Overlay(self)
        pos=self.conf.get('position')
        if isinstance(pos,list) and len(pos)==2:
            try:self.overlay.move(int(pos[0]),int(pos[1]))
            except (ValueError,TypeError):pass
        self.ensure_reachable()
        self.timer=QTimer(self);self.timer.timeout.connect(self.tick);self.timer.start(500)
        if not smoke:
            from mac_capture import Capture
            self.capture=Capture()
            try:self.hotkeys=Hotkeys(self.bus.hotkey.emit);self.apply_keys()
            except Exception as error:self.key_status.setText(str(error)+' · 화면 버튼은 사용할 수 있습니다.')

    def number(self,key,default,lo,hi):
        try:return max(lo,min(hi,int(self.conf.get(key,default))))
        except (ValueError,TypeError):return default

    def slider(self,value,minimum):
        slider=QSlider(Qt.Orientation.Horizontal);slider.setRange(minimum,100);slider.setValue(value);slider.valueChanged.connect(self.changed);return slider

    def permission(self):
        from mac_capture import request_permission
        allowed=request_permission()
        self.status.setText('권한이 허용됐습니다. 창 목록을 새로고침하세요.' if allowed else '시스템 설정 → 개인정보 보호 및 보안 → 화면 및 시스템 오디오 기록에서 이 앱을 허용하고 다시 실행하세요.')

    def refresh_windows(self):
        if self.busy or self.capture is None:return
        self.busy=True;self.refresh_button.setEnabled(False);self.status.setText('선택 가능한 창을 확인하는 중…')
        self.pool.submit(self.list_job)

    def list_job(self):
        try:self.bus.windows.emit(self.capture.refresh())
        except Exception as error:self.bus.failed.emit((None,str(error)))

    def received_windows(self,choices):
        self.busy=False;self.refresh_button.setEnabled(True);old=self.windows.currentData()
        self.windows.blockSignals(True);self.windows.clear();self.windows.addItem('게임 창을 선택하세요',None)
        for ident,label in choices:self.windows.addItem(label,ident)
        index=self.windows.findData(old)
        if index>=0:self.windows.setCurrentIndex(index)
        self.windows.blockSignals(False)
        if self.windows.currentData()!=old:self.target_changed()
        self.status.setText('CrossOver에서 실행한 MapleStory 게임 창을 선택하세요.' if choices else '보이는 창이 없습니다. 게임을 실행하고 최소화를 해제하세요.')

    def target_changed(self,*_):
        self.model.session.pause(time.monotonic());self.model.invalidate();self.last_undo=None
        self.last_preview=None
        if hasattr(self,'capture_preview'):
            self.capture_preview.clear();self.capture_preview.setText('새 영역을 확인하는 중…');self.save_preview.setEnabled(False)
        if hasattr(self,'status'):self.status.setText('선택한 영역의 경험치를 확인하는 중…')
        if hasattr(self,'overlay'):self.save()

    def capture_job(self,ident,edges,generation):
        try:
            image,at=self.capture.image(ident);image=crop_frame(image,edges)
            key=(ident,edges)
            if self.reader_key!=key:self.reader=MacHudReader(vision=True);self.pickup=PickupReader();self.reader_key=key
            value=self.reader.read_image(image)
            lines=self.pickup.read(image,self.reader.factor)
            self.bus.result.emit(dict(generation=generation,at=at,value=value,lines=lines,resized=self.pickup.changed,
                size=image.size,preview=hud_preview(image),factor=self.reader.factor,backend=self.capture.backend,
                recognition=self.reader.source,recognition_note=self.reader.note))
        except Exception as error:self.bus.failed.emit((generation,str(error)))

    def receive(self,packet):
        self.busy=False
        if not self.model.feed(packet):return
        self.frame_size=packet['size']
        preview=packet.get('preview')
        if preview is not None:
            self.last_preview=preview
            qimage=QImage(preview.tobytes(),preview.width,preview.height,preview.width*3,QImage.Format.Format_RGB888).copy()
            self.capture_preview.setPixmap(QPixmap.fromImage(qimage).scaled(650,120,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
            factor=packet.get('factor');scale=f'{factor:.3g}배' if factor else '확인 중'
            self.preview_info.setText(f"캡처 {self.frame_size[0]}×{self.frame_size[1]} · {packet.get('recognition') or '문자 탐색 중'} · 배율 {scale} · {VERSION}\n{packet.get('recognition_note','')}")
            self.save_preview.setEnabled(True)
        if packet['value']:
            n,pct=packet['value'];text=f'EXP {n:,} · {pct:.2f}% · 화면 {self.frame_size[0]}×{self.frame_size[1]}'
            if self.model.pickups.uncertain:text+=' · 메소 메시지 누락 가능'
            if self.model.session.warning:text+=' · '+self.model.session.warning
            self.status.setText(text)
        else:self.status.setText(f'화면 {self.frame_size[0]}×{self.frame_size[1]} 수신 · 경험치 숫자 확인 중. 인식 영역 탭의 하단 화면을 확인하세요.')

    def clear_edges(self):
        for spin in self.edges:spin.setValue(0)

    def export_preview(self):
        if self.last_preview is None:return
        # Freeze the user-reviewed frame while the save dialog is open.
        preview=self.last_preview.copy()
        filename,_=QFileDialog.getSaveFileName(self,'진단용 하단 화면 저장',str(Path.home()/'Desktop/MapleMeterChecker-HUD.png'),'PNG 이미지 (*.png)')
        if not filename:return
        try:
            preview.save(filename,format='PNG')
            self.status.setText('선택한 하단 화면만 PNG로 저장했습니다. 자동 전송하지 않습니다.')
        except OSError as error:self.status.setText(f'PNG 저장 실패: {error}')

    def failed(self,error):
        self.busy=False;self.refresh_button.setEnabled(True)
        generation,message=error
        if generation is None or generation==self.model.generation:self.status.setText(message)

    def tick(self):
        if self.closing:return
        now=time.monotonic()
        if self.last_undo and now-self.last_undo[0]>=8:self.last_undo=None
        self.undo.setEnabled(self.last_undo is not None)
        self.start.setText('일시정지' if self.model.session.running else ('계속 측정' if self.model.session.started else '측정 시작'))
        self.start.setEnabled(self.model.session.running or (any(cb.isChecked() for cb in self.metrics.values()) and self.model.reading is not None and self.model.reading.level is not None and now-self.model.last_good<3))
        visible=self.show_panel.isChecked() and (self.model.session.started or self.preview.isChecked())
        if visible and not self.overlay.isVisible():self.overlay.show();self.overlay.apply_native_flags()
        elif not visible:self.overlay.hide()
        self.overlay.refresh()
        if self.capture and self.windows.currentData() is not None and not self.busy:
            self.busy=True
            self.pool.submit(self.capture_job,self.windows.currentData(),tuple(s.value() for s in self.edges),self.model.generation)

    def action(self,name):
        if name=='settings':self.show_settings();return
        if name=='lock':self.locked.toggle();return
        if name=='units':self.percent.toggle();return
        now=time.monotonic()
        if name=='reset':
            import copy
            self.last_undo=(now,copy.deepcopy(self.model.session))
            self.model.reset(now);self.status.setText('초기화했습니다. 8초 동안 취소할 수 있습니다.');return
        try:self.model.toggle(now)
        except ValueError as error:self.status.setText(str(error))

    def undo_reset(self):
        if not self.last_undo or time.monotonic()-self.last_undo[0]>=8:return
        _,old=self.last_undo;current=self.model.session;now=time.monotonic()
        old.gained+=current.gained;old.percent_gained+=current.percent_gained;old.meso+=current.meso
        old.meso_seen|=current.meso_seen;old.current=current.current or old.current
        # Preserve elapsed pre-reset time and include only the time actually
        # measured after reset, including pauses in that interval.
        old.seconds=old.elapsed(self.last_undo[0])+current.elapsed(now)
        old.running=current.running;old.clock=now if old.running else None
        self.model.session=old;self.last_undo=None
        self.model.generation+=1;self.model.after=now
        self.status.setText('초기화를 취소했습니다.')

    def changed(self,*_):
        if not hasattr(self,'overlay'):return
        self.overlay.set_locked(self.locked.isChecked());self.overlay.refresh();self.save()

    def apply_keys(self):
        if self.hotkeys is None:return
        mapping={k:edit.text().strip() for k,edit in self.key_inputs.items()}
        try:
            failed=self.hotkeys.update(mapping)
            self.key_status.setText('충돌한 단축키: '+', '.join(KEY_LABELS[k] for k in failed) if failed else '단축키 적용 완료 · Alt = Option, Ctrl = Control')
            self.save()
        except (ValueError,RuntimeError) as error:self.key_status.setText(str(error))

    def ensure_reachable(self):
        header=self.overlay.geometry();header.setHeight(35)
        if not any(s.availableGeometry().intersects(header) for s in QApplication.screens()):self.recover()

    def recover(self):
        area=QApplication.primaryScreen().availableGeometry();self.overlay.move(area.x()+60,area.y()+80);self.locked.setChecked(False);self.save()

    def show_settings(self):self.showNormal();self.raise_();self.activateWindow()

    def save(self):
        if not hasattr(self,'overlay'):return
        conf=dict(metrics_revision=2,metrics=[k for k,cb in self.metrics.items() if cb.isChecked()],percent=self.percent.isChecked(),
                  font_size=self.font_size.value(),background_opacity=self.bg_alpha.value(),text_opacity=self.text_alpha.value(),
                  position=[self.overlay.x(),self.overlay.y()],hotkeys={k:e.text().strip() for k,e in self.key_inputs.items()},
                  crop_edges=[s.value() for s in self.edges])
        try:
            temp=self.data/'settings.tmp';temp.write_text(json.dumps(conf,ensure_ascii=False),encoding='utf-8');temp.replace(self.data/'settings.json')
        except OSError:self.status.setText('설정을 저장하지 못했습니다. 저장 공간을 확인하세요.')

    def closeEvent(self,event):
        self.closing=True;self.timer.stop();self.save();self.overlay.close()
        if self.hotkeys:self.hotkeys.close()
        self.pool.shutdown(wait=False,cancel_futures=True);event.accept();QApplication.quit()


def main():
    smoke='--smoke-test' in sys.argv
    if not smoke and sys.platform!='darwin':raise SystemExit('This application is for macOS 13 or later.')
    app=QApplication(sys.argv);app.setApplicationName('Maple meter checker');app.setQuitOnLastWindowClosed(False)
    directory=Path(os.environ.get('MMC_TEST_DATA',str(Path.home()/'Library/Application Support/MapleMeterChecker')))
    directory.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(directory/'app.lock'));lock.setStaleLockTime(30000)
    if not lock.tryLock(100):
        QMessageBox.information(None,'Maple meter checker','이미 실행 중입니다. Dock에서 앱을 선택하세요.');return 0
    window=Window(smoke);window.show()
    if smoke:
        window.preview.setChecked(True)
        def finish():
            try:
                window.bg_alpha.setValue(0);window.font_size.setValue(8);window.overlay.refresh()
                assert window.overlay.width()>=350
                assert len(window.metrics)==10
                assert window.overlay.grab().width()>0
                from PIL import Image
                from PIL.ImageDraw import Draw
                if sys.platform=='darwin':
                    from PIL import ImageFont
                    from mac_vision import recognize,text_rows,parse_exp_line
                    ocr_sample=Image.new('RGB',(1000,300),(25,40,60))
                    font=ImageFont.truetype(str(ASSETS/'Pretendard-Bold.otf'),24)
                    Draw(ocr_sample).text((500,250),'EXP. 414,000 [63.18%]',font=font,fill='white')
                    assert (414000,63.18) in [parse_exp_line(row) for row in text_rows(recognize(ocr_sample))]
                    print('MAC_VISION_SMOKE_OK',flush=True)
                sample=Image.new('RGB',(1000,158),(25,40,60));Draw(sample).text((600,100),'EXP 143,519 [25.83%]',fill='white')
                window.receive(dict(generation=window.model.generation,at=time.monotonic(),value=(143519,25.83),
                    lines=[],resized=False,size=(1000,748),preview=sample,factor=1.,backend='smoke-test'))
                assert window.save_preview.isEnabled() and not window.capture_preview.pixmap().isNull()
                window.tabs.setCurrentIndex(3);app.processEvents()
                if os.environ.get('MMC_SMOKE_IMAGE'):window.grab().save(os.environ['MMC_SMOKE_IMAGE'])
                print('MAC_APP_SMOKE_OK',flush=True)
                window.close()
            except Exception:
                import traceback;traceback.print_exc();os._exit(1)
        QTimer.singleShot(1500,finish)
    result=app.exec();lock.unlock();return result


if __name__=='__main__':sys.exit(main())
