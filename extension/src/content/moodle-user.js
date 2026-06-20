/** Best-effort read of the logged-in Moodle user from the page DOM, used as the quota key.
 *  Content scripts can't see the page's JS globals (isolated world), so we read the DOM:
 *  the profile link carries the stable numeric user id. Returns null if not found, in
 *  which case the request is sent without a user_id and the server doesn't gate it. */
export function getMoodleUserId(doc) {
  const profileLink = doc.querySelector('a[href*="/user/profile.php?id="]');
  if (profileLink) {
    const match = (profileLink.getAttribute("href") || "").match(/[?&]id=(\d+)/);
    if (match) return `moodle:${match[1]}`;
  }

  const nameEl = doc.querySelector(
    '[data-region="user-menu"] .usertext, .userbutton .usertext, .usermenu .usertext'
  );
  if (nameEl && nameEl.textContent.trim()) {
    return `name:${nameEl.textContent.trim()}`;
  }

  return null;
}
