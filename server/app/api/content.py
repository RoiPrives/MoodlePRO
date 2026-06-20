from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job, Transcript
from app.db.session import get_session
from app.schemas import (
    ChapterResponse,
    CourseItem,
    CourseSummaryRequest,
    CourseSummaryScope,
    QuizQuestion,
    QuizRequest,
    QuizResponse,
    SolveRequest,
    SummaryRequest,
    SummaryResponse,
)
from app.services import dedup
from app.services.chaptering import get_chapterer
from app.services.jobs import get_job_or_404
from app.services.quiz import get_quiz_generator
from app.services.solver import get_solver
from app.services.srt import parse_srt
from app.services.summarizer import get_summarizer

router = APIRouter()


async def _resolve_academic_texts(session: AsyncSession, items: list[CourseItem]) -> list[CourseItem]:
    resolved = []
    for item in items:
        if item.item_type == "lecture":
            stmt = select(Job).where(Job.moodle_video_id == item.id, Job.status == "completed")
            result = await session.execute(stmt)
            job = result.scalars().first()
            if job and job.audio_hash:
                stmt_t = select(Transcript).where(Transcript.audio_hash == job.audio_hash)
                res_t = await session.execute(stmt_t)
                trans = res_t.scalars().first()
                if trans:
                    item.text = trans.text
                    resolved.append(item)
                    continue
            raise HTTPException(
                status_code=400,
                detail=f"Lecture '{item.title}' is not transcribed yet. Please download its transcript first.",
            )
        else:
            resolved.append(item)
    return resolved


async def _get_job_transcript(session: AsyncSession, job_id: str):
    job = await get_job_or_404(session, job_id)
    if job.audio_hash is None:
        raise HTTPException(status_code=409, detail="Job has no transcript yet")
    transcript = await dedup.find_transcript(session, job.audio_hash)
    if transcript is None:
        raise HTTPException(status_code=409, detail="Job has no transcript yet")
    return transcript


@router.post("/items/summary", response_model=SummaryResponse)
async def summarize_item(request: SummaryRequest) -> SummaryResponse:
    summary = await get_summarizer().summarize(
        request.text, request.mode, file_base64=request.file_base64, mime_type=request.mime_type
    )
    return SummaryResponse(summary=summary)


@router.post("/items/quiz", response_model=QuizResponse)
async def quiz_item(request: QuizRequest) -> QuizResponse:
    questions = await get_quiz_generator().generate_quiz(
        request.text, request.num_questions, file_base64=request.file_base64, mime_type=request.mime_type
    )
    return QuizResponse(questions=[QuizQuestion(**q) for q in questions])


@router.post("/items/solve")
async def solve_assignment(
    request: SolveRequest, session: AsyncSession = Depends(get_session)
) -> Response:
    pdf_bytes = await get_solver().solve(
        request.title,
        request.text,
        file_base64=request.file_base64,
        mime_type=request.mime_type,
        course_lectures=request.course_lectures,
        session=session,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=solutions.pdf"}
    )



_SCOPE_TO_ITEM_TYPE = {
    CourseSummaryScope.assignments: "assignment",
    CourseSummaryScope.lectures: "lecture",
    CourseSummaryScope.slides: "slides",
}


def _filter_items_by_scope(items: list[CourseItem], scope: CourseSummaryScope) -> list[CourseItem]:
    if scope == CourseSummaryScope.everything:
        return items
    item_type = _SCOPE_TO_ITEM_TYPE[scope]
    return [item for item in items if item.item_type == item_type]


@router.post("/courses/summary", response_model=SummaryResponse)
async def summarize_course(
    request: CourseSummaryRequest, session: AsyncSession = Depends(get_session)
) -> SummaryResponse:
    filtered = _filter_items_by_scope(request.items, request.scope)
    if not filtered:
        return SummaryResponse(summary="No matching items were found for the requested scope.")

    resolved = await _resolve_academic_texts(session, filtered)
    combined = "\n\n".join(f"## {item.title}\n{item.text}" for item in resolved)
    summary = await get_summarizer().summarize(combined)
    return SummaryResponse(summary=summary)


@router.post("/courses/quiz", response_model=QuizResponse)
async def quiz_course(
    request: CourseSummaryRequest, session: AsyncSession = Depends(get_session)
) -> QuizResponse:
    filtered = _filter_items_by_scope(request.items, request.scope)
    if not filtered:
        return QuizResponse(questions=[])

    resolved = await _resolve_academic_texts(session, filtered)
    combined = "\n\n".join(f"## {item.title}\n{item.text}" for item in resolved)
    questions = await get_quiz_generator().generate_quiz(
        combined, num_questions=request.num_questions or 3, difficulty=request.difficulty or "medium"
    )
    return QuizResponse(questions=[QuizQuestion(**q) for q in questions])


async def _get_chapters(session: AsyncSession, job_id: str) -> list[dict]:
    transcript = await _get_job_transcript(session, job_id)
    segments = parse_srt(transcript.srt)
    if not segments:
        return []
    return await get_chapterer().make_chapters(segments)


@router.get("/jobs/{job_id}/chapters", response_model=list[ChapterResponse])
async def get_job_chapters(job_id: str, session: AsyncSession = Depends(get_session)) -> list[ChapterResponse]:
    chapters = await _get_chapters(session, job_id)
    return [ChapterResponse(id=c["id"], title=c["title"], start=c["start"], end=c["end"]) for c in chapters]


def _find_chapter(chapters: list[dict], chapter_id: int) -> dict:
    for chapter in chapters:
        if chapter["id"] == chapter_id:
            return chapter
    raise HTTPException(status_code=404, detail="Chapter not found")


@router.post("/jobs/{job_id}/chapters/{chapter_id}/summary", response_model=SummaryResponse)
async def summarize_chapter(
    job_id: str, chapter_id: int, session: AsyncSession = Depends(get_session)
) -> SummaryResponse:
    chapters = await _get_chapters(session, job_id)
    chapter = _find_chapter(chapters, chapter_id)
    summary = await get_summarizer().summarize(chapter["text"])
    return SummaryResponse(summary=summary)


@router.post("/jobs/{job_id}/chapters/{chapter_id}/quiz", response_model=QuizResponse)
async def quiz_chapter(
    job_id: str, chapter_id: int, session: AsyncSession = Depends(get_session)
) -> QuizResponse:
    chapters = await _get_chapters(session, job_id)
    chapter = _find_chapter(chapters, chapter_id)
    questions = await get_quiz_generator().generate_quiz(chapter["text"])
    return QuizResponse(questions=[QuizQuestion(**q) for q in questions])
