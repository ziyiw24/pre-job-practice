"""异步任务数据访问层"""

from __future__ import annotations

import json
from typing import Optional

import structlog

from app.core.db import get_mysql_pool

logger = structlog.get_logger()

# Local/demo mode has no MySQL pool. Keeping tasks in-process makes the async
# API behave identically and lets the complete learning flow be exercised.
_memory_tasks: dict[str, dict] = {}


async def create_task(
    task_id: str,
    user_id: Optional[int],
    user_input: str,
    question_count: int,
    difficulty: str,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        _memory_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "result_json": None,
            "error_message": None,
        }
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO quiz_tasks (task_id, user_id, user_input, question_count, difficulty, status) "
                "VALUES (%s, %s, %s, %s, %s, 'pending')",
                (task_id, user_id, user_input, question_count, difficulty),
            )


async def update_task_status(
    task_id: str,
    status: str,
    result_json: Optional[dict] = None,
    error_message: Optional[str] = None,
) -> None:
    pool = get_mysql_pool()
    if pool is None:
        task = _memory_tasks.get(task_id)
        if task is not None:
            task.update(status=status, result_json=result_json, error_message=error_message)
        return
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE quiz_tasks SET status = %s, result_json = %s, error_message = %s WHERE task_id = %s",
                (
                    status,
                    json.dumps(result_json, ensure_ascii=False) if result_json else None,
                    error_message,
                    task_id,
                ),
            )


async def get_task(task_id: str) -> Optional[dict]:
    pool = get_mysql_pool()
    if pool is None:
        return _memory_tasks.get(task_id)
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(
                "SELECT task_id, status, result_json, error_message FROM quiz_tasks WHERE task_id = %s",
                (task_id,),
            )
            row = await cur.fetchone()
            if row and row.get("result_json"):
                if isinstance(row["result_json"], str):
                    row["result_json"] = json.loads(row["result_json"])
            return row


# Need the import for DictCursor
import aiomysql
