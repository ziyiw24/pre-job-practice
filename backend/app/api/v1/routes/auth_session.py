from fastapi import APIRouter, Depends

from app.api.v1.routes.platform import call
from app.core.auth import create_token, get_current_user
from app.core.config import get_settings
from app.models.common import ApiResponse
from app.models.platform import DevLoginRequest
from app.services import platform_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/session", response_model=ApiResponse)
async def session(user_id: int = Depends(get_current_user)):
    memberships = await call("memberships", user_id)
    if memberships.code != 0:
        return memberships
    rows = memberships.data or []
    active = next((x for x in rows if x["role"] in {"owner", "manager"}), rows[0] if rows else None)
    return ApiResponse.success({"user_id": user_id, "memberships": rows, "active_membership": active})


@router.post("/dev-login", response_model=ApiResponse)
async def dev_login(req: DevLoginRequest):
    if get_settings().app_environment == "production":
        return ApiResponse.error(4030, "生产环境禁止模拟登录")
    user_id = 9001 if req.role == "manager" else 9002
    role = "manager" if req.role == "manager" else "employee"
    platform_service.ensure_demo_membership(user_id, role)
    return ApiResponse.success({
        "token": create_token(user_id, f"dev-{role}"),
        "user": {"id": user_id, "nickname": "演示店长" if role == "manager" else "演示员工", "avatar_url": "", "total_xp": 0},
        "membership": {"store_id": "store_demo", "store_name": "上岗练演示门店", "role": role},
    })
