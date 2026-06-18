---
name: moodlepro-hackathon-base44
description: MoodlePRO is a HACKATHON project with Base44 credits — re-tuned priorities; Base44 proxies LLM steps but NOT ASR; demo-first scoping
metadata:
  type: project
---

MoodlePRO is being built for a **HACKATHON** (confirmed 2026-06-18), not a polished Chrome Web Store launch. The team has **Base44 credits**.

**Why this changes everything:** Judges reward a working, impressive end-to-end demo built fast. Web Store publishing, long-term cost-scaling, and BYOK onboarding friction matter far less now. Optimize for demo-day wow + reliability, not production hardening.

**Base44 facts (Wix-acquired no-code/AI full-stack app builder — hosted DB, auth, backend functions, built-in LLM integrations):**
- Base44's built-in AI is **LLM/text only** (good for the summary + MCQ quiz-generation steps). A Base44-hosted backend funded by credits can proxy those LLM calls, **removing BYOK friction for the demo**.
- **Base44 does NOT do ASR / speech-to-text (Whisper).** Audio transcription is a different capability. The lecture transcript is the foundation of the whole product, so **ASR still needs Groq/OpenAI Whisper regardless of Base44 credits.** Do not assume Base44 covers transcription.
- Base44 builds web apps, not Chrome extensions — use a Base44 app as an HTTP backend the extension calls; don't try to rebuild the extension in Base44.

**How to apply (re-tuned recommendation):**
- For the hackathon, prefer **Base44 backend proxy for LLM steps** over BYOK (less onboarding friction in a live demo). For ASR, hardcode a Groq Whisper key in the backend (it's behind Base44, not shipped in the extension bundle) OR pre-transcribe the demo lecture.
- De-risk the demo: pre-transcribe the lecture shown on stage and cache it by video ID so the live demo never waits on/fails ASR. Keep a live transcription path to show it's real, but have the cached fallback.
- Single most impressive flow to nail: open BGU lecture video -> side-panel auto-scrolling HE/EN transcript -> select timestamp range -> generate MCQ quiz from that range. That's the end-to-end wow.

Supersedes the BYOK-first recommendation in [[moodlepro-publishing-cost-model]] FOR THE HACKATHON timeframe (BYOK/publishing still correct for an eventual public launch). Related: [[project-moodlepro]], [[chrome-builtin-ai-hebrew-limits]].
</content>
