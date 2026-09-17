"""Synthetic V10 release validation in a separately selected runtime process."""
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
# validator verifies every pinned runtime byte and selects V10 in a child process.
sys.path[:0] = [str(METHOD_ROOT / 'evaluate-subject-index/scripts'), str(METHOD_ROOT / 'evaluate-subject-index/tests')]
from test_v10_runtime import prepare_v10


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


class V10SuccessorReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = tempfile.TemporaryDirectory()
        cls.base = Path(cls.base_dir.name)
        case = unittest.TestCase()
        fixture = prepare_v10(case)
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
            for name, role in (('overlay', 'access_overlay'), ('review', 'access_review')):
                files[role] = files['study_lock'].parent / lock['benchmark_access'][name]['path']
            evidence_paths = [files['study_lock'].parent / row['source_artifact']['path'] for row in lock['density_basis']['chunks']]
            bindings = {}
            for path in [*files.values(), *evidence_paths]:
                name = path.relative_to(fixture.root).as_posix()
                target = cls.base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                bindings[path] = {'path': name, 'sha256': validator.sha(target)}
            cls.metadata = {'schema_version': 'subject-index-successor-release-v3',
                'release_id': lock['release']['release_id'], 'methodology_commit': validator.V10_METHODOLOGY_COMMIT,
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
        self.git('config', 'user.name', 'Synthetic V10 test')
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

    def test_unchanged_v8_source_proof_passes_under_explicit_v10(self):
        before = {role: self.file(role).read_bytes() for role in ('state', 'draft', 'review', 'benchmark', 'source_policy')}
        code, output = self.validate()
        self.assertEqual(0, code, output)
        self.assertEqual('v10', json.loads(output)['runtime_profile'])
        lock = validator.read(self.file('study_lock'))
        self.assertNotEqual(lock['source_benchmark_semantic_sha256'], lock['benchmark_semantic_sha256'])
        self.assertTrue(validator.read(self.file('access_overlay'))['deltas'])
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
        self.assert_rejected('differs from the approved semantic amendment')

    def test_source_state_cannot_be_relabelled_v10(self):
        state = validator.read(self.file('state'))
        state['schema_version'] = 'subject-index-evaluation-state-v8'
        write(self.file('state'), state)
        lock = validator.read(self.file('study_lock'))
        lock['release']['lineage']['source_only_state_sha256'] = validator.sha(self.file('state'))
        self.save_lock(lock)
        self.assert_rejected('Current source freeze state is invalid')

    def test_changed_source_draft_is_not_accepted_by_transport_rebinding(self):
        self.file('draft').write_bytes(self.file('draft').read_bytes() + b'\n')
        self.seal()
        self.assert_rejected('draft_file_sha256 mismatch')

    def test_v8_lock_cannot_be_used_as_v10(self):
        lock = validator.read(self.file('study_lock'))
        lock['schema_version'] = 'ohfr-study-benchmark-lock-v1'
        self.save_lock(lock)
        self.assert_rejected('Invalid study lock schema')

    def test_v10_descriptor_cannot_select_v8_runtime(self):
        self.metadata['methodology_commit'] = validator.METHODOLOGY_COMMIT
        self.save_metadata()
        self.assert_rejected('pin differs')

    def test_rehashed_uncommitted_proof_is_rejected(self):
        self.file('review').write_bytes(self.file('review').read_bytes() + b'\n')
        self.metadata['artifacts']['review']['sha256'] = validator.sha(self.file('review'))
        self.save_metadata()
        self.assert_rejected('committed freeze bytes')


    def save_access(self, overlay=None, review=None):
        overlay = overlay or validator.read(self.file('access_overlay'))
        review = review or validator.read(self.file('access_review'))
        overlay['overlay_sha256'] = validator.digest({k: v for k, v in overlay.items() if k != 'overlay_sha256'})
        write(self.file('access_overlay'), overlay)
        review['overlay_sha256'] = overlay['overlay_sha256']
        review['overlay_file_sha256'] = validator.sha(self.file('access_overlay'))
        review['population_sha256'] = validator.digest({'before': overlay['before_population'], 'after': overlay['after_population']})
        write(self.file('access_review'), review)
        lock = validator.read(self.file('study_lock'))
        lock['benchmark_access']['overlay']['sha256'] = validator.sha(self.file('access_overlay'))
        lock['benchmark_access']['review']['sha256'] = validator.sha(self.file('access_review'))
        lock['benchmark_access']['overlay_sha256'] = overlay['overlay_sha256']
        self.save_lock(lock)

    def test_access_proof_roles_are_required(self):
        self.metadata['artifacts'].pop('access_review')
        self.save_metadata()
        self.assert_rejected('artifact roles differ')

    def test_access_role_must_match_exact_lock_path(self):
        target = self.file('access_overlay').with_name('unselected-copy.json')
        shutil.copyfile(self.file('access_overlay'), target)
        self.metadata['artifacts']['access_overlay']['path'] = target.relative_to(self.root).as_posix()
        self.seal()
        self.assert_rejected('Access proof role differs')

    def test_rebound_review_requires_independent_reviewer(self):
        review = validator.read(self.file('access_review'))
        review['reviewer_id'] = validator.read(self.file('access_overlay'))['author_id']
        self.save_access(review=review)
        self.assert_rejected('independent reviewer')

    def test_rebound_review_must_cover_exact_delta_ids(self):
        review = validator.read(self.file('access_review'))
        review['reviewed_delta_ids'] = []
        self.save_access(review=review)
        self.assert_rejected('cover every delta')

    def test_rebound_overlay_cannot_change_source_scope(self):
        overlay = validator.read(self.file('access_overlay'))
        overlay['source_scope']['document_page_span'] = [1, 2]
        self.save_access(overlay=overlay)
        self.assert_rejected('source scope/page map')

    def test_rebound_overlay_cannot_claim_candidate_blindness_after_exposure(self):
        overlay = validator.read(self.file('access_overlay'))
        overlay['candidate_seen'] = True
        self.save_access(overlay=overlay)
        self.assert_rejected('access overlay schema')

    def test_fully_rebound_population_drift_is_rejected(self):
        overlay = validator.read(self.file('access_overlay'))
        overlay['after_population']['subjects'] = []
        self.save_access(overlay=overlay)
        self.assert_rejected('after population differs')

    def test_effective_fingerprint_must_match_applied_overlay(self):
        lock = validator.read(self.file('study_lock'))
        lock['benchmark_semantic_sha256'] = '0' * 64
        lock['benchmark_access']['effective_benchmark_semantic_sha256'] = '0' * 64
        self.save_lock(lock)
        self.assert_rejected('fingerprint differs')

    def test_rehashed_uncommitted_access_proof_is_rejected(self):
        self.file('access_review').write_bytes(self.file('access_review').read_bytes() + b'\n')
        self.metadata['artifacts']['access_review']['sha256'] = validator.sha(self.file('access_review'))
        self.save_metadata()
        self.assert_rejected('committed freeze bytes')


if __name__ == '__main__':
    unittest.main()
