"""Synthetic V9 release validation in a separately selected runtime process."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_successor_release as validator

METHOD_ROOT = Path(os.environ['SUCCESSOR_METHODOLOGY_REPO']).resolve()
# Fixture construction deliberately remains in a default V8 process. The actual
# validator verifies every pinned runtime byte and selects V9 in a child process.
sys.path[:0] = [str(METHOD_ROOT / 'evaluate-subject-index/scripts'), str(METHOD_ROOT / 'evaluate-subject-index/tests')]
from test_v9_runtime import prepare_v9


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class V9SuccessorReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = tempfile.TemporaryDirectory()
        cls.base = Path(cls.base_dir.name)
        case = unittest.TestCase()
        fixture = prepare_v9(case)
        try:
            files = {role: Path(getattr(fixture.args, arg)) for role, arg in (
                ('state', 'release_state'), ('draft', 'release_draft'), ('review', 'release_review'),
                ('benchmark', 'release_benchmark'), ('source_policy', 'release_policy'),
                ('study_lock', 'study_lock'), ('policy_template', 'study_policy'))}
            state = validator.read(files['state'])
            for role, stage in (('page_map', 'page_mapping'), ('chunk_manifest', 'chunk_definition')):
                row = next(r for r in state['artifacts'] if r['stage'] == stage)
                files[role] = files['state'].parent / row['path']
            lock = validator.read(files['study_lock'])
            evidence_paths = [files['study_lock'].parent / row['source_artifact']['path'] for row in lock['density_basis']['chunks']]
            bindings = {}
            for path in [*files.values(), *evidence_paths]:
                name = path.relative_to(fixture.root).as_posix()
                target = cls.base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                bindings[path] = {'path': name, 'sha256': validator.sha(target)}
            cls.metadata = {'schema_version': 'subject-index-successor-release-v2',
                'release_id': lock['release']['release_id'], 'methodology_commit': validator.V9_METHODOLOGY_COMMIT,
                'artifact_freeze_commit': None, 'artifacts': {role: bindings[path] for role, path in files.items()},
                'evidence': [bindings[path] for path in evidence_paths], 'checkpoints': [], 'release_sha256': None}
        finally:
            case.doCleanups()

    @classmethod
    def tearDownClass(cls):
        cls.base_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(self.base, self.root, dirs_exist_ok=True)
        self.metadata = deepcopy(self.metadata)
        self.git('init', '--quiet')
        self.git('config', 'user.name', 'Synthetic V9 test')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        self.seal()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], stderr=subprocess.PIPE)

    def file(self, role):
        return self.root / self.metadata['artifacts'][role]['path']

    def save_metadata(self):
        self.metadata['release_sha256'] = validator.digest({k: v for k, v in self.metadata.items() if k != 'release_sha256'})
        write(self.root / 'successor-release.json', self.metadata)

    def seal(self):
        bindings = [*self.metadata['artifacts'].values(), *self.metadata['evidence']]
        for binding in bindings:
            binding['sha256'] = validator.sha(self.root / binding['path'])
        self.git('add', '--', *[r['path'] for r in bindings])
        self.git('commit', '--quiet', '--allow-empty', '-m', 'Synthetic frozen proof')
        self.metadata['artifact_freeze_commit'] = self.git('rev-parse', 'HEAD').decode().strip()
        self.save_metadata()

    def save_lock(self, lock):
        lock['lock_sha256'] = validator.digest({k: v for k, v in lock.items() if k != 'lock_sha256'})
        write(self.file('study_lock'), lock)
        self.seal()

    def validate(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_successor_release.py'),
            '--root', str(self.root), '--release', 'successor-release.json', '--methodology-repo', str(METHOD_ROOT)],
            capture_output=True, text=True)
        return result.returncode, result.stdout + result.stderr

    def assert_rejected(self, text):
        code, output = self.validate()
        self.assertNotEqual(0, code, output)
        self.assertIn(text, output)

    def test_unchanged_v8_source_proof_passes_under_explicit_v9(self):
        before = {role: self.file(role).read_bytes() for role in ('state', 'draft', 'review', 'benchmark', 'source_policy')}
        code, output = self.validate()
        self.assertEqual(0, code, output)
        self.assertEqual('v9', json.loads(output)['runtime_profile'])
        self.assertEqual(before, {role: self.file(role).read_bytes() for role in before})
        self.assertEqual('subject-index-evaluation-state-v6', validator.read(self.file('state'))['schema_version'])

    def test_source_methodology_rejects_unknown_fields_and_profiles(self):
        original = validator.read(self.file('study_lock'))
        for key, value in [('unknown_extension', True), ('policy_profile', 'subject-index-standard-policy-v8.1')]:
            with self.subTest(key=key):
                lock = deepcopy(original)
                lock['source_methodology'][key] = value
                self.save_lock(lock)
                self.assert_rejected('Invalid study lock schema')

    def test_source_policy_hashes_must_match(self):
        original = validator.read(self.file('study_lock'))
        for key in ('source_policy_sha256', 'source_policy_file_sha256'):
            with self.subTest(key=key):
                lock = deepcopy(original)
                lock['source_methodology'][key] = '0' * 64
                self.save_lock(lock)
                self.assert_rejected('source policy')

    def test_missing_source_policy_role_fails(self):
        self.metadata['artifacts'].pop('source_policy')
        self.save_metadata()
        self.assert_rejected('artifact roles differ')

    def test_fully_rebound_target_policy_semantic_change_fails(self):
        template = validator.read(self.file('policy_template'))
        template['policy_semantic_content']['audience']['label'] = 'Changed synthetic audience'
        template['template_sha256'] = validator.digest({k: v for k, v in template.items() if k != 'template_sha256'})
        write(self.file('policy_template'), template)
        lock = validator.read(self.file('study_lock'))
        lock['policy_semantic_sha256'] = validator.digest(template['policy_semantic_content'])
        self.save_lock(lock)
        self.assert_rejected('changes substantive source settings')

    def test_source_state_cannot_be_relabelled_v9(self):
        state = validator.read(self.file('state'))
        state['schema_version'] = 'subject-index-evaluation-state-v7'
        write(self.file('state'), state)
        lock = validator.read(self.file('study_lock'))
        lock['release']['lineage']['source_only_state_sha256'] = validator.sha(self.file('state'))
        self.save_lock(lock)
        self.assert_rejected('Current source freeze state is invalid')

    def test_changed_source_draft_is_not_accepted_by_transport_rebinding(self):
        self.file('draft').write_bytes(self.file('draft').read_bytes() + b'\n')
        self.seal()
        self.assert_rejected('draft_file_sha256 mismatch')

    def test_v8_lock_cannot_be_used_as_v9(self):
        lock = validator.read(self.file('study_lock'))
        lock['schema_version'] = 'ohfr-study-benchmark-lock-v1'
        self.save_lock(lock)
        self.assert_rejected('Invalid study lock schema')

    def test_v9_descriptor_cannot_select_v8_runtime(self):
        self.metadata['methodology_commit'] = validator.METHODOLOGY_COMMIT
        self.save_metadata()
        self.assert_rejected('pin differs')

    def test_rehashed_uncommitted_proof_is_rejected(self):
        self.file('review').write_bytes(self.file('review').read_bytes() + b'\n')
        self.metadata['artifacts']['review']['sha256'] = validator.sha(self.file('review'))
        self.save_metadata()
        self.assert_rejected('committed freeze bytes')


if __name__ == '__main__':
    unittest.main()
