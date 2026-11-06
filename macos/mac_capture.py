"""Capture only the window explicitly selected by the user (macOS 14+)."""
import io
import os
import threading
import time
from PIL import Image


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

    def refresh(self):
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

    def image(self, ident):
        import ScreenCaptureKit as SC
        import Quartz
        import Foundation
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
            data = Foundation.NSMutableData.data()
            destination = Quartz.CGImageDestinationCreateWithData(data, 'public.png', 1, None)
            Quartz.CGImageDestinationAddImage(destination, cgimage, None)
            if not Quartz.CGImageDestinationFinalize(destination):
                raise RuntimeError('화면 이미지 변환에 실패했습니다.')
            image = Image.open(io.BytesIO(bytes(data))).convert('RGB')
            return image, captured_at
