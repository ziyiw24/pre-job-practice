"""生产文档元数据与 block 持久化；原文文件保存在私有 COS。"""
from __future__ import annotations
import hashlib
from app.core.db import get_mysql_pool
from app.models.training_document import DocumentBlock, TrainingDocument

def _pool():
    pool=get_mysql_pool()
    if pool is None:raise RuntimeError("DATABASE_UNAVAILABLE")
    return pool

async def require_store_role(store_id: str, user_id: int, allowed: set[str]):
    async with _pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT role FROM store_members WHERE store_id=%s AND user_id=%s",(store_id,user_id)); row=await cur.fetchone()
    if not row or row[0] not in allowed:raise PermissionError("FORBIDDEN")

async def save_document(doc: TrainingDocument):
    if not doc.store_id or not doc.storage_key:raise ValueError("DOCUMENT_TENANT_REQUIRED")
    async with _pool().acquire() as conn:
        await conn.begin()
        try:
            async with conn.cursor() as cur:
                await cur.execute("INSERT INTO documents(document_id,store_id,file_name,storage_key,status,content_hash) VALUES(%s,%s,%s,%s,%s,%s)",(doc.document_id,doc.store_id,doc.file_name,doc.storage_key,doc.status,hashlib.sha256(doc.content.encode()).hexdigest())); pk=cur.lastrowid
                for b in doc.blocks:await cur.execute("INSERT INTO document_blocks(document_id,block_id,page_number,paragraph_index,text,start_offset,end_offset) VALUES(%s,%s,%s,%s,%s,%s,%s)",(pk,b.block_id,b.page_number,b.paragraph_index,b.text,b.start_offset,b.end_offset))
            await conn.commit()
        except Exception:await conn.rollback();raise

async def load_document(document_id: str) -> TrainingDocument | None:
    """Redis/进程缓存失效时，从权威 MySQL 元数据与 block 恢复。"""
    async with _pool().acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT id,document_id,store_id,file_name,storage_key,status,deleted_at "
                "FROM documents WHERE document_id=%s", (document_id,),
            )
            row = await cur.fetchone()
            if not row:
                return None
            await cur.execute(
                "SELECT block_id,page_number,paragraph_index,text,start_offset,end_offset "
                "FROM document_blocks WHERE document_id=%s ORDER BY paragraph_index,id", (row[0],),
            )
            blocks = [DocumentBlock(block_id=x[0], page_number=x[1], paragraph_index=x[2],
                                    text=x[3], start_offset=x[4], end_offset=x[5])
                      for x in await cur.fetchall()]
    return TrainingDocument(
        document_id=row[1], store_id=str(row[2]), file_name=row[3], storage_key=row[4],
        status=row[5], deleted=row[6] is not None, blocks=blocks,
        content="\n".join(block.text for block in blocks),
    )

async def soft_delete(document_id: str, store_id: str, user_id: int):
    await require_store_role(store_id,user_id,{"owner","manager"})
    async with _pool().acquire() as conn:
        async with conn.cursor() as cur:await cur.execute("UPDATE documents SET deleted_at=NOW() WHERE document_id=%s AND store_id=%s",(document_id,store_id))
