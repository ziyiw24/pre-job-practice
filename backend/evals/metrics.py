import re


def measure(case: dict, questions: list[dict]) -> dict:
    total = len(questions)
    quote_ok = sum(q.get("evidence", {}).get("quote", "") in case["content"] for q in questions)
    numeric = [q for q in questions if re.search(r"\d", q.get("evidence", {}).get("quote", ""))]
    numeric_ok = sum(set(re.findall(r"\d+(?:\.\d+)?", q["stem"] + q["explanation"])).issubset(set(re.findall(r"\d+(?:\.\d+)?", q["evidence"]["quote"]))) for q in numeric)
    return {"question_count": total, "quote_accuracy": quote_ok / total if total else 0, "number_fidelity": numeric_ok / len(numeric) if numeric else 1}


def aggregate(rows: list[dict]) -> dict:
    ordered=sorted(x.get("latency_ms",0) for x in rows);p95=ordered[min(len(ordered)-1,max(0,int(len(ordered)*.95)-1))]
    return {"cases": len(rows), "questions": sum(x["question_count"] for x in rows), "generation_success_rate":sum(x.get("success",True) for x in rows)/len(rows),"schema_failure_rate":sum(not x.get("schema_valid",True) for x in rows)/len(rows),"quote_accuracy": sum(x["quote_accuracy"] for x in rows) / len(rows), "evidence_failure_rate":1-sum(x["quote_accuracy"] for x in rows)/len(rows),"number_fidelity": sum(x["number_fidelity"] for x in rows) / len(rows),"latency_p95_ms":p95,"token_usage":0,"estimated_cost":0}
