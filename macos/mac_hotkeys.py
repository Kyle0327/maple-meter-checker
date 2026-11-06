"""Registered Carbon hotkeys; no keyboard monitoring or Accessibility access."""
import ctypes as C

KEY_CODES = {'A':0,'S':1,'D':2,'F':3,'H':4,'G':5,'Z':6,'X':7,'C':8,'V':9,
             'B':11,'Q':12,'W':13,'E':14,'R':15,'Y':16,'T':17,'O':31,'U':32,
             'I':34,'P':35,'L':37,'J':38,'K':40,'N':45,'M':46,
             'F1':122,'F2':120,'F3':99,'F4':118,'F5':96,'F6':97,
             'F7':98,'F8':100,'F9':101,'F10':109,'F11':103}
MODIFIERS = {'Cmd':256, 'Shift':512, 'Alt':2048, 'Ctrl':4096}
DEFAULT_KEYS = {'toggle':'Ctrl+Alt+S','settings':'Ctrl+Alt+O','lock':'Ctrl+Alt+L',
                'reset':'Ctrl+Alt+R','units':'Ctrl+Alt+E'}


def parse(value):
    parts=value.split('+')
    if len(parts)<2 or parts[-1] not in KEY_CODES:
        raise ValueError('보조 키와 A–Z 또는 F1–F11을 조합하세요.')
    mods=0
    for key in parts[:-1]:
        if key not in MODIFIERS:raise ValueError('Cmd, Ctrl, Alt, Shift만 사용할 수 있습니다.')
        mods |= MODIFIERS[key]
    if not mods & (256|2048|4096):raise ValueError('Cmd, Ctrl, Alt 중 하나를 포함하세요.')
    return KEY_CODES[parts[-1]], mods


class EventType(C.Structure):
    _fields_=[('eventClass',C.c_uint32),('eventKind',C.c_uint32)]


class HotKeyID(C.Structure):
    _fields_=[('signature',C.c_uint32),('id',C.c_uint32)]


def fourcc(value):return int.from_bytes(value.encode('ascii'),'big')


class Hotkeys:
    def __init__(self, callback):
        self.lib=C.CDLL('/System/Library/Frameworks/Carbon.framework/Carbon')
        self.refs=[];self.mapping={};self.handler=C.c_void_p()
        self.callback=callback
        self.proc_type=C.CFUNCTYPE(C.c_int32,C.c_void_p,C.c_void_p,C.c_void_p)
        self.proc=self.proc_type(self.receive)
        lib=self.lib
        lib.GetApplicationEventTarget.restype=C.c_void_p
        lib.InstallEventHandler.argtypes=[C.c_void_p,self.proc_type,C.c_uint32,C.POINTER(EventType),C.c_void_p,C.POINTER(C.c_void_p)]
        lib.InstallEventHandler.restype=C.c_int32
        lib.RegisterEventHotKey.argtypes=[C.c_uint32,C.c_uint32,HotKeyID,C.c_void_p,C.c_uint32,C.POINTER(C.c_void_p)]
        lib.RegisterEventHotKey.restype=C.c_int32
        lib.UnregisterEventHotKey.argtypes=[C.c_void_p]
        lib.RemoveEventHandler.argtypes=[C.c_void_p]
        lib.GetEventParameter.argtypes=[C.c_void_p,C.c_uint32,C.c_uint32,C.c_void_p,C.c_uint32,C.c_void_p,C.c_void_p]
        lib.GetEventParameter.restype=C.c_int32
        event=EventType(fourcc('keyb'),6)
        status=lib.InstallEventHandler(lib.GetApplicationEventTarget(),self.proc,1,C.byref(event),None,C.byref(self.handler))
        if status:raise RuntimeError(f'단축키 이벤트 등록 실패 ({status})')

    def receive(self, handler, event, user):
        ident=HotKeyID()
        status=self.lib.GetEventParameter(event,fourcc('----'),fourcc('hkid'),None,C.sizeof(ident),None,C.byref(ident))
        if status or ident.signature!=fourcc('MMCK'):return -9874
        name=self.mapping.get(ident.id)
        if name:self.callback(name)
        return 0

    def update(self, mapping):
        if set(mapping)!=set(DEFAULT_KEYS):raise ValueError('모든 단축키를 지정하세요.')
        codes=[parse(mapping[k]) for k in DEFAULT_KEYS]
        if len(codes)!=len(set(codes)):raise ValueError('같은 단축키를 중복 사용할 수 없습니다.')
        for ref in self.refs:self.lib.UnregisterEventHotKey(ref)
        self.refs=[];self.mapping={};failed=[]
        for i,(name,(key,mods)) in enumerate(zip(DEFAULT_KEYS,codes)):
            ref=C.c_void_p()
            result=self.lib.RegisterEventHotKey(key,mods,HotKeyID(fourcc('MMCK'),i+1),self.lib.GetApplicationEventTarget(),0,C.byref(ref))
            if result:failed.append(name)
            else:self.refs.append(ref);self.mapping[i+1]=name
        return failed

    def close(self):
        for ref in self.refs:self.lib.UnregisterEventHotKey(ref)
        self.refs=[]
        if self.handler:self.lib.RemoveEventHandler(self.handler);self.handler=None
