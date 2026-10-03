from app.services.skill_extractor import skill_extractor


def test_alias_resolution_and_case_insensitivity():
    sample_text = "Proficient in js, PyThOn, k8s, sklearn, and postgresql database."
    skills = skill_extractor.extract_skills_from_text(sample_text)

    assert "JavaScript" in skills
    assert "Python" in skills
    assert "Kubernetes" in skills
    assert "scikit-learn" in skills
    assert "PostgreSQL" in skills


def test_section_attribution_demonstrated_vs_listed():
    full_text = """
SKILLS:
Python, Docker, Kubernetes, GraphQL

EXPERIENCE:
Software Engineer at Acme Corp (2021 - Present)
- Developed REST APIs in Python.
- Deployed microservices using Docker containers.
"""
    sections = {
        "skills": "Python, Docker, Kubernetes, GraphQL",
        "experience": "Software Engineer at Acme Corp\n- Developed REST APIs in Python.\n- Deployed microservices using Docker containers."
    }

    result = skill_extractor.extract_and_attribute_skills(full_text, sections)
    flat_skills = {s["name"]: s["demonstrated"] for s in result["flat_skills"]}

    # Python & Docker appear in experience -> Demonstrated
    assert flat_skills.get("Python") is True
    assert flat_skills.get("Docker") is True

    # Kubernetes & GraphQL appear only in skills -> Listed Only
    assert flat_skills.get("Kubernetes") is False
    assert flat_skills.get("GraphQL") is False


def test_extract_candidate_metadata():
    text = """
David Miller
david.miller@techcorp.io | +1 (555) 987-6543 | linkedin.com/in/david-miller | github.com/dmiller
San Francisco, CA

Professional Experience:
Senior Developer | Stripe (2018 - 2024)
- 6+ years of experience building high-scale financial systems.
"""
    sections = {
        "header": "David Miller\ndavid.miller@techcorp.io | +1 (555) 987-6543",
        "experience": "Senior Developer | Stripe (2018 - 2024)\n- 6+ years of experience"
    }

    meta = skill_extractor.extract_candidate_metadata(text, sections)
    assert meta["email"] == "david.miller@techcorp.io"
    assert "555" in meta["phone"]
    assert "linkedin.com/in/david-miller" in meta["linkedin"]
    assert "github.com/dmiller" in meta["github"]
    assert meta["years_of_experience"] >= 5.0
