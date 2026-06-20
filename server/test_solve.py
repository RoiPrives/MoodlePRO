import asyncio
import os
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Setup environment database URL
DATABASE_URL = "postgresql+asyncpg://moodlepro:moodlepro@localhost:5432/moodlepro"
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def setup_test_data():
    from app.db.models import Job, Transcript

    async with SessionLocal() as session:
        # Check if test job already exists
        stmt = select(Job).where(Job.moodle_video_id == "1")
        result = await session.execute(stmt)
        existing_job = result.scalars().first()

        if existing_job:
            print("Test lecture job with moodle_video_id='1' already exists.")
            audio_hash = existing_job.audio_hash
        else:
            print("Creating test lecture job...")
            audio_hash = "fake-calc-lecture-audio-hash-123"
            job = Job(
                video_url="http://localhost:8000/testvideo/lecture.mp4",
                moodle_video_id="1",
                audio_hash=audio_hash,
                status="completed"
            )
            session.add(job)
            await session.commit()

        # Check if test transcript already exists
        stmt_t = select(Transcript).where(Transcript.audio_hash == audio_hash)
        result_t = await session.execute(stmt_t)
        existing_trans = result_t.scalars().first()

        if not existing_trans:
            print("Creating test transcript...")
            trans = Transcript(
                audio_hash=audio_hash,
                language="en",
                text=(
                    "Welcome to Lecture 1 on Calculus basics. In this lecture, we define "
                    "derivatives. The derivative of a function x^n with respect to x is n * x^(n-1). "
                    "For example, the derivative of x^2 is 2x. Also, the derivative of a constant "
                    "multiplied by x (like c * x) is just c. So the derivative of 5x is 5. "
                    "Punctuation and constants are preserved under linear combinations of derivatives."
                ),
                srt="1\n00:00:00,000 --> 00:00:10,000\nWelcome to Lecture 1 on Calculus basics."
            )
            session.add(trans)
            await session.commit()
            print("Test data setup complete.")
        else:
            print("Test transcript already exists.")


async def test_solve_endpoint():
    payload = {
        "title": "Calculus Assignment 1",
        "text": "Solve the following problem from Lecture 1: What is the derivative of the function f(x) = x^2 + 5x?",
        "item_type": "assignment",
        "course_lectures": [
            {
                "id": "1",
                "item_type": "lecture",
                "title": "Lecture 1: Introduction to Calculus",
                "text": ""
            }
        ]
    }

    print("Sending POST request to http://localhost:8000/items/solve...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post("http://localhost:8000/items/solve", json=payload)
        
    print(f"Response status code: {response.status_code}")
    if response.status_code == 200:
        pdf_path = "solutions_demo.pdf"
        with open(pdf_path, "wb") as f:
            f.write(response.content)
        print(f"Success! Generated PDF saved to: {pdf_path}")
        print(f"File size: {len(response.content)} bytes")
    else:
        print("Error details:")
        print(response.text)


async def main():
    # Insert app path so we can import DB models
    import sys
    from pathlib import Path
    server_path = Path(__file__).resolve().parent
    sys.path.insert(0, str(server_path))

    await setup_test_data()
    await test_solve_endpoint()


if __name__ == "__main__":
    asyncio.run(main())
