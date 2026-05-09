#!/usr/bin/env python3
import json, hashlib, re, sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
docs=root/'docs'
manifest=json.loads((docs/'review_manifest.json').read_text())
assert manifest['status']=='review_only_generation_stopped'
tracks=manifest['tracks']
assert len(tracks)==34, len(tracks)
assert manifest['last_complete_track']==34
html=(docs/'index.html').read_text()
for needle in [
    'Bass Oracle 111',
    'review_manifest.json',
    'generation stopped',
    'No stream, no generator, no payment flow',
    'audio/',
    'Operator handoff',
    'reports/BASS_ORACLE_MORNING_HANDOFF_20260509-091556.md',
    'reports/BASS_ORACLE_NIGHTSHIFT_REPORT_INDEX_20260509-111637.md',
    'reports/BASS_ORACLE_NIGHTSHIFT_REVIEW_20260509-110126.md',
    'launch/BASS_ORACLE_MORNING_REVEAL_SAFETY_CARD_20260509-1201.md',
    'launch/BASS_ORACLE_LISTENER_DECISION_MATRIX_20260509-0900.md',
    'External Kick/Twitch status is not claimed',
    'no payment, outreach, upload, GPU, training, or public-release action is approved here',
]:
    assert needle in html, needle
for handoff_path in [
    docs/'reports/BASS_ORACLE_MORNING_HANDOFF_20260509-091556.md',
    docs/'reports/BASS_ORACLE_NIGHTSHIFT_REPORT_INDEX_20260509-111637.md',
    docs/'reports/BASS_ORACLE_NIGHTSHIFT_REVIEW_20260509-110126.md',
    docs/'launch/BASS_ORACLE_MORNING_REVEAL_SAFETY_CARD_20260509-1201.md',
    docs/'launch/BASS_ORACLE_LISTENER_DECISION_MATRIX_20260509-0900.md',
]:
    assert handoff_path.exists(), handoff_path
for t in tracks:
    p=docs/t['audio']
    assert p.exists(), p
    assert p.stat().st_size == t['size_bytes'], (p, p.stat().st_size, t['size_bytes'])
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    assert h == t['sha256'], (p, h, t['sha256'])
# no archive over GitHub single-file limit
for p in docs.rglob('*'):
    if p.is_file():
        assert p.stat().st_size < 100_000_000, f'GitHub hard-limit risk: {p}'
# simple secret/action language guard
text='\n'.join(p.read_text(errors='ignore') for p in [docs/'index.html', docs/'review_manifest.json', root/'README.md'])
bad_phrases = ['payment link is live','training started','gpu job started','stream is live','api_key']
bad_phrases.append('BEGIN ' + 'PRIVATE KEY')
for bad in bad_phrases:
    assert bad.lower() not in text.lower(), bad
print('verify_site ok: 34 tracks, checksums, page needles, file-size guard')
