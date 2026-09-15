from fastapi import APIRouter, Depends
from app.core.auth import get_current_user
from app.models.common import ApiResponse
from app.models.platform import AssignmentCreate, AssignmentSubmit, CourseCreate, MemberCreate, StoreCreate
from app.services import platform_service as svc
from app.core.config import get_settings
from app.repositories.mysql_platform_repository import mysql_platform_repository
import inspect

router=APIRouter(tags=["training-platform"])
def backend():return mysql_platform_repository if get_settings().platform_store=="mysql" else svc
async def call(name,*args):
    try:
        value=getattr(backend(),name)(*args)
        return ApiResponse.success(await value if inspect.isawaitable(value) else value)
    except PermissionError:return ApiResponse.error(4030,"无权访问该门店资源")
    except (ValueError,KeyError) as exc:return ApiResponse.error(4006,str(exc).strip("'"))
@router.post("/stores")
async def store(req:StoreCreate,user_id:int=Depends(get_current_user)):return await call("create_store",user_id,req.name)
@router.post("/stores/{store_id}/members")
async def member(store_id:str,req:MemberCreate,user_id:int=Depends(get_current_user)):return await call("add_member",store_id,user_id,req.user_id,req.role)
@router.post("/stores/{store_id}/courses")
async def course(store_id:str,req:CourseCreate,user_id:int=Depends(get_current_user)):return await call("create_course",store_id,user_id,req)
@router.post("/courses/{course_id}/publish")
async def publish(course_id:str,user_id:int=Depends(get_current_user)):return await call("publish_course",course_id,user_id)
@router.post("/courses/{course_id}/assignments")
async def assign(course_id:str,req:AssignmentCreate,user_id:int=Depends(get_current_user)):return await call("assign",course_id,user_id,req.employee_user_id)
@router.get("/employee/assignments/{assignment_id}/questions")
async def questions(assignment_id:str,user_id:int=Depends(get_current_user)):return await call("public_questions",assignment_id,user_id)
@router.post("/employee/assignments/{assignment_id}/answers")
async def answers(assignment_id:str,req:AssignmentSubmit,user_id:int=Depends(get_current_user)):return await call("submit",assignment_id,user_id,req.answers)
@router.get("/employee/assignments/{assignment_id}/report")
async def assignment_report(assignment_id:str,user_id:int=Depends(get_current_user)):return await call("report",assignment_id,user_id)
@router.get("/stores/{store_id}/results")
async def store_results(store_id:str,user_id:int=Depends(get_current_user)):return await call("store_results",store_id,user_id)
