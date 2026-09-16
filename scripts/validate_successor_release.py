#!/usr/bin/env python3
"""Verify a successor release using pinned methodology; never perform source review."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile


METHODOLOGY_COMMIT = "7ed97581c1e82eb13052874b0e82eb429580a7b1"
ROLES = {"state", "draft", "review", "benchmark", "study_lock", "page_map", "chunk_manifest", "source_policy", "policy_template"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.PIPE)


def read(path):
    value = json.loads(path.read_bytes())
    require(isinstance(value, dict), f"Expected JSON object: {path}")
    return value


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(root, name):
    require(isinstance(name, str) and bool(name) and "\\" not in name, "Expected a relative POSIX artifact path")
    parts = name.split("/")
    require(not PurePosixPath(name).is_absolute() and all(p not in ("", ".", "..") for p in parts), f"Unsafe artifact path: {name}")
    path = root / name
    require(path.resolve().is_relative_to(root.resolve()), f"Artifact escapes repository: {name}")
    require(not any((root.joinpath(*parts[:i])).is_symlink() for i in range(1, len(parts) + 1)), f"Symlink artifact path: {name}")
    return path


def bound_file(root, binding):
    require(isinstance(binding, dict) and set(binding) == {"path", "sha256"}, "Artifact binding requires only path and sha256")
    require(isinstance(binding["sha256"], str) and re.fullmatch(r"[a-f0-9]{64}", binding["sha256"]), "Invalid file SHA-256")
    path = relative_path(root, binding["path"])
    require(path.is_file() and sha(path) == binding["sha256"], f"Artifact bytes mismatch: {binding['path']}")
    return path


def committed_file(root, revision, name):
    path = relative_path(root, name)
    entries = git(root, "ls-tree", "-z", revision, "--", name).split(b"\0")
    entries = [entry for entry in entries if entry]
    require(len(entries) == 1, f"Artifact absent from {revision}: {name}")
    metadata, found = entries[0].split(b"\t", 1)
    mode, kind, blob = metadata.decode().split()
    require(found.decode() == name and kind == "blob" and mode in {"100644", "100755"}, f"Not a regular committed file: {name}")
    require(path.read_bytes() == git(root, "cat-file", "blob", blob), f"Artifact differs from committed freeze bytes: {name}")


def load_methodology(root):
    """Verify importable code against the reviewed commit before loading it."""
    require(git(root, "rev-parse", f"{METHODOLOGY_COMMIT}^{{commit}}").decode().strip() == METHODOLOGY_COMMIT, "Pinned methodology commit unavailable")
    skill = root / "evaluate-subject-index"
    expected = set(git(root, "ls-tree", "-r", "--name-only", METHODOLOGY_COMMIT, "--", "evaluate-subject-index").decode().splitlines())
    actual = {p.relative_to(root).as_posix() for p in skill.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    require(actual == expected, "Methodology checkout has missing or extra skill files")
    for name in sorted(expected):
        committed_file(root, METHODOLOGY_COMMIT, name)
    sys.path.insert(0, str(skill / "scripts"))
    import study_comparison
    return study_comparison


def validate(root, descriptor_path, method):
    root = root.resolve()
    descriptor_path = relative_path(root, descriptor_path)
    release = read(descriptor_path)
    require(set(release) == {"schema_version", "release_id", "methodology_commit", "artifact_freeze_commit", "artifacts", "evidence", "checkpoints", "release_sha256"}, "Unexpected or missing release metadata fields")
    require(release["schema_version"] == "subject-index-successor-release-v1", "Unknown successor release metadata version")
    require(release["methodology_commit"] == METHODOLOGY_COMMIT, "Release methodology pin differs")
    require(release["release_sha256"] == digest({k: v for k, v in release.items() if k != "release_sha256"}), "Release metadata self-hash mismatch")
    freeze = release["artifact_freeze_commit"]
    require(isinstance(freeze, str) and re.fullmatch(r"[a-f0-9]{40}", freeze), "Expected exact artifact freeze commit")
    git(root, "merge-base", "--is-ancestor", freeze, "HEAD")
    require(set(release["artifacts"]) == ROLES, "Required successor artifact roles differ")
    require(isinstance(release["evidence"], list) and isinstance(release["checkpoints"], list), "Evidence/checkpoints must be arrays")
    bindings = list(release["artifacts"].values()) + release["evidence"]
    paths = [binding["path"] for binding in bindings]
    require(len(paths) == len(set(paths)), "Duplicate release artifact path")
    require(descriptor_path.relative_to(root).as_posix() not in paths, "Release metadata cannot bind itself as a frozen artifact")
    for binding in bindings:
        bound_file(root, binding)
        committed_file(root, freeze, binding["path"])
    by_path = {binding["path"]: binding for binding in bindings}
    files = {role: root / binding["path"] for role, binding in release["artifacts"].items()}
    documents = {role: read(path) for role, path in files.items()}
    lock, final, state = (documents[k] for k in ("study_lock", "benchmark", "state"))
    require(lock["release"]["lineage"]["kind"] == "current_source_freeze", "Successor requires current_source_freeze")
    require(release["release_id"] == lock["release"]["release_id"], "Release ID differs from lock")
    method.validate_release(lock, final, sha(files["benchmark"]))
    method.validate_native_lineage(lock, final, files["state"], files["draft"], files["review"])

    # No PDF/discovery text needed: verify the explicitly bound public freeze proof.
    from dimension_score_v8_cli import validate_v8_policy
    from schema_validation import schema_errors
    for role, stage, schema in (
        ("draft", "benchmark_synthesis", "source-subject-benchmark-draft-v1"),
        ("review", "benchmark_review", "source-benchmark-review-v1"),
        ("benchmark", "benchmark_freeze", "source-subject-benchmark-v2"),
        ("page_map", "page_mapping", "page-map-v1"),
        ("chunk_manifest", "chunk_definition", "chunk-manifest-v1"),
        ("source_policy", "define_policy", "subject-index-evaluation-policy-v4"),
    ):
        matches = [r for r in state["artifacts"] if r["stage"] == stage and r.get("schema_version") == schema]
        require(len(matches) == 1, f"Expected one typed source registration: {role}")
        registered = relative_path(files["state"].parent, matches[0]["path"])
        require(registered == files[role] and matches[0]["sha256"] == sha(files[role]), f"Typed source registration path/hash mismatch: {role}")
    source_policy = documents["source_policy"]
    require(not schema_errors(source_policy, "evaluation-policy-v4.schema.json"), "Invalid source policy")
    validate_v8_policy(source_policy)
    require(source_policy["policy_sha256"] == digest({k: v for k, v in source_policy.items() if k != "policy_sha256"}) == final["policy_sha256"], "Source policy canonical binding differs")
    scope = lock["source_scope"]
    require(all(source_policy["source_scope"][k] == v for k, v in scope.items()), "Source policy scope differs")
    require(state["source"]["document_page_span"] == scope["document_page_span"], "Frozen state source span differs")
    template = documents["policy_template"]
    require(template.get("schema_version") == "subject-index-study-policy-template-v1", "Expected unfrozen study policy template")
    require(method.policy_semantic_hash(template) == lock["policy_semantic_sha256"], "Template/lock semantic policy mismatch")
    require(not (set(template["policy_semantic_content"]) & method.POLICY_WRAPPERS), "Study template contains identity/freeze wrappers")
    # In-memory schema adapter: reuse real source wrappers, never invent a freeze.
    # This view is not written, selected, or represented as an approved policy.
    policy = {k: deepcopy(v) for k, v in source_policy.items() if k in method.POLICY_WRAPPERS}
    policy.update(deepcopy(template["policy_semantic_content"]))
    policy["policy_sha256"] = digest({k: v for k, v in policy.items() if k != "policy_sha256"})
    validate_v8_policy(policy)
    require(all(policy["source_scope"][k] == v for k, v in scope.items()), "Template source scope differs")
    require(policy["policy_profile"]["id"] == lock["policy_profile"] and policy["audit_design"]["mode"] == lock["audit_mode"], "Template mode/profile differs")
    method.validate_density_evidence(lock, files["study_lock"].parent, documents["page_map"], documents["chunk_manifest"])
    for row in lock["density_basis"]["chunks"]:
        path = relative_path(files["study_lock"].parent, row["source_artifact"]["path"])
        relative = path.relative_to(root).as_posix()
        require(by_path.get(relative) == {"path": relative, "sha256": row["source_artifact"]["sha256"]}, "Density evidence missing from committed release bindings")
        measurement = read(path)
        correction = measurement.get("metadata_correction")
        if correction is not None:
            references = [
                {"path": correction["original_measurement_path"], "sha256": correction["original_measurement_file_sha256"]},
                {"path": correction["scope_addendum_path"], "sha256": correction["scope_addendum_file_sha256"]},
                correction["independent_source_scope_disposition"],
            ]
            require(all(by_path.get(r["path"]) == r for r in references), "Density correction provenance not bound in release evidence")
            original = read(root / references[0]["path"])
            restored = deepcopy(measurement)
            restored.pop("metadata_correction")
            restored["protocol"]["source_role_note"] = original["protocol"]["source_role_note"]
            require(restored == original, "Metadata-only density correction changed computation/content")

    # Archives follow the freeze commit; metadata follows archives. No self-inclusion.
    checkpoint_paths = set()
    for checkpoint in release["checkpoints"]:
        require(set(checkpoint) == {"path", "sha256", "members"}, "Checkpoint requires path, sha256 and explicit members")
        name = checkpoint["path"]
        require(name not in by_path and name not in checkpoint_paths and name != descriptor_path.relative_to(root).as_posix(), "Checkpoint path collision/self-reference")
        checkpoint_paths.add(name)
        path = bound_file(root, {k: checkpoint[k] for k in ("path", "sha256")})
        members = checkpoint["members"]
        require(isinstance(members, dict) and bool(members), "Checkpoint members must be a nonempty path-to-artifact-path map")
        require(set(members.values()).issubset(by_path), "Checkpoint member must bind a frozen artifact, never release metadata or an archive")
        require({release["artifacts"][role]["path"] for role in ("state", "draft", "review", "benchmark")}.issubset(members.values()), "Checkpoint lacks the complete source freeze proof")
        with zipfile.ZipFile(path) as archive:
            infos = [i for i in archive.infolist() if not i.is_dir()]
            require(len(infos) == len(members) and {i.filename for i in infos} == set(members), "Checkpoint missing/duplicate/undeclared members")
            require(archive.testzip() is None, "Corrupt checkpoint ZIP")
            for member, artifact in members.items():
                relative_path(root, member)  # Validate names; never extract.
                require(hashlib.sha256(archive.read(member)).hexdigest() == by_path[artifact]["sha256"], f"Checkpoint member differs: {member}")
    return {"ok": True, "release_id": release["release_id"], "artifact_freeze_commit": freeze, "methodology_commit": METHODOLOGY_COMMIT, "frozen_files": len(bindings), "checkpoints": len(checkpoint_paths), "editorial_review_performed": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--release", required=True, help="Repository-relative successor release metadata path")
    parser.add_argument("--methodology-repo", type=Path, required=True)
    args = parser.parse_args()
    try:
        method = load_methodology(args.methodology_repo.resolve())
        print(json.dumps(validate(args.root, args.release, method), indent=2))
    except (ValueError, KeyError, TypeError, OSError, subprocess.CalledProcessError, zipfile.BadZipFile) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
