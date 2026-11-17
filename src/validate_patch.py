"""Verify the output equals exactly the authorized edits and is reversible."""
import argparse
import json
from pathlib import Path
from nds import read_rom, patch, sha


def validate(original, modified, manifest):
    expected = patch(original, manifest)
    if modified != expected:
        raise ValueError('Output differs from exact manifest result')
    restored = bytearray(modified)
    for edit in manifest['edits']:
        pos = original.files[edit['path']][0] + edit['offset']
        before = bytes.fromhex(edit['before_hex'])
        restored[pos:pos + len(before)] = before
    if restored != original.data:
        raise ValueError('Reverse validation failed')
    return {'original_sha256': sha(original.data), 'modified_sha256': sha(modified),
            'changed_bytes': sum(a != b for a, b in zip(original.data, modified)),
            'exact_manifest_match': True, 'reverse_verified': True,
            'gameplay_tested': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rom', default='rom/original.nds')
    parser.add_argument('--patched', default='build/inazuma_mystery.nds')
    parser.add_argument('--manifest', default='local/patch.json')
    args = parser.parse_args()
    result = validate(read_rom(args.rom), Path(args.patched).read_bytes(),
                      json.loads(Path(args.manifest).read_text(encoding='utf-8')))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError) as error:
        raise SystemExit(str(error))
