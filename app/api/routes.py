from fastapi import APIRouter

from app.core.analyzer import analyze_ticket
from app.schemas.request import AnalyzeTicketRequest
from app.schemas.response import AnalyzeTicketResponse

router = APIRouter()

@router.get("/")
def root():
    return {
        "message": "QueueStorm Investigator API is running",
        "docs": "https://queuestorm-investigator-f1k2.onrender.com/docs",
        "health": "https://queuestorm-investigator-f1k2.onrender.com/health"
    }

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
def analyze_ticket_endpoint(payload: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    return analyze_ticket(payload)
