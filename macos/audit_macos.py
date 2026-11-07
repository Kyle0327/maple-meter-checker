"""Reject any bundled Mach-O slice requiring a newer OS than Ventura."""
from pathlib import Path
import json
from macholib.MachO import MachO
from macholib.mach_o import LC_BUILD_VERSION, LC_VERSION_MIN_MACOSX

MAGIC={bytes.fromhex(s) for s in ('feedface','feedfacf','cefaedfe','cffaedfe','cafebabe','bebafeca','cafebabf','bfbafeca')}


def version_tuple(value):return (value>>16,(value>>8)&255,value&255)


def audit(bundle,report):
    rows=[];seen=set()
    for path in sorted(Path(bundle).rglob('*')):
        if not path.is_file() or path.resolve() in seen:continue
        seen.add(path.resolve())
        with path.open('rb') as f:magic=f.read(4)
        if magic not in MAGIC:continue
        for header in MachO(str(path)).headers:
            versions=[]
            for command,details,_ in header.commands:
                if command.cmd==LC_BUILD_VERSION:versions.append(version_tuple(details.minos))
                elif command.cmd==LC_VERSION_MIN_MACOSX:versions.append(version_tuple(details.version))
            if not versions:raise RuntimeError(f'No deployment target in {path}')
            minimum=max(versions)
            rows.append(dict(file=str(path.relative_to(bundle)),cpu=header.header.cputype,minimum_macos='.'.join(map(str,minimum))))
            if minimum>(13,0,0):raise RuntimeError(f'{path.name} requires macOS {minimum}, newer than Ventura 13.0')
    if not rows:raise RuntimeError('No Mach-O binaries were checked')
    Path(report).write_text(json.dumps(dict(target='macOS 13.0',checked_slices=len(rows),binaries=rows),indent=2))
    print(f'Ventura deployment-target audit passed: {len(rows)} Mach-O slices')


if __name__=='__main__':
    import sys
    audit(Path(sys.argv[1]),Path(sys.argv[2]))
