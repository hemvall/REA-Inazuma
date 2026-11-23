"""Atomic Club save containing the confirmed sheet and its native state."""

from collections import Counter
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_STORED, ZipFile

from nds import read_rom
from recruitment import validate_draft
from recruitment_rom import MAX_TEAM_RECRUITS, build_recruitment_rom


class RecruitmentStore:
    def __init__(self, path, rom, directory):
        self.path = Path(path) if path is not None else None
        self.original = read_rom(rom)
        self.rom = Path(directory) / 'recruited.nds'
        profile = Path(rom).with_name('profile.json')
        self.base_hash = json.loads(profile.read_text(encoding='utf-8'))['rom_sha256']

    def build(self, drafts, *, arena=False):
        output = build_recruitment_rom(
            self.original, expected_sha256=self.base_hash, drafts=drafts, arena=arena,
        )
        self.rom.write_bytes(output)
        return output

    @staticmethod
    def drafts_from(metadata):
        version = metadata['format']
        if version in (1, 2):
            return [validate_draft(metadata['draft'])]
        if version == 3:
            drafts = [validate_draft(draft) for draft in metadata['drafts']]
            counts = Counter(draft['team_id'] for draft in drafts)
            if not drafts or max(counts.values()) > MAX_TEAM_RECRUITS:
                raise ValueError('Effectif de recrutement invalide.')
            if len({(draft['team_id'], draft['template_unit']) for draft in drafts}) != len(drafts):
                raise ValueError('Recrutement en double.')
            return drafts
        raise ValueError('Format de recrutement inconnu.')

    @staticmethod
    def read(path, *, with_state=False):
        if not path.is_file():
            return [], None, None
        with ZipFile(path) as archive:
            metadata = json.loads(archive.read('recruitment.json'))
            drafts = RecruitmentStore.drafts_from(metadata)
            state = None
            if with_state and 'club.state' in archive.namelist():
                if not 0 < archive.getinfo('club.state').file_size <= 128 * 1024 * 1024:
                    raise ValueError('Taille de la sauvegarde Club invalide.')
                state = archive.read('club.state')
            return drafts, metadata, state

    def load(self):
        drafts, metadata, state = self.read(self.path, with_state=True)
        if not drafts:
            return None
        previous_count = metadata.get('state_count', 1 if metadata['format'] == 1 else 0)
        if state is not None and (metadata['base_sha256'] != self.base_hash
                                  or not 1 <= previous_count <= len(drafts)):
            raise ValueError('La sauvegarde du recrutement utilise une autre version du Club.')
        return drafts, state, previous_count

    @staticmethod
    def check_available(drafts, draft):
        team = [old for old in drafts if old['team_id'] == draft['team_id']]
        if any(old['template_unit'] == draft['template_unit'] for old in team):
            raise ValueError(f"{draft['name']} a déjà été recruté par cette équipe.")
        if len(team) >= MAX_TEAM_RECRUITS:
            raise ValueError('Cette équipe a atteint la limite de 11 recrues.')

    @staticmethod
    def reserve(path, draft):
        drafts, metadata, state = RecruitmentStore.read(path, with_state=True)
        draft = validate_draft(draft)
        RecruitmentStore.check_available(drafts, draft)
        data = {'format': 3, 'drafts': [*drafts, draft]}
        if state is not None:
            data['base_sha256'] = metadata['base_sha256']
            data['state_count'] = metadata.get('state_count', 1)
        RecruitmentStore.write(path, data, state)

    def save(self, drafts, state):
        current, _, _ = self.read(self.path)
        # A recruitment confirmed in the lobby may await the next Club load.
        combined = current if len(current) > len(drafts) else drafts
        self.write(self.path, {'format': 3, 'base_sha256': self.base_hash,
                               'drafts': combined, 'state_count': len(drafts)}, state)

    @staticmethod
    def write(destination, metadata, state=None):
        destination.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
            path = Path(temporary.name)
        try:
            with ZipFile(path, 'w', ZIP_STORED) as archive:
                archive.writestr('recruitment.json', json.dumps(metadata, ensure_ascii=False))
                if state is not None:
                    archive.writestr('club.state', state)
            path.replace(destination)
        finally:
            path.unlink(missing_ok=True)
