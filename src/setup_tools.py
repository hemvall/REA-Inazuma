"""Download official portable Windows tools into ignored local storage."""
import hashlib
import json
import urllib.request
import urllib.error
import zipfile
from pathlib import Path


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'inazuma-local-setup'})
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def main():
    root = Path('local/tools')
    root.mkdir(parents=True, exist_ok=True)
    record_path = root / 'downloads.json'
    records = json.loads(record_path.read_text(encoding='utf-8')) if record_path.exists() else []
    for name, repo, matches in [
        ('xdelta', 'jmacd/xdelta', lambda s: 'windows-x86_64' in s and s.endswith('.zip')),
        ('desmume', 'TASEmulators/desmume', lambda s: 'win64' in s and s.endswith('.zip')),
        ('tinke', 'pleonex/tinke', lambda s: s.lower().startswith('tinke-') and s.endswith('.zip')),
    ]:
        existing = next((r for r in records if r['tool'] == name), None)
        if existing and existing['executables'] and all(Path(p).exists() for p in existing['executables']):
            print(f'{name} already downloaded', flush=True)
            continue
        try:
            release = json.loads(fetch(f'https://api.github.com/repos/{repo}/releases/latest'))
        except urllib.error.HTTPError as error:
            if repo != 'pleonex/tinke' or error.code != 403:
                raise
            release = {'tag_name': 'v0.9.2',
                       'html_url': 'https://github.com/pleonex/tinke/releases/tag/v0.9.2',
                       'assets': [{'name': 'Tinke-v0.9.2.zip', 'browser_download_url':
                           'https://github.com/pleonex/tinke/releases/download/v0.9.2/Tinke-v0.9.2.zip'}]}
        assets = [asset for asset in release['assets'] if matches(asset['name'])]
        if len(assets) != 1:
            raise ValueError(f'Expected one Windows asset for {repo}: {[a["name"] for a in assets]}')
        asset = assets[0]
        print(f'Downloading {name}: {asset["name"]}', flush=True)
        data = fetch(asset['browser_download_url'])
        digest = hashlib.sha256(data).hexdigest()
        if asset.get('digest') and asset['digest'] != 'sha256:' + digest:
            raise ValueError('Publisher digest mismatch')
        archive = root / asset['name']
        archive.write_bytes(data)
        destination = (root / name).resolve()
        destination.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.infolist():
                if not (destination / member.filename).resolve().is_relative_to(destination):
                    raise ValueError('Unsafe archive member')
            zipped.extractall(destination)
        records.append({'tool': name, 'version': release['tag_name'],
                        'source': release['html_url'], 'download': asset['browser_download_url'],
                        'sha256': digest, 'publisher_digest_verified': bool(asset.get('digest')),
                        'executables': [str(p) for p in destination.rglob('*.exe')]})
        (root / 'downloads.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
        print(f'Extracted to {destination}', flush=True)


if __name__ == '__main__':
    main()
