from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.core.auth import get_optional_user
from app.models.common import ApiResponse
from app.models.training_document import DocumentGenerateRequest, DraftQuestionUpdate, TrainingDocument, TrainingDraft
from app.services.training_document_service import approve_draft, create_draft, delete_draft_question, get_document, get_draft, parse_document, restore_document, restore_draft, update_draft_question
from app.core.config import get_settings

router = APIRouter(prefix="/training/documents", tags=["training-documents"])

async def _cache_put(kind: str, key: str, value: str):
    settings=get_settings()
    if settings.training_task_store=="redis":
        from redis.asyncio import from_url
        client=from_url(settings.redis_url,decode_responses=True); await client.set(f"training:{kind}:{key}",value,ex=86400); await client.aclose()

async def _load_document(document_id: str):
    doc=get_document(document_id)
    if doc:return doc
    settings=get_settings()
    if settings.training_task_store=="redis":
        from redis.asyncio import from_url
        client=from_url(settings.redis_url,decode_responses=True); raw=await client.get(f"training:document:{document_id}"); await client.aclose()
        if raw:doc=TrainingDocument.model_validate_json(raw);restore_document(doc);return doc
    if settings.platform_store=="mysql":
        from app.repositories.training_document_repository import load_document
        doc=await load_document(document_id)
        if doc:
            restore_document(doc);await _cache_put("document",document_id,doc.model_dump_json());return doc
    return None

async def _load_draft(quiz_id: str):
    draft=get_draft(quiz_id)
    if draft:return draft
    settings=get_settings()
    if settings.training_task_store=="redis":
        from redis.asyncio import from_url
        client=from_url(settings.redis_url,decode_responses=True); raw=await client.get(f"training:draft:{quiz_id}"); await client.aclose()
        if raw:draft=TrainingDraft.model_validate_json(raw);restore_draft(draft);return draft
    return None

async def _authorize(store_id: str | None, user_id: int | None):
    settings=get_settings()
    if settings.app_environment != "production":return
    if not store_id or user_id is None:raise PermissionError("FORBIDDEN")
    from app.repositories.training_document_repository import require_store_role
    await require_store_role(store_id,user_id,{"owner","manager"})


@router.post("", response_model=ApiResponse)
async def upload_document(file: UploadFile = File(...), store_id: str = Form(""), user_id: int | None = Depends(get_optional_user)):
    data = await file.read()
    try: doc = parse_document(file.filename or "document", data)
    except ValueError as exc: return ApiResponse.error(4002, str(exc))
    settings = get_settings()
    try: await _authorize(store_id or None,user_id)
    except PermissionError:return ApiResponse.error(4030,"无权上传到该门店")
    doc.store_id=store_id or None;doc.owner_user_id=user_id
    if settings.training_document_store == "cos":
        from app.services.cos_service import upload_private_bytes
        suffix = ".pdf" if doc.file_name.lower().endswith(".pdf") else ".docx"
        doc.storage_key = await upload_private_bytes(data, f"{settings.training_upload_prefix}{doc.document_id}{suffix}", file.content_type or "application/octet-stream")
    if settings.platform_store=="mysql":
        from app.repositories.training_document_repository import save_document
        await save_document(doc)
    await _cache_put("document",doc.document_id,doc.model_dump_json())
    return ApiResponse.success(doc.model_dump(exclude={"content", "blocks"}))


@router.get("/{document_id}", response_model=ApiResponse)
async def document_status(document_id: str, user_id: int | None = Depends(get_optional_user)):
    doc = await _load_document(document_id)
    try: await _authorize(doc.store_id if doc else None,user_id)
    except PermissionError:return ApiResponse.error(4030,"无权访问该文档")
    return ApiResponse.success(doc.model_dump()) if doc and not doc.deleted else ApiResponse.error(4041, "文档不存在")

@router.delete("/{document_id}",response_model=ApiResponse)
async def delete_document(document_id:str,user_id:int|None=Depends(get_optional_user)):
    doc=await _load_document(document_id)
    if not doc or doc.deleted:return ApiResponse.error(4041,"文档不存在")
    try:await _authorize(doc.store_id,user_id)
    except PermissionError:return ApiResponse.error(4030,"无权删除该文档")
    doc.deleted=True;await _cache_put("document",doc.document_id,doc.model_dump_json())
    if get_settings().platform_store=="mysql":
        from app.repositories.training_document_repository import soft_delete
        await soft_delete(doc.document_id,doc.store_id or "",user_id or 0)
    return ApiResponse.success({"document_id":document_id,"deleted":True,"storage_cleanup":"scheduled"})


@router.post("/{document_id}/generate", response_model=ApiResponse)
async def generate_from_document(document_id: str, req: DocumentGenerateRequest, user_id: int | None = Depends(get_optional_user)):
    doc=await _load_document(document_id)
    if not doc or doc.deleted:return ApiResponse.error(4041,"文档不存在")
    try:await _authorize(doc.store_id if doc else None,user_id)
    except PermissionError:return ApiResponse.error(4030,"无权使用该文档")
    try: draft = create_draft(document_id, req.title, req.question_count, req.difficulty)
    except ValueError as exc: return ApiResponse.error(4003, str(exc))
    await _cache_put("draft",draft.quiz_id,draft.model_dump_json())
    return ApiResponse.success({"quiz_id": draft.quiz_id, "status": draft.status})


draft_router = APIRouter(prefix="/training/drafts", tags=["training-drafts"])


@draft_router.get("/{quiz_id}", response_model=ApiResponse)
async def draft_detail(quiz_id: str, user_id: int | None = Depends(get_optional_user)):
    draft = await _load_draft(quiz_id)
    try:await _authorize(draft.store_id if draft else None,user_id)
    except PermissionError:return ApiResponse.error(4030,"无权访问该草稿")
    return ApiResponse.success(draft.model_dump()) if draft else ApiResponse.error(4042, "草稿不存在")


@draft_router.put("/{quiz_id}/questions/{question_id}", response_model=ApiResponse)
async def edit_question(quiz_id: str, question_id: str, req: DraftQuestionUpdate, user_id: int | None = Depends(get_optional_user)):
    loaded=await _load_draft(quiz_id)
    try:await _authorize(loaded.store_id if loaded else None,user_id)
    except PermissionError:return ApiResponse.error(4030,"无权编辑该草稿")
    try: draft = update_draft_question(quiz_id, question_id, req)
    except ValueError as exc: return ApiResponse.error(4004, str(exc))
    await _cache_put("draft",draft.quiz_id,draft.model_dump_json())
    return ApiResponse.success(draft.model_dump())

@draft_router.delete("/{quiz_id}/questions/{question_id}",response_model=ApiResponse)
async def delete_question(quiz_id:str,question_id:str,user_id:int|None=Depends(get_optional_user)):
    loaded=await _load_draft(quiz_id)
    try:await _authorize(loaded.store_id if loaded else None,user_id)
    except PermissionError:return ApiResponse.error(4030,"无权编辑该草稿")
    try:draft=delete_draft_question(quiz_id,question_id)
    except ValueError as exc:return ApiResponse.error(4004,str(exc))
    await _cache_put("draft",draft.quiz_id,draft.model_dump_json());return ApiResponse.success(draft.model_dump())


@draft_router.post("/{quiz_id}/approve", response_model=ApiResponse)
async def approve(quiz_id: str, user_id: int | None = Depends(get_optional_user)):
    loaded=await _load_draft(quiz_id)
    if loaded:await _load_document(loaded.document_id)
    try:await _authorize(loaded.store_id if loaded else None,user_id)
    except PermissionError:return ApiResponse.error(4030,"无权审核该草稿")
    try: draft = approve_draft(quiz_id)
    except ValueError as exc: return ApiResponse.error(4005, str(exc))
    await _cache_put("draft",draft.quiz_id,draft.model_dump_json())
    return ApiResponse.success(draft.model_dump())
