import json
import logging
from typing import Dict, Any, List, Optional
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    @staticmethod
    async def generate_feedback(
        candidate_name: str,
        target_role: str,
        match_score: float,
        quality_score: float,
        matched_skills: List[str],
        missing_skills: List[str],
        mistakes: List[Dict[str, Any]],
        learning_headline: str
    ) -> str:
        """
        Generates personalized executive feedback.
        Uses LLM API if key is present; otherwise falls back to intelligent rule-based synthesis.
        """
        if settings.LLM_API_KEY:
            try:
                # Attempt call to Gemini or compatible OpenAI endpoint
                async with httpx.AsyncClient(timeout=10.0) as client:
                    # Generic Gemini API call if key starts with AIza
                    if settings.LLM_API_KEY.startswith("AIza"):
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.LLM_API_KEY}"
                        prompt = f"""
You are an expert tech recruiter and resume coach.
Review this candidate profile:
Candidate: {candidate_name}
Target Role: {target_role}
Match Score: {match_score}%
Resume Quality Score: {quality_score}/100
Strengths: {', '.join(matched_skills[:6])}
Key Gaps: {', '.join(missing_skills[:4])}
Top Issues: {', '.join([m['issue'] for m in mistakes[:3]])}

Provide a concise 3-paragraph executive coaching summary:
1. Candidate profile summary and competitive strengths.
2. The most critical gap to bridge for the {target_role} role.
3. Top high-leverage fixes to improve interview callback rate.
"""
                        resp = await client.post(url, json={
                            "contents": [{"parts": [{"text": prompt}]}]
                        })
                        if resp.status_code == 200:
                            data = resp.json()
                            candidate_text = data["candidates"][0]["content"]["parts"][0]["text"]
                            return candidate_text.strip()
            except Exception as e:
                logger.warning(f"LLM API request failed, falling back to rule-based summary: {e}")

        # Rule-based fallback summary
        return LLMService._generate_rule_based_summary(
            candidate_name, target_role, match_score, quality_score,
            matched_skills, missing_skills, mistakes, learning_headline
        )

    @staticmethod
    def _generate_rule_based_summary(
        candidate_name: str,
        target_role: str,
        match_score: float,
        quality_score: float,
        matched_skills: List[str],
        missing_skills: List[str],
        mistakes: List[Dict[str, Any]],
        learning_headline: str
    ) -> str:
        name = candidate_name if candidate_name and candidate_name != "Candidate" else "The candidate"
        
        # Paragraph 1: Profile & Strengths
        if matched_skills:
            skills_str = ", ".join(matched_skills[:4])
            p1 = f"{name} demonstrates a solid technical foundation, showing verified proficiency in {skills_str}. For the **{target_role}** position, the resume achieves an initial match score of **{match_score}%**, with a documented Resume Quality Score of **{quality_score}/100**."
        else:
            p1 = f"{name} presents a versatile background with transferable engineering skills. For the target **{target_role}** role, the profile currently scores **{match_score}%**, offering substantial upside with targeted alignment."

        # Paragraph 2: Skill Growth Opportunity
        if missing_skills:
            miss_str = ", ".join(missing_skills[:3])
            p2 = f"To maximize market competitiveness for {target_role}, the most strategic growth area is mastering **{miss_str}**. {learning_headline}. Integrating these technologies through hands-on portfolio projects will directly elevate ATS ranking and technical interview readiness."
        else:
            p2 = f"The candidate meets the primary core technical requirements for {target_role}. Focus should now shift to architecting advanced production systems, optimizing system bottlenecks, and highlighting leadership."

        # Paragraph 3: Resume Presentation & Fixes
        critical_mistakes = [m for m in mistakes if m.get("severity") == "Critical"]
        warning_mistakes = [m for m in mistakes if m.get("severity") == "Warning"]

        if critical_mistakes:
            p3 = f"**Immediate Action Required:** Address {len(critical_mistakes)} critical resume formatting issue(s) ({critical_mistakes[0]['category']}: {critical_mistakes[0]['issue']}). Resolving these will prevent automated ATS filtering and boost overall presentation quality."
        elif warning_mistakes:
            p3 = f"**Key Polishing Tip:** Elevate bullet points by incorporating quantifiable metrics (e.g. latency, scale, revenue) and active power verbs, ensuring all claimed skills are backed by concrete achievements in work experience."
        else:
            p3 = f"**Polishing Tip:** The resume structure is exceptionally clean and ATS-compliant. Ensure project bullet points consistently quantify outcomes using the Google XYZ formula to impress technical hiring managers."

        return f"{p1}\n\n{p2}\n\n{p3}"


llm_service = LLMService()
