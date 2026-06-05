import os
import re
from typing import Any, Dict, List, Optional

import httpx


class OJSError(Exception):
    pass


def clean_text(value: Any) -> str:
    """Normalize OJS multilingual fields and remove embedded HTML comments."""
    if value is None:
        return ""
    if isinstance(value, dict):
        value = value.get("es") or value.get("en") or next((v for v in value.values() if v), "")
    text = str(value)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return " ".join(text.split()).strip()


def stage_label(stage_id: Optional[int]) -> str:
    return {
        1: "Envío",
        2: "Revisión interna",
        3: "Revisión",
        4: "Edición",
        5: "Producción / Publicado",
    }.get(stage_id, f"Etapa desconocida ({stage_id})")


class OJSClient:
    def __init__(self) -> None:
        self.base_url = os.environ["OJS_BASE_URL"].rstrip("/")
        self.token = os.environ.get("OJS_API_TOKEN", "").strip()
        self.timeout = float(os.environ.get("REQUEST_TIMEOUT_SECONDS", "30"))

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=self._headers(), params=params)
        if response.status_code >= 400:
            raise OJSError(f"OJS respondió {response.status_code}: {response.text[:500]}")
        return response.json()

    async def list_submissions(self, count: int = 100, offset: int = 0) -> Dict[str, Any]:
        return await self.get("submissions", {"count": count, "offset": offset})

    async def get_submission(self, submission_id: int) -> Dict[str, Any]:
        return await self.get(f"submissions/{submission_id}")

    async def get_submission_files(self, submission_id: int) -> Dict[str, Any]:
        return await self.get(f"submissions/{submission_id}/files", {"count": 100})

    @staticmethod
    def summarize_submission(item: Dict[str, Any]) -> Dict[str, Any]:
        publications = item.get("publications") or []
        pub = publications[0] if publications else {}

        title = clean_text(pub.get("fullTitle") or pub.get("title"))
        authors = clean_text(pub.get("authorsString"))
        doi_obj = pub.get("doiObject") or {}

        return {
            "id": item.get("id"),
            "title": title,
            "authors": authors,
            "stageId": item.get("stageId"),
            "stage": stage_label(item.get("stageId")),
            "status": item.get("status"),
            "statusLabel": item.get("statusLabel"),
            "sectionId": pub.get("sectionId"),
            "dateSubmitted": item.get("dateSubmitted"),
            "dateLastActivity": item.get("dateLastActivity"),
            "datePublished": pub.get("datePublished"),
            "doi": doi_obj.get("doi"),
            "pages": pub.get("pages"),
            "urlWorkflow": item.get("urlWorkflow") or item.get("urlEditorialWorkflow"),
            "urlPublished": item.get("urlPublished"),
        }

    async def summarized_submissions(self, count: int = 100, offset: int = 0) -> Dict[str, Any]:
        raw = await self.list_submissions(count=count, offset=offset)
        items = [self.summarize_submission(item) for item in raw.get("items", [])]
        return {
            "itemsMax": raw.get("itemsMax"),
            "count": len(items),
            "items": items,
        }
