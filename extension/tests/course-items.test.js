import { beforeEach, describe, expect, it, vi } from "vitest";
import { injectCourseItemButtons } from "../src/content/course-items.js";

function setupDom() {
  document.body.innerHTML = `
    <ul class="section m-0 p-0 img-text d-block" data-for="cmlist">
      <li class="activity activity-wrapper resource modtype_resource   " id="module-100" data-for="cmitem" data-id="100">
        <div class="activity-item focus-control" data-region="activity-card">
          <div class="activity-name-area activity-instance d-flex flex-column me-2">
            <div class="activitytitle modtype_resource position-relative align-self-start">
              <div class="activityname">
                <a href="https://moodle.bgu.ac.il/moodle/mod/resource/view.php?id=100" class="aalink stretched-link">
                  <span class="instancename">Syllabus</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      </li>
    </ul>
  `;
}

beforeEach(() => {
  setupDom();
  global.fetch = vi.fn();
});

describe("injectCourseItemButtons", () => {
  it("injects a button into the activity-name-area", () => {
    injectCourseItemButtons(document, "http://localhost:8000");
    const container = document.querySelector('[data-moodlepro-ui]');
    expect(container).not.toBeNull();
    const button = container.querySelector("button");
    expect(button.textContent).toContain("Summary + Quiz");
  });

  it("does not duplicate buttons when called twice", () => {
    injectCourseItemButtons(document, "http://localhost:8000");
    injectCourseItemButtons(document, "http://localhost:8000");
    const containers = document.querySelectorAll('[data-moodlepro-ui]');
    expect(containers).toHaveLength(1);
  });

  it("calls the summary and quiz endpoints on click", async () => {
    global.fetch.mockImplementation((url) => {
      if (typeof url === "string" && url.includes("resource/view.php")) {
        return Promise.resolve({
          url,
          headers: { get: () => "text/html" },
          text: async () => "<html><body>no embedded file here</body></html>",
        });
      }
      if (url.endsWith("/items/summary")) {
        return Promise.resolve({ ok: true, json: async () => ({ summary: "a summary" }) });
      }
      if (url.endsWith("/items/quiz")) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            questions: [
              { question: "Q1?", options: ["a", "b", "c", "d"], correct_index: 1, explanation: "because" },
            ],
          }),
        });
      }
      return Promise.reject(new Error("unexpected url " + url));
    });

    injectCourseItemButtons(document, "http://localhost:8000");
    const button = document.querySelector('[data-moodlepro-ui] button');
    button.click();

    await vi.waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/items/summary",
        expect.objectContaining({ method: "POST" })
      );
    });

    const summaryCall = global.fetch.mock.calls.find(([url]) => url.endsWith("/items/summary"));
    const summaryBody = JSON.parse(summaryCall[1].body);
    expect(summaryBody).toEqual(
      expect.objectContaining({ title: "Syllabus", item_type: "slides", mode: "default" })
    );

    expect(global.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/items/quiz",
      expect.objectContaining({ method: "POST" })
    );

    await vi.waitFor(() => {
      expect(document.querySelector("#moodlepro-modal").textContent).toContain("a summary");
    });
  });

  it("injects a Solve Assignment button and triggers solve endpoint for assignments", async () => {
    // Add assignment item to DOM
    document.body.innerHTML += `
      <li class="activity activity-wrapper assign modtype_assign" id="module-101" data-for="cmitem" data-id="101">
        <div class="activity-item focus-control" data-region="activity-card">
          <div class="activity-name-area activity-instance d-flex flex-column me-2">
            <div class="activitytitle modtype_assign position-relative align-self-start">
              <div class="activityname">
                <a href="https://moodle.bgu.ac.il/moodle/mod/assign/view.php?id=101" class="aalink stretched-link">
                  <span class="instancename">Homework 1</span>
                </a>
              </div>
            </div>
          </div>
        </div>
      </li>
    `;

    global.fetch.mockImplementation((url) => {
      if (typeof url === "string" && url.includes("assign/view.php")) {
        return Promise.resolve({
          url,
          headers: { get: () => "text/html" },
          text: async () => "<html><body>no files</body></html>",
        });
      }
      if (url.endsWith("/items/solve")) {
        // Return a mock PDF blob
        return Promise.resolve({
          ok: true,
          blob: async () => new Blob(["pdf content"], { type: "application/pdf" }),
        });
      }
      return Promise.reject(new Error("unexpected url " + url));
    });

    // Mock URL.createObjectURL and revokeObjectURL
    window.URL.createObjectURL = vi.fn(() => "blob:mock-url");
    window.URL.revokeObjectURL = vi.fn();

    injectCourseItemButtons(document, "http://localhost:8000");
    
    const li = document.querySelector('li[data-id="101"]');
    const solveBtn = Array.from(li.querySelectorAll("button")).find(b => b.textContent.includes("Solve Assignment"));
    expect(solveBtn).toBeDefined();

    solveBtn.click();

    await vi.waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        "http://localhost:8000/items/solve",
        expect.objectContaining({ method: "POST" })
      );
    });

    const solveCall = global.fetch.mock.calls.find(([url]) => url.endsWith("/items/solve"));
    const body = JSON.parse(solveCall[1].body);
    expect(body.title).toBe("Homework 1");
    expect(body.item_type).toBe("assignment");
    expect(body.course_lectures).toBeDefined();
  });
});
