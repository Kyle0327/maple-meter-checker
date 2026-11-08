import subprocess
import unittest
from unittest.mock import patch
from mac_permissions import settings_label,reset_screen_permission,BUNDLE_ID


class PermissionTests(unittest.TestCase):
    def test_ventura_uses_actual_screen_recording_menu_name(self):
        self.assertEqual(settings_label('13.7'),'화면 기록 (Screen Recording)')
        self.assertIn('시스템 오디오',settings_label('14.0'))

    def test_reset_is_limited_to_this_apps_screen_permission(self):
        with patch('mac_permissions.subprocess.run',return_value=subprocess.CompletedProcess([],0)) as run:
            reset_screen_permission('/Applications/MapleMeterChecker.app')
        self.assertEqual(run.call_args.args[0],['/usr/bin/tccutil','reset','ScreenCapture',BUNDLE_ID])
        self.assertFalse(run.call_args.kwargs.get('shell',False))

    def test_reset_failure_does_not_report_success(self):
        with patch('mac_permissions.subprocess.run',return_value=subprocess.CompletedProcess([],1)):
            with self.assertRaises(RuntimeError):reset_screen_permission('/Applications/MapleMeterChecker.app')

    def test_translocated_app_requires_installation_first(self):
        with patch('mac_permissions.subprocess.run') as run:
            with self.assertRaises(RuntimeError):reset_screen_permission('/private/var/folders/x/AppTranslocation/id/d/MapleMeterChecker.app')
            run.assert_not_called()
