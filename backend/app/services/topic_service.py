"""从版本化内容目录读取已审核专题。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.models.topic import Topic

_TOPICS_FILE = Path(__file__).resolve().parents[1] / "content" / "topics.json"


@lru_cache(maxsize=1)
def _load_topics() -> list[Topic]:
    with _TOPICS_FILE.open(encoding="utf-8") as file:
        topics = [Topic.model_validate(item) for item in json.load(file)]
    return [topic for topic in topics if topic.review_status == "approved"]


def list_topics(category: str | None = None, difficulty: str | None = None, keyword: str | None = None) -> list[Topic]:
    topics = _load_topics()
    if category:
        topics = [topic for topic in topics if topic.category == category]
    if difficulty:
        topics = [topic for topic in topics if topic.difficulty == difficulty]
    if keyword:
        query = keyword.strip().lower()
        topics = [topic for topic in topics if query in f"{topic.title} {topic.summary}".lower()]
    return topics


def get_topic(topic_id: str) -> Topic | None:
    return next((topic for topic in _load_topics() if topic.id == topic_id or topic.slug == topic_id), None)


def match_topic(query: str) -> Topic | None:
    """Map a natural-language learning request to an approved local topic.

    Exact title/alias matches win; longer contained terms are preferred so that
    queries such as "我想学一下胆经这个知识点" resolve predictably.
    """
    normalized = "".join(query.lower().split())
    if not normalized:
        return None

    candidates: list[tuple[int, Topic]] = []
    for topic in _load_topics():
        terms = [topic.title, topic.slug, *topic.search_terms]
        score = max(
            (len(term) for term in terms if "".join(term.lower().split()) in normalized),
            default=0,
        )
        if score:
            candidates.append((score, topic))
    return max(candidates, key=lambda item: item[0])[1] if candidates else None


def build_topic_context(topic: Topic) -> str:
    source_lines = "\n".join(
        f"[{index}] {source.publisher}《{source.title}》 {source.url}".strip()
        for index, source in enumerate(topic.sources, 1)
    )
    return f"【已审核专题】{topic.title}\n【内容】{topic.content}\n【来源】\n{source_lines}"
