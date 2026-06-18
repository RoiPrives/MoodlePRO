---
name: chrome-builtin-ai-hebrew-limits
description: Planning insight — Chrome built-in AI (Gemini Nano) has strong English but weak/uncertain Hebrew; affects any bilingual on-device AI plan
metadata:
  type: project
---

Planning constraint for any project relying on Chrome's built-in on-device AI (Gemini Nano: Prompt/LanguageModel API, Summarizer, Writer/Rewriter, Translator, Language Detector APIs):

- These APIs are **English-first**. Summarizer/Prompt API language support beyond English has been limited/experimental. **Hebrew output quality should be assumed weak/unverified until tested on-device.**
- Translator API supports a set of language pairs that has grown over time, but Hebrew pairs have historically been limited — verify availability at build time.
- There is **no built-in audio speech-to-text API** for arbitrary media; Web Speech API targets live mic input with variable quality. Transcribing lecture audio (especially Hebrew) realistically needs Whisper (local WASM or server) or a cloud ASR service.

**Why:** Recorded as a domain insight because it repeatedly determines architecture: on-device (free, private) vs cloud (better Hebrew, costs money, privacy/ToS concerns).

**How to apply:** Whenever a plan assumes Gemini Nano "just works" for Hebrew, flag it as an unverified risk and propose a cloud fallback path. Always recommend an early spike to test Hebrew quality before committing the architecture.
