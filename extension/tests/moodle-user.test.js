import { beforeEach, describe, expect, it } from "vitest";
import { getMoodleUserId } from "../src/content/moodle-user.js";

beforeEach(() => {
  document.body.innerHTML = "";
});

describe("getMoodleUserId", () => {
  it("reads the numeric user id from a profile link", () => {
    document.body.innerHTML = `
      <a href="https://moodle.bgu.ac.il/moodle/user/profile.php?id=12345">My profile</a>`;
    expect(getMoodleUserId(document)).toBe("moodle:12345");
  });

  it("falls back to the user-menu name when no profile link exists", () => {
    document.body.innerHTML = `
      <div data-region="user-menu"><span class="usertext">דנה כהן</span></div>`;
    expect(getMoodleUserId(document)).toBe("name:דנה כהן");
  });

  it("returns null when the user can't be identified", () => {
    document.body.innerHTML = `<div>no user info</div>`;
    expect(getMoodleUserId(document)).toBeNull();
  });
});
