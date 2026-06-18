---
name: project-moodlepro
description: MoodlePRO — Chrome extension augmenting BGU Moodle with AI video + content features; goals, constraints, open decisions
metadata:
  type: project
---

**MoodlePRO** is a Chrome extension to augment Ben-Gurion University's Moodle with features Moodle lacks.

Planned feature set (verbatim from user, 2026-06-18):
- Video: EN/HE subtitles, EN/HE transcript, side-panel auto-scrolling transcript, MCQ quiz generator over a chosen timestamp range, video download.
- Non-video: AI summaries (Gemini Nano) of lectures (from transcript)/assignments/documents with casual vs comprehensive modes; per-course filter menu (lectures/assignments/documents, by professor/TA).

**Why:** Personal/academic project to make studying at BGU more efficient.

**Resolved technical facts (2026-06-18 Tier-1 answers):**
- Player = native HTML5 video.js (class `vjs-tech`) with a DIRECT, UNENCRYPTED MP4 `<source>` on CloudFront. No DRM. `oncontextmenu="return false"` is cosmetic only. → subtitle overlay, transcript, sync, and download are all technically trivial.
- A `local/video_directory` Moodle plugin gives each video a stable NUMERIC ID (`thumb.php?id=439866`). Use it as the transcript CACHE KEY (transcribe once per video, reuse forever).
- NO captions exist on BGU lectures → cloud ASR is mandatory (not optional). Recommend Groq `whisper-large-v3` (cheap, fast, strong Hebrew).
- Priority: Hebrew TRANSCRIPTION accuracy > Hebrew summary output. So ASR goes cloud; summary language is secondary (Gemini Nano weak-Hebrew only affects the secondary step now).
- User intends to PUBLISH on the Chrome Web Store. See [[moodlepro-publishing-cost-model]] — this is now the architecture-deciding question (can't embed your own API key; privacy policy required; downloader is the highest store-review/copyright risk).

**Recommended v1 architecture:** BYOK (user pastes own Groq key) + content-script DOM scraping (not Moodle Web Services) + ffmpeg.wasm audio extraction in an offscreen doc before ASR + transcript cache by video ID.

**Still-open technical pivots:** (4) DOM scraping fragility vs Moodle WS API (chose DOM for v1); (5) ToS/copyright risk of download + scraping for a PUBLISHED extension. See [[chrome-builtin-ai-hebrew-limits]].
