#!/usr/bin/env python3
"""Verify the Bass Oracle 111 review/launch crate stays local, safe, and count-consistent."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_READY_TRACKS = 34
EXPECTED_TARGET_TRACKS = 111

LAUNCH_MANIFEST = ROOT / "docs/launch/bass_oracle_launch_manifest.json"
REVIEW_MANIFEST = ROOT / "docs/review_manifest.json"
PLAYLIST_M3U = ROOT / "docs/launch/bass_oracle_034_ready_playlist.m3u"
FFMPEG_CONCAT = ROOT / "docs/launch/bass_oracle_034_ffmpeg_concat.txt"
LISTENING_CSV = ROOT / "docs/launch/bass_oracle_034_listening_review.csv"
LAUNCH_FRAMEWORK = ROOT / "docs/launch/NIGHTBUILDING_LAUNCH_FRAMEWORK.md"
STREAM_SNAPSHOT = ROOT / "docs/reports/BASS_ORACLE_STREAM_STATUS_SNAPSHOT_20260509-081615.md"
LISTENER_DECISION_MATRIX = ROOT / "docs/launch/BASS_ORACLE_LISTENER_DECISION_MATRIX_20260509-0900.md"
MORNING_HANDOFF = ROOT / "docs/reports/BASS_ORACLE_MORNING_HANDOFF_20260509-091556.md"
NIGHTSHIFT_REPORT_GLOB = "BASS_ORACLE_NIGHTSHIFT_REVIEW_*.md"

REQUIRED_ASSETS = [
    ROOT / "docs/launch/assets/bass_oracle_111_avatar.png",
    ROOT / "docs/launch/assets/m1ndb0tz_vtuber_sprite_live.png",
    ROOT / "docs/launch/assets/shy_strawberry_big.png",
    ROOT / "docs/launch/assets/gold_life_coin.png",
    ROOT / "docs/launch/assets/tax_collector_gold_big.png",
]

REQUIRED_CLOSED_GATE_PHRASES = [
    "does not start streams",
    "post publicly",
    "upload datasets",
    "create payment links",
    "GPU/training jobs",
    "Duplicate livestream pusher startup",
    "RTMP target was redacted as `rtmp://[REDACTED]`",
]

UNSAFE_OVERCLAIM_PATTERNS = [
    re.compile(r"\b(revenue|sales?|profit)\s+(earned|generated|made)\b", re.I),
    re.compile(r"\b(Kick|Twitch)\s+(is\s+)?live\b", re.I),
    re.compile(r"\b(uploaded|published|released)\s+(to\s+)?(Hugging\s*Face|HF|public)\b", re.I),
]

SECRET_PATTERNS = [
    re.compile(r"rtmps?://(?!\[REDACTED\](?:\)|`|\s|$))[^\s`)]*", re.I),
    re.compile(r"\b(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?(?!\[REDACTED\])[^'\"\s]{8,}", re.I),
    re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
]


def load_json(path: Path) -> dict:
    assert path.exists(), f"missing required JSON: {path.relative_to(ROOT)}"
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def assert_count(label: str, actual: int, expected: int = EXPECTED_READY_TRACKS) -> None:
    assert actual == expected, f"{label}: expected {expected}, got {actual}"


def non_comment_playlist_entries(path: Path) -> list[str]:
    assert path.exists(), f"missing playlist: {path.relative_to(ROOT)}"
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def concat_entries(path: Path) -> list[str]:
    assert path.exists(), f"missing ffmpeg concat file: {path.relative_to(ROOT)}"
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("file "):
            entries.append(line)
    return entries


def csv_rows(path: Path) -> list[dict[str, str]]:
    assert path.exists(), f"missing listening CSV: {path.relative_to(ROOT)}"
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def verify_counts_and_paths() -> None:
    launch = load_json(LAUNCH_MANIFEST)
    review = load_json(REVIEW_MANIFEST)

    assert launch.get("entity") == "Bass Oracle 111"
    assert launch.get("target_tracks") == EXPECTED_TARGET_TRACKS
    assert_count("launch ready_tracks", int(launch.get("ready_tracks", -1)))
    assert_count("launch tracks", len(launch.get("tracks", [])))
    assert launch.get("total_duration_hms") == "2:17:45"

    assert review.get("status") == "review_only_generation_stopped"
    assert_count("review complete_track_count", int(review.get("complete_track_count", -1)))
    assert review.get("target_track_count") == EXPECTED_TARGET_TRACKS
    review_tracks = review.get("tracks", [])
    assert_count("review tracks", len(review_tracks))

    assert_count("playlist entries", len(non_comment_playlist_entries(PLAYLIST_M3U)))
    assert_count("ffmpeg concat entries", len(concat_entries(FFMPEG_CONCAT)))
    rows = csv_rows(LISTENING_CSV)
    assert_count("listening CSV rows", len(rows))

    for i, row in enumerate(rows, start=1):
        assert int(row["index"]) == i, f"CSV row index mismatch at row {i}"
        assert row["status"] == "ready_for_listening_review", f"CSV row {i} status drifted"
        assert row["sha256"], f"CSV row {i} missing sha256"

    for i, track in enumerate(review_tracks, start=1):
        assert int(track["track_number"]) == i, f"review track_number mismatch at {i}"
        audio_path = ROOT / "docs" / track["audio"]
        assert audio_path.exists(), f"missing committed review audio: {audio_path.relative_to(ROOT)}"
        assert audio_path.stat().st_size == int(track["size_bytes"]), f"audio size mismatch: {audio_path.relative_to(ROOT)}"

    for asset in REQUIRED_ASSETS:
        assert asset.exists(), f"missing launch asset: {asset.relative_to(ROOT)}"
        assert asset.stat().st_size > 0, f"empty launch asset: {asset.relative_to(ROOT)}"


def verify_closed_gates_and_language() -> None:
    for path in [LAUNCH_FRAMEWORK, STREAM_SNAPSHOT, LISTENER_DECISION_MATRIX, MORNING_HANDOFF]:
        assert path.exists(), f"missing safety document: {path.relative_to(ROOT)}"
    safety_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [LAUNCH_FRAMEWORK, STREAM_SNAPSHOT, LISTENER_DECISION_MATRIX, MORNING_HANDOFF]
    )
    for phrase in REQUIRED_CLOSED_GATE_PHRASES:
        assert phrase in safety_text, f"missing closed-gate phrase: {phrase}"
    for pattern in UNSAFE_OVERCLAIM_PATTERNS:
        match = pattern.search(safety_text)
        assert not match, f"unsafe overclaim language found: {match.group(0)!r}"


def verify_nightshift_review_reports() -> None:
    """Dynamically verify every timestamped nightshift review remains safe and proof-grounded."""
    reports = sorted((ROOT / "docs/reports").glob(NIGHTSHIFT_REPORT_GLOB))
    assert reports, f"missing nightshift review reports matching docs/reports/{NIGHTSHIFT_REPORT_GLOB}"

    for report in reports:
        text = report.read_text(encoding="utf-8")
        relative = report.relative_to(ROOT)
        for required in [
            "docs/launch/bass_oracle_launch_manifest.json",
            "closed",
        ]:
            assert required in text, f"{relative} missing proof/safety phrase: {required}"
        assert ("34 ready tracks" in text or "34 / 111 tracks ready" in text or "34 / 111 ready tracks" in text), (
            f"{relative} must cite the 34-track ready crate state"
        )
        lowered = text.lower()
        assert (
            "not claimed" in lowered
            or "not checked" in lowered
            or "not verified" in lowered
            or "not** verified" in lowered
            or "not kick/twitch liveness proof" in lowered
        ), f"{relative} must avoid claiming external Kick/Twitch liveness"
        assert "rtmp://[REDACTED]" in text, f"{relative} must keep RTMP evidence redacted"
        for pattern in UNSAFE_OVERCLAIM_PATTERNS:
            match = pattern.search(text)
            if match:
                context = lowered[max(0, match.start() - 80): match.end() + 80]
                negated = any(phrase in context for phrase in ["not checked", "not claimed", "not verified", "not** verified", "not kick/twitch liveness proof"])
                assert negated, f"unsafe overclaim language in {relative}: {match.group(0)!r}"
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            assert not match, f"raw secret or RTMP target in {relative}: {match.group(0)[:48]!r}"


def verify_operator_handoff_documents() -> None:
    """Keep the human-facing handoff artifacts aligned with the verified crate."""
    review = load_json(REVIEW_MANIFEST)
    committed_audio_paths = {f"`{track['audio']}`" for track in review.get("tracks", [])}

    matrix = LISTENER_DECISION_MATRIX.read_text(encoding="utf-8")
    assert matrix.count("| pending_human_listen |") == EXPECTED_READY_TRACKS, (
        "listener decision matrix must keep all 34 tracks pending by default"
    )
    for required_path in [
        "docs/review_manifest.json",
        "docs/launch/bass_oracle_launch_manifest.json",
        "docs/launch/bass_oracle_034_ready_playlist.m3u",
        "docs/launch/bass_oracle_034_listening_review.csv",
        "docs/reports/BASS_ORACLE_STREAM_STATUS_SNAPSHOT_20260509-081615.md",
    ]:
        assert required_path in matrix, f"listener matrix missing proof path: {required_path}"
        assert (ROOT / required_path).exists(), f"listener matrix proof path does not exist: {required_path}"
    for audio_ref in committed_audio_paths:
        assert audio_ref in matrix, f"listener matrix missing committed audio ref: {audio_ref}"

    handoff = MORNING_HANDOFF.read_text(encoding="utf-8")
    for required_path in [
        "docs/index.html",
        "docs/review_manifest.json",
        "docs/launch/bass_oracle_launch_manifest.json",
        "docs/launch/BASS_ORACLE_LISTENER_DECISION_MATRIX_20260509-0900.md",
        "docs/reports/BASS_ORACLE_STREAM_STATUS_SNAPSHOT_20260509-081615.md",
        "docs/reports/BASS_ORACLE_NIGHTSHIFT_REVIEW_20260509-084622.md",
    ]:
        assert required_path in handoff, f"morning handoff missing proof path: {required_path}"
        assert (ROOT / required_path).exists(), f"morning handoff proof path does not exist: {required_path}"
    for phrase in [
        "External Kick/Twitch status: not checked and not claimed.",
        "pending_human_listen",
        "Add a focused morning-reveal verifier or index hook",
    ]:
        assert phrase in handoff, f"morning handoff missing safety/next-step phrase: {phrase}"


def verify_no_secrets_in_operator_docs() -> None:
    scan_roots = [ROOT / "docs/launch", ROOT / "docs/reports", ROOT / "site"]
    text_files = []
    for scan_root in scan_roots:
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md", ".json", ".csv", ".m3u", ".txt", ".html", ".js"}:
                text_files.append(path)
    for path in text_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            assert not match, f"potential secret or raw RTMP target in {path.relative_to(ROOT)}: {match.group(0)[:48]!r}"


def main() -> None:
    verify_counts_and_paths()
    verify_closed_gates_and_language()
    verify_nightshift_review_reports()
    verify_operator_handoff_documents()
    verify_no_secrets_in_operator_docs()
    print("Bass Oracle launch verifier passed: counts, paths, handoffs, nightshift reports, closed gates, and redactions are consistent.")


if __name__ == "__main__":
    main()
