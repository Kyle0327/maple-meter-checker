"""One meter per desktop session, so global shortcuts cannot collide."""
import ctypes
from ctypes import wintypes

def acquire_instance():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR]
    kernel.CreateMutexW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateMutexW(None,False,'Local\\MapleMeterChecker.Desktop')
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    if ctypes.get_last_error()==183:
        kernel.CloseHandle(handle)
        u=ctypes.windll.user32
        u.FindWindowW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR];u.FindWindowW.restype=wintypes.HWND
        u.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int]
        u.SetForegroundWindow.argtypes=[wintypes.HWND]
        hwnd=u.FindWindowW(None,'Maple meter checker · 설정')
        if hwnd:
            u.ShowWindow(hwnd,9);u.SetForegroundWindow(hwnd)
        else:u.MessageBoxW(None,'이미 실행 중입니다. 잠시 후 설정 창을 확인해 주세요.','Maple meter checker',0x40)
        return None
    return handle
