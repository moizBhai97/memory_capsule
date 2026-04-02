"""
Capsule CRUD + file upload endpoints.
"""

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse

from api.middleware.auth import verify_api_key
from api.state import get_pipeline, get_sqlite
from capsule.models import CapsuleStatus, SourceApp

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source_app: str = Form(default="api"),
    source_sender: str | None = Form(default=None),
    source_chat: str | None = Form(default=None),
):
    """
    Upload any file (audio, image, PDF, text).
    Processing happens in background — returns capsule ID immediately.
    Poll GET /capsules/{id} to check status.
    """
    pipeline = get_pipeline()

    # Save uploaded file to temp location
    suffix = Path(file.filename).suffix if file.filename else ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        source_app_enum = SourceApp(source_app)
    except ValueError:
        source_app_enum = SourceApp.API

    async def _process():
        try:
            await pipeline.process_file(
                file_path=tmp_path,
                source_app=source_app_enum,
                source_sender=source_sender,
                source_chat=source_chat,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    background_tasks.add_task(_process)

    return JSONResponse(
        status_code=202,
        content={
            "message": "File received. Processing in background.",
            "status": "processing",
        },
    )


@router.post("")
async def create_text_capsule(
    background_tasks: BackgroundTasks,
    body: dict,
):
    """
    Create a capsule from text, URL, or structured data.

    Body:
    {
        "text": "...",           # required (or url)
        "url": "https://...",    # optional
        "source_app": "api",
        "source_sender": "Ahmed",
        "source_chat": "Project Group",
        "metadata": {}
    }
    """
    pipeline = get_pipeline()

    text = body.get("text", "")
    url = body.get("url")
    source_app = body.get("source_app", "api")
    source_sender = body.get("source_sender")
    source_chat = body.get("source_chat")
    metadata = body.get("metadata", {})

    if not text and not url:
        raise HTTPException(status_code=400, detail="Either 'text' or 'url' is required")

    try:
        source_app_enum = SourceApp(source_app)
    except ValueError:
        source_app_enum = SourceApp.API

    async def _process():
        await pipeline.process_text(
            text=text,
            source_app=source_app_enum,
            source_sender=source_sender,
            source_chat=source_chat,
            source_url=url,
            metadata=metadata,
        )

    background_tasks.add_task(_process)

    return JSONResponse(
        status_code=202,
        content={"message": "Content received. Processing in background."},
    )


@router.get("/{capsule_id}")
async def get_capsule(capsule_id: str):
    sqlite = get_sqlite()
    capsule = sqlite.get(capsule_id)
    if not capsule:
        raise HTTPException(status_code=404, detail="Capsule not found")
    return capsule.to_dict()


@router.get("")
async def list_capsules(
    limit: int = 50,
    offset: int = 0,
    source_app: str | None = None,
    source_type: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    sqlite = get_sqlite()
    capsules = sqlite.list(
        limit=limit,
        offset=offset,
        source_app=source_app,
        source_type=source_type,
        from_date=from_date,
        to_date=to_date,
    )
    return {
        "capsules": [c.to_dict() for c in capsules],
        "count": len(capsules),
        "total": sqlite.count(),
    }
