# Yui Zalo Bot - Usage & Features

## Overview
Yui is an unofficial Zalo bot with:
- chat + group context memory
- internet search command
- voice reply / voice acting
- image + voice understanding
- RAG document Q&A
- anti-spam protections
- auto friend accept for group members

## Main Commands

### Group Commands (tag bot)
- `@yui [question]` - ask normal question
- `@Commit [question]` - alias trigger (configured by `BOT_MENTION_ALIASES`)
- `@yui /search [query]` - force internet search
- `@yui /search on|off` - toggle search for this thread
- `@yui /vc [text]` - one-shot voice response
- `@yui /va [text]` - voice acting only (no Gemini call)
- `@yui /voice on|off` - enable/disable voice
- `@yui /voice only on|off` - auto voice-only mode
- `@yui /voice list` - list available voices
- `@yui /voice [number]` - select a voice
- `@yui /voice reload` - reload custom + preset voices
- `@yui /rag ...` - document RAG commands

### DM Commands
- `/search [query]`
- `/search on|off`
- `/vc [text]`
- `/va [text]`
- `/voice on|off|only on|only off|list|reload|[number]`
- `/rag ...`
- `help` or `?`

## Combined Command Support
- `/search ... /vc`
- `/vc /search ...`

Both are supported in group and DM.

## Voice Pipeline

### TTS Engine Priority
1. VieNeu-TTS
2. Qwen/VieHieu TTS
3. Piper fallback

### Voice send modes (`VOICE_SEND_METHOD`)
- `voice_url_first`
- `attachment_first`
- `both`
- `zalo_native_like`
- `triple_redundant`

### Voice-only behavior
- `VOICE_ONLY_MODE=true` skips sending text when voice mode is active.

### Voice acting
- `/va [text]` sends text directly to TTS (no Gemini generation).

## TTS Abbreviation Reading
Bot normalizes common VN chat abbreviations and supports custom nickname pronunciation:
- `Tcon` -> `tê con`
- `HLECon` -> `hắc lờ e con`

This is handled before TTS synthesis to improve natural speech.

## Anti-Stretch Protection (VieNeu)
To prevent long broken audio (e.g. 40s for short text):
- chunk-level duration anomaly detection
- retry with softened punctuation
- fallback to Piper for abnormal chunk
- hard trim as last resort

Config:
- `VIENEU_MAX_STRETCH_RATIO` (default `2.6`)

## VieNeu Model Switching (.env)
- `VIENEU_MODE`: `turbo` | `standard` | `remote`
- `VIENEU_MODEL`: model id you want to force
- `VIENEU_API_BASE`: required when `VIENEU_MODE=remote`

Official VieNeu model families:
- `pnnbao-ump/VieNeu-TTS-v2-Turbo`
- `pnnbao-ump/VieNeu-TTS-v2`
- `pnnbao-ump/VieNeu-TTS-0.3B`
- `pnnbao-ump/VieNeu-TTS`

## GPU Behavior
Current setup pins container to GTX 1060 (host GPU index 1):
- `NVIDIA_VISIBLE_DEVICES=1`
- compose `gpus.device_ids: ["1"]`
- `CUDA_VISIBLE_DEVICES=0` (inside container logical index)

Startup and runtime logs include visible GPU and selected CUDA device.

## Internet Search
- `ENABLE_SEARCH` controls default behavior
- `/search [query]` always forces internet search path
- uses `GEMINI_SEARCH_MODELS` with fallback

## RAG Document Features
- upload files (pdf/docx/xlsx/pptx/txt/csv/json/js/py/html/md...)
- chunk + embed into sqlite store
- ask with `/rag [question]`
- file selection with `/rag dung ...`
- cleanup with `/rag xoa ...` and `/rag clear`

## Useful Environment Variables
- `VOICE_ENABLED`
- `VOICE_ONLY_MODE`
- `VOICE_SEND_METHOD`
- `VOICE_NATIVE_EMULATION`
- `VOICE_NATIVE_TTL_MS`
- `VOICE_FILE_TTL_HOURS`
- `VIEHIEU_TTS_MAX_NEW_TOKENS`
- `VIEHIEU_GPU_KEEP_ALIVE_MINUTES`
- `VIENEU_GPU_ENABLED`
- `VIENEU_MODE`
- `VIENEU_MODEL`
- `VIENEU_API_BASE`
- `VIENEU_MAX_STRETCH_RATIO`
- `NVIDIA_VISIBLE_DEVICES`
- `CUDA_VISIBLE_DEVICES`
- `BOT_MENTION_ALIASES`
- `BLOCKLIST_USERS` (name/uid based hard ignore)
- `GROUP_PREFIX`

### BLOCKLIST_USERS format
- `name_only|name:uid|:uid_only`
- Example: `BLOCKLIST_USERS=Spammer|Phong Lữ:6023260713651011265|:1234567890`
- If matched, bot ignores messages and does not reply.

## Run / Deploy
- Build + start:
  - `docker compose up -d --build`
- Validate compose:
  - `docker compose config`

## Notes
- This bot uses unofficial APIs.
- Voice transcript/sync behavior can vary by Zalo client versions.
