import os
import aiosqlite
import json
from datetime import datetime

DB_FILE = "content.db"

async def init_db():
    """
    Initializes the SQLite database schema if not already present.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                niche TEXT,
                content_type TEXT,
                personality TEXT,
                title TEXT,
                script TEXT,
                hashtags TEXT,
                description TEXT,
                video_path TEXT,
                youtube_url TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()

async def create_job(job_id: str, user_id: int, prompt: str):
    """
    Creates a new job tracking record.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        now = datetime.utcnow().isoformat()
        await db.execute(
            "INSERT INTO jobs (id, user_id, prompt, status, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, user_id, prompt, "pending", now)
        )
        await db.commit()

async def update_job(job_id: str, **kwargs):
    """
    Updates column values for a specific job tracking record.
    """
    if not kwargs:
        return
    async with aiosqlite.connect(DB_FILE) as db:
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(job_id)
        await db.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", tuple(values))
        await db.commit()

async def get_job(job_id: str) -> dict:
    """
    Retrieves a single job record as a dictionary.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def get_latest_job(user_id: int) -> dict:
    """
    Retrieves the most recent job for a specific user.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def get_recent_jobs(user_id: int, limit: int = 5) -> list:
    """
    Retrieves a list of recent jobs for a specific user.
    """
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def cancel_job(job_id: str):
    """
    Marks a job as cancelled in the database.
    """
    await update_job(job_id, status="cancelled")
