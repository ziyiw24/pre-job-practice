from __future__ import annotations
import io, re, uuid, zipfile
from pathlib import Path
import docx2txt
from pypdf import PdfReader
from app.models.training_document import DocumentBlock, DraftQuestionUpdate, TrainingDocument, TrainingDraft
from app.models.training import TrainingGenerateRequest, TrainingQuestion

MAX_BYTES = 10 * 1024 * 1024
MAX_PAGES = 50
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_DOCX_ENTRIES = 2000
_documents: dict[str, TrainingDocument] = {}
_drafts: dict[str, TrainingDraft] = {}


def _safe_name(name: str) -> str:
    return re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", Path(name).name)[:120]


def parse_document(file_name: str, data: bytes) -> TrainingDocument:
    if len(data) > MAX_BYTES: raise ValueError("FILE_TOO_LARGE")
    suffix = Path(file_name).suffix.lower()
    if suffix not in {".pdf", ".docx"}: raise ValueError("UNSUPPORTED_FILE_TYPE")
    document_id = f"doc_{uuid.uuid4().hex[:12]}"; blocks = []; offset = 0
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"): raise ValueError("INVALID_FILE_SIGNATURE")
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted: raise ValueError("ENCRYPTED_PDF")
        if len(reader.pages) > MAX_PAGES: raise ValueError("TOO_MANY_PAGES")
        parts = [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    else:
        if not zipfile.is_zipfile(io.BytesIO(data)): raise ValueError("INVALID_FILE_SIGNATURE")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_DOCX_ENTRIES or sum(item.file_size for item in infos) > MAX_DOCX_UNCOMPRESSED_BYTES:
                raise ValueError("DOCX_EXPANSION_TOO_LARGE")
        temp = Path("/tmp") / f"{document_id}.docx"; temp.write_bytes(data)
        try: text = docx2txt.process(str(temp)) or ""
        finally: temp.unlink(missing_ok=True)
        parts = [(None, text)]
    for page, text in parts:
        for paragraph in [x.strip() for x in text.splitlines() if x.strip()]:
            start = offset; offset += len(paragraph)
            blocks.append(DocumentBlock(block_id=f"b{len(blocks)+1}", page_number=page, paragraph_index=len(blocks), text=paragraph, start_offset=start, end_offset=offset))
            offset += 1
    content = "\n".join(x.text for x in blocks)
    if len(content.strip()) < 20: raise ValueError("NO_EXTRACTABLE_TEXT")
    doc = TrainingDocument(document_id=document_id, file_name=_safe_name(file_name), status="ready", blocks=blocks, content=content)
    _documents[document_id] = doc
    return doc


def get_document(document_id: str): return _documents.get(document_id)
def restore_document(doc: TrainingDocument): _documents[doc.document_id] = doc


def create_draft(document_id: str, title: str, question_count: int, difficulty: str) -> TrainingDraft:
    from app.services.training_service import _make_demo_quiz
    doc = _documents.get(document_id)
    if not doc or doc.status != "ready": raise ValueError("DOCUMENT_NOT_READY")
    quiz = _make_demo_quiz(TrainingGenerateRequest.model_construct(client_request_id=f"document_{uuid.uuid4().hex}", title=title, content=doc.content[:8000], question_count=question_count, difficulty=difficulty))
    # 服务端根据 block 重新定位页码，不信任模型页码。
    for q in quiz.questions:
        for block in doc.blocks:
            local = block.text.find(q.evidence.quote)
            if local >= 0:
                q.evidence.document_id = document_id; q.evidence.block_id = block.block_id; q.evidence.page_number = block.page_number
                q.evidence.start_offset = block.start_offset + local; q.evidence.end_offset = q.evidence.start_offset + len(q.evidence.quote)
                break
    draft = TrainingDraft(quiz_id=quiz.quiz_id, document_id=document_id, store_id=doc.store_id, status="awaiting_review", questions=[q.model_dump() for q in quiz.questions])
    _drafts[draft.quiz_id] = draft
    return draft


def get_draft(quiz_id: str): return _drafts.get(quiz_id)
def restore_draft(draft: TrainingDraft): _drafts[draft.quiz_id] = draft


def update_draft_question(quiz_id: str, question_id: str, change: DraftQuestionUpdate) -> TrainingDraft:
    draft = _drafts.get(quiz_id)
    if not draft or draft.status not in {"draft", "awaiting_review"}: raise ValueError("DRAFT_NOT_EDITABLE")
    question = next((q for q in draft.questions if q["id"] == question_id), None)
    if not question: raise ValueError("QUESTION_NOT_FOUND")
    values = change.model_dump(exclude_none=True); confirmed = values.pop("confirmed", None)
    question.update(values)
    if confirmed is True and question_id not in draft.confirmed_question_ids: draft.confirmed_question_ids.append(question_id)
    if confirmed is False and question_id in draft.confirmed_question_ids: draft.confirmed_question_ids.remove(question_id)
    return draft

def delete_draft_question(quiz_id:str,question_id:str)->TrainingDraft:
    draft=_drafts.get(quiz_id)
    if not draft or draft.status not in {"draft","awaiting_review"}:raise ValueError("DRAFT_NOT_EDITABLE")
    before=len(draft.questions);draft.questions=[q for q in draft.questions if q["id"]!=question_id]
    if len(draft.questions)==before:raise ValueError("QUESTION_NOT_FOUND")
    if question_id in draft.confirmed_question_ids:draft.confirmed_question_ids.remove(question_id)
    return draft


def approve_draft(quiz_id: str) -> TrainingDraft:
    draft = _drafts.get(quiz_id)
    if not draft: raise ValueError("DRAFT_NOT_FOUND")
    if not draft.questions:raise ValueError("DRAFT_HAS_NO_QUESTIONS")
    doc=_documents.get(draft.document_id)
    if not doc or doc.deleted:raise ValueError("DOCUMENT_NOT_READY")
    try:validated=[TrainingQuestion.model_validate(q) for q in draft.questions]
    except Exception as exc:raise ValueError("QUESTION_SCHEMA_INVALID") from exc
    if doc and any(q.evidence.quote not in doc.content for q in validated):raise ValueError("EVIDENCE_MISSING")
    required = {q["id"] for q in draft.questions if q.get("requires_confirmation")}
    if not required.issubset(set(draft.confirmed_question_ids)): raise ValueError("HIGH_RISK_CONFIRMATION_REQUIRED")
    draft.status = "approved"
    return draft
