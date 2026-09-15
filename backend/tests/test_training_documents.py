import io, zipfile
import app.services.training_document_service as document_service
from fastapi.testclient import TestClient
from app.main import app


def make_docx(text: str) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", f'<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>')
    return out.getvalue()


def test_docx_upload_and_offsets():
    with TestClient(app) as client:
        response = client.post("/api/v1/training/documents", files={"file": ("manual.docx", make_docx("开店前必须检查设备并在记录表上签字确认。"), "application/octet-stream")})
        assert response.json()["code"] == 0
        doc_id = response.json()["data"]["document_id"]
        detail = client.get(f"/api/v1/training/documents/{doc_id}").json()["data"]
    assert detail["status"] == "ready"
    assert detail["blocks"][0]["text"] in detail["content"]


def test_document_generate_edit_and_approve_flow():
    text="开店前必须检查设备并在记录表上签字确认，未签字不得开始营业。"
    with TestClient(app) as client:
        uploaded=client.post("/api/v1/training/documents",files={"file":("manual.docx",make_docx(text),"application/octet-stream")}).json()["data"]
        made=client.post(f"/api/v1/training/documents/{uploaded['document_id']}/generate",json={"title":"开店","question_count":3}).json()
        assert made["code"]==0; quiz_id=made["data"]["quiz_id"]
        draft=client.get(f"/api/v1/training/drafts/{quiz_id}").json()["data"]
        assert draft["questions"][0]["evidence"]["document_id"]==uploaded["document_id"]
        edited=client.put(f"/api/v1/training/drafts/{quiz_id}/questions/q1",json={"stem":"修改后的题干"}).json()["data"]
        assert edited["questions"][0]["stem"]=="修改后的题干"
        deleted=client.delete(f"/api/v1/training/drafts/{quiz_id}/questions/q3").json()["data"]
        assert len(deleted["questions"])==2
        assert client.post(f"/api/v1/training/drafts/{quiz_id}/approve").json()["data"]["status"]=="approved"


def test_rejects_fake_pdf():
    with TestClient(app) as client:
        body = client.post("/api/v1/training/documents", files={"file": ("x.pdf", b"not pdf", "application/pdf")}).json()
    assert body["code"] == 4002


def test_rejects_docx_expansion_bomb(monkeypatch):
    monkeypatch.setattr(document_service, "MAX_DOCX_UNCOMPRESSED_BYTES", 1)
    with TestClient(app) as client:
        body = client.post("/api/v1/training/documents", files={"file": ("x.docx", make_docx("足够长的培训规则内容，员工必须严格执行并报告异常。"), "application/octet-stream")}).json()
    assert body["code"] == 4002
    assert body["message"] == "DOCX_EXPANSION_TOO_LARGE"


def test_deleted_document_cannot_be_read_or_generated():
    text = "开店前必须检查设备并在记录表上签字确认，发现异常必须立即报告负责人。"
    with TestClient(app) as client:
        uploaded = client.post("/api/v1/training/documents", files={"file": ("manual.docx", make_docx(text), "application/octet-stream")}).json()["data"]
        document_id = uploaded["document_id"]
        assert client.delete(f"/api/v1/training/documents/{document_id}").json()["code"] == 0
        assert client.get(f"/api/v1/training/documents/{document_id}").json()["code"] == 4041
        assert client.post(f"/api/v1/training/documents/{document_id}/generate", json={"question_count": 3}).json()["code"] == 4041


def test_deleted_document_blocks_existing_draft_approval():
    text = "开店前必须检查设备并在记录表上签字确认，未签字不得开始营业。"
    with TestClient(app) as client:
        document_id = client.post("/api/v1/training/documents", files={"file": ("manual.docx", make_docx(text), "application/octet-stream")}).json()["data"]["document_id"]
        quiz_id = client.post(f"/api/v1/training/documents/{document_id}/generate", json={"question_count": 3}).json()["data"]["quiz_id"]
        client.delete(f"/api/v1/training/documents/{document_id}")
        assert client.post(f"/api/v1/training/drafts/{quiz_id}/approve").json()["code"] == 4005
