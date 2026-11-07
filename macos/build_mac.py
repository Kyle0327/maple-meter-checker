"""Build on macOS, preserving .app symlinks with ditto."""
from pathlib import Path
import hashlib
import importlib.metadata as metadata
import json
import platform
import shutil
import subprocess
import sys
from PIL import Image

if sys.platform!='darwin':raise SystemExit('Build this app on macOS.')
root=Path(__file__).resolve().parent
Image.open(root/'checker.png').save(root/'checker.icns',format='ICNS')
assets=['glyphs.json','checker.png','Pretendard-Bold.otf','Pretendard-ExtraBold.otf','Pretendard-LICENSE.txt','Python-LICENSE.txt']
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed','--noupx',
      '--name','MapleMeterChecker','--osx-bundle-identifier','com.kyle0327.maplemeterchecker',
      '--icon',str(root/'checker.icns'),'--distpath',str(root/'dist'),'--workpath',str(root/'build'),
      '--specpath',str(root),'--hidden-import','ScreenCaptureKit','--hidden-import','Quartz',
      '--hidden-import','Foundation','--hidden-import','AppKit','--hidden-import','objc']
for asset in assets:args+=['--add-data',f'{root/asset}:.']
# Qt and PyObjC remain dynamically linked. Include upstream license notices.
licenses=root/'third-party-licenses';licenses.mkdir(exist_ok=True)
inventory=[]
for dist in metadata.distributions():
    name=dist.metadata['Name'];inventory.append({'name':name,'version':dist.version})
    for file in dist.files or []:
        if any(part.lower().startswith(('license','copying','notice')) for part in file.parts):
            source=Path(dist.locate_file(file))
            if source.is_file():
                destination=licenses/name/str(file)
                destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,destination)
(licenses/'dependencies.json').write_text(json.dumps(inventory,indent=2))
args+=['--add-data',f'{licenses}:licenses',str(root/'mac_app.py')]
subprocess.run(args,check=True)
import plistlib
bundle=root/'dist/MapleMeterChecker.app'
plist=bundle/'Contents/Info.plist'
info=plistlib.loads(plist.read_bytes())
info.update(CFBundleShortVersionString='2.2.0',CFBundleVersion='22003',
            LSMinimumSystemVersion='13.0',NSHighResolutionCapable=True,
            NSScreenCaptureUsageDescription='선택한 메이플스토리 게임 창의 경험치와 메소를 읽습니다. 화면이나 오디오는 저장하거나 전송하지 않습니다.')
plist.write_bytes(plistlib.dumps(info))
# Ad-hoc integrity signature only. This is NOT Developer ID signing/notarization.
subprocess.run(['codesign','--force','--deep','--sign','-',str(bundle)],check=True)
subprocess.run(['codesign','--verify','--deep','--strict',str(bundle)],check=True)
arch=platform.machine();out=root/'release';out.mkdir(exist_ok=True)
from audit_macos import audit
audit(bundle,out/f'macOS-compatibility-{arch}.json')
dest=out/f'MapleMeterChecker-macOS-{arch}-preview.zip'
subprocess.run(['ditto','-c','-k','--sequesterRsrc','--keepParent',str(bundle),str(dest)],check=True)
(out/(dest.name+'.sha256')).write_text(hashlib.sha256(dest.read_bytes()).hexdigest()+'  '+dest.name+'\n')
print(dest)
