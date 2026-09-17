#!/usr/bin/env python3
"""Validate the immutable benchmark-v3 release and its housekeeping controls."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DESCRIPTOR_PATH = ROOT / "benchmark-release.v3.json"
STATE_PATH = ROOT / "evaluation-state.json"
MANIFEST_PATH = ROOT / "artifact-manifest.json"
EXPECTED_FREEZE_COMMIT = "98dbffd0ca171b5b7db76dbe1b2b5d5265ccacab"
EXPECTED_BENCHMARK_FILE_SHA256 = "34a399cda8ca9f1b07b9fa0ddad36ac4f5073ef12d8b12df42fb023818508b27"
EXPECTED_BENCHMARK_CANONICAL_SHA256 = "b925797fcab50b2008ad5974590e323f772e5ea7013efa84ce7606007439aeb3"
EXPECTED_COUNTS = {"subjects": 1366, "relationships": 3460, "reader_tasks": 1026}


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"Cannot read valid JSON from {path.relative_to(ROOT)}: {exc}") from exc


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ValidationError(f"Cannot hash {path.relative_to(ROOT)}: {exc}") from exc
    return digest.hexdigest()


def canonical_hash(payload: dict[str, Any], own_hash_field: str) -> str:
    clone = dict(payload)
    clone.pop(own_hash_field, None)
    encoded = json.dumps(clone, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def artifact_by_id(records: list[dict[str, Any]], artifact_id: str) -> dict[str, Any]:
    matches = [record for record in records if record.get("artifact_id") == artifact_id]
    require(len(matches) == 1, f"Expected exactly one artifact {artifact_id}, found {len(matches)}")
    return matches[0]


def artifact_by_path(records: list[dict[str, Any]], path: str) -> dict[str, Any]:
    matches = [record for record in records if record.get("path") == path]
    require(len(matches) == 1, f"Expected exactly one artifact at {path}, found {len(matches)}")
    return matches[0]


def validate_git_freeze(freeze_commit: str, benchmark_path: str) -> None:
    try:
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", freeze_commit, "HEAD"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        comparison = subprocess.run(
            ["git", "diff", "--exit-code", freeze_commit, "--", benchmark_path],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValidationError(f"Unable to verify Git freeze commit: {exc}") from exc
    require(comparison.returncode == 0, f"{benchmark_path} differs from artifact freeze commit {freeze_commit}")


def validate_checkpoint(path: Path, expected_sha256: str, state: dict[str, Any]) -> None:
    require(path.is_file(), f"Final-release checkpoint is missing: {path.relative_to(ROOT)}")
    require(sha256_file(path) == expected_sha256, "Final-release checkpoint file SHA-256 mismatch")
    try:
        with zipfile.ZipFile(path) as archive:
            require(archive.testzip() is None, "Final-release checkpoint has a corrupt ZIP member")
            metadata = json.loads(archive.read("bundle-metadata.json"))
            state_bytes = archive.read("evaluation-state.json")
            manifest_bytes = archive.read("artifact-manifest.json")
            descriptor_bytes = archive.read("benchmark-release.v3.json")
            bundled_state = json.loads(state_bytes)
            bundled_manifest = json.loads(manifest_bytes)
            require(
                "benchmark-release.v3.json" in metadata.get("included_paths", []),
                "Release descriptor is absent from final-release checkpoint",
            )
    except (OSError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        raise ValidationError(f"Cannot validate final-release checkpoint: {exc}") from exc

    release_state = state.get("benchmark_workflow", {}).get("release", {})
    require(metadata.get("state_sha256") == release_state.get("checkpoint_state_sha256"), "Checkpoint state snapshot hash mismatch")
    require(metadata.get("manifest_sha256") == release_state.get("checkpoint_manifest_sha256"), "Checkpoint manifest snapshot hash mismatch")
    require(sha256_bytes(state_bytes) == metadata.get("state_sha256"), "Bundled state bytes do not match bundle metadata")
    require(sha256_bytes(manifest_bytes) == metadata.get("manifest_sha256"), "Bundled manifest bytes do not match bundle metadata")
    require(
        bundled_state.get("benchmark_workflow", {}).get("merge_gate")
        == "cleared_after_v3_adjudication_and_coordinator_merge",
        "Checkpoint does not contain the corrected cleared merge gate",
    )
    descriptor_entry = artifact_by_path(bundled_manifest.get("artifacts", []), "benchmark-release.v3.json")
    bundled_descriptor_sha256 = sha256_bytes(descriptor_bytes)
    require(
        descriptor_entry.get("sha256") == bundled_descriptor_sha256,
        "Checkpoint manifest does not match its bundled release descriptor bytes",
    )
    require(
        bundled_descriptor_sha256 == sha256_file(DESCRIPTOR_PATH),
        "Checkpoint contains a different release descriptor than the live repository",
    )


def main() -> int:
    try:
        descriptor = load_json(DESCRIPTOR_PATH)
        state = load_json(STATE_PATH)
        manifest = load_json(MANIFEST_PATH)

        require(descriptor.get("schema_version") == "subject-index-benchmark-release-v1", "Unexpected release descriptor schema")
        require(descriptor.get("version") == 3, "Release descriptor is not benchmark v3")
        require(
            descriptor.get("artifact_freeze", {}).get("commit") == EXPECTED_FREEZE_COMMIT,
            "Release descriptor attempted to redefine the immutable v3 freeze commit",
        )
        require(
            descriptor.get("artifacts", {}).get("benchmark", {}).get("file_sha256")
            == EXPECTED_BENCHMARK_FILE_SHA256,
            "Release descriptor attempted to redefine the immutable benchmark-v3 file hash",
        )
        require(
            descriptor.get("artifacts", {}).get("benchmark", {}).get("canonical_sha256")
            == EXPECTED_BENCHMARK_CANONICAL_SHA256,
            "Release descriptor attempted to redefine the immutable benchmark-v3 canonical hash",
        )
        require(descriptor.get("counts") == EXPECTED_COUNTS, "Release descriptor attempted to redefine benchmark-v3 counts")
        require(
            descriptor.get("release_sha256") == canonical_hash(descriptor, "release_sha256"),
            "Release descriptor canonical SHA-256 mismatch",
        )

        artifacts = descriptor.get("artifacts", {})
        canonical_fields = {
            "policy": "policy_sha256",
            "page_map": "page_map_sha256",
            "chunk_manifest": "chunk_manifest_sha256",
            "benchmark": "benchmark_sha256",
        }
        for name, artifact in artifacts.items():
            path_value = artifact.get("path")
            if path_value is None:
                continue
            path = ROOT / path_value
            expected = artifact.get("file_sha256")
            require(isinstance(expected, str) and sha256_file(path) == expected, f"{name} file SHA-256 mismatch")
            if name in canonical_fields:
                payload = load_json(path)
                own_hash_field = canonical_fields[name]
                expected_canonical = artifact.get("canonical_sha256")
                require(payload.get(own_hash_field) == expected_canonical, f"{name} embedded canonical SHA-256 mismatch")
                require(canonical_hash(payload, own_hash_field) == expected_canonical, f"{name} recomputed canonical SHA-256 mismatch")

        benchmark = load_json(ROOT / artifacts["benchmark"]["path"])
        review = load_json(ROOT / artifacts["review_ledger"]["path"])
        require(benchmark.get("version") == 3, "Frozen benchmark version mismatch")
        require(benchmark.get("candidate_blindness") == "preserved", "Benchmark candidate blindness is not preserved")
        require(len(benchmark.get("subjects", [])) == EXPECTED_COUNTS["subjects"], "Subject count mismatch")
        require(len(benchmark.get("relationships", [])) == EXPECTED_COUNTS["relationships"], "Relationship count mismatch")
        require(len(benchmark.get("reader_tasks", [])) == EXPECTED_COUNTS["reader_tasks"], "Reader-task count mismatch")
        require(review.get("review_mode") == "full", "Independent review was not full")
        require(review.get("candidate_blindness") == "preserved", "Review candidate blindness is not preserved")
        require(review.get("recommendation") == "approve_revised", "Review recommendation mismatch")
        completion = review.get("completion", {})
        require(completion.get("editorial_review_complete") is True, "Independent editorial review is incomplete")
        require(completion.get("no_unreviewed_required_items") is True, "Independent review has unreviewed required items")

        freeze_commit = EXPECTED_FREEZE_COMMIT
        validate_git_freeze(freeze_commit, artifacts["benchmark"]["path"])
        workflow = state.get("benchmark_workflow", {})
        require(
            workflow.get("merge_gate") == "cleared_after_v3_adjudication_and_coordinator_merge",
            "Live merge gate is not cleared",
        )
        require(workflow.get("artifact_freeze_commit") == freeze_commit, "State artifact freeze commit mismatch")
        require(not state.get("blockers"), "Live evaluation state has active blockers")

        descriptor_file_sha = sha256_file(DESCRIPTOR_PATH)
        manifest_descriptor = artifact_by_path(manifest.get("artifacts", []), "benchmark-release.v3.json")
        state_descriptor = artifact_by_id(state.get("artifacts", []), manifest_descriptor["artifact_id"])
        require(manifest_descriptor.get("sha256") == descriptor_file_sha, "Manifest release-descriptor SHA-256 mismatch")
        require(state_descriptor.get("sha256") == descriptor_file_sha, "State release-descriptor SHA-256 mismatch")

        release_state = workflow.get("release", {})
        checkpoint_path = release_state.get("final_release_checkpoint_path")
        checkpoint_sha = release_state.get("final_release_checkpoint_sha256")
        require(
            isinstance(checkpoint_path, str) and isinstance(checkpoint_sha, str),
            "Final-release checkpoint is not registered in state",
        )
        manifest_checkpoint = artifact_by_path(manifest.get("artifacts", []), checkpoint_path)
        state_checkpoint = artifact_by_id(state.get("artifacts", []), manifest_checkpoint["artifact_id"])
        require(manifest_checkpoint.get("sha256") == checkpoint_sha, "Manifest final-release checkpoint SHA-256 mismatch")
        require(state_checkpoint.get("sha256") == checkpoint_sha, "State final-release checkpoint SHA-256 mismatch")
        validate_checkpoint(ROOT / checkpoint_path, checkpoint_sha, state)

        # Historical v3 checks above remain mandatory and unchanged.
        # Preserve the first successor proof when selecting its reviewed correction.
        for release_path in ("successor-release.json", "successor-release.corrected.v1.json"):
            successor = subprocess.run([
                sys.executable, str(ROOT / "scripts/run_successor_checks.py"),
                "--root", str(ROOT), "--release", release_path, "--if-selected",
            ], check=False)
            require(successor.returncode == 0, f"Selected successor validation failed: {release_path}")

        print(
            json.dumps(
                {
                    "ok": True,
                    "release_id": descriptor["release_id"],
                    "artifact_freeze_commit": freeze_commit,
                    "benchmark_canonical_sha256": artifacts["benchmark"]["canonical_sha256"],
                    "final_release_checkpoint_sha256": checkpoint_sha,
                },
                indent=2,
            )
        )
        return 0
    except ValidationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
