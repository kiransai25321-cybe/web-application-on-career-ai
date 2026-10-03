from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Retrieve currently authenticated user from session or None."""
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user


def login_required(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency that ensures the user is logged in or redirects/aborts."""
    user = get_current_user(request, db)
    if not user:
        # Check if API request or browser request
        accept_header = request.headers.get("accept", "")
        if "application/json" in accept_header or request.url.path.startswith("/api/"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        # Browser request: redirect to /login with next parameter
        next_url = str(request.url.path)
        if request.url.query:
            next_url += f"?{request.url.query}"
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": f"/login?next={next_url}"}
        )
    return user
