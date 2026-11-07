import contextlib
import os
import sys
import types
import unittest
from unittest.mock import patch,Mock
from mac_capture import Capture,capture_backend


class VenturaTests(unittest.TestCase):
    def test_version_routes_without_touching_new_apis(self):
        self.assertEqual(capture_backend('13.0'),'coregraphics')
        self.assertEqual(capture_backend('13.7.6'),'coregraphics')
        self.assertEqual(capture_backend('14.0'),'screencapturekit')
        self.assertEqual(capture_backend('26.0'),'screencapturekit')
        for version in ('12.7','',None):
            with patch('mac_capture.platform.mac_ver',return_value=('',(),'')):
                with self.assertRaises(RuntimeError):capture_backend(version)

    def quartz(self):
        q=types.SimpleNamespace()
        for name in ('kCGWindowBounds','kCGWindowOwnerPID','kCGWindowLayer','kCGWindowNumber','kCGWindowOwnerName','kCGWindowName'):
            setattr(q,name,name)
        for i,name in enumerate(('kCGWindowListOptionOnScreenOnly','kCGWindowListExcludeDesktopElements','kCGWindowListOptionIncludingWindow','kCGWindowImageBoundsIgnoreFraming','kCGWindowImageBestResolution')):
            setattr(q,name,1<<i)
        q.kCGNullWindowID=0;q.CGRectNull='NULL_RECT';q.CGPreflightScreenCaptureAccess=lambda:True
        def entry(ident,pid=99999,layer=0,width=800):
            return {q.kCGWindowNumber:ident,q.kCGWindowOwnerPID:pid,q.kCGWindowLayer:layer,
                q.kCGWindowBounds:{'Width':width,'Height':600},q.kCGWindowOwnerName:'CrossOver',q.kCGWindowName:'MapleStory'}
        q.CGWindowListCopyWindowInfo=Mock(return_value=[entry(42),entry(43,os.getpid()),entry(44,layer=3),entry(45,width=100)])
        q.CGWindowListCreateImage=Mock(return_value='image')
        return q

    def test_only_selected_visible_game_window_is_captured(self):
        q=self.quartz();objc=types.SimpleNamespace(autorelease_pool=contextlib.nullcontext)
        # A missing ScreenCaptureKit module proves the Ventura path is isolated.
        with patch.dict(sys.modules,{'Quartz':q,'objc':objc,'ScreenCaptureKit':None}),patch('mac_capture.capture_backend',return_value='coregraphics'):
            c=Capture();self.assertEqual(c.refresh(),[(42,'CrossOver — MapleStory')])
            with patch.object(c,'convert_image',return_value='converted'):
                self.assertEqual(c.image(42)[0],'converted')
            q.CGWindowListCreateImage.assert_called_once_with(q.CGRectNull,q.kCGWindowListOptionIncludingWindow,42,
                q.kCGWindowImageBoundsIgnoreFraming|q.kCGWindowImageBestResolution)

    def test_closed_window_does_not_fall_back_to_desktop(self):
        q=self.quartz()
        with patch.dict(sys.modules,{'Quartz':q,'objc':types.SimpleNamespace(autorelease_pool=contextlib.nullcontext)}),patch('mac_capture.capture_backend',return_value='coregraphics'):
            c=Capture()
            with self.assertRaises(RuntimeError):c.image(1000)
            q.CGWindowListCreateImage.assert_not_called()

    def test_denied_permission_prevents_capture(self):
        q=self.quartz();q.CGPreflightScreenCaptureAccess=lambda:False
        with patch.dict(sys.modules,{'Quartz':q}),patch('mac_capture.capture_backend',return_value='coregraphics'):
            with self.assertRaises(RuntimeError):Capture().refresh()
            q.CGWindowListCopyWindowInfo.assert_not_called()

    def test_newer_macos_keeps_screenshotkit_path(self):
        with patch('mac_capture.capture_backend',return_value='screencapturekit'):
            self.assertEqual(Capture().backend,'screencapturekit')

if __name__=='__main__':unittest.main()
