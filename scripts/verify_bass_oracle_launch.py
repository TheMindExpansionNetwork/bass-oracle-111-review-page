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
NIGHTSHIFT_REPORT_INDEX_GLOB = "BASS_ORACLE_NIGHTSHIFT_REPORT_INDEX_*.md"
MORNING_REVEAL_SAFETY_CARD_GLOB = "BASS_ORACLE_MORNING_REVEAL_SAFETY_CARD_*.md"
WAKE_OPERATOR_DECISION_QUEUE_GLOB = "BASS_ORACLE_WAKE_OPERATOR_DECISION_QUEUE_*.md"
WAKE_READY_OPERATOR_BRIEF_GLOB = "bass_oracle_wake_ready_operator_brief_*.json"

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


def verify_nightshift_report_index() -> None:
    """Require the latest operator index to enumerate every nightshift review artifact."""
    indexes = sorted((ROOT / "docs/reports").glob(NIGHTSHIFT_REPORT_INDEX_GLOB))
    assert indexes, f"missing nightshift report index matching docs/reports/{NIGHTSHIFT_REPORT_INDEX_GLOB}"
    latest_index = indexes[-1]
    index_text = latest_index.read_text(encoding="utf-8")
    relative_index = latest_index.relative_to(ROOT)

    reports = sorted((ROOT / "docs/reports").glob(NIGHTSHIFT_REPORT_GLOB))
    assert reports, "nightshift report index has no review reports to enumerate"
    for report in reports:
        relative_report = str(report.relative_to(ROOT))
        assert relative_report in index_text, f"{relative_index} missing review path: {relative_report}"

    for required_path in [
        "docs/launch/bass_oracle_launch_manifest.json",
        "docs/review_manifest.json",
        "docs/launch/bass_oracle_034_ready_playlist.m3u",
        "docs/launch/bass_oracle_034_listening_review.csv",
        "docs/launch/BASS_ORACLE_LISTENER_DECISION_MATRIX_20260509-0900.md",
        "docs/reports/BASS_ORACLE_STREAM_STATUS_SNAPSHOT_20260509-081615.md",
    ]:
        assert required_path in index_text, f"{relative_index} missing proof anchor: {required_path}"
        assert (ROOT / required_path).exists(), f"report index proof anchor does not exist: {required_path}"

    for phrase in [
        "34 / 111 ready tracks",
        "rtmp://[REDACTED]",
        "External Kick/Twitch liveness is not checked, not verified, and not claimed.",
        "Duplicate livestream pusher startup remains closed; this report does not start streams.",
        "Cron creation/update/removal: closed.",
    ]:
        assert phrase in index_text, f"{relative_index} missing closed-gate/index phrase: {phrase}"
    for pattern in UNSAFE_OVERCLAIM_PATTERNS + SECRET_PATTERNS:
        match = pattern.search(index_text)
        assert not match, f"unsafe language or secret in {relative_index}: {match.group(0)[:48]!r}"


def verify_morning_reveal_safety_card() -> None:
    """Require the latest morning reveal safety card to stay proof-grounded and closed-gate."""
    cards = sorted((ROOT / "docs/launch").glob(MORNING_REVEAL_SAFETY_CARD_GLOB))
    assert cards, f"missing morning reveal safety card matching docs/launch/{MORNING_REVEAL_SAFETY_CARD_GLOB}"
    latest_card = cards[-1]
    text = latest_card.read_text(encoding="utf-8")
    relative = latest_card.relative_to(ROOT)

    for required_path in [
        "docs/launch/bass_oracle_launch_manifest.json",
        "docs/review_manifest.json",
        "docs/launch/bass_oracle_034_ready_playlist.m3u",
        "docs/launch/bass_oracle_034_listening_review.csv",
        "docs/launch/BASS_ORACLE_LISTENER_DECISION_MATRIX_20260509-0900.md",
        "docs/reports/BASS_ORACLE_NIGHTSHIFT_REPORT_INDEX_20260509-111637.md",
    ]:
        assert required_path in text, f"{relative} missing proof path: {required_path}"
        assert (ROOT / required_path).exists(), f"morning reveal safety-card proof path does not exist: {required_path}"

    for phrase in [
        "34-track review crate",
        "34 / 111 ready tracks",
        "2:17:45",
        "rtmp://[REDACTED]",
        "External Kick/Twitch liveness is not checked, not verified, and not claimed.",
        "Duplicate livestream pusher startup remains closed; this safety card does not start streams.",
        "Cron creation/update/removal and recursive autonomous scheduling: closed.",
        "Secrets, `.env` values, RTMP keys, tokens, and credentials: not printed; use `[REDACTED]` only.",
    ]:
        assert phrase in text, f"{relative} missing safety-card phrase: {phrase}"

    for pattern in UNSAFE_OVERCLAIM_PATTERNS + SECRET_PATTERNS:
        match = pattern.search(text)
        if match:
            lowered = text.lower()
            context = lowered[max(0, match.start() - 80): match.end() + 80]
            negated = any(phrase in context for phrase in ["not checked", "not claimed", "not verified"])
            assert negated, f"unsafe language or secret in {relative}: {match.group(0)[:48]!r}"


def verify_wake_operator_decision_queue() -> None:
    """Require the latest wake-operator queue to summarize proof paths without opening gates."""
    queues = sorted((ROOT / "docs/launch").glob(WAKE_OPERATOR_DECISION_QUEUE_GLOB))
    assert queues, f"missing wake operator decision queue matching docs/launch/{WAKE_OPERATOR_DECISION_QUEUE_GLOB}"
    latest_queue = queues[-1]
    text = latest_queue.read_text(encoding="utf-8")
    relative = latest_queue.relative_to(ROOT)

    for required_path in [
        "docs/launch/bass_oracle_launch_manifest.json",
        "docs/review_manifest.json",
        "docs/launch/bass_oracle_034_ready_playlist.m3u",
        "docs/launch/bass_oracle_034_listening_review.csv",
        "docs/launch/BASS_ORACLE_LISTENER_DECISION_MATRIX_20260509-0900.md",
        "docs/reports/BASS_ORACLE_NIGHTSHIFT_REPORT_INDEX_20260509-111637.md",
        "docs/launch/BASS_ORACLE_MORNING_REVEAL_SAFETY_CARD_20260509-1201.md",
        "docs/reports/BASS_ORACLE_STREAM_STATUS_SNAPSHOT_20260509-081615.md",
    ]:
        assert required_path in text, f"{relative} missing proof path: {required_path}"
        assert (ROOT / required_path).exists(), f"wake queue proof path does not exist: {required_path}"

    for phrase in [
        "34 / 111 ready tracks",
        "2:17:45",
        "pending_human_listen",
        "rtmp://[REDACTED]",
        "External Kick/Twitch liveness is not checked, not verified, and not claimed.",
        "Duplicate livestream pusher startup remains closed; this queue does not start streams.",
        "Public posting, outreach, DMs, email, and form submissions: closed.",
        "HF/private dataset uploads and public release: closed.",
        "Cron creation, update, removal, and recursive autonomous scheduling: closed.",
        "Secrets, `.env` values, RTMP keys, tokens, and credentials: not printed; use `[REDACTED]` only.",
    ]:
        assert phrase in text, f"{relative} missing decision-queue phrase: {phrase}"

    decision_rows = [line for line in text.splitlines() if line.startswith("| P")]
    assert len(decision_rows) >= 5, f"{relative} should keep at least five bounded operator decision rows"
    for pattern in UNSAFE_OVERCLAIM_PATTERNS + SECRET_PATTERNS:
        match = pattern.search(text)
        if match:
            lowered = text.lower()
            context = lowered[max(0, match.start() - 80): match.end() + 80]
            negated = any(phrase in context for phrase in ["not checked", "not claimed", "not verified"])
            assert negated, f"unsafe language or secret in {relative}: {match.group(0)[:48]!r}"


def verify_wake_ready_operator_brief() -> None:
    """Require the latest machine-readable wake brief to stay proof-grounded and closed-gate."""
    briefs = sorted((ROOT / "docs/launch").glob(WAKE_READY_OPERATOR_BRIEF_GLOB))
    assert briefs, f"missing wake-ready operator brief matching docs/launch/{WAKE_READY_OPERATOR_BRIEF_GLOB}"
    latest_brief = briefs[-1]
    brief = load_json(latest_brief)
    relative = latest_brief.relative_to(ROOT)

    assert brief.get("artifact") == "bass_oracle_wake_ready_operator_brief", f"{relative} artifact id drifted"
    assert brief.get("status") == "local_draft_for_morning_handoff", f"{relative} must remain a local draft"
    assert "no stream" in brief.get("increment_scope", "").lower(), f"{relative} scope must keep stream startup closed"

    crate = brief.get("crate_summary", {})
    assert crate.get("entity") == "Bass Oracle 111", f"{relative} crate entity drifted"
    assert_count("wake-ready brief ready_tracks", int(crate.get("ready_tracks", -1)))
    assert int(crate.get("target_tracks", -1)) == EXPECTED_TARGET_TRACKS, f"{relative} target track count drifted"
    assert crate.get("total_duration_hms") == "2:17:45", f"{relative} total duration drifted"
    assert_count("wake-ready brief playlist_entries", int(crate.get("playlist_entries", -1)))
    assert_count("wake-ready brief listening_review_rows", int(crate.get("listening_review_rows", -1)))
    assert crate.get("default_listener_status") == "pending_human_listen", f"{relative} listener status should stay pending"

    stream = brief.get("stream_status_snapshot", {})
    assert stream.get("local_process_census_only") is True, f"{relative} stream status must be local-process-only"
    assert stream.get("rtmp_target_redaction") == "[REDACTED]", f"{relative} must not contain raw RTMP targets"
    assert stream.get("external_kick_twitch_liveness") == "not_checked_not_verified_not_claimed", (
        f"{relative} must not claim external Kick/Twitch liveness"
    )
    assert stream.get("duplicate_livestream_pusher_startup") == "closed_not_started", (
        f"{relative} must keep duplicate pusher startup closed"
    )

    proof_paths = brief.get("proof_paths", [])
    for required_path in [
        "docs/launch/bass_oracle_launch_manifest.json",
        "docs/review_manifest.json",
        "docs/launch/bass_oracle_034_ready_playlist.m3u",
        "docs/launch/bass_oracle_034_listening_review.csv",
        "docs/launch/BASS_ORACLE_LISTENER_DECISION_MATRIX_20260509-0900.md",
        "docs/reports/BASS_ORACLE_NIGHTSHIFT_REPORT_INDEX_20260509-111637.md",
        "docs/launch/BASS_ORACLE_MORNING_REVEAL_SAFETY_CARD_20260509-1201.md",
        "docs/launch/BASS_ORACLE_WAKE_OPERATOR_DECISION_QUEUE_20260509-1246.md",
        "docs/launch/BASS_ORACLE_STREAM_OPERATOR_SNAPSHOT_20260509-131646.md",
        "docs/reports/BASS_ORACLE_PRE_WAKE_HANDOFF_DELTA_20260509-1332.md",
    ]:
        assert required_path in proof_paths, f"{relative} missing proof path: {required_path}"
        assert (ROOT / required_path).exists(), f"wake-ready brief proof path does not exist: {required_path}"

    decisions = brief.get("morning_operator_decisions", [])
    assert len(decisions) >= 4, f"{relative} should keep at least four morning operator decisions"
    for decision in decisions:
        assert "human" in decision.get("gate", "").lower() or "no_" in decision.get("gate", "").lower() or "planning_only" in decision.get("gate", "").lower(), (
            f"{relative} decision {decision.get('id', '<missing id>')} must keep a closed/human gate"
        )

    closed_gates = brief.get("closed_gates", {})
    for gate, value in closed_gates.items():
        assert value is False, f"{relative} closed gate {gate} must remain false"
    for required_gate in [
        "public_posting",
        "outreach_dm_email_forms",
        "payment_links_or_revenue_claims",
        "hf_or_private_dataset_upload",
        "public_release",
        "gpu_modal_runpod_or_training_jobs",
        "cron_create_update_remove",
        "stream_pusher_start_or_restart",
        "restreamer_or_provider_mutation",
        "secrets_printed",
    ]:
        assert required_gate in closed_gates, f"{relative} missing closed gate: {required_gate}"

    text = latest_brief.read_text(encoding="utf-8")
    for pattern in UNSAFE_OVERCLAIM_PATTERNS + SECRET_PATTERNS:
        match = pattern.search(text)
        if match:
            lowered = text.lower()
            context = lowered[max(0, match.start() - 80): match.end() + 80]
            negated = any(phrase in context for phrase in ["not_checked", "not verified", "not claimed"])
            assert negated, f"unsafe language or secret in {relative}: {match.group(0)[:48]!r}"


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
    verify_nightshift_report_index()
    verify_morning_reveal_safety_card()
    verify_wake_operator_decision_queue()
    verify_wake_ready_operator_brief()
    verify_operator_handoff_documents()
    verify_no_secrets_in_operator_docs()
    print("Bass Oracle launch verifier passed: counts, paths, handoffs, nightshift reports, morning reveal safety card, wake operator queue, wake-ready operator brief, closed gates, and redactions are consistent.")


if __name__ == "__main__":
    main()
