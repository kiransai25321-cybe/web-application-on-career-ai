from app.services.matcher import job_matcher


def test_job_matcher_standard_role():
    resume_text = """
Senior Python Developer with 5 years experience.
Built scalable REST APIs using FastAPI and PostgreSQL.
Containerized microservices with Docker and managed source code with Git.
Experienced in Redis caching and Linux environments.
"""
    skills = ["Python", "FastAPI", "PostgreSQL", "Git", "REST APIs", "Docker", "Redis", "Linux"]

    match = job_matcher.match_role("python-developer", resume_text, skills)

    assert match["role_title"] == "Python Developer"
    assert match["match_score"] >= 70.0
    assert "Python" in match["matched_required"]
    assert "FastAPI" in match["matched_required"]
    assert "PostgreSQL" in match["matched_required"]
    assert match["skill_overlap_score"] > 0
    assert match["tfidf_score"] > 0


def test_job_matcher_custom_job_description():
    resume_text = "Experienced in Python, React, TypeScript, and Docker."
    skills = ["Python", "React", "TypeScript", "Docker"]
    custom_jd = """
We are looking for a Full Stack Engineer proficient in React, TypeScript, Python, and AWS.
Experience with Docker is a plus.
"""

    match = job_matcher.match_custom_job_description(custom_jd, resume_text, skills)
    assert match["role_title"] == "Custom Job Description"
    assert match["match_score"] > 40.0
    assert "React" in match["matched_skills"]
    assert "Python" in match["matched_skills"]
