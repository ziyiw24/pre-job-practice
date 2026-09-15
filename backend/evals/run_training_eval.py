from __future__ import annotations
import argparse, asyncio, json, time
from pathlib import Path
from app.agents.training.graph import build_training_graph
from app.infrastructure.llm.mock_training_gateway import MockTrainingModelGateway
from evals.metrics import aggregate, measure
from app.models.training import TrainingGenerateRequest
from app.services.training_service import _make_demo_quiz


async def run(dataset: Path, mode: str) -> dict:
    rows = []
    for path in sorted(dataset.glob("*.json")):
        started=time.monotonic()
        case = json.loads(path.read_text())
        try:
            if mode == "baseline":
                quiz = _make_demo_quiz(TrainingGenerateRequest.model_construct(client_request_id=f"eval_{case['case_id']}", title=case["category"], content=case["content"], question_count=5, difficulty="mixed"))
                questions = [q.model_dump() for q in quiz.questions]
            else:
                state = await build_training_graph(MockTrainingModelGateway()).ainvoke({"task_id": case["case_id"], "title": case["category"], "content": case["content"], "question_count": 5, "difficulty": "mixed", "revision_count": 0, "max_revisions": 2, "model_calls": 0, "max_model_calls": 6, "status": "running", "prompt_version": "training-v1", "graph_version": "training-author-v1"})
                questions = state.get("questions", [])
            row=measure(case, questions);row.update({"success":True,"schema_valid":True})
        except Exception:
            row={"success":False,"schema_valid":False,"question_count":0,"quote_coverage":0,"evidence_failure_rate":1,"number_consistency":0,"estimated_tokens":0,"estimated_cost":0}
        row["latency_ms"]=round((time.monotonic()-started)*1000);rows.append(row)
    return {"mode": mode, "provider": "mock", **aggregate(rows)}


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--dataset", type=Path, required=True); parser.add_argument("--mode", choices=["baseline", "agent"], default="agent")
    args=parser.parse_args(); print(json.dumps(asyncio.run(run(args.dataset, args.mode)), ensure_ascii=False, indent=2))


if __name__ == "__main__": main()
