import { COLORS, addHoverEffect } from "./theme.js";

// Used by the feedback button and the lecture-quota review prompt (quota-prompt.js).
export const REVIEW_URL =
  "https://hub02.com/hubs/03bd43e5-ca7c-4287-beb1-738104497ca5/tools/6413fd4c-b224-4117-8871-7b676c9d22df";

const INITIAL_LABEL = 'קבלו עוד הרצאות ע"י השארת ביקורת ⭐';

const buttonStyle = [
  "padding:12px 20px", "font-size:14px", "font-weight:700", "border:none", "border-radius:10px",
  "background:linear-gradient(135deg," + COLORS.orangeLight + "," + COLORS.orangeDeep + ")",
  "color:#1a1107", "cursor:pointer", "font-family:sans-serif", "width:100%",
  "box-shadow:0 4px 14px rgba(247,148,30,.5)", "transition:transform .15s ease",
].join(";");

/** A small always-present button that sends testers to leave a review on hub02. First
 *  click opens the review page; the button then turns into a compact referral panel
 *  (your username + who invited you, both optional) with a one-tap claim, so the
 *  review/referral bonus is available right away instead of only once the user is
 *  later blocked by the lecture quota. */
export function injectFeedbackButton(doc, { onClaim, win = doc.defaultView } = {}) {
  if (doc.querySelector('[data-moodlepro-ui="feedback"]')) return;

  const container = doc.createElement("div");
  container.setAttribute("data-moodlepro-ui", "feedback");
  container.style.cssText =
    "position:fixed;bottom:16px;left:16px;z-index:2147483600;font-family:sans-serif;direction:rtl;" +
    "max-width:250px;";
  doc.body.appendChild(container);

  const button = doc.createElement("button");
  button.textContent = INITIAL_LABEL;
  button.style.cssText = buttonStyle;
  button.addEventListener("mouseenter", () => { button.style.transform = "translateY(-2px) scale(1.03)"; });
  button.addEventListener("mouseleave", () => { button.style.transform = "none"; });

  const showReferralPanel = () => {
    container.textContent = "";

    const panel = doc.createElement("div");
    panel.style.cssText =
      "background:#fff;color:#111;border-radius:10px;border:1px solid " + COLORS.border +
      ";padding:12px;box-shadow:0 4px 14px rgba(0,0,0,.3);";

    const inputStyle =
      "display:block;width:100%;margin:4px 0;padding:7px;border:1px solid #ccc;border-radius:5px;" +
      "font-size:12.5px;box-sizing:border-box;";

    const usernameInput = doc.createElement("input");
    usernameInput.type = "text";
    usernameInput.placeholder = "שם המשתמש שלך במודל (אופציונלי)";
    usernameInput.style.cssText = inputStyle;
    panel.appendChild(usernameInput);

    const referralNote = doc.createElement("div");
    referralNote.textContent = "🤝 הזמנתם חבר/ה? כל אחד מכם מקבל עוד הרצאות נוספות!";
    referralNote.style.cssText =
      "font-size:11.5px;color:" + COLORS.orangeDeep + ";font-weight:600;margin:6px 0 2px;text-align:center;";
    panel.appendChild(referralNote);

    const referredByInput = doc.createElement("input");
    referredByInput.type = "text";
    referredByInput.placeholder = "מי הזמין אתכם? (אופציונלי)";
    referredByInput.style.cssText = inputStyle;
    panel.appendChild(referredByInput);

    const claimBtn = doc.createElement("button");
    claimBtn.textContent = "כבר השארתי ביקורת — קבל קרדיטים 🎁";
    claimBtn.style.cssText = buttonStyle + ";margin-top:6px;font-size:12.5px;padding:9px 14px;";
    addHoverEffect(claimBtn, COLORS.orangeLight, COLORS.orangeDeep);
    panel.appendChild(claimBtn);

    claimBtn.addEventListener("click", async () => {
      claimBtn.disabled = true;
      claimBtn.textContent = "מעדכן…";
      try {
        const result = await onClaim({
          username: usernameInput.value.trim() || null,
          referredBy: referredByInput.value.trim() || null,
        });
        panel.textContent = "";
        const ok = doc.createElement("div");
        ok.textContent =
          referredByInput.value.trim() && result && result.referral_credits > 0
            ? "🎁 קיבלת קרדיטים + בונוס הפניה!"
            : "🎁 קיבלת קרדיטים נוספים!";
        ok.style.cssText = "font-weight:bold;font-size:13px;color:#2e7d32;text-align:center;";
        panel.appendChild(ok);
      } catch {
        claimBtn.disabled = false;
        claimBtn.textContent = "כבר השארתי ביקורת — קבל קרדיטים 🎁";
      }
    });

    container.appendChild(panel);
  };

  button.addEventListener("click", () => {
    if (win && win.open) win.open(REVIEW_URL, "_blank", "noopener,noreferrer");
    if (onClaim) showReferralPanel();
  });

  container.appendChild(button);
}
