import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.config import settings


class RoleRecommender:
    def __init__(self, job_roles_path: Optional[Path] = None):
        if job_roles_path is None:
            job_roles_path = settings.BASE_DIR / "app" / "data" / "job_roles.json"

        with open(job_roles_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.roles = data.get("roles", [])

    def recommend_roles(self, candidate_skills: List[str], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Ranks all roles based on candidate's skills and returns top recommendations.
        """
        candidate_skills_set = {s.lower() for s in candidate_skills}
        ranked_roles: List[Dict[str, Any]] = []

        for role in self.roles:
            role_id = role.get("id")
            title = role.get("title")
            category = role.get("category", "Technology")
            description = role.get("description", "")
            req_skills = role.get("required_skills", [])
            nice_skills = role.get("nice_to_have_skills", [])
            weights = role.get("skill_weights", {})

            # Match sets
            matched_req = [s for s in req_skills if s.lower() in candidate_skills_set]
            missing_req = [s for s in req_skills if s.lower() not in candidate_skills_set]

            matched_nice = [s for s in nice_skills if s.lower() in candidate_skills_set]
            missing_nice = [s for s in nice_skills if s.lower() not in candidate_skills_set]

            # Weighted scoring
            total_req_weight = sum(weights.get(s, 1.0) for s in req_skills) or 1.0
            matched_req_weight = sum(weights.get(s, 1.0) for s in matched_req)

            total_nice_weight = sum(weights.get(s, 1.0) for s in nice_skills) or 1.0
            matched_nice_weight = sum(weights.get(s, 1.0) for s in matched_nice)

            req_ratio = matched_req_weight / total_req_weight
            nice_ratio = matched_nice_weight / total_nice_weight

            # 70% required skills, 30% nice to have skills
            fit_score = (0.70 * req_ratio) + (0.30 * nice_ratio)
            fit_percentage = round(min(100.0, max(0.0, fit_score * 100)), 1)

            # Generate dynamic one-line reason
            all_matched = matched_req + matched_nice
            if len(all_matched) >= 3:
                top_matched_display = ", ".join(all_matched[:3])
                reason = f"Strong in {top_matched_display}"
            elif len(all_matched) > 0:
                top_matched_display = ", ".join(all_matched)
                reason = f"Matches key foundations: {top_matched_display}"
            else:
                reason = "Opportunity to transition by building foundational skills"

            ranked_roles.append({
                "id": role_id,
                "title": title,
                "category": category,
                "description": description,
                "fit_percentage": fit_percentage,
                "matched_skills": all_matched,
                "matched_required": matched_req,
                "missing_required": missing_req,
                "matched_nice_to_have": matched_nice,
                "missing_nice_to_have": missing_nice,
                "reason": reason,
                "required_count": len(req_skills),
                "matched_req_count": len(matched_req),
            })

        # Rank descending by fit_percentage and then by matched_req_count
        ranked_roles.sort(key=lambda x: (x["fit_percentage"], x["matched_req_count"]), reverse=True)
        return ranked_roles


# Singleton role recommender
role_recommender = RoleRecommender()
