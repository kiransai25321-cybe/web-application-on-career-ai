import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from app.config import settings
from app.services.skill_extractor import skill_extractor


class JobMatcher:
    def __init__(self, job_roles_path: Optional[Path] = None):
        if job_roles_path is None:
            job_roles_path = settings.BASE_DIR / "app" / "data" / "job_roles.json"

        with open(job_roles_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.roles_by_id = {r["id"]: r for r in data.get("roles", [])}
        self.roles_by_title = {r["title"].lower(): r for r in data.get("roles", [])}

    def get_role_data(self, role_identifier: str) -> Optional[Dict[str, Any]]:
        """Finds role definition by id or title."""
        if role_identifier in self.roles_by_id:
            return self.roles_by_id[role_identifier]
        clean_title = role_identifier.strip().lower()
        if clean_title in self.roles_by_title:
            return self.roles_by_title[clean_title]
        # Partial match fallback
        for r in self.roles_by_id.values():
            if clean_title in r["title"].lower() or r["title"].lower() in clean_title:
                return r
        # Default to first role if not found
        return next(iter(self.roles_by_id.values()), None)

    def match_role(
        self,
        role_identifier: str,
        resume_text: str,
        candidate_skills: List[str]
    ) -> Dict[str, Any]:
        """
        Calculates the comprehensive match score between a candidate's resume and a standard role.

        FORMULA DOCUMENTATION:
        -----------------------
        1. Required Skill Overlap Ratio (R_req):
           R_req = Sum(weight_i for i in matched_required) / Sum(weight_i for i in all_required)

        2. Nice-to-Have Skill Overlap Ratio (R_nice):
           R_nice = Sum(weight_j for j in matched_nice) / Sum(weight_j for j in all_nice)

        3. Total Weighted Skill Overlap Score (S_skill, 0 - 100):
           S_skill = (0.70 * R_req + 0.30 * R_nice) * 100

        4. TF-IDF Textual Cosine Similarity (S_tfidf, 0 - 100):
           S_tfidf = cosine_similarity(TF_IDF(resume_text), TF_IDF(role_description_and_skills)) * 100

        5. Final Blended Match Score (Match_Score, 0 - 100):
           Match_Score = round(0.75 * S_skill + 0.25 * S_tfidf, 1)
        """
        role = self.get_role_data(role_identifier)
        if not role:
            return self._empty_match("Unknown Role")

        req_skills = role.get("required_skills", [])
        nice_skills = role.get("nice_to_have_skills", [])
        weights = role.get("skill_weights", {})

        candidate_skills_set = {s.lower() for s in candidate_skills}

        matched_req = [s for s in req_skills if s.lower() in candidate_skills_set]
        missing_req = [s for s in req_skills if s.lower() not in candidate_skills_set]

        matched_nice = [s for s in nice_skills if s.lower() in candidate_skills_set]
        missing_nice = [s for s in nice_skills if s.lower() not in candidate_skills_set]

        # Calculate weighted skill overlap
        total_req_weight = sum(weights.get(s, 1.0) for s in req_skills) or 1.0
        matched_req_weight = sum(weights.get(s, 1.0) for s in matched_req)
        r_req = matched_req_weight / total_req_weight

        total_nice_weight = sum(weights.get(s, 1.0) for s in nice_skills) or 1.0
        matched_nice_weight = sum(weights.get(s, 1.0) for s in matched_nice)
        r_nice = matched_nice_weight / total_nice_weight

        skill_overlap_ratio = (0.70 * r_req) + (0.30 * r_nice)
        skill_score = skill_overlap_ratio * 100.0

        # Build role reference text for TF-IDF
        role_text = f"{role.get('title', '')} {role.get('description', '')} " + " ".join(req_skills) + " " + " ".join(nice_skills)
        tfidf_score = self._compute_tfidf_similarity(resume_text, role_text)

        # Blended final score
        final_score = round((0.75 * skill_score) + (0.25 * tfidf_score), 1)
        final_score = min(100.0, max(0.0, final_score))

        return {
            "role_id": role.get("id"),
            "role_title": role.get("title"),
            "role_description": role.get("description"),
            "category": role.get("category"),
            "match_score": final_score,
            "skill_overlap_score": round(skill_score, 1),
            "tfidf_score": round(tfidf_score, 1),
            "matched_skills": matched_req + matched_nice,
            "matched_required": matched_req,
            "missing_required": missing_req,
            "matched_nice_to_have": matched_nice,
            "missing_nice_to_have": missing_nice,
            "total_required_count": len(req_skills),
            "total_nice_count": len(nice_skills),
        }

    def match_custom_job_description(
        self,
        job_description_text: str,
        resume_text: str,
        candidate_skills: List[str]
    ) -> Dict[str, Any]:
        """
        Matches resume against an arbitrary user-pasted job description.
        Extracts skills from the JD using SkillExtractor, splits them into core and nice-to-have,
        and applies the same blended formula.
        """
        extracted_jd_skills = list(skill_extractor.extract_skills_from_text(job_description_text))
        
        # If no skills extracted, fallback to text similarity
        if not extracted_jd_skills:
            tfidf_score = self._compute_tfidf_similarity(resume_text, job_description_text)
            return {
                "role_id": "custom-role",
                "role_title": "Custom Job Description",
                "role_description": job_description_text[:300] + "..." if len(job_description_text) > 300 else job_description_text,
                "category": "Custom",
                "match_score": round(tfidf_score, 1),
                "skill_overlap_score": round(tfidf_score, 1),
                "tfidf_score": round(tfidf_score, 1),
                "matched_skills": [],
                "matched_required": [],
                "missing_required": [],
                "matched_nice_to_have": [],
                "missing_nice_to_have": [],
                "total_required_count": 0,
                "total_nice_count": 0,
            }

        # Divide extracted JD skills: first 60% as required, remaining 40% as nice-to-have
        split_idx = max(1, int(len(extracted_jd_skills) * 0.6))
        req_skills = extracted_jd_skills[:split_idx]
        nice_skills = extracted_jd_skills[split_idx:]

        candidate_skills_set = {s.lower() for s in candidate_skills}
        matched_req = [s for s in req_skills if s.lower() in candidate_skills_set]
        missing_req = [s for s in req_skills if s.lower() not in candidate_skills_set]

        matched_nice = [s for s in nice_skills if s.lower() in candidate_skills_set]
        missing_nice = [s for s in nice_skills if s.lower() not in candidate_skills_set]

        r_req = len(matched_req) / len(req_skills) if req_skills else 1.0
        r_nice = len(matched_nice) / len(nice_skills) if nice_skills else 1.0

        skill_overlap_ratio = (0.70 * r_req) + (0.30 * r_nice)
        skill_score = skill_overlap_ratio * 100.0

        tfidf_score = self._compute_tfidf_similarity(resume_text, job_description_text)
        final_score = round((0.75 * skill_score) + (0.25 * tfidf_score), 1)
        final_score = min(100.0, max(0.0, final_score))

        return {
            "role_id": "custom-role",
            "role_title": "Custom Job Description",
            "role_description": job_description_text[:200] + "..." if len(job_description_text) > 200 else job_description_text,
            "category": "Custom",
            "match_score": final_score,
            "skill_overlap_score": round(skill_score, 1),
            "tfidf_score": round(tfidf_score, 1),
            "matched_skills": matched_req + matched_nice,
            "matched_required": matched_req,
            "missing_required": missing_req,
            "matched_nice_to_have": matched_nice,
            "missing_nice_to_have": missing_nice,
            "total_required_count": len(req_skills),
            "total_nice_count": len(nice_skills),
        }

    def _compute_tfidf_similarity(self, doc1: str, doc2: str) -> float:
        """Computes TF-IDF cosine similarity between two texts, returning 0.0 - 100.0."""
        cleaned1 = doc1.strip()
        cleaned2 = doc2.strip()
        if not cleaned1 or not cleaned2:
            return 0.0

        try:
            vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
            tfidf_matrix = vectorizer.fit_transform([cleaned1, cleaned2])
            sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(sim * 100.0)
        except Exception:
            return 0.0

    def _empty_match(self, title: str) -> Dict[str, Any]:
        return {
            "role_id": "unknown",
            "role_title": title,
            "role_description": "",
            "category": "General",
            "match_score": 0.0,
            "skill_overlap_score": 0.0,
            "tfidf_score": 0.0,
            "matched_skills": [],
            "matched_required": [],
            "missing_required": [],
            "matched_nice_to_have": [],
            "missing_nice_to_have": [],
            "total_required_count": 0,
            "total_nice_count": 0,
        }


# Singleton matcher
job_matcher = JobMatcher()
