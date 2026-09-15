import uuid
from typing import Literal
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from app.core.auth import get_current_user
from app.core.config import get_settings
from app.core.db import get_mysql_pool
from app.models.common import ApiResponse

router=APIRouter(prefix="/privacy",tags=["privacy"]);_requests=[]
class PrivacyRequest(BaseModel):
    request_type:Literal["complaint","delete_account","delete_document"]
    resource_id:str|None=Field(default=None,max_length=64)
    detail:str=Field(default="",max_length=1000)

@router.post("/requests",response_model=ApiResponse)
async def create_privacy_request(req:PrivacyRequest,user_id:int=Depends(get_current_user)):
    request_id=f"privacy_{uuid.uuid4().hex[:12]}"
    if get_settings().platform_store=="mysql":
        pool=get_mysql_pool()
        if pool is None:return ApiResponse.error(5030,"数据库暂不可用")
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("INSERT INTO privacy_requests(user_id,request_type,resource_id,detail) VALUES(%s,%s,%s,%s)",(user_id,req.request_type,req.resource_id,req.detail));request_id=str(cur.lastrowid)
    else:_requests.append({"id":request_id,"user_id":user_id,**req.model_dump()})
    return ApiResponse.success({"request_id":request_id,"status":"pending"})
