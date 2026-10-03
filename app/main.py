import json
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, Request, Depends, Form, UploadFile, File, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import init_db, get_db
from app.models import User, Analysis
from app.auth.routes import router as auth_router
from app.auth.dependencies import get_current_user, login_required
from app.auth.security import get_or_set_csrf_token, verify_csrf_token

from app.services.parser import ResumeParser
from app.services.skill_extractor import skill_extractor
from app.services.role_recommender import role_recommender
from app.services.matcher import job_matcher
from app.services.learning_plan import learning_plan_service
from app.services.resume_checker import resume_checker
from app.services.llm_service import llm_service
from app.services.report_pdf import generate_pdf_report

app = FastAPI(
    title=settings.APP_NAME,
    description="Full-stack AI Resume Analyzer with skill extraction, role matching, mistake audit, and learning roadmaps",
    version="1.0.0"
)

# Mount Session Middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=settings.SESSION_MAX_AGE_DAYS * 86400,
    same_site="lax",
    https_only=False
)

# Mount Static Files
static_dir = settings.BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = settings.BASE_DIR / "app" / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Include Auth Router
app.include_router(auth_router)


@app.on_event("startup")
def on_startup():
    init_db()


# -------------------------------------------------------------
# Web Application Routes
# -------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user(request, db)
    csrf_token = get_or_set_csrf_token(request)

    recent_analyses = []
    if current_user:
        recent_analyses = (
            db.query(Analysis)
            .filter(Analysis.user_id == current_user.id)
            .order_by(Analysis.created_at.desc())
            .limit(3)
            .all()
        )

    all_roles = role_recommender.roles
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "user": current_user,
            "csrf_token": csrf_token,
            "roles": all_roles,
            "recent_analyses": recent_analyses,
        }
    )


@app.post("/analyze", response_class=HTMLResponse)
async def analyze_resume_form(
    request: Request,
    resume_file: UploadFile = File(...),
    target_role: str = Form("AUTO"),
    custom_jd: str = Form(""),
    csrf_token: str = Form(...),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(url="/?error=Invalid+or+expired+security+token.", status_code=status.HTTP_303_SEE_OTHER)

    filename = resume_file.filename or "resume.pdf"
    file_lower = filename.lower()
    if not (file_lower.endswith(".pdf") or file_lower.endswith(".docx")):
        return RedirectResponse(url="/?error=Unsupported+file+format.+Please+upload+a+PDF+or+DOCX+file.", status_code=status.HTTP_303_SEE_OTHER)

    file_bytes = await resume_file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        return RedirectResponse(url="/?error=File+size+exceeds+5MB+limit.", status_code=status.HTTP_303_SEE_OTHER)

    # 1. Parse Resume
    file_type = "pdf" if file_lower.endswith(".pdf") else "docx"
    try:
        if file_type == "pdf":
            full_text, sections, metadata = ResumeParser.parse_pdf(file_bytes)
        else:
            full_text, sections, metadata = ResumeParser.parse_docx(file_bytes)
    except Exception as e:
        return RedirectResponse(url=f"/?error=Failed+to+read+resume+content:+{str(e)[:100]}", status_code=status.HTTP_303_SEE_OTHER)

    if not full_text.strip():
        return RedirectResponse(url="/?error=Resume+is+empty+or+contains+only+scanned+unreadable+images.", status_code=status.HTTP_303_SEE_OTHER)

    # 2. Extract Skills & Candidate Metadata
    extracted_skills = skill_extractor.extract_and_attribute_skills(full_text, sections)
    contact_info = skill_extractor.extract_candidate_metadata(full_text, sections)
    all_skills_list = extracted_skills.get("all_skills", [])

    # 3. Role Recommendations Ranking
    recommended_roles = role_recommender.recommend_roles(all_skills_list, top_n=5)

    # 4. Resolve Target Role
    selected_role_title = "Full Stack Developer"
    if custom_jd.strip():
        match_details = job_matcher.match_custom_job_description(custom_jd.strip(), full_text, all_skills_list)
        selected_role_title = "Custom Job Description"
    elif target_role == "AUTO" or not target_role:
        if recommended_roles:
            selected_role_title = recommended_roles[0]["title"]
            match_details = job_matcher.match_role(selected_role_title, full_text, all_skills_list)
        else:
            match_details = job_matcher.match_role("Full Stack Developer", full_text, all_skills_list)
            selected_role_title = "Full Stack Developer"
    else:
        match_details = job_matcher.match_role(target_role, full_text, all_skills_list)
        selected_role_title = match_details.get("role_title", target_role)

    match_score = match_details["match_score"]

    # 5. Skills to Learn Roadmap
    learning_plan = learning_plan_service.generate_roadmap(
        target_role=selected_role_title,
        current_match_score=match_score,
        candidate_skills=all_skills_list,
        missing_required=match_details.get("missing_required", []),
        missing_nice_to_have=match_details.get("missing_nice_to_have", []),
        resume_text=full_text
    )

    # 6. Resume Mistake Checker & Quality Score
    mistakes_data = resume_checker.audit_resume(
        full_text=full_text,
        sections=sections,
        metadata=metadata,
        extracted_skills=extracted_skills,
        contact_info=contact_info,
        target_role=selected_role_title
    )
    quality_score = mistakes_data["quality_score"]

    # 7. Executive Feedback Summary
    llm_summary = await llm_service.generate_feedback(
        candidate_name=contact_info.get("name", "Candidate"),
        target_role=selected_role_title,
        match_score=match_score,
        quality_score=quality_score,
        matched_skills=match_details.get("matched_skills", []),
        missing_skills=match_details.get("missing_required", []),
        mistakes=mistakes_data.get("issues", []),
        learning_headline=learning_plan.get("headline", "")
    )

    # 8. Save Analysis into Database
    new_analysis = Analysis(
        user_id=user.id,
        filename=filename,
        file_type=file_type,
        selected_role=selected_role_title,
        match_score=match_score,
        quality_score=quality_score,
        parsed_text=full_text[:5000],  # store excerpt
        contact_info_json=json.dumps(contact_info),
        skills_json=json.dumps(extracted_skills),
        recommended_roles_json=json.dumps(recommended_roles),
        match_details_json=json.dumps(match_details),
        learning_plan_json=json.dumps(learning_plan),
        mistakes_json=json.dumps(mistakes_data),
        llm_summary=llm_summary
    )
    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)

    return RedirectResponse(url=f"/dashboard/{new_analysis.id}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/dashboard/{analysis_id}", response_class=HTMLResponse)
async def view_dashboard(
    request: Request,
    analysis_id: int,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis report not found.")

    csrf_token = get_or_set_csrf_token(request)
    all_roles = role_recommender.roles

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": user,
            "analysis": analysis.to_dict(),
            "contact_info": analysis.get_contact_info(),
            "skills": analysis.get_skills(),
            "recommended_roles": analysis.get_recommended_roles(),
            "match_details": analysis.get_match_details(),
            "learning_plan": analysis.get_learning_plan(),
            "mistakes_data": analysis.get_mistakes(),
            "all_roles": all_roles,
            "csrf_token": csrf_token,
        }
    )


@app.post("/dashboard/{analysis_id}/rematch")
async def rematch_target_role(
    request: Request,
    analysis_id: int,
    target_role: str = Form(...),
    custom_jd: str = Form(""),
    csrf_token: str = Form(...),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(url=f"/dashboard/{analysis_id}?error=Invalid+security+token.", status_code=status.HTTP_303_SEE_OTHER)

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    skills_data = analysis.get_skills()
    candidate_skills = skills_data.get("all_skills", [])
    resume_text = analysis.parsed_text or ""

    # Recompute Match
    if custom_jd.strip():
        match_details = job_matcher.match_custom_job_description(custom_jd.strip(), resume_text, candidate_skills)
        selected_role_title = "Custom Job Description"
    else:
        match_details = job_matcher.match_role(target_role, resume_text, candidate_skills)
        selected_role_title = match_details.get("role_title", target_role)

    match_score = match_details["match_score"]

    # Recompute Learning Roadmap
    learning_plan = learning_plan_service.generate_roadmap(
        target_role=selected_role_title,
        current_match_score=match_score,
        candidate_skills=candidate_skills,
        missing_required=match_details.get("missing_required", []),
        missing_nice_to_have=match_details.get("missing_nice_to_have", []),
        resume_text=resume_text
    )

    analysis.selected_role = selected_role_title
    analysis.match_score = match_score
    analysis.match_details_json = json.dumps(match_details)
    analysis.learning_plan_json = json.dumps(learning_plan)
    db.commit()

    return RedirectResponse(url=f"/dashboard/{analysis_id}?tab=match&success=Role+rematched+successfully.", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/report/{analysis_id}.pdf")
async def download_report_pdf(
    analysis_id: int,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id
    ).first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis report not found.")

    pdf_bytes = generate_pdf_report(analysis.to_dict())
    clean_filename = f"Resume_Analysis_{analysis.selected_role.replace(' ', '_')}_{analysis.id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}"'}
    )


@app.get("/history", response_class=HTMLResponse)
async def view_history(
    request: Request,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    csrf_token = get_or_set_csrf_token(request)
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )

    # Chronological order for chart
    chronological = list(reversed(analyses))
    chart_labels = [a.created_at.strftime("%b %d") for a in chronological]
    chart_quality = [a.quality_score for a in chronological]
    chart_match = [a.match_score for a in chronological]

    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "user": user,
            "csrf_token": csrf_token,
            "analyses": analyses,
            "chart_labels": chart_labels,
            "chart_quality": chart_quality,
            "chart_match": chart_match,
        }
    )


@app.post("/history/{analysis_id}/delete")
async def delete_analysis_record(
    request: Request,
    analysis_id: int,
    csrf_token: str = Form(...),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    if not verify_csrf_token(request, csrf_token):
        return RedirectResponse(url="/history?error=Invalid+security+token.", status_code=status.HTTP_303_SEE_OTHER)

    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id
    ).first()

    if analysis:
        db.delete(analysis)
        db.commit()

    return RedirectResponse(url="/history?success=Analysis+deleted+successfully.", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/compare", response_class=HTMLResponse)
async def compare_page(
    request: Request,
    id1: Optional[int] = None,
    id2: Optional[int] = None,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    csrf_token = get_or_set_csrf_token(request)
    all_analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )

    analysis1 = None
    analysis2 = None
    comparison = None

    if id1 and id2 and id1 != id2:
        analysis1 = db.query(Analysis).filter(Analysis.id == id1, Analysis.user_id == user.id).first()
        analysis2 = db.query(Analysis).filter(Analysis.id == id2, Analysis.user_id == user.id).first()

    if not analysis1 and len(all_analyses) >= 2:
        analysis2 = all_analyses[0]
        analysis1 = all_analyses[1]

    if analysis1 and analysis2:
        # Compute diffs
        skills1 = set(analysis1.get_skills().get("all_skills", []))
        skills2 = set(analysis2.get_skills().get("all_skills", []))
        new_skills = sorted(list(skills2 - skills1))

        mistakes1 = {m["issue"] for m in analysis1.get_mistakes().get("issues", [])}
        mistakes2 = {m["issue"] for m in analysis2.get_mistakes().get("issues", [])}
        
        resolved_issues = [
            m for m in analysis1.get_mistakes().get("issues", [])
            if m["issue"] not in mistakes2
        ]
        remaining_issues = [
            m for m in analysis2.get_mistakes().get("issues", [])
        ]

        comparison = {
            "v1_quality": analysis1.quality_score,
            "v2_quality": analysis2.quality_score,
            "quality_delta": round(analysis2.quality_score - analysis1.quality_score, 1),
            "v1_match": analysis1.match_score,
            "v2_match": analysis2.match_score,
            "match_delta": round(analysis2.match_score - analysis1.match_score, 1),
            "v1_role": analysis1.selected_role,
            "v2_role": analysis2.selected_role,
            "new_skills": new_skills,
            "resolved_mistakes": resolved_issues,
            "remaining_mistakes": remaining_issues,
        }

    return templates.TemplateResponse(
        request=request,
        name="compare.html",
        context={
            "user": user,
            "csrf_token": csrf_token,
            "all_analyses": [a.to_dict() for a in all_analyses],
            "analysis1": analysis1.to_dict() if analysis1 else None,
            "analysis2": analysis2.to_dict() if analysis2 else None,
            "comparison": comparison,
        }
    )


# -------------------------------------------------------------
# JSON REST API Endpoints
# -------------------------------------------------------------

@app.get("/api/roles")
async def api_get_roles():
    """Returns all available standard job roles."""
    return {"roles": role_recommender.roles}


@app.get("/api/history")
async def api_get_history(user: User = Depends(login_required), db: Session = Depends(get_db)):
    """Returns past analyses for the authenticated user."""
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )
    return {"analyses": [a.to_dict() for a in analyses]}


@app.get("/api/analysis/{analysis_id}")
async def api_get_analysis(
    analysis_id: int,
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    """Returns single analysis record by ID."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == user.id
    ).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return analysis.to_dict()


@app.post("/api/analyze")
async def api_analyze_resume(
    resume_file: UploadFile = File(...),
    target_role: Optional[str] = Form("AUTO"),
    custom_jd: Optional[str] = Form(""),
    user: User = Depends(login_required),
    db: Session = Depends(get_db)
):
    """REST API endpoint to analyze a resume file and return full JSON results."""
    filename = resume_file.filename or "resume.pdf"
    file_lower = filename.lower()
    if not (file_lower.endswith(".pdf") or file_lower.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are supported.")

    file_bytes = await resume_file.read()
    if len(file_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 5MB maximum size.")

    file_type = "pdf" if file_lower.endswith(".pdf") else "docx"
    if file_type == "pdf":
        full_text, sections, metadata = ResumeParser.parse_pdf(file_bytes)
    else:
        full_text, sections, metadata = ResumeParser.parse_docx(file_bytes)

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the file.")

    extracted_skills = skill_extractor.extract_and_attribute_skills(full_text, sections)
    contact_info = skill_extractor.extract_candidate_metadata(full_text, sections)
    all_skills_list = extracted_skills.get("all_skills", [])
    recommended_roles = role_recommender.recommend_roles(all_skills_list, top_n=5)

    if custom_jd and custom_jd.strip():
        match_details = job_matcher.match_custom_job_description(custom_jd.strip(), full_text, all_skills_list)
        selected_role_title = "Custom Job Description"
    elif target_role == "AUTO" or not target_role:
        selected_role_title = recommended_roles[0]["title"] if recommended_roles else "Full Stack Developer"
        match_details = job_matcher.match_role(selected_role_title, full_text, all_skills_list)
    else:
        match_details = job_matcher.match_role(target_role, full_text, all_skills_list)
        selected_role_title = match_details.get("role_title", target_role)

    match_score = match_details["match_score"]
    learning_plan = learning_plan_service.generate_roadmap(
        target_role=selected_role_title,
        current_match_score=match_score,
        candidate_skills=all_skills_list,
        missing_required=match_details.get("missing_required", []),
        missing_nice_to_have=match_details.get("missing_nice_to_have", []),
        resume_text=full_text
    )

    mistakes_data = resume_checker.audit_resume(
        full_text=full_text,
        sections=sections,
        metadata=metadata,
        extracted_skills=extracted_skills,
        contact_info=contact_info,
        target_role=selected_role_title
    )

    llm_summary = await llm_service.generate_feedback(
        candidate_name=contact_info.get("name", "Candidate"),
        target_role=selected_role_title,
        match_score=match_score,
        quality_score=mistakes_data["quality_score"],
        matched_skills=match_details.get("matched_skills", []),
        missing_skills=match_details.get("missing_required", []),
        mistakes=mistakes_data.get("issues", []),
        learning_headline=learning_plan.get("headline", "")
    )

    new_analysis = Analysis(
        user_id=user.id,
        filename=filename,
        file_type=file_type,
        selected_role=selected_role_title,
        match_score=match_score,
        quality_score=mistakes_data["quality_score"],
        parsed_text=full_text[:5000],
        contact_info_json=json.dumps(contact_info),
        skills_json=json.dumps(extracted_skills),
        recommended_roles_json=json.dumps(recommended_roles),
        match_details_json=json.dumps(match_details),
        learning_plan_json=json.dumps(learning_plan),
        mistakes_json=json.dumps(mistakes_data),
        llm_summary=llm_summary
    )
    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)

    return new_analysis.to_dict()
