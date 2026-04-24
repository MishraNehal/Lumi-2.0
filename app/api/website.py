from fastapi import APIRouter

router = APIRouter(prefix="/website", tags=["Website"])


@router.get("/status")
def website_status() -> dict[str, str]:
    return {"module": "website", "status": "future-module"}
