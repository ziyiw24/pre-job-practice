"""M4 用例层。内存实现用于演示/测试，生产表结构见 migrations/002。"""
import secrets, uuid
from app.models.platform import CourseCreate

stores: dict[str, dict] = {}; courses: dict[str, dict] = {}; assignments: dict[str, dict] = {}; invites: dict[str,dict] = {}

def ensure_demo_membership(user_id: int, role: str):
    store=stores.setdefault("store_demo",{"id":"store_demo","name":"上岗练演示门店","members":{}})
    store["members"][user_id]=role
    store["members"].setdefault(9001,"manager");store["members"].setdefault(9002,"employee")
    courses.setdefault("course_demo",{"id":"course_demo","store_id":"store_demo","title":"原料时效与异常处理","status":"published","confirmed_question_ids":[],"questions":[{"id":"q1","type":"single","scenario":"发现一盒未标记的已开封原料。","stem":"正确处理方式是什么？","options":[{"key":"A","text":"继续使用"},{"key":"B","text":"隔离并报告负责人"}],"answer":["B"],"explanation":"未标记原料不得继续使用。","knowledge_point":"原料标签","evidence":{"quote":"未标记或标记不清的原料不得继续使用"},"risk_tags":["safety"],"requires_confirmation":True}]})
    assignments.setdefault("assignment_demo",{"id":"assignment_demo","store_id":"store_demo","course_id":"course_demo","employee_user_id":9002,"status":"pending","report":None})
    return store

def memberships(user_id: int):
    return [{"store_id":s["id"],"store_name":s["name"],"role":role} for s in stores.values() if (role:=s["members"].get(user_id))]

def dashboard(store_id: str,user_id: int):
    require_role(store_id,user_id,{"owner","manager"})
    scoped_courses=[c for c in courses.values() if c["store_id"]==store_id]
    scoped_assignments=[a for a in assignments.values() if a["store_id"]==store_id]
    return {"course_count":len(scoped_courses),"draft_count":sum(c["status"]!="published" for c in scoped_courses),"published_count":sum(c["status"]=="published" for c in scoped_courses),"pending_assignments":sum(a["status"]!="completed" for a in scoped_assignments),"completed_assignments":sum(a["status"]=="completed" for a in scoped_assignments)}

def list_courses(store_id: str,user_id: int):
    require_role(store_id,user_id,{"owner","manager"})
    return [{"id":c["id"],"title":c["title"],"status":c["status"],"question_count":len(c["questions"])} for c in courses.values() if c["store_id"]==store_id]

def list_members(store_id: str,user_id: int):
    store=require_role(store_id,user_id,{"owner","manager"})
    return [{"user_id":uid,"role":role,"nickname":f"用户 {uid}"} for uid,role in store["members"].items()]

def list_employee_assignments(user_id: int,status: str|None=None):
    rows=[a for a in assignments.values() if a["employee_user_id"]==user_id and (not status or a["status"]==status)]
    return [{"id":a["id"],"store_id":a["store_id"],"course_id":a["course_id"],"title":courses[a["course_id"]]["title"],"status":a["status"],"score":a["report"]["score"] if a["report"] else None} for a in rows]

def create_invite(store_id:str,user_id:int,role:str,max_uses:int,expires_hours:int):
    require_role(store_id,user_id,{"owner","manager"});code=secrets.token_hex(4).upper();invites[code]={"store_id":store_id,"role":role,"max_uses":max_uses,"used_count":0};return {"invite_code":code,"role":role,"expires_hours":expires_hours}

def join_invite(user_id:int,invite_code:str):
    invite=invites.get(invite_code.upper())
    if not invite or invite["used_count"]>=invite["max_uses"]:raise ValueError("INVITE_INVALID")
    stores[invite["store_id"]]["members"][user_id]=invite["role"];invite["used_count"]+=1
    store=stores[invite["store_id"]];return {"store_id":store["id"],"store_name":store["name"],"role":invite["role"]}

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
