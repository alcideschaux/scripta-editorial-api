import os
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from ojs_client import OJSClient, OJSError


app = FastAPI(
    title="Scripta Scientia Editorial API",
    description="Capa editorial propia para consultar y organizar envíos de OJS.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def require_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    expected = os.environ.get("EDITORIAL_API_KEY", "").strip()
    if not expected:
        return
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="API key inválida o ausente.")


def client() -> OJSClient:
    try:
        return OJSClient()
    except KeyError as exc:
        raise HTTPException(status_code=500, detail=f"Variable de entorno faltante: {exc}")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "service": "scripta-editorial-api"}


@app.get("/ojs/health", dependencies=[Depends(require_api_key)])
async def ojs_health(ojs: OJSClient = Depends(client)) -> Dict[str, Any]:
    try:
        data = await ojs.get("contexts")
        return {
            "status": "ok",
            "ojs_base_url": ojs.base_url,
            "contexts_found": data.get("itemsMax"),
        }
    except OJSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/submissions", dependencies=[Depends(require_api_key)])
async def submissions(
    count: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    stageId: Optional[int] = Query(default=None),
    status: Optional[int] = Query(default=None),
    ojs: OJSClient = Depends(client),
) -> Dict[str, Any]:
    try:
        data = await ojs.summarized_submissions(count=count, offset=offset)
    except OJSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    items = data["items"]
    if stageId is not None:
        items = [item for item in items if item.get("stageId") == stageId]
    if status is not None:
        items = [item for item in items if item.get("status") == status]

    return {
        "itemsMax": data["itemsMax"],
        "count": len(items),
        "items": items,
    }


@app.get("/submissions/queue", dependencies=[Depends(require_api_key)])
async def submissions_queue(ojs: OJSClient = Depends(client)) -> Dict[str, Any]:
    return await submissions(stageId=1, ojs=ojs)


@app.get("/submissions/review", dependencies=[Depends(require_api_key)])
async def submissions_review(ojs: OJSClient = Depends(client)) -> Dict[str, Any]:
    return await submissions(stageId=3, ojs=ojs)


@app.get("/submissions/editing", dependencies=[Depends(require_api_key)])
async def submissions_editing(ojs: OJSClient = Depends(client)) -> Dict[str, Any]:
    return await submissions(stageId=4, ojs=ojs)


@app.get("/submissions/published", dependencies=[Depends(require_api_key)])
async def submissions_published(ojs: OJSClient = Depends(client)) -> Dict[str, Any]:
    return await submissions(status=3, ojs=ojs)


@app.get("/submissions/{submission_id}", dependencies=[Depends(require_api_key)])
async def submission_detail(submission_id: int, ojs: OJSClient = Depends(client)) -> Dict[str, Any]:
    try:
        raw = await ojs.get_submission(submission_id)
        summary = ojs.summarize_submission(raw)
        return {"summary": summary, "raw": raw}
    except OJSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/submissions/{submission_id}/files", dependencies=[Depends(require_api_key)])
async def submission_files(submission_id: int, ojs: OJSClient = Depends(client)) -> Dict[str, Any]:
    try:
        return await ojs.get_submission_files(submission_id)
    except OJSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/dashboard", dependencies=[Depends(require_api_key)])
async def dashboard(ojs: OJSClient = Depends(client)) -> Dict[str, Any]:
    try:
        data = await ojs.summarized_submissions(count=200)
    except OJSError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    items = data["items"]
    by_stage: Dict[str, int] = {}
    by_status: Dict[str, int] = {}

    for item in items:
        by_stage[item["stage"]] = by_stage.get(item["stage"], 0) + 1
        label = item.get("statusLabel") or str(item.get("status"))
        by_status[label] = by_status.get(label, 0) + 1

    active = [item for item in items if item.get("status") != 3]
    published = [item for item in items if item.get("status") == 3]

    return {
        "total": data["itemsMax"],
        "loaded": len(items),
        "active_count": len(active),
        "published_count": len(published),
        "by_stage": by_stage,
        "by_status": by_status,
        "recent_active": active[:10],
    }
