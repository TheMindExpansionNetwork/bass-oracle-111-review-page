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
for needle in ['Bass Oracle 111','review_manifest.json','generation stopped','No stream, no generator, no payment flow','audio/']:
    assert needle in html, needle
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
for bad in ['payment link is live','training started','gpu job started','stream is live','api_key','BEGIN PRIVATE KEY']:
    assert bad.lower() not in text.lower(), bad
print('verify_site ok: 34 tracks, checksums, page needles, file-size guard')
