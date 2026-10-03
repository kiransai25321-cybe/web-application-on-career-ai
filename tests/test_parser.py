from pathlib import Path
from app.services.parser import ResumeParser
from app.config import settings

SAMPLES_DIR = settings.BASE_DIR / "samples"


def test_parse_docx_strong_swe():
    docx_path = SAMPLES_DIR / "sample_strong_swe.docx"
    assert docx_path.exists(), "Sample docx file must exist"

    with open(docx_path, "rb") as f:
        file_bytes = f.read()

    full_text, sections, metadata = ResumeParser.parse_docx(file_bytes)

    assert "David Chen" in full_text
    assert "FastAPI" in full_text
    assert "PostgreSQL" in full_text
    assert metadata["word_count"] > 100

    # Verify key sections detected
    assert "skills" in sections or "experience" in sections
    assert "summary" in sections or "experience" in sections


def test_parse_pdf_weak_candidate():
    pdf_path = SAMPLES_DIR / "sample_weak_candidate.pdf"
    assert pdf_path.exists(), "Sample pdf file must exist"

    with open(pdf_path, "rb") as f:
        file_bytes = f.read()

    full_text, sections, metadata = ResumeParser.parse_pdf(file_bytes)

    assert "Johnny Developer" in full_text
    assert "coolgamerboy99@gmail.com" in full_text
    assert metadata["page_count"] >= 1
    assert metadata["word_count"] > 40


def test_section_splitting_heuristics():
    raw_text = """
John Doe
john@test.com | 555-1234

PROFESSIONAL SUMMARY
Experienced software engineer with 5 years building web applications.

TECHNICAL SKILLS
Python, JavaScript, React, Docker, SQL

WORK EXPERIENCE
Senior Engineer | Acme Corp (2020 - 2024)
- Developed APIs using FastAPI and PostgreSQL.
- Reduced latency by 30%.

EDUCATION
B.S. in Computer Science | MIT (2016 - 2020)
"""
    sections = ResumeParser.split_into_sections(raw_text)
    assert "summary" in sections
    assert "skills" in sections
    assert "experience" in sections
    assert "education" in sections
    assert "FastAPI" in sections["experience"]
    assert "MIT" in sections["education"]
