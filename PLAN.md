# MoodlePRO — in-flight work plan

Working notes for picking this back up in a fresh session. Run `git status --short` first —
everything below is currently **uncommitted**.

## ✅ Done (implemented + tests passing)

1. **Download buttons** — summary modal (`extension/src/content/result-modal.js`) and live
   transcript sidebar (`extension/src/content/sidebar.js`) each got a client-side "Download"
   button (Blob + `<a download>`, no server round-trip). Tests: `result-modal.test.js`,
   new `sidebar.test.js`. `npm test` in `extension/` → 86/86 passing.

2. **Referral bonus system** (server):
   - `server/app/core/config.py` — `referral_bonus_lectures: int = 3`.
   - `server/app/db/models.py` — `UserReward` gained `username`, `referred_by`,
     `referral_credits` columns.
   - `server/app/schemas.py` — `UsageResponse.referral_credits`, new `ReviewClaimRequest`
     (`username`, `referred_by`).
   - `server/app/services/usage.py` — `grant_review_bonus()` now takes `username`/
     `referred_by`; on a valid (non-self) referral, both accounts get
     `+referral_bonus_lectures` once each. `get_usage()` returns `referral_credits`.
   - `server/app/api/users.py` — `POST /users/{user_id}/review` accepts the new body.
   - `server/app/db/session.py` — Postgres `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` nudges
     for the 3 new `user_rewards` columns + an index on `username`.
   - `server/tests/test_usage.py` — added referral tests (credits both sides, claimed once,
     self-referral ignored). `pytest` → 8/8 in that file, 58/58 server-wide.

3. **Referral UI** (extension):
   - `extension/src/shared/api-client.js` — `claimReview(userId, { username, referredBy })`
     now POSTs a JSON body.
   - `extension/src/content/quota-prompt.js` — redesigned: bigger review CTA, a referral
     callout line, two optional inputs ("your Moodle username" / "who invited you"), success
     message distinguishes plain review bonus vs. review+referral bonus.
   - `extension/src/content/inject.js` — `onReviewed` now forwards `{username, referredBy}`
     to `api.claimReview` and returns the usage payload back to the prompt.
   - All wired end-to-end; `inject.test.js`'s quota-prompt test still passes unmodified.

4. **Feedback button copy** — `extension/src/content/feedback.js` button text is now the
   exact verbatim copy requested: `קבלו עוד הרצאות ע"י השארת ביקורת ⭐`.

5. **Unlimited-quota allowlist** — two mechanisms, both feeding the same
   `_is_unlimited()` check in `server/app/services/usage.py`:
   - **Id-based (current, no prompt at all)**: `settings.unlimited_user_ids` in
     `server/app/core/config.py` hardcodes the stable `moodle:<id>` key the extension
     already sends with every request — `moodle:439866` (leonovt), `moodle:428572`
     (prives). Matched directly in `check_and_reserve()`/`get_usage()`, zero user
     interaction needed.
   - **Username-based (honor system, for anyone else added later)**:
     `settings.unlimited_usernames` (`{"leonovt", "prives"}`, case-insensitive) matched
     against `UserReward.username`, which gets set as a side effect of `POST
     /users/{user_id}/review`'s optional `username` field (the existing referral flow —
     there's no separate username-registration endpoint; that one-time
     `username-setup.js` prompt was built and then removed since the id-based path made
     it redundant for the two known people).
   - `schemas.UsageResponse.unlimited`; extension `usage-badge.js` renders `🎓 ∞` when
     unlimited.
   - Tests: `test_usage.py` (62/62 server-wide), extension 86/86.

6. **Real review URL** — the hub02 review link (`.../tools/6413fd4c-...`) replaced the
   temporary placeholder in `feedback.js` (also used by `quota-prompt.js`); `feedback.test.js`
   now imports `REVIEW_URL` instead of hardcoding it, so it can't drift again.

7. **Landing page review button** — `index.html` hero now has a secondary "⭐ השאירו ביקורת"
   button (`.cta-secondary` style) next to the install CTA, linking to the same hub02 URL.

8. **Assignment-solving (`פתרון`) grounded with web search** —
   `server/app/services/summarizer.py`'s `GeminiSummarizer` now attaches Gemini's built-in
   `google_search` tool when `mode == "solve"`, so it can pull live web context (formulas,
   definitions, worked examples) instead of relying only on the provided material. Still
   uses `STRONG_MODEL` (`gemini-3.1-pro`) for solve mode. Test:
   `test_gemini_summarizer_grounds_solve_mode_with_google_search` in `test_content.py`.

## 🚧 Not started — landing page review/referral section

User asked to make the review CTA "clearer/bigger" on the landing page; a button now exists
(see #7) but there's no dedicated section explaining the incentive yet. Still needed:
- A section near the hero or reviews mentioning both bonuses explicitly (leave a review →
  +5 lectures; name who invited you → +3 for both), mirroring the extension's copy.

## 📋 Backlog ideas (discussed, not committed to — revisit only if asked)

- Per-chapter summaries (build on `chapters.js`).
- Click a transcript line in the sidebar to seek the video (reverse of current sync).
- Spaced-repetition re-asking of previously-missed quiz questions (`gradeAdvice`'s `missed`).
- Multi-lecture / whole-course summary digest.
- Resume-playback-position memory per lecture.
- Cross-video transcript search (previously discussed as the top pick, not started).

## Useful context for whoever resumes this

- No alembic — schema changes ship via `Base.metadata.create_all` + manual
  `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` nudges in `server/app/db/session.py::init_db`
  (Postgres only; SQLite test DBs start fresh each run).
- Whole review/referral/unlimited system is **honor system by design** — no verification
  that a typed username is real. Matches the existing review-bonus trust model.
- Run extension tests: `cd extension && npm test`. Run server tests:
  `cd server && python -m pytest -q`.
