import { REVIEW_URL } from "./feedback.js";

/** Shown when a user hits their lecture quota. Offers the honor-system review path:
 *  "Leave a review" opens hub02; "I left a review" calls onReviewed() to claim the bonus
 *  and retry. */
export function showQuotaPrompt(doc, { onReviewed, win = doc.defaultView } = {}) {
  const existing = doc.getElementById("moodlepro-quota-backdrop");
  if (existing) existing.remove();

  const backdrop = doc.createElement("div");
  backdrop.id = "moodlepro-quota-backdrop";
  backdrop.style.cssText = [
    "position:fixed", "inset:0", "background:rgba(0,0,0,.5)", "z-index:2147483600",
    "display:flex", "align-items:center", "justify-content:center",
  ].join(";");

  const box = doc.createElement("div");
  box.style.cssText = [
    "background:#fff", "color:#111", "max-width:380px", "width:90%", "border-radius:8px",
    "padding:22px", "font-family:sans-serif", "direction:rtl", "text-align:center",
    "box-shadow:0 4px 24px rgba(0,0,0,.4)",
  ].join(";");

  const title = doc.createElement("div");
  title.textContent = "הגעת למכסת ההרצאות החינמית";
  title.style.cssText = "font-weight:bold;font-size:16px;margin-bottom:8px;";
  box.appendChild(title);

  const msg = doc.createElement("div");
  msg.textContent = "השאירו ביקורת וקבלו 5 הרצאות נוספות 🎁";
  msg.style.cssText = "font-size:13px;color:#444;margin-bottom:16px;";
  box.appendChild(msg);

  const close = () => backdrop.remove();

  const reviewBtn = doc.createElement("button");
  reviewBtn.textContent = "⭐ השאר ביקורת";
  reviewBtn.style.cssText = "display:block;width:100%;margin:6px 0;padding:9px;border:none;border-radius:5px;background:#ff9800;color:#fff;font-weight:600;font-size:14px;cursor:pointer;";
  reviewBtn.addEventListener("click", () => {
    if (win && win.open) win.open(REVIEW_URL, "_blank", "noopener,noreferrer");
  });
  box.appendChild(reviewBtn);

  const confirmBtn = doc.createElement("button");
  confirmBtn.textContent = "כבר השארתי ביקורת";
  confirmBtn.style.cssText = "display:block;width:100%;margin:6px 0;padding:9px;border:1px solid #2e7d32;border-radius:5px;background:#fff;color:#2e7d32;font-weight:600;font-size:14px;cursor:pointer;";
  confirmBtn.addEventListener("click", async () => {
    confirmBtn.disabled = true;
    confirmBtn.textContent = "מעדכן…";
    try {
      if (onReviewed) await onReviewed();
      close();
    } catch {
      confirmBtn.disabled = false;
      confirmBtn.textContent = "כבר השארתי ביקורת";
    }
  });
  box.appendChild(confirmBtn);

  const cancelBtn = doc.createElement("button");
  cancelBtn.textContent = "סגור";
  cancelBtn.style.cssText = "display:block;width:100%;margin:6px 0 0;padding:7px;border:none;border-radius:5px;background:transparent;color:#777;font-size:13px;cursor:pointer;";
  cancelBtn.addEventListener("click", close);
  box.appendChild(cancelBtn);

  backdrop.addEventListener("click", (e) => {
    if (e.target === backdrop) close();
  });

  backdrop.appendChild(box);
  doc.body.appendChild(backdrop);
  return { backdrop, close };
}
