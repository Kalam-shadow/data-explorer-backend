from fastapi import APIRouter
from app.session.manager import delete_session

router = APIRouter()

@router.post("/exit")
def exit_session(session_id: str):
    delete_session(session_id)
    return {"status": "deleted"}
