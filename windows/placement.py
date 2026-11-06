"""Desktop placement including monitors with negative coordinates."""
import ctypes
from ctypes import wintypes

def clamp_desktop(x,y,width,height,areas):
    if not areas:return int(x),int(y)
    left=min(r[0] for r in areas);top=min(r[1] for r in areas)
    right=max(r[2] for r in areas);bottom=max(r[3] for r in areas)
    x=max(left,min(x,right-width));y=max(top,min(y,bottom-height))
    # Keep the header reachable even when monitors form a staggered layout.
    if not any(x+width>l and x<r and y+26>t and y<b for l,t,r,b in areas):
        area=min(areas,key=lambda a:max(a[0]-x,0,x-a[2])**2+max(a[1]-y,0,y-a[3])**2)
        l,t,r,b=area;x=max(l,min(x,r-width));y=max(t,min(y,b-height))
    return int(x),int(y)

def monitor_areas():
    u=ctypes.windll.user32;areas=[]
    class Info(ctypes.Structure):
        _fields_=[('size',wintypes.DWORD),('monitor',wintypes.RECT),('work',wintypes.RECT),('flags',wintypes.DWORD)]
    callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HANDLE,wintypes.HDC,ctypes.POINTER(wintypes.RECT),wintypes.LPARAM)
    u.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Info)]
    def visit(handle,dc,rect,data):
        info=Info();info.size=ctypes.sizeof(Info)
        if u.GetMonitorInfoW(handle,ctypes.byref(info)):
            r=info.work;areas.append((r.left,r.top,r.right,r.bottom))
        return True
    u.EnumDisplayMonitors(None,None,callback(visit),0)
    return areas
