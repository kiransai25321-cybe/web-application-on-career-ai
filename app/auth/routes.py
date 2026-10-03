import re
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.config import settings
from app.database import get_db
from app.models import User, Analysis
from app.auth.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    check_rate_limit,
    record_failed_attempt,
    reset_failed_attempts,
    get_or_set_csrf_token,
    verify_csrf_token,
)
from app.auth.google_oauth import oauth
from app.auth.dependencies import get_current_user, login_required

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next: str = "",
    error: str = "",
    success: str = "",
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if current_user:
        return RedirectResponse(url=next or "/", status_code=status.HTTP_303_SEE_OTHER)

    csrf_token = get_or_set_csrf_token(request)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "csrf_token": csrf_token,
            "next": next,
            "error": error,
            "success": success,
            "google_oauth_enabled": settings.google_oauth_enabled,
            "user": None,
        }
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    remember_me: str = Form(""),
    csrf_token: str = Form(...),
    next: str = Form(""),
    db: Session = Depends(get_db)
):
    # Verify CSRF
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "next": next,
                "error": "Session expired or invalid security token. Please try again.",
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    client_ip = request.client.host if request.client else "unknown"

    # Rate limiting check
    is_limited, remaining_sec = check_rate_limit(client_ip, identifier)
    if is_limited:
        minutes = max(1, remaining_sec // 60)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "next": next,
                "error": f"Too many failed login attempts. Please try again in {minutes} minutes.",
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS
        )

    # Check credentials
    clean_identifier = identifier.strip().lower()
    user = db.query(User).filter(
        or_(
            User.username == clean_identifier,
            User.email == clean_identifier
        )
    ).first()

    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        record_failed_attempt(client_ip, identifier)
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "next": next,
                "error": "Invalid credentials. Please verify your username/email and password.",
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Success: reset rate limit attempts
    reset_failed_attempts(client_ip, identifier)

    # Set session
    request.session["user_id"] = user.id
    if remember_me:
        request.session["remember_me"] = True

    redirect_to = next if (next and next.startswith("/")) else "/"
    return RedirectResponse(url=redirect_to, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(
    request: Request,
    error: str = "",
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    if current_user:
        return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    csrf_token = get_or_set_csrf_token(request)
    return templates.TemplateResponse(
        request=request,
        name="signup.html",
        context={
            "csrf_token": csrf_token,
            "error": error,
            "google_oauth_enabled": settings.google_oauth_enabled,
            "user": None,
        }
    )



@router.post("/signup", response_class=HTMLResponse)
async def signup_submit(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    name: str = Form(""),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db)
):
    # Verify CSRF
    if not verify_csrf_token(request, csrf_token):
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "error": "Invalid security token. Please try again.",
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    clean_username = username.strip().lower()
    clean_email = email.strip().lower()

    # Validation
    if not re.match(r"^[a-zA-Z0-9_]{3,30}$", clean_username):
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "error": "Username must be 3-30 characters long and contain only letters, numbers, or underscores.",
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "error": "Please enter a valid email address.",
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "error": "Passwords do not match.",
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    valid_pass, pass_err = validate_password_strength(password)
    if not valid_pass:
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "error": pass_err,
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Check uniqueness
    existing_user = db.query(User).filter(
        or_(
            User.username == clean_username,
            User.email == clean_email
        )
    ).first()

    if existing_user:
        if existing_user.username == clean_username:
            err = "This username is already taken."
        else:
            err = "An account with this email already exists."
        return templates.TemplateResponse(
            request=request,
            name="signup.html",
            context={
                "csrf_token": get_or_set_csrf_token(request),
                "error": err,
                "google_oauth_enabled": settings.google_oauth_enabled,
                "user": None,
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Create user
    new_user = User(
        username=clean_username,
        email=clean_email,
        password_hash=hash_password(password),
        name=name.strip() or clean_username
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Log in automatically
    request.session["user_id"] = new_user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login?success=You+have+been+logged+out+successfully.", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/auth/google")
async def google_login(request: Request):
    if not settings.google_oauth_enabled:
        return RedirectResponse(url="/login?error=Google+OAuth+is+not+configured.", status_code=status.HTTP_303_SEE_OTHER)
    
    redirect_uri = "http://localhost:8000/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not settings.google_oauth_enabled:
        return RedirectResponse(url="/login?error=Google+OAuth+is+not+configured.", status_code=status.HTTP_303_SEE_OTHER)

    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        return RedirectResponse(url="/login?error=Google+authentication+was+cancelled+or+failed.", status_code=status.HTTP_303_SEE_OTHER)

    user_info = token.get("userinfo")
    if not user_info:
        return RedirectResponse(url="/login?error=Could+not+retrieve+Google+profile+data.", status_code=status.HTTP_303_SEE_OTHER)

    google_id = user_info.get("sub")
    email = user_info.get("email", "").lower()
    name = user_info.get("name", "")
    avatar_url = user_info.get("picture", "")

    if not email:
        return RedirectResponse(url="/login?error=Google+account+did+not+provide+an+email.", status_code=status.HTTP_303_SEE_OTHER)

    # Check if user exists by email
    user = db.query(User).filter(User.email == email).first()

    if user:
        # Link Google account if not linked
        if not user.google_id:
            user.google_id = google_id
        if not user.avatar_url and avatar_url:
            user.avatar_url = avatar_url
        if not user.name and name:
            user.name = name
        db.commit()
    else:
        # Create username from email or name
        base_username = re.sub(r"[^a-zA-Z0-9_]", "", email.split("@")[0])[:20]
        if not base_username:
            base_username = "user"
        username = base_username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}_{counter}"
            counter += 1

        user = User(
            username=username,
            email=email,
            password_hash=None,
            google_id=google_id,
            name=name or username,
            avatar_url=avatar_url
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    request.session["user_id"] = user.id
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(
    request: Request,
    error: str = "",
    success: str = "",
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    csrf_token = get_or_set_csrf_token(request)
    analyses_count = db.query(Analysis).filter(Analysis.user_id == user.id).count()
    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={
            "user": user,
            "csrf_token": csrf_token,
            "analyses_count": analyses_count,
            "error": error,
            "success": success,
        }
    )


@router.post("/profile/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(""),
    new_password: str = Form(...),
    confirm_new_password: str = Form(...),
    csrf_token: str = Form(...),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(url="/profile?error=Invalid+security+token.", status_code=status.HTTP_303_SEE_OTHER)

    if not user.password_hash:
        return RedirectResponse(url="/profile?error=Your+account+uses+Google+login+without+a+password.", status_code=status.HTTP_303_SEE_OTHER)

    if not verify_password(current_password, user.password_hash):
        return RedirectResponse(url="/profile?error=Current+password+is+incorrect.", status_code=status.HTTP_303_SEE_OTHER)

    if new_password != confirm_new_password:
        return RedirectResponse(url="/profile?error=New+passwords+do+not+match.", status_code=status.HTTP_303_SEE_OTHER)

    valid_pass, pass_err = validate_password_strength(new_password)
    if not valid_pass:
        return RedirectResponse(url=f"/profile?error={pass_err}", status_code=status.HTTP_303_SEE_OTHER)

    user.password_hash = hash_password(new_password)
    db.commit()

    return RedirectResponse(url="/profile?success=Password+updated+successfully.", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/profile/delete-account")
async def delete_account(
    request: Request,
    confirmation: str = Form(...),
    csrf_token: str = Form(...),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(url="/profile?error=Invalid+security+token.", status_code=status.HTTP_303_SEE_OTHER)

    if confirmation.strip().lower() != "delete":
        return RedirectResponse(url="/profile?error=Please+type+DELETE+to+confirm+account+deletion.", status_code=status.HTTP_303_SEE_OTHER)

    # Delete all analyses and user
    db.delete(user)
    db.commit()

    request.session.clear()
    return RedirectResponse(url="/signup?success=Your+account+and+all+associated+data+have+been+permanently+deleted.", status_code=status.HTTP_303_SEE_OTHER)
