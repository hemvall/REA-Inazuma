"""Extract exact NitroFS resources, without guessing a dialogue container format."""
import argparse
from pathlib import Path
from nds import read_rom, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', default='rom/original.nds')
    parser.add_argument('--resource', help='Exact path from inspection.json')
    parser.add_argument('--output', default='build/resource.bin')
    args = parser.parse_args()
    rom = read_rom(args.rom)
    if args.resource is None:
        for path, (start, end) in sorted(rom.files.items()):
            if any(word in path.lower() for word in ('evet', '.pkb', '.pki', 'event', 'text')):
                print(f'{path}\t{end-start} bytes\tROM offset {start:#x}')
        print('Candidates only. No dialogue, encoding, compression or entry IDs confirmed.')
        return
    if args.resource not in rom.files:
        raise ValueError('Resource not present in this ROM')
    start, end = rom.files[args.resource]
    data = rom.data[start:end]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_bytes(data)
    print(f'Extracted {len(data)} bytes; SHA-256 {sha(data)}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
