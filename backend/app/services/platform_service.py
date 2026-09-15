"""M4 用例层。内存实现用于演示/测试，生产表结构见 migrations/002。"""
import uuid
from app.models.platform import CourseCreate

stores: dict[str, dict] = {}; courses: dict[str, dict] = {}; assignments: dict[str, dict] = {}

def create_store(user_id: int, name: str):
    sid=f"store_{uuid.uuid4().hex[:10]}"; stores[sid]={"id":sid,"name":name,"members":{user_id:"owner"}}; return stores[sid]
def require_role(store_id: str, user_id: int, allowed: set[str]):
    store=stores.get(store_id); role=store and store["members"].get(user_id)
    if role not in allowed: raise PermissionError("FORBIDDEN")
    return store
def add_member(store_id: str, actor: int, user_id: int, role: str):
    store=require_role(store_id,actor,{"owner"}); store["members"][user_id]=role; return {"store_id":store_id,"user_id":user_id,"role":role}
def create_course(store_id: str, actor: int, data: CourseCreate):
    require_role(store_id,actor,{"owner","manager"}); cid=f"course_{uuid.uuid4().hex[:10]}"; courses[cid]={"id":cid,"store_id":store_id,"title":data.title,"status":"draft","questions":[q.model_dump() for q in data.questions],"confirmed_question_ids":data.confirmed_question_ids}; return courses[cid]
def publish_course(course_id: str, actor: int):
    course=courses.get(course_id)
    if not course: raise KeyError("COURSE_NOT_FOUND")
    require_role(course["store_id"],actor,{"owner","manager"})
    required={q["id"] for q in course["questions"] if q.get("requires_confirmation")}
    if not required.issubset(set(course["confirmed_question_ids"])): raise ValueError("HIGH_RISK_CONFIRMATION_REQUIRED")
    course["status"]="published"; return course
def assign(course_id: str, actor: int, employee: int):
    course=courses.get(course_id)
    if not course or course["status"]!="published": raise ValueError("COURSE_NOT_PUBLISHED")
    require_role(course["store_id"],actor,{"owner","manager"}); require_role(course["store_id"],employee,{"employee"})
    aid=f"assignment_{uuid.uuid4().hex[:10]}"; assignments[aid]={"id":aid,"store_id":course["store_id"],"course_id":course_id,"employee_user_id":employee,"status":"pending","report":None}; return assignments[aid]
def public_questions(assignment_id: str, user_id: int):
    a=assignments.get(assignment_id)
    if not a or a["employee_user_id"]!=user_id: raise PermissionError("FORBIDDEN")
    course=courses[a["course_id"]]; a["status"]="in_progress"
    return [{k:v for k,v in q.items() if k not in {"answer","explanation"}} for q in course["questions"]]
def submit(assignment_id: str, user_id: int, answers: list):
    a=assignments.get(assignment_id)
    if not a or a["employee_user_id"]!=user_id: raise PermissionError("FORBIDDEN")
    if a["status"]=="completed": return a["report"]
    questions=courses[a["course_id"]]["questions"]; supplied={x.question_id:set(x.selected_answers) for x in answers}; results={q["id"]:supplied.get(q["id"],set())==set(q["answer"]) for q in questions}; score=round(sum(results.values())*100/len(questions)) if questions else 0
    a["status"]="completed"; a["report"]={"score":score,"correct_count":sum(results.values()),"total_count":len(questions),"answer_results":results,"questions":questions,"certification_notice":"本结果仅用于在线学习，不等同于实操上岗认证。"}; return a["report"]
def report(assignment_id: str,user_id:int):
    a=assignments.get(assignment_id)
    if not a or a["employee_user_id"]!=user_id: raise PermissionError("FORBIDDEN")
    if not a["report"]: raise ValueError("ASSIGNMENT_NOT_COMPLETED")
    return a["report"]
def store_results(store_id:str,actor:int):
    require_role(store_id,actor,{"owner","manager"})
    return [{"assignment_id":a["id"],"employee_user_id":a["employee_user_id"],"course_id":a["course_id"],"status":a["status"],"score":a["report"]["score"] if a["report"] else None} for a in assignments.values() if a["store_id"]==store_id]
