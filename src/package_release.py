"""Create a source delivery without ROMs, extracted assets, credentials or states."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    files=[]
    for directory in ('src','web','profiles','story','tests'):
        files.extend(p for p in (ROOT/directory).rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix in ('.py','.js','.css','.html','.json','.jsonl','.md'))
    files.extend(p for p in (ROOT/'web/assets').iterdir()
                 if p.is_file() and p.suffix in ('.png', '.ttf', '.txt'))
    files.extend(p for p in (ROOT/'docs').rglob('*.md') if p.is_file())
    chester_sample = ROOT/'docs/plans/chester-essai-voix.mp3'
    if chester_sample.is_file():
        files.append(chester_sample)
    files.extend(p for p in ROOT.iterdir() if p.is_file() and
                 (p.suffix in ('.md','.cmd') or p.name.startswith('requirements') or p.name in ('.gitignore','.graphifyignore')))
    target=ROOT/'dist/InazumIA-develop-source.zip'
    target.parent.mkdir(exist_ok=True)
    manifest={str(p.relative_to(ROOT)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in manifest:archive.write(ROOT/name,'InazumIA/'+name)
        archive.writestr('InazumIA/SHA256SUMS.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(target) as archive:
        if archive.testzip():raise RuntimeError('Corrupt release archive')
        for name in archive.namelist():
            if Path(name).suffix in ('.nds','.sav','.state','.dll') or '/local/' in name:
                raise RuntimeError('Private runtime artifact in release')
        for name,digest in manifest.items():
            if hashlib.sha256(archive.read('InazumIA/'+name)).hexdigest()!=digest:
                raise RuntimeError('Release manifest mismatch: '+name)
    checksum=hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix('.zip.sha256').write_text(checksum+'  '+target.name+'\n',encoding='ascii')
    print(str(target))
    print(f'{len(manifest)} files; SHA-256 {checksum}')


if __name__=='__main__':main()
