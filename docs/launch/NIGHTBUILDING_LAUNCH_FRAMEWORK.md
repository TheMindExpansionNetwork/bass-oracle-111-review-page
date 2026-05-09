# Bass Oracle 111 Nightbuilding Launch Framework

## Current crate
- Ready tracks: 34 / 111
- Total reviewed-playlist duration: 2:17:45
- Public posture: review/playlist-safe; generated/owned audio only.
- Track 035: error/no audio; resume factory from 035 after stream is stable.

## Best framework for tonight
1. **Single source of truth:** `/opt/data/workspace/launch-packs/bass-oracle-nightbuilding-launch-20260509/bass_oracle_launch_manifest.json`
2. **DJ playlist:** use `bass_oracle_034_ready_playlist.m3u` in local players and `bass_oracle_034_ffmpeg_concat.txt` for FFmpeg concat/mix tests.
3. **Live deck:** one Program Deck/Restreamer source fans out to Kick + Twitch; no duplicate direct pushers.
4. **Generation wall:** resume song generation only as queue/background after stream health is proven.
5. **Avatar lane:** use `assets/bass_oracle_111_avatar.png` as the DJ entity; keep Sonic/Jimsky emotes as overlay bursts.
6. **Review gate:** update `bass_oracle_034_listening_review.csv` after listening: approve / reroll / keep-for-background / reject.

## Kick + Twitch rules
- Use one stable local/Restreamer program feed, not multiple FFmpeg pushers.
- Keys stay in protected env only; reports say set/missing, never values.
- Twitch is blocked until a Twitch RTMP/key env is present or Restreamer relay creds are found.

## Resume 111-track factory
- Resume at track 035.
- Sync metadata after every 1-5 tracks.
- Keep HF dataset private until listening/release approval.
