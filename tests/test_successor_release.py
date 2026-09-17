"""Synthetic release proofs only; no source PDF or candidate data fixtures."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import validate_successor_release as validator

METHOD_ROOT = Path(os.environ["SUCCESSOR_METHODOLOGY_REPO"]).resolve()
method = validator.load_methodology(METHOD_ROOT)
sys.path.insert(0, str(METHOD_ROOT / "evaluate-subject-index/tests"))
from test_study_comparison import StudyFixture
from state_cli import artifact_id


def write(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")


class SuccessorReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_dir = tempfile.TemporaryDirectory()
        cls.base = Path(cls.base_dir.name)
        fixture = StudyFixture(unittest.TestCase(), policy_change=True)
        try:
            state_path = fixture.current_source_release(revised=True)
            files = {"state": state_path, "draft": Path(fixture.args.release_draft),
                     "review": Path(fixture.args.release_review), "benchmark": Path(fixture.args.release_benchmark),
                     "study_lock": Path(fixture.args.study_lock), "policy_template": Path(fixture.args.study_policy)}
            state = method.read(state_path)
            for role, stage in (("page_map", "page_mapping"), ("chunk_manifest", "chunk_definition"), ("source_policy", "define_policy")):
                record = next(r for r in state["artifacts"] if r["stage"] == stage)
                files[role] = state_path.parent / record["path"]
            artifacts = {}
            for role, path in files.items():
                name = path.relative_to(fixture.root).as_posix()
                target = cls.base / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                artifacts[role] = {"path": name, "sha256": validator.sha(target)}
            lock = method.read(cls.base / artifacts["study_lock"]["path"])
            measurement = {"schema_version": "source-density-measurement-v1", "measurement_id": "SYNTHETIC",
                **{k: v for k, v in lock["source_scope"].items() if k != "document_page_span"},
                "candidate_information_used": False, "extractor": "synthetic", "script_sha256": "a" * 64,
                "extraction_xml_sha256": "b" * 64,
                "protocol": {"inclusions": ["Body prose"], "exclusions": ["Running heads"], "token": "Whitespace", "scope": "Owned pages", "source_role_note": "Original synthetic note"},
                "total_indexable_source_words": 100,
                "chunks": [{"chunk_id": "CHUNK-001", "owned_document_pages": [1], "indexable_source_words": 100}],
                "pages": [{"document_page": 1, "source_page_label": "1", "indexable_source_words": 100}]}
            evidence = []
            for name, value in (("proof/original.json", measurement), ("proof/addendum.json", {"synthetic": "addendum"}), ("proof/scope.json", {"synthetic": "independent scope"})):
                write(cls.base / name, value)
                evidence.append({"path": name, "sha256": validator.sha(cls.base / name)})
            measurement = deepcopy(measurement)
            measurement["protocol"]["source_role_note"] = "Corrected synthetic note"
            measurement["metadata_correction"] = {
                "original_measurement_path": evidence[0]["path"], "original_measurement_file_sha256": evidence[0]["sha256"],
                "scope_addendum_path": evidence[1]["path"], "scope_addendum_file_sha256": evidence[1]["sha256"],
                "independent_source_scope_disposition": evidence[2]}
            write(cls.base / "release/density.json", measurement)
            evidence.append({"path": "release/density.json", "sha256": validator.sha(cls.base / "release/density.json")})
            lock["density_basis"]["chunks"][0]["source_artifact"] = {"path": "density.json", "sha256": evidence[-1]["sha256"]}
            lock["density_basis"]["measurement_sha256"] = method.digest(lock["density_basis"]["chunks"])
            lock["lock_sha256"] = method.digest({k: v for k, v in lock.items() if k != "lock_sha256"})
            write(cls.base / artifacts["study_lock"]["path"], lock)
            artifacts["study_lock"]["sha256"] = validator.sha(cls.base / artifacts["study_lock"]["path"])
            cls.metadata = {"schema_version": "subject-index-successor-release-v1", "release_id": lock["release"]["release_id"],
                "methodology_commit": validator.METHODOLOGY_COMMIT, "artifact_freeze_commit": None,
                "artifacts": artifacts, "evidence": evidence, "checkpoints": [], "release_sha256": None}
        finally:
            fixture.close()

    @classmethod
    def tearDownClass(cls):
        cls.base_dir.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(self.base, self.root, dirs_exist_ok=True)
        self.metadata = deepcopy(self.metadata)
        self.run_git("init", "--quiet")
        self.run_git("config", "user.name", "Synthetic test")
        self.run_git("config", "user.email", "synthetic@example.invalid")
        self.seal()

    def run_git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.PIPE)

    def file(self, role):
        return self.root / self.metadata["artifacts"][role]["path"]

    def save_metadata(self):
        self.metadata["release_sha256"] = validator.digest({k: v for k, v in self.metadata.items() if k != "release_sha256"})
        write(self.root / "successor-release.json", self.metadata)

    def seal(self):
        bindings = list(self.metadata["artifacts"].values()) + self.metadata["evidence"]
        for binding in bindings:
            binding["sha256"] = validator.sha(self.root / binding["path"])
        self.run_git("add", "--", *[b["path"] for b in bindings])
        self.run_git("commit", "--quiet", "--allow-empty", "-m", "Synthetic frozen artifacts")
        self.metadata["artifact_freeze_commit"] = self.run_git("rev-parse", "HEAD").decode().strip()
        self.save_metadata()

    def rebind_proof(self):
        state = method.read(self.file("state"))
        for row in state["artifacts"]:
            path = self.file("state").parent / row["path"]
            if path.is_file():
                row["sha256"] = validator.sha(path)
                row["artifact_id"] = artifact_id(row["path"], row["sha256"])
        write(self.file("state"), state)
        lock = method.read(self.file("study_lock"))
        for role, field in (("state", "source_only_state_sha256"), ("draft", "draft_file_sha256"), ("review", "review_file_sha256")):
            lock["release"]["lineage"][field] = validator.sha(self.file(role))
        final = method.read(self.file("benchmark"))
        lock["release"].update(benchmark_file_sha256=validator.sha(self.file("benchmark")), benchmark_sha256=final["benchmark_sha256"])
        lock["benchmark_semantic_sha256"] = method.benchmark_semantic_hash(final)
        lock["lock_sha256"] = method.digest({k: v for k, v in lock.items() if k != "lock_sha256"})
        write(self.file("study_lock"), lock)
        self.seal()

    def validate(self):
        return validator.validate(self.root, "successor-release.json", method)

    def test_public_proof_passes_without_pdf_or_extracted_text(self):
        self.assertFalse(list(self.root.rglob("*.pdf")))
        self.assertTrue(self.validate()["ok"])

    def test_metadata_self_hash_and_runtime_pin_fail_closed(self):
        self.metadata["release_id"] = "CHANGED"
        write(self.root / "successor-release.json", self.metadata)
        with self.assertRaisesRegex(ValueError, "self-hash"):
            self.validate()
        self.metadata["methodology_commit"] = "a" * 40
        self.save_metadata()
        with self.assertRaisesRegex(ValueError, "pin differs"):
            self.validate()

    def test_rehashed_working_bytes_cannot_replace_committed_freeze(self):
        self.file("review").write_bytes(self.file("review").read_bytes() + b"\n")
        self.metadata["artifacts"]["review"]["sha256"] = validator.sha(self.file("review"))
        self.save_metadata()
        with self.assertRaisesRegex(ValueError, "committed freeze bytes"):
            self.validate()

    def test_unapproved_field_change_fails_after_all_transport_hashes_rebound(self):
        final = method.read(self.file("benchmark"))
        final["subjects"][0]["stance"] = "An unapproved synthetic stance change."
        final["benchmark_sha256"] = method.digest({k: v for k, v in final.items() if k != "benchmark_sha256"})
        write(self.file("benchmark"), final)
        self.rebind_proof()
        with self.assertRaisesRegex(ValueError, "approved_changes"):
            self.validate()

    def test_false_canonical_benchmark_hash_fails(self):
        final = method.read(self.file("benchmark")); final["benchmark_sha256"] = "0" * 64
        write(self.file("benchmark"), final); self.rebind_proof()
        with self.assertRaisesRegex(ValueError, "self-hash"):
            self.validate()

    def test_missing_typed_registration_fails(self):
        state = method.read(self.file("state"))
        next(r for r in state["artifacts"] if r["stage"] == "benchmark_review")["schema_version"] = "untyped-review"
        write(self.file("state"), state); self.rebind_proof()
        with self.assertRaisesRegex(ValueError, "typed freeze registration"):
            self.validate()

    def test_policy_semantics_cannot_be_swapped(self):
        template = method.read(self.file("policy_template"))
        template["policy_semantic_content"]["audience"]["label"] = "Different synthetic audience"
        template["template_sha256"] = method.digest({k: v for k, v in template.items() if k != "template_sha256"})
        write(self.file("policy_template"), template); self.seal()
        with self.assertRaisesRegex(ValueError, "semantic policy"):
            self.validate()

    def test_false_benchmark_semantic_identity_fails(self):
        lock = method.read(self.file("study_lock"))
        lock["benchmark_semantic_sha256"] = "0" * 64
        lock["lock_sha256"] = method.digest({k: v for k, v in lock.items() if k != "lock_sha256"})
        write(self.file("study_lock"), lock); self.seal()
        with self.assertRaisesRegex(ValueError, "semantic benchmark"):
            self.validate()

    def test_density_total_and_provenance_must_match(self):
        density = self.root / "release/density.json"
        doc = method.read(density); doc["total_indexable_source_words"] = 101
        write(density, doc)
        lock = method.read(self.file("study_lock"))
        lock["density_basis"]["chunks"][0]["source_artifact"]["sha256"] = validator.sha(density)
        lock["density_basis"]["measurement_sha256"] = method.digest(lock["density_basis"]["chunks"])
        lock["lock_sha256"] = method.digest({k: v for k, v in lock.items() if k != "lock_sha256"})
        write(self.file("study_lock"), lock); self.seal()
        with self.assertRaisesRegex(ValueError, "total does not recompute"):
            self.validate()

    def test_missing_density_correction_proof_fails(self):
        self.metadata["evidence"] = [r for r in self.metadata["evidence"] if r["path"] != "proof/scope.json"]
        self.save_metadata()
        with self.assertRaisesRegex(ValueError, "correction provenance"):
            self.validate()

    def test_consistent_recount_cannot_claim_metadata_only_revision(self):
        density = self.root / "release/density.json"
        doc = method.read(density)
        doc["total_indexable_source_words"] = 101
        doc["chunks"][0]["indexable_source_words"] = 101
        doc["pages"][0]["indexable_source_words"] = 101
        write(density, doc)
        lock = method.read(self.file("study_lock"))
        lock["density_basis"]["chunks"][0].update(indexable_source_words=101, source_artifact={"path": "density.json", "sha256": validator.sha(density)})
        lock["density_basis"]["measurement_sha256"] = method.digest(lock["density_basis"]["chunks"])
        lock["lock_sha256"] = method.digest({k: v for k, v in lock.items() if k != "lock_sha256"})
        write(self.file("study_lock"), lock); self.seal()
        with self.assertRaisesRegex(ValueError, "Metadata-only density correction"):
            self.validate()

    def test_traversal_and_symlinks_fail(self):
        with self.assertRaisesRegex(ValueError, "Unsafe artifact"):
            validator.relative_path(self.root, "../outside")
        (self.root / "linked.json").symlink_to(self.file("review"))
        with self.assertRaisesRegex(ValueError, "Symlink"):
            validator.relative_path(self.root, "linked.json")

    def test_checkpoint_members_hashes_and_no_recursive_metadata(self):
        members = {f"{role}.json": self.metadata["artifacts"][role]["path"] for role in ("state", "draft", "review", "benchmark")}
        archive = self.root / "checkpoint.zip"
        with zipfile.ZipFile(archive, "w") as output:
            for name, path in members.items():
                output.write(self.root / path, name)
        self.metadata["checkpoints"] = [{"path": "checkpoint.zip", "sha256": validator.sha(archive), "members": members}]
        self.save_metadata(); self.assertEqual(1, self.validate()["checkpoints"])
        with zipfile.ZipFile(archive, "w") as output:
            for name, path in members.items():
                output.writestr(name, b"wrong" if name == "review.json" else (self.root / path).read_bytes())
        self.metadata["checkpoints"][0]["sha256"] = validator.sha(archive); self.save_metadata()
        with self.assertRaisesRegex(ValueError, "Checkpoint member differs"):
            self.validate()
        self.metadata["checkpoints"][0]["members"]["metadata.json"] = "successor-release.json"; self.save_metadata()
        with self.assertRaisesRegex(ValueError, "never release metadata"):
            self.validate()

    def test_dispatch_is_explicit_before_selection_and_fails_after_deletion(self):
        runner = Path(__file__).resolve().parents[1] / "scripts/run_successor_checks.py"
        command = [sys.executable, str(runner), "--root", str(self.root), "--if-selected"]
        (self.root / "successor-release.json").unlink()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("historical_v3_only", json.loads(result.stdout)["scope"])
        self.save_metadata(); self.run_git("add", "successor-release.json")
        self.run_git("commit", "--quiet", "-m", "Synthetic release selection")
        (self.root / "successor-release.json").unlink()
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertIn("Selected successor release metadata is missing", result.stdout)

    def test_selected_runner_rejects_missing_focused_tests_before_bootstrap(self):
        runner = Path(__file__).resolve().parents[1] / "scripts/run_successor_checks.py"
        result = subprocess.run([sys.executable, str(runner), "--root", str(self.root)], capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertIn("Focused successor tests are missing", result.stdout)


if __name__ == "__main__":
    unittest.main()
