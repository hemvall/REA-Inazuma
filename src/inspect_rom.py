"""Write a local header and NitroFS inventory; never identify language by guess."""
import argparse
import json
from pathlib import Path
from nds import read_rom


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('rom', nargs='?', default='rom/original.nds')
    parser.add_argument('--output', default='build/inspection.json')
    args = parser.parse_args()
    report = read_rom(args.rom).report()
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"SHA-256: {report['sha256']}\nGame code: {report['game_code']}\nRevision: {report['revision']}\nFiles: {len(report['files'])}\nReport: {args.output}")


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError) as error:
        raise SystemExit(str(error))
