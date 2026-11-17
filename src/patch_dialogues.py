"""Apply a locally researched, hash-locked, exact-length binary manifest."""
import argparse
import json
from pathlib import Path
from nds import read_rom, patch, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', default='rom/original.nds')
    parser.add_argument('--manifest', default='local/patch.json')
    parser.add_argument('--output', default='build/inazuma_mystery.nds')
    args = parser.parse_args()
    if Path(args.rom).resolve() == Path(args.output).resolve():
        raise ValueError('Refusing to overwrite original ROM')
    rom = read_rom(args.rom)
    data = patch(rom, json.loads(Path(args.manifest).read_text(encoding='utf-8')))
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_bytes(data)
    print(f'Wrote {args.output}; SHA-256 {sha(data)}. Gameplay NOT tested.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error))
