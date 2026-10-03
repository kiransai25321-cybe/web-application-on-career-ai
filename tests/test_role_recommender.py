from app.services.role_recommender import role_recommender


def test_recommendations_for_backend_skills():
    skills = ["Python", "FastAPI", "PostgreSQL", "Docker", "Git", "REST APIs", "Redis"]
    recs = role_recommender.recommend_roles(skills, top_n=5)

    assert len(recs) >= 3
    top_titles = [r["title"] for r in recs[:3]]

    # Python Developer or Backend Developer should be in top 3
    assert any("Python Developer" in t or "Backend Developer" in t for t in top_titles)

    # Top recommendation should have high fit (>65%)
    assert recs[0]["fit_percentage"] >= 65.0
    assert "Strong in" in recs[0]["reason"] or "Matches" in recs[0]["reason"]


def test_recommendations_for_data_science_skills():
    skills = ["Python", "pandas", "NumPy", "scikit-learn", "SQL", "Tableau"]
    recs = role_recommender.recommend_roles(skills, top_n=5)

    top_titles = [r["title"] for r in recs[:3]]
    assert any("Data Scientist" in t or "Data Analyst" in t for t in top_titles)
