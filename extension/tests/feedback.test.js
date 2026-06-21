import { beforeEach, describe, expect, it, vi } from "vitest";
import { injectFeedbackButton, REVIEW_URL } from "../src/content/feedback.js";

beforeEach(() => {
  document.body.innerHTML = "";
});

describe("injectFeedbackButton", () => {
  it("adds a review button to the page", () => {
    injectFeedbackButton(document);
    expect(document.querySelector('[data-moodlepro-ui="feedback"]')).not.toBeNull();
  });

  it("does not add a second button if one already exists", () => {
    injectFeedbackButton(document);
    injectFeedbackButton(document);
    expect(document.querySelectorAll('[data-moodlepro-ui="feedback"]')).toHaveLength(1);
  });

  it("opens the hub02 review link on click", () => {
    const win = { open: vi.fn() };
    injectFeedbackButton(document, { win });

    document.querySelector('[data-moodlepro-ui="feedback"] button').click();

    expect(win.open).toHaveBeenCalledWith(REVIEW_URL, "_blank", "noopener,noreferrer");
  });

  it("shows a referral panel (username + who invited you) after the first click", () => {
    const win = { open: vi.fn() };
    const onClaim = vi.fn();
    injectFeedbackButton(document, { win, onClaim });

    const container = document.querySelector('[data-moodlepro-ui="feedback"]');
    container.querySelector("button").click();

    expect(container.querySelectorAll("input")).toHaveLength(2);
    expect(container.querySelector("button").textContent).toContain("כבר השארתי ביקורת");
  });

  it("claims with the typed username/referredBy and shows the referral message", async () => {
    const onClaim = vi.fn().mockResolvedValue({ referral_credits: 3 });
    injectFeedbackButton(document, { win: { open: vi.fn() }, onClaim });

    const container = document.querySelector('[data-moodlepro-ui="feedback"]');
    container.querySelector("button").click(); // opens referral panel

    const [usernameInput, referredByInput] = container.querySelectorAll("input");
    usernameInput.value = "newbie";
    referredByInput.value = "leonovt";
    container.querySelector("button").click(); // claims

    await Promise.resolve();
    await Promise.resolve();

    expect(onClaim).toHaveBeenCalledWith({ username: "newbie", referredBy: "leonovt" });
    expect(container.textContent).toContain("בונוס הפניה");
  });

  it("re-enables the claim button so the user can retry if claiming fails", async () => {
    const onClaim = vi.fn().mockRejectedValue(new Error("network"));
    injectFeedbackButton(document, { win: { open: vi.fn() }, onClaim });

    const container = document.querySelector('[data-moodlepro-ui="feedback"]');
    container.querySelector("button").click(); // opens referral panel
    const claimBtn = container.querySelector("button");
    claimBtn.click();
    await Promise.resolve();
    await Promise.resolve();

    expect(claimBtn.disabled).toBe(false);
    expect(claimBtn.textContent).toContain("כבר השארתי ביקורת");
  });
});
