"""Application-private fonts; no installation or system settings changes."""
import ctypes
from ctypes import wintypes
from pathlib import Path

def load_fonts():
    gdi=ctypes.windll.gdi32
    gdi.AddFontResourceExW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p]
    return sum(gdi.AddFontResourceExW(str(Path(__file__).with_name(name)),0x10,None)
        for name in ('Pretendard-Bold.otf','Pretendard-ExtraBold.otf'))

def apply_icons(window):
    import tkinter as tk
    folder=Path(__file__).parent
    window.iconbitmap(default=str(folder/'checker.ico'))
    window._brand_icon=tk.PhotoImage(file=str(folder/'checker.png'))
    window.iconphoto(True,window._brand_icon)
