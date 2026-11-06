import ctypes
from ctypes import wintypes
import queue
import threading
from presentation import DEFAULT_KEYS,parse_hotkey,validate_hotkeys

class Hotkeys:
    def __init__(self,mapping):
        self.events=queue.Queue();self.commands=queue.Queue();self.tid=None
        self.mapping=dict(mapping);self.ready=threading.Event()
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()

    def update(self,mapping):
        validate_hotkeys(mapping);self.commands.put(dict(mapping))
        if self.tid:ctypes.windll.user32.PostThreadMessageW(self.tid,0x8001,0,0)

    def run(self):
        u=ctypes.windll.user32;msg=wintypes.MSG();registered=[]
        self.tid=ctypes.windll.kernel32.GetCurrentThreadId()
        u.PeekMessageW(ctypes.byref(msg),None,0,0,0);self.ready.set()
        def register(mapping):
            for key in registered:u.UnregisterHotKey(None,key)
            registered.clear();failed=[]
            for i,name in enumerate(DEFAULT_KEYS):
                mods,vk=parse_hotkey(mapping[name]);ident=0x6b00+i
                if u.RegisterHotKey(None,ident,mods,vk):registered.append(ident)
                else:failed.append(name)
            self.events.put(('ready',failed))
        register(self.mapping)
        try:
            while u.GetMessageW(ctypes.byref(msg),None,0,0)>0:
                if msg.message==0x312:
                    index=int(msg.wParam)-0x6b00
                    if 0<=index<len(DEFAULT_KEYS):self.events.put(('key',list(DEFAULT_KEYS)[index]))
                elif msg.message==0x8001:
                    latest=None
                    while not self.commands.empty():latest=self.commands.get()
                    if latest is not None:self.mapping=latest;register(latest)
        finally:
            for key in registered:u.UnregisterHotKey(None,key)

    def close(self):
        if self.tid:ctypes.windll.user32.PostThreadMessageW(self.tid,0x12,0,0)
