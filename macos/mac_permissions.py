"""Screen Recording permission guidance and user-invoked, app-only reset."""
import platform
import subprocess
from pathlib import Path

BUNDLE_ID='com.kyle0327.maplemeterchecker'
SETTINGS_URL='x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture'


def settings_label(version=None):
    version=platform.mac_ver()[0] if version is None else version
    try:major=int(version.split('.')[0])
    except (ValueError,AttributeError):major=13
    return '화면 기록 (Screen Recording)' if major<=13 else '화면 및 시스템 오디오 기록 (Screen & System Audio Recording)'


def bundle_path():
    import Foundation
    return str(Foundation.NSBundle.mainBundle().bundlePath())


def reset_screen_permission(path):
    # Never reset all applications, grant access, or modify the TCC database.
    # The caller must obtain the user's explicit confirmation first.
    if 'AppTranslocation' in Path(path).parts:
        raise RuntimeError('먼저 앱을 응용 프로그램 폴더로 옮긴 뒤 그 앱을 다시 실행하세요.')
    result=subprocess.run(['/usr/bin/tccutil','reset','ScreenCapture',BUNDLE_ID],
                          capture_output=True,text=True,timeout=10)
    if result.returncode:
        raise RuntimeError('권한 기록을 초기화하지 못했습니다. 화면 기록 목록에서 이 앱 항목을 제거한 뒤 다시 허용해 주세요.')
