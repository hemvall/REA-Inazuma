"""Build and verify an xdelta3 patch, including a decoded round trip."""
import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from nds import read_rom, patch
from validate_patch import validate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', default='rom/original.nds')
    parser.add_argument('--manifest', default='local/patch.json')
    parser.add_argument('--xdelta', default='xdelta3')
    parser.add_argument('--output', default='build/inazuma_mystery.nds')
    parser.add_argument('--patch-output', default='dist/inazuma_mystery.xdelta')
    parser.add_argument('--report', default='build/verification.json')
    args = parser.parse_args()
    destinations = [Path(args.output).resolve(), Path(args.patch_output).resolve(), Path(args.report).resolve()]
    if len(set(destinations)) != 3 or Path(args.rom).resolve() in destinations or Path(args.manifest).resolve() in destinations:
        raise ValueError('Refusing to overwrite original ROM')
    rom = read_rom(args.rom)
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    data = patch(rom, manifest)
    executable = shutil.which(args.xdelta)
    if executable is None and args.xdelta == 'xdelta3':
        candidates = sorted(Path('local/tools/xdelta').rglob('xdelta3.exe'))
        if len(candidates) == 1:
            executable = str(candidates[0].resolve())
    if executable is None:
        raise ValueError('xdelta3 is missing. Install it or pass --xdelta PATH.')
    report = validate(rom, data, manifest)
    Path('build').mkdir(exist_ok=True)
    Path('dist').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir='build') as temp:
        target = Path(temp) / 'modified.nds'
        delta = Path(temp) / 'patch.xdelta'
        decoded = Path(temp) / 'decoded.nds'
        target.write_bytes(data)
        subprocess.run([executable, '-e', '-s', str(Path(args.rom).resolve()), str(target), str(delta)], check=True)
        subprocess.run([executable, '-d', '-s', str(Path(args.rom).resolve()), str(delta), str(decoded)], check=True)
        if decoded.read_bytes() != data:
            raise ValueError('xdelta round trip failed')
        for destination in destinations:
            destination.parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_bytes(data)
        Path(args.patch_output).write_bytes(delta.read_bytes())
    report['xdelta_round_trip'] = True
    Path(args.report).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('ROM and xdelta built and structurally verified. Gameplay NOT tested.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
