from pathlib import Path
from app.config import settings
from app.services.parser import ResumeParser
from app.services.skill_extractor import skill_extractor
from app.services.resume_checker import resume_checker
from app.services.role_recommender import role_recommender

SAMPLES_DIR = settings.BASE_DIR / "samples"


def test_weak_sample_resume_triggers_expected_mistakes():
    pdf_path = SAMPLES_DIR / "sample_weak_candidate.pdf"
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    full_text, sections, metadata = ResumeParser.parse_pdf(file_bytes)
    extracted_skills = skill_extractor.extract_and_attribute_skills(full_text, sections)
    contact_info = skill_extractor.extract_candidate_metadata(full_text, sections)

    audit = resume_checker.audit_resume(
        full_text=full_text,
        sections=sections,
        metadata=metadata,
        extracted_skills=extracted_skills,
        contact_info=contact_info,
        target_role="Full Stack Developer"
    )

    issues = audit["issues"]
    categories = [i["category"] for i in issues]
    severities = [i["severity"] for i in issues]

    # Must contain critical mistakes
    assert "Critical" in severities
    assert audit["critical_count"] >= 2

    # 1. Unprofessional email or missing phone
    assert "Contact Information" in categories
    assert any("coolgamerboy99" in str(i) for i in issues)

    # 2. Inappropriate personal info (DOB, marital status, gender, photo)
    assert any("Personal Info" in c or "ATS Readability" in c for c in categories)
    assert any("Age" in i["issue"] or "marital" in i["issue"].lower() or "photo" in i["issue"].lower() for i in issues)

    # 3. Weak / Passive action verbs ('responsible for')
    assert "Action Verbs" in categories
    assert any("responsible for" in str(i).lower() or "passive" in str(i).lower() for i in issues)

    # 4. Measurable metrics missing
    assert "Measurable Impact" in categories

    # 5. Overused buzzwords (hardworking, team player, results-oriented, synergy)
    assert "Clichés & Buzzwords" in categories

    # 6. Duplicated words ("the the")
    assert any("the the" in str(i).lower() or "repeated" in str(i).lower() for i in issues)

    # 7. Quality score should be heavily penalized (< 55)
    assert audit["quality_score"] < 55.0


def test_strong_sample_resume_quality_and_ranking():
    docx_path = SAMPLES_DIR / "sample_strong_swe.docx"
    with open(docx_path, "rb") as f:
        file_bytes = f.read()

    full_text, sections, metadata = ResumeParser.parse_docx(file_bytes)
    extracted_skills = skill_extractor.extract_and_attribute_skills(full_text, sections)
    contact_info = skill_extractor.extract_candidate_metadata(full_text, sections)

    audit = resume_checker.audit_resume(
        full_text=full_text,
        sections=sections,
        metadata=metadata,
        extracted_skills=extracted_skills,
        contact_info=contact_info,
        target_role="Full Stack Developer"
    )

    # Strong resume should have 0 critical issues and high quality score
    assert audit["critical_count"] == 0
    assert audit["quality_score"] >= 80.0

    # Role recommendations should rank Full Stack / Python / Backend Developer at the top
    all_skills = extracted_skills["all_skills"]
    recs = role_recommender.recommend_roles(all_skills, top_n=3)
    top_titles = [r["title"] for r in recs]

    assert any(role in top_titles for role in ["Full Stack Developer", "Backend Developer", "Python Developer"])
    assert recs[0]["fit_percentage"] >= 75.0


def test_non_technical_sample_ranking():
    pdf_path = SAMPLES_DIR / "sample_non_tech.pdf"
    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    full_text, sections, metadata = ResumeParser.parse_pdf(file_bytes)
    extracted_skills = skill_extractor.extract_and_attribute_skills(full_text, sections)

    all_skills = extracted_skills["all_skills"]
    recs = role_recommender.recommend_roles(all_skills, top_n=5)

    # Technical developer roles should have low fit (< 40%) for marketing resume
    top_role = recs[0]
    dev_roles = [r for r in recs if r["id"] in ["python-developer", "backend-developer", "devops-engineer"]]
    for dr in dev_roles:
        assert dr["fit_percentage"] < 40.0
