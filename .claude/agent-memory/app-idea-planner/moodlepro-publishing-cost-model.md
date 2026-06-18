---
name: moodlepro-publishing-cost-model
description: MoodlePRO will be published on the Chrome Web Store — recommend BYOK over embedded keys/backend; download feature is top legal/review risk
metadata:
  type: project
---

MoodlePRO is intended for PUBLIC release on the Chrome Web Store (not personal-only). This changes the cost and liability model fundamentally.

**Why:** A published cloud-AI extension cannot embed the developer's own API key (it gets extracted from the bundle → developer pays for all users / key gets revoked). And the developer becomes a data processor shipping many users' authenticated university content to third-party APIs.

**How to apply (recommendations made 2026-06-18):**
- Recommend **BYOK (Bring-Your-Own-Key)** for v1: each user pastes their own Groq/OpenAI key into the options page (stored in `chrome.storage.local`). Solves cost-scaling AND shifts the "send content to a third party" decision to the user. Mitigate onboarding friction with a short setup guide.
- A developer-run backend proxy + freemium is the alternative but is heavy for a solo student (server, Stripe, quotas, abuse control, higher legal exposure) — defer until product is validated.
- Chrome Web Store REQUIRES a privacy policy when handling keys/content (host on GitHub Pages). Justify permissions narrowly (no `<all_urls>`).
- The **video downloader is the highest store-review + copyright risk** (Google removes extensions facilitating unauthorized access to copyrighted content). **DECISION (user, 2026-06-18): KEEP the download feature, gated behind a toggle + copyright disclaimer** (off by default; user must accept disclaimer to enable). This is fine for the hackathon; for an eventual PUBLIC Web Store listing, still consider omitting it from the public build to reduce review risk.
- A shared cross-user transcript cache (one user transcribes, others reuse) is elegant but needs a backend AND raises content-redistribution/copyright issues — defer past v1.

Related: [[project-moodlepro]], [[chrome-builtin-ai-hebrew-limits]].
