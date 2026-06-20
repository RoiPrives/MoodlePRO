import { createResultModal } from "./result-modal.js";
import { arrayBufferToBase64, resolveResourceFile } from "./resource-file.js";
import { scrapeCourseItems } from "./course-scraper.js";
import { toApiItems, isAcademicItem } from "./course-toolbar.js";

/** Slides/resource and assignment items don't carry real content in their course-page text — fetch the actual file. */
async function resolveFileFields(item) {
  if ((item.type !== "slides" && item.type !== "assignment") || !item.href) return {};
  const file = await resolveResourceFile(item.href);
  if (!file) return {};
  return { file_base64: arrayBufferToBase64(file.buffer), mime_type: file.mimeType };
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`request to ${url} failed: ${res.status}`);
  }
  return res.json();
}

function findLiForItem(doc, id) {
  return doc.querySelector(`li[data-for="cmitem"][data-id="${id}"]`);
}

export function injectCourseItemButtons(doc, serverBaseUrl) {
  const httpBase = serverBaseUrl.replace(/\/$/, "");
  const items = scrapeCourseItems(doc);

  items.forEach((item) => {
    const li = findLiForItem(doc, item.id);
    if (!li) return;

    const nameArea = li.querySelector(".activity-name-area");
    if (!nameArea) return;
    if (nameArea.querySelector("[data-moodlepro-ui]")) return;

    const container = doc.createElement("div");
    container.setAttribute("data-moodlepro-ui", "1");
    container.style.cssText = "display:flex; gap:8px; margin-top:6px; flex-wrap:wrap;";

    const summaryQuizBtn = doc.createElement("button");
    summaryQuizBtn.textContent = "📝 Summary + Quiz";
    summaryQuizBtn.style.cssText = [
      "padding:4px 10px", "font-size:12px",
      "border:1px solid #e07a00", "border-radius:4px", "background:#ff9800", "color:#fff",
      "font-weight:600", "cursor:pointer",
    ].join(";");

    summaryQuizBtn.addEventListener("click", async () => {
      const modal = createResultModal(doc);
      modal.showLoading("Reading item content and generating summary + quiz... This may take a moment.");
      try {
        const fileFields = await resolveFileFields(item);
        const [summaryRes, quizRes] = await Promise.all([
          postJson(`${httpBase}/items/summary`, {
            title: item.title,
            text: item.text,
            item_type: item.type,
            mode: "default",
            ...fileFields,
          }),
          postJson(`${httpBase}/items/quiz`, {
            title: item.title,
            text: item.text,
            item_type: item.type,
            num_questions: 5,
            ...fileFields,
          }),
        ]);
        modal.showSummaryAndQuiz(summaryRes.summary, quizRes.questions);
      } catch (err) {
        modal.showError(err.message);
      }
    });
    container.appendChild(summaryQuizBtn);

    if (item.type === "assignment") {
      const solveBtn = doc.createElement("button");
      solveBtn.textContent = "🔍 Solve Assignment";
      solveBtn.style.cssText = [
        "padding:4px 10px", "font-size:12px",
        "border:1px solid #28a745", "border-radius:4px", "background:#28a745", "color:#fff",
        "font-weight:600", "cursor:pointer",
      ].join(";");

      solveBtn.addEventListener("click", async () => {
        const modal = createResultModal(doc);
        modal.showLoading("Reading assignment file, researching online, and generating PDF solutions guide...");
        try {
          const fileFields = await resolveFileFields(item);
          const allItems = scrapeCourseItems(doc);
          const lectures = toApiItems(allItems).filter(isAcademicItem);

          const res = await fetch(`${httpBase}/items/solve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: item.title,
              text: item.text,
              item_type: item.type,
              course_lectures: lectures,
              ...fileFields,
            }),
          });
          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.detail || `request failed: ${res.status}`);
          }
          const blob = await res.blob();
          const url = window.URL.createObjectURL(blob);
          const a = doc.createElement("a");
          a.href = url;
          a.download = `solutions_${item.title.replace(/[^\w֐-׿ ]/g, "").trim().replace(/\s+/g, "_")}.pdf`;
          doc.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
          modal.showSummary("Solutions PDF generated and downloaded successfully!");
        } catch (err) {
          modal.showError(err.message);
        }
      });
      container.appendChild(solveBtn);
    }

    nameArea.appendChild(container);
  });
}
