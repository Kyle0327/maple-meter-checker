"""Shared metric labels, formatting and measured overlay layout."""
METRICS={
    'exp_total':'누적 경험치', 'exp_min':'분당 경험치',
    'exp_30min':'30분 경험치', 'exp_hour':'1시간 경험치',
    'meso_total':'누적 메소 +α', 'meso_min':'분당 메소 +α',
    'meso_30min':'30분 메소 +α', 'meso_hour':'1시간 메소 +α',
    'level_eta':'레벨업까지 (예상)', 'elapsed':'측정 시간',
}
DEFAULT_KEYS={
    'toggle':'Ctrl+Alt+F8', 'settings':'Ctrl+Alt+F9', 'lock':'Ctrl+Alt+F10',
    'reset':'Ctrl+Alt+R', 'units':'Ctrl+Alt+E',
}
KEY_LABELS={'toggle':'시작 / 일시정지','settings':'설정 열기','lock':'위치 잠금 / 클릭 통과',
            'reset':'초기화','units':'경험치 양 ↔ %'}

def format_value(key,value,percent=False):
    if value is None:return '—'
    if key in ('elapsed','level_eta'):
        import math
        if not math.isfinite(value) or value<0:return '—'
        s=math.ceil(value) if key=='level_eta' else int(value)
        return f'{s//3600:02}:{s//60%60:02}:{s%60:02}'
    if percent and key.startswith('exp_'):return f'{value:,.4f}%'
    return f'{value:,.0f}'

def selected_metrics(conf):
    selected=set(conf.get('metrics',METRICS)) & METRICS.keys()
    # Enable the newly added metric once; later explicit deselection persists.
    if conf.get('metrics_revision')!=2:selected.add('level_eta')
    return selected

def row_layout(count,label_height,value_height,header=72):
    # Both labels and values share a center; separators clear their actual
    # measured bounding height, even at minimum font size and non-default DPI.
    content=max(label_height,value_height)
    height=content+16
    return [(header+i*height+8,header+i*height+8+content,header+(i+1)*height) for i in range(count)]

def parse_hotkey(value):
    parts=value.split('+');mods=0
    if len(parts)<2:raise ValueError('Ctrl 또는 Alt 조합을 사용하세요.')
    for part in parts[:-1]:
        if part not in ('Ctrl','Alt','Shift'):raise ValueError('지원하지 않는 보조 키입니다.')
        mods|={'Ctrl':2,'Alt':1,'Shift':4}[part]
    if not mods&3:raise ValueError('Ctrl 또는 Alt가 필요합니다.')
    key=parts[-1]
    if key.startswith('F') and key[1:].isdigit() and 1<=int(key[1:])<=11:vk=0x6f+int(key[1:])
    elif len(key)==1 and 'A'<=key<='Z':vk=ord(key)
    else:raise ValueError('A–Z 또는 F1–F11을 사용하세요.')
    return mods|0x4000,vk

def validate_hotkeys(mapping):
    if set(mapping)!=set(DEFAULT_KEYS):raise ValueError('모든 동작에 단축키를 지정하세요.')
    codes=[parse_hotkey(mapping[k]) for k in DEFAULT_KEYS]
    if len(set(codes))!=len(codes):raise ValueError('같은 단축키를 두 동작에 지정할 수 없습니다.')
    return mapping
