"""M4 MySQL 持久化适配器，所有资源查询同时约束 store/user。"""
from __future__ import annotations
import hashlib, json, secrets, uuid
from app.core.db import get_mysql_pool

class MySQLPlatformRepository:
    def _pool(self):
        pool=get_mysql_pool()
        if pool is None:raise RuntimeError("DATABASE_UNAVAILABLE")
        return pool
    async def create_store(self,user_id,name):
        async with self._pool().acquire() as conn:
            await conn.begin()
            try:
                async with conn.cursor() as cur:
                    await cur.execute("INSERT INTO stores(name,owner_user_id) VALUES(%s,%s)",(name,user_id)); sid=cur.lastrowid
                    await cur.execute("INSERT INTO store_members(store_id,user_id,role) VALUES(%s,%s,'owner')",(sid,user_id))
                await conn.commit(); return {"id":str(sid),"name":name}
            except Exception:await conn.rollback();raise
    async def memberships(self,user_id):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT s.id,s.name,sm.role FROM store_members sm JOIN stores s ON s.id=sm.store_id WHERE sm.user_id=%s AND sm.status='active' ORDER BY sm.id",(user_id,));rows=await cur.fetchall()
        return [{"store_id":str(x[0]),"store_name":x[1],"role":x[2]} for x in rows]
    async def dashboard(self,store_id,user_id):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await self._role(cur,store_id,user_id,{"owner","manager"})
                await cur.execute("SELECT COUNT(*),SUM(status!='published'),SUM(status='published') FROM training_courses WHERE store_id=%s",(store_id,));c=await cur.fetchone()
                await cur.execute("SELECT SUM(status!='completed'),SUM(status='completed') FROM training_assignments WHERE store_id=%s",(store_id,));a=await cur.fetchone()
        return {"course_count":c[0] or 0,"draft_count":c[1] or 0,"published_count":c[2] or 0,"pending_assignments":a[0] or 0,"completed_assignments":a[1] or 0}
    async def list_courses(self,store_id,user_id):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await self._role(cur,store_id,user_id,{"owner","manager"});await cur.execute("SELECT tc.id,tc.title,tc.status,COUNT(tq.id) FROM training_courses tc LEFT JOIN training_questions tq ON tq.course_id=tc.id WHERE tc.store_id=%s GROUP BY tc.id ORDER BY tc.updated_at DESC",(store_id,));rows=await cur.fetchall()
        return [{"id":str(x[0]),"title":x[1],"status":x[2],"question_count":x[3]} for x in rows]
    async def list_members(self,store_id,user_id):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await self._role(cur,store_id,user_id,{"owner","manager"});await cur.execute("SELECT u.id,u.nickname,sm.role FROM store_members sm JOIN users u ON u.id=sm.user_id WHERE sm.store_id=%s AND sm.status='active' ORDER BY sm.id",(store_id,));rows=await cur.fetchall()
        return [{"user_id":x[0],"nickname":x[1],"role":x[2]} for x in rows]
    async def list_employee_assignments(self,user_id,status=None):
        sql="SELECT ta.id,ta.store_id,ta.course_id,tc.title,ta.status,aa.score FROM training_assignments ta JOIN training_courses tc ON tc.id=ta.course_id LEFT JOIN answer_attempts aa ON aa.assignment_id=ta.id AND aa.status='completed' WHERE ta.employee_user_id=%s";params=[user_id]
        if status:sql+=" AND ta.status=%s";params.append(status)
        sql+=" ORDER BY ta.id DESC"
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:await cur.execute(sql,tuple(params));rows=await cur.fetchall()
        return [{"id":str(x[0]),"store_id":str(x[1]),"course_id":str(x[2]),"title":x[3],"status":x[4],"score":x[5]} for x in rows]
    async def create_invite(self,store_id,user_id,role,max_uses,expires_hours):
        code=secrets.token_hex(4).upper();digest=hashlib.sha256(code.encode()).hexdigest()
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await self._role(cur,store_id,user_id,{"owner","manager"});await cur.execute("INSERT INTO store_invites(store_id,invite_code_hash,role,expires_at,max_uses,created_by) VALUES(%s,%s,%s,DATE_ADD(NOW(),INTERVAL %s HOUR),%s,%s)",(store_id,digest,role,expires_hours,max_uses,user_id))
        return {"invite_code":code,"role":role,"expires_hours":expires_hours}
    async def join_invite(self,user_id,invite_code):
        digest=hashlib.sha256(invite_code.upper().encode()).hexdigest()
        async with self._pool().acquire() as conn:
            await conn.begin()
            try:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT id,store_id,role,max_uses,used_count FROM store_invites WHERE invite_code_hash=%s AND expires_at>NOW() FOR UPDATE",(digest,));row=await cur.fetchone()
                    if not row or row[4]>=row[3]:raise ValueError("INVITE_INVALID")
                    await cur.execute("INSERT INTO store_members(store_id,user_id,role,status) VALUES(%s,%s,%s,'active') ON DUPLICATE KEY UPDATE role=VALUES(role),status='active'",(row[1],user_id,row[2]));await cur.execute("UPDATE store_invites SET used_count=used_count+1 WHERE id=%s",(row[0],));await cur.execute("SELECT name FROM stores WHERE id=%s",(row[1],));name=(await cur.fetchone())[0]
                await conn.commit();return {"store_id":str(row[1]),"store_name":name,"role":row[2]}
            except Exception:await conn.rollback();raise
    async def _role(self,cur,store_id,user_id,allowed):
        await cur.execute("SELECT role FROM store_members WHERE store_id=%s AND user_id=%s AND status='active'",(store_id,user_id)); row=await cur.fetchone()
        if not row or row[0] not in allowed:raise PermissionError("FORBIDDEN")
    async def add_member(self,store_id,actor,user_id,role):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await self._role(cur,store_id,actor,{"owner"}); await cur.execute("INSERT INTO store_members(store_id,user_id,role) VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE role=VALUES(role)",(store_id,user_id,role))
        return {"store_id":str(store_id),"user_id":user_id,"role":role}
    async def create_course(self,store_id,actor,data):
        async with self._pool().acquire() as conn:
            await conn.begin()
            try:
                async with conn.cursor() as cur:
                    await self._role(cur,store_id,actor,{"owner","manager"}); qid=f"quiz_{uuid.uuid4().hex[:12]}"
                    await cur.execute("INSERT INTO training_courses(quiz_id,store_id,title,status,prompt_version,graph_version,model_version,reviewer_user_id) VALUES(%s,%s,%s,'draft','training-v1','training-author-v1','configured',%s)",(qid,store_id,data.title,actor)); cid=cur.lastrowid
                    for q in data.questions:
                        confirmed=actor if q.id in data.confirmed_question_ids else None
                        await cur.execute("INSERT INTO training_questions(course_id,question_id,stem,answer_json,explanation,evidence_json,requires_confirmation,confirmed_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(cid,q.id,q.stem,json.dumps(q.answer),q.explanation,q.evidence.model_dump_json(),q.requires_confirmation,confirmed)); question_pk=cur.lastrowid
                        for o in q.options:await cur.execute("INSERT INTO question_options(question_id,option_key,option_text) VALUES(%s,%s,%s)",(question_pk,o.key,o.text))
                await conn.commit(); return {"id":str(cid),"store_id":str(store_id),"title":data.title,"status":"draft"}
            except Exception:await conn.rollback();raise
    async def publish_course(self,course_id,actor):
        async with self._pool().acquire() as conn:
            await conn.begin()
            try:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT store_id FROM training_courses WHERE id=%s FOR UPDATE",(course_id,)); row=await cur.fetchone()
                    if not row:raise KeyError("COURSE_NOT_FOUND")
                    await self._role(cur,row[0],actor,{"owner","manager"}); await cur.execute("SELECT COUNT(*) FROM training_questions WHERE course_id=%s AND requires_confirmation=1 AND confirmed_by IS NULL",(course_id,))
                    if (await cur.fetchone())[0]:raise ValueError("HIGH_RISK_CONFIRMATION_REQUIRED")
                    await cur.execute("UPDATE training_courses SET status='published',reviewer_user_id=%s WHERE id=%s",(actor,course_id)); await cur.execute("INSERT INTO course_publications(course_id,store_id,published_by) VALUES(%s,%s,%s)",(course_id,row[0],actor))
                await conn.commit();return {"id":str(course_id),"status":"published"}
            except Exception:await conn.rollback();raise
    async def assign(self,course_id,actor,employee):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT store_id,status FROM training_courses WHERE id=%s",(course_id,)); row=await cur.fetchone()
                if not row or row[1]!="published":raise ValueError("COURSE_NOT_PUBLISHED")
                await self._role(cur,row[0],actor,{"owner","manager"}); await self._role(cur,row[0],employee,{"employee"}); await cur.execute("INSERT INTO training_assignments(store_id,course_id,employee_user_id) VALUES(%s,%s,%s)",(row[0],course_id,employee)); aid=cur.lastrowid
        return {"id":str(aid),"store_id":str(row[0]),"course_id":str(course_id),"employee_user_id":employee,"status":"pending"}
    async def public_questions(self,assignment_id,user_id):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT course_id FROM training_assignments WHERE id=%s AND employee_user_id=%s",(assignment_id,user_id)); row=await cur.fetchone()
                if not row:raise PermissionError("FORBIDDEN")
                await cur.execute("SELECT tq.id,tq.question_id,tq.stem,tq.evidence_json,tq.requires_confirmation FROM training_questions tq WHERE tq.course_id=%s ORDER BY tq.id",(row[0],)); qs=await cur.fetchall(); result=[]
                for pk,qid,stem,evidence,risk in qs:
                    await cur.execute("SELECT option_key,option_text FROM question_options WHERE question_id=%s ORDER BY id",(pk,)); opts=await cur.fetchall(); result.append({"id":qid,"stem":stem,"options":[{"key":x[0],"text":x[1]} for x in opts],"evidence":json.loads(evidence),"requires_confirmation":bool(risk)})
                await cur.execute("UPDATE training_assignments SET status='in_progress' WHERE id=%s AND status='pending'",(assignment_id,));return result
    async def submit(self,assignment_id,user_id,answers):
        async with self._pool().acquire() as conn:
            await conn.begin()
            try:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT store_id,course_id,status FROM training_assignments WHERE id=%s AND employee_user_id=%s FOR UPDATE",(assignment_id,user_id)); a=await cur.fetchone()
                    if not a:raise PermissionError("FORBIDDEN")
                    if a[2]=="completed":
                        await cur.execute("SELECT tr.report_json FROM training_reports tr JOIN answer_attempts aa ON aa.id=tr.attempt_id WHERE aa.assignment_id=%s AND aa.employee_user_id=%s ORDER BY tr.id DESC LIMIT 1",(assignment_id,user_id)); existing=await cur.fetchone()
                        if not existing:raise ValueError("ASSIGNMENT_NOT_COMPLETED")
                        await conn.rollback();return json.loads(existing[0])
                    await cur.execute("SELECT id,question_id,answer_json,explanation,evidence_json FROM training_questions WHERE course_id=%s",(a[1],)); qs=await cur.fetchall(); supplied={x.question_id:set(x.selected_answers) for x in answers}; results={q[1]:supplied.get(q[1],set())==set(json.loads(q[2])) for q in qs}; score=round(sum(results.values())*100/len(qs)) if qs else 0
                    await cur.execute("INSERT INTO answer_attempts(assignment_id,store_id,employee_user_id,status,score,submitted_at) VALUES(%s,%s,%s,'completed',%s,NOW())",(assignment_id,a[0],user_id,score)); attempt=cur.lastrowid
                    for item in answers:
                        q=next((x for x in qs if x[1]==item.question_id),None)
                        if q:await cur.execute("INSERT INTO training_answer_records(attempt_id,question_id,selected_json,is_correct,duration_ms) VALUES(%s,%s,%s,%s,%s)",(attempt,q[0],json.dumps(item.selected_answers),results[q[1]],item.duration_ms))
                    report={"score":score,"correct_count":sum(results.values()),"total_count":len(qs),"answer_results":results,"questions":[{"id":q[1],"answer":json.loads(q[2]),"explanation":q[3],"evidence":json.loads(q[4])} for q in qs],"certification_notice":"本结果仅用于在线学习，不等同于实操上岗认证。"}; await cur.execute("INSERT INTO training_reports(attempt_id,store_id,report_json) VALUES(%s,%s,%s)",(attempt,a[0],json.dumps(report,ensure_ascii=False))); await cur.execute("UPDATE training_assignments SET status='completed',completed_at=NOW() WHERE id=%s",(assignment_id,))
                await conn.commit();return report
            except Exception:await conn.rollback();raise
    async def report(self,assignment_id,user_id):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT tr.report_json FROM training_reports tr JOIN answer_attempts aa ON aa.id=tr.attempt_id WHERE aa.assignment_id=%s AND aa.employee_user_id=%s",(assignment_id,user_id)); row=await cur.fetchone()
                if not row:raise ValueError("ASSIGNMENT_NOT_COMPLETED")
                return json.loads(row[0])
    async def store_results(self,store_id,actor):
        async with self._pool().acquire() as conn:
            async with conn.cursor() as cur:
                await self._role(cur,store_id,actor,{"owner","manager"})
                await cur.execute("SELECT ta.id,ta.employee_user_id,ta.course_id,ta.status,aa.score FROM training_assignments ta LEFT JOIN answer_attempts aa ON aa.assignment_id=ta.id AND aa.status='completed' WHERE ta.store_id=%s ORDER BY ta.id DESC",(store_id,));rows=await cur.fetchall()
        return [{"assignment_id":str(x[0]),"employee_user_id":x[1],"course_id":str(x[2]),"status":x[3],"score":x[4]} for x in rows]

mysql_platform_repository=MySQLPlatformRepository()
