"""Selected-window capture: CoreGraphics on Ventura, ScreenCaptureKit on 14+."""
import io
import os
import platform
import threading
import time
from PIL import Image


def capture_backend(version=None):
    version=platform.mac_ver()[0] if version is None else version
    try:major=int(version.split('.')[0])
    except (ValueError,AttributeError):raise RuntimeError('macOS 버전을 확인할 수 없습니다.')
    if major<13:raise RuntimeError('macOS Ventura 13 이상이 필요합니다.')
    return 'coregraphics' if major==13 else 'screencapturekit'


def has_permission():
    import Quartz
    return bool(Quartz.CGPreflightScreenCaptureAccess())


def request_permission():
    import Quartz
    return bool(Quartz.CGRequestScreenCaptureAccess())


def await_result(start, timeout=12):
    event = threading.Event()
    result = []
    def done(value, error):
        result.extend((value, error))
        event.set()
    start(done)
    if not event.wait(timeout):
        raise RuntimeError('화면 응답이 늦습니다. 게임 창과 화면 기록 권한을 확인하세요.')
    value, error = result
    if error:
        raise RuntimeError(str(error.localizedDescription()))
    if value is None:
        raise RuntimeError('화면 데이터를 받지 못했습니다.')
    return value


class Capture:
    def __init__(self):
        self.windows = {}
        self.backend = capture_backend()

    def refresh(self):
        if self.backend=='coregraphics':return self.refresh_ventura()
        import ScreenCaptureKit as SC
        import objc
        if not has_permission():
            raise RuntimeError('먼저 화면 기록 권한을 허용한 뒤 앱을 다시 여세요.')
        with objc.autorelease_pool():
            content = await_result(lambda done: SC.SCShareableContent.
                getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(True, True, done))
            windows = {}
            choices = []
            for window in content.windows():
                app = window.owningApplication()
                frame = window.frame()
                if app is None or app.processID() == os.getpid() or frame.size.width < 300 or frame.size.height < 200:
                    continue
                ident = int(window.windowID())
                title = str(window.title() or '(제목 없음)')
                label = f'{app.applicationName()} — {title}'
                windows[ident] = window
                choices.append((ident, label))
            self.windows = windows
            return sorted(choices, key=lambda item: ('maple' not in item[1].lower(), item[1].lower()))

    def refresh_ventura(self):
        import Quartz as Q
        if not has_permission():
            raise RuntimeError('먼저 화면 기록 권한을 허용한 뒤 앱을 다시 여세요.')
        entries=Q.CGWindowListCopyWindowInfo(Q.kCGWindowListOptionOnScreenOnly|Q.kCGWindowListExcludeDesktopElements,Q.kCGNullWindowID) or []
        windows={};choices=[]
        for entry in entries:
            bounds=entry.get(Q.kCGWindowBounds,{})
            if (entry.get(Q.kCGWindowOwnerPID)==os.getpid() or entry.get(Q.kCGWindowLayer,0)!=0
                    or bounds.get('Width',0)<300 or bounds.get('Height',0)<200):continue
            ident=int(entry[Q.kCGWindowNumber]);windows[ident]=entry
            choices.append((ident,f"{entry.get(Q.kCGWindowOwnerName,'앱')} — {entry.get(Q.kCGWindowName) or '(제목 없음)'}"))
        self.windows=windows
        return sorted(choices,key=lambda item:('maple' not in item[1].lower(),item[1].lower()))

    @staticmethod
    def convert_image(cgimage):
        import Quartz
        import Foundation
        if cgimage is None:
            raise RuntimeError('게임 창을 캡처하지 못했습니다. 화면 기록 권한과 창 최소화 여부를 확인하세요.')
        data=Foundation.NSMutableData.data()
        destination=Quartz.CGImageDestinationCreateWithData(data,'public.png',1,None)
        if destination is None:raise RuntimeError('화면 이미지 변환을 준비하지 못했습니다.')
        Quartz.CGImageDestinationAddImage(destination,cgimage,None)
        if not Quartz.CGImageDestinationFinalize(destination):
            raise RuntimeError('화면 이미지 변환에 실패했습니다.')
        return Image.open(io.BytesIO(bytes(data))).convert('RGB')

    def image_ventura(self,ident):
        import Quartz as Q
        import objc
        self.refresh_ventura()
        if ident not in self.windows:
            raise RuntimeError('선택한 게임 창이 닫히거나 최소화됐습니다. 창 목록을 새로고침하세요.')
        with objc.autorelease_pool():
            captured_at=time.monotonic()
            # IncludingWindow captures this exact ID, not the desktop or
            # overlapping overlay windows. This API is used only on macOS 13.
            cgimage=Q.CGWindowListCreateImage(Q.CGRectNull,Q.kCGWindowListOptionIncludingWindow,
                ident,Q.kCGWindowImageBoundsIgnoreFraming|Q.kCGWindowImageBestResolution)
            return self.convert_image(cgimage),captured_at

    def image(self, ident):
        if self.backend=='coregraphics':return self.image_ventura(ident)
        import ScreenCaptureKit as SC
        import Quartz
        import objc
        if not has_permission():
            raise RuntimeError('화면 기록 권한이 없습니다. 설정에서 확인하세요.')
        # Refresh metadata on every frame: window resolution and Retina scale
        # can change without the selected window ID changing.
        self.refresh()
        window = self.windows.get(ident)
        if window is None:
            raise RuntimeError('선택한 게임 창이 닫히거나 최소화됐습니다. 창 목록을 새로고침하세요.')
        with objc.autorelease_pool():
            filt = SC.SCContentFilter.alloc().initWithDesktopIndependentWindow_(window)
            rect = filt.contentRect()
            scale = float(filt.pointPixelScale())
            cfg = SC.SCStreamConfiguration.alloc().init()
            cfg.setWidth_(max(1, round(rect.size.width * scale)))
            cfg.setHeight_(max(1, round(rect.size.height * scale)))
            cfg.setShowsCursor_(False)
            cfg.setCapturesAudio_(False)
            cfg.setIgnoreShadowsSingleWindow_(True)
            captured_at = time.monotonic()
            cgimage = await_result(lambda done: SC.SCScreenshotManager.
                captureImageWithFilter_configuration_completionHandler_(filt, cfg, done))
            return self.convert_image(cgimage), captured_at
