import base64
import io
import re
from fpdf import FPDF
from google.genai import types
from sqlalchemy import select

from app.core.config import settings
from app.db.models import Job, Transcript
from app.services.llm_client import MODEL, get_client


def extract_lecture_numbers(text: str) -> list[int]:
    """Helper to extract lecture numbers from text like 'Lecture 3' or 'הרצאה 4'."""
    text_lower = text.lower()
    pattern = r'(?:lecture|lec|l|הרצאה|הרצאה מספר)\s*#?\s*(\d+)'
    matches = re.findall(pattern, text_lower)
    return [int(m) for m in matches if m.isdigit()]


def reverse_hebrew(text: str) -> str:
    """Helper to reverse Hebrew word order and characters for LTR PDF rendering engines."""
    lines = text.split("\n")
    processed_lines = []
    for line in lines:
        if not line.strip():
            processed_lines.append("")
            continue
        # Check if the line contains Hebrew characters
        if re.search(r"[\u0590-\u05ff]", line):
            words = line.split()
            reversed_words = []
            for word in words:
                if re.search(r"[\u0590-\u05ff]", word):
                    # Keep punctuation relative to the word if needed, but simple reverse works well
                    reversed_words.append(word[::-1])
                else:
                    reversed_words.append(word)
            reversed_words.reverse()
            processed_lines.append(" ".join(reversed_words))
        else:
            processed_lines.append(line)
    return "\n".join(processed_lines)


class AssignmentSolver:
    async def solve(
        self,
        title: str,
        text: str,
        *,
        file_base64: str | None = None,
        mime_type: str | None = None,
        course_lectures: list = None,
        session = None,
    ) -> bytes:
        parts = []
        if file_base64:
            parts.append(
                types.Part.from_bytes(
                    data=base64.b64decode(file_base64),
                    mime_type=mime_type or "application/pdf",
                )
            )

        # Look for referenced lectures and get their transcripts
        referenced_transcripts = []
        if course_lectures and session:
            mentioned_numbers = extract_lecture_numbers(title + " " + text)
            for lec in course_lectures:
                lec_numbers = extract_lecture_numbers(lec.title)
                if any(num in lec_numbers for num in mentioned_numbers):
                    stmt = select(Job).where(Job.moodle_video_id == lec.id, Job.status == "completed")
                    result = await session.execute(stmt)
                    job = result.scalars().first()
                    if job and job.audio_hash:
                        stmt_t = select(Transcript).where(Transcript.audio_hash == job.audio_hash)
                        res_t = await session.execute(stmt_t)
                        trans = res_t.scalars().first()
                        if trans and trans.text:
                            referenced_transcripts.append((lec.title, trans.text))

        additional_context = ""
        if referenced_transcripts:
            additional_context = "\n\n--- Additional Lecture Transcripts Context ---"
            for lec_title, trans_text in referenced_transcripts:
                additional_context += f"\n\nLecture: {lec_title}\nTranscript:\n{trans_text}\n"

        prompt = (
            f"Solve the following university assignment: '{title}'.\n\n"
            f"Assignment Details/Scraped Text:\n{text}\n"
            f"{additional_context}\n"
            "Analyze the assignment and the provided lecture transcripts context (if any). "
            "Search the web using the Google Search tool to find relevant "
            "formulas, references, lecture materials, or solutions guidelines. "
            "Write a highly detailed, comprehensive, step-by-step solutions guide/answer key. "
            "Write the solution in the same language as the assignment (e.g., if the assignment is in Hebrew, write the solution in Hebrew)."
        )
        parts.append(types.Part.from_text(text=prompt))

        # Enable search grounding tool
        grounding_tool = types.Tool(google_search=types.GoogleSearch())

        response = await get_client().aio.models.generate_content(
            model=MODEL,
            contents=parts,
            config=types.GenerateContentConfig(
                tools=[grounding_tool],
                system_instruction=(
                    "You are an expert academic tutor. You solve university homework, assignments, "
                    "and exercises with rigorous, step-by-step explanations, math derivations, "
                    "and references. Make sure the answers are correct, comprehensive, and clear."
                ),
            ),
        )

        solutions_text = response.text
        return self._generate_pdf(title, solutions_text)

    def _generate_pdf(self, title: str, content: str) -> bytes:
        pdf = FPDF()
        pdf.add_page()

        # Try to use DejaVu font for Unicode support (Hebrew), fall back to Helvetica if not found
        try:
            pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
            pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
            pdf.set_font("DejaVu", size=11)
            is_unicode = True
        except Exception:
            pdf.set_font("Helvetica", size=11)
            is_unicode = False

        # Document Header
        pdf.set_text_color(0, 86, 179) # Premium blue
        if is_unicode:
            header_title = reverse_hebrew(f"Solutions: {title}")
        else:
            header_title = f"Solutions: {title}"

        # We can use multi_cell or cell. multi_cell handles text wrapping.
        pdf.set_font(pdf.font_family, "B", 16)
        pdf.multi_cell(0, 10, header_title, align="C")
        pdf.ln(8)

        # Content body
        pdf.set_font(pdf.font_family, "", 11)
        pdf.set_text_color(30, 30, 30) # Soft black for high readability

        body_text = content
        if is_unicode:
            body_text = reverse_hebrew(body_text)

        # Write content line by line to support margins and multi-cell wrapping
        for idx, line in enumerate(body_text.split("\n")):
            if not line.strip():
                pdf.ln(4)
                continue
            # Use multi_cell to automatically wrap long lines
            try:
                # Ensure x is reset to left margin to avoid offset width calculation issues
                pdf.x = pdf.l_margin
                pdf.multi_cell(0, 6, line)
            except Exception as e:
                print(f"FAILED TO RENDER LINE {idx}: {repr(line)}")
                print(f"Line length: {len(line)}, pdf.x: {pdf.x}, pdf.w: {pdf.w}, pdf.l_margin: {pdf.l_margin}, pdf.r_margin: {pdf.r_margin}")
                print(f"Exception: {e}")
                # Fallback: try with explicit width and if that fails, try to strip or ignore
                try:
                    pdf.x = pdf.l_margin
                    pdf.multi_cell(pdf.epw, 6, line)
                except Exception as e2:
                    print(f"Fallback also failed: {e2}")
                    # Last resort: write a cleaned version or skip
                    cleaned = "".join(c for c in line if ord(c) < 65536)
                    try:
                        pdf.multi_cell(pdf.epw, 6, cleaned[:100] + "... [truncated due to error]")
                    except Exception:
                        pass

        # Return as bytes
        pdf_buffer = io.BytesIO()
        pdf.output(pdf_buffer)
        return pdf_buffer.getvalue()


_solver = AssignmentSolver()


def get_solver() -> AssignmentSolver:
    return _solver
