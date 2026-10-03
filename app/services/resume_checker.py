import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from spellchecker import SpellChecker
from app.config import settings

# Initialize spell checker
spell = SpellChecker()

# Common technical and resume terms to ignore in spell checking
TECH_WHITELIST: Set[str] = {
    "api", "apis", "frontend", "backend", "fullstack", "devops", "cloud", "saas", "paas",
    "fastapi", "django", "flask", "react", "vue", "angular", "node", "nodejs", "typescript",
    "javascript", "postgres", "postgresql", "mysql", "sqlite", "mongodb", "redis", "docker",
    "kubernetes", "k8s", "aws", "gcp", "azure", "linux", "git", "github", "gitlab", "jira",
    "scrum", "agile", "sql", "nosql", "ci", "cd", "graphql", "oauth", "jwt", "rest", "restful",
    "html", "css", "tailwind", "bootstrap", "pydantic", "sqlalchemy", "numpy", "pandas",
    "scikit", "sklearn", "pytorch", "tensorflow", "keras", "opencv", "matplotlib", "seaborn",
    "airflow", "spark", "hadoop", "microservices", "json", "xml", "yaml", "crm", "kpi", "kpis",
    "ui", "ux", "sdk", "sdks", "orm", "crud", "etl", "regex", "datetime", "linkedin", "async",
    "sync", "boolean", "uuid", "repo", "repos", "pr", "prs", "config", "init", "env", "scalable",
    "refactor", "refactored", "codebase", "analytics", "algo", "algos", "algorithms"
}
spell.word_frequency.load_words(TECH_WHITELIST)


class ResumeChecker:
    def __init__(self):
        # Load action verbs and buzzwords
        verbs_path = settings.BASE_DIR / "app" / "data" / "action_verbs.json"
        buzzwords_path = settings.BASE_DIR / "app" / "data" / "buzzwords.json"

        with open(verbs_path, "r", encoding="utf-8") as f:
            self.action_verbs_data = json.load(f)

        with open(buzzwords_path, "r", encoding="utf-8") as f:
            self.buzzwords_data = json.load(f)

        self.weak_phrases = self.action_verbs_data.get("weak_phrases", [])
        self.strong_verbs = set(self.action_verbs_data.get("strong_verbs", []))
        self.replacements = self.action_verbs_data.get("suggested_replacements", {})
        self.buzzwords = self.buzzwords_data.get("buzzwords", [])

    def audit_resume(
        self,
        full_text: str,
        sections: Dict[str, str],
        metadata: Dict[str, Any],
        extracted_skills: Dict[str, Any],
        contact_info: Dict[str, Any],
        target_role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes comprehensive rule-based checks and returns structured mistakes,
        Resume Quality Score (0-100), and improvement potential.
        """
        issues: List[Dict[str, Any]] = []

        # 1. Contact Information Checks
        self._check_contact_info(contact_info, full_text, issues)

        # 2. Section Structure Checks
        self._check_sections(sections, issues)

        # 3. Resume Length & Page Budget
        self._check_length(metadata, full_text, issues)

        # 4. Weak Action Verbs & Passive Voice
        self._check_action_verbs(sections, full_text, issues)

        # 5. Measurable Metrics & Quantifiable Impact
        self._check_measurable_results(sections, full_text, issues)

        # 6. Skills Listed vs. Demonstrated
        self._check_undemonstrated_skills(extracted_skills, sections, issues)

        # 7. Buzzwords & Clichés
        self._check_buzzwords(full_text, issues)

        # 8. Inappropriate Personal Information
        self._check_inappropriate_info(full_text, issues)

        # 9. First-person Pronouns & Dense Paragraphs
        self._check_style_and_pronouns(sections, full_text, issues)

        # 10. Repeated Words & Spelling Checks
        self._check_spelling_and_repetition(full_text, issues)

        # 11. ATS Readability & Formatting
        self._check_ats_friendliness(metadata, full_text, target_role, issues)

        # Calculate Quality Score
        quality_score, deductions = self._calculate_quality_score(issues)
        potential_score = min(100.0, max(quality_score + 25.0, 95.0))

        critical_count = sum(1 for i in issues if i["severity"] == "Critical")
        warning_count = sum(1 for i in issues if i["severity"] == "Warning")
        tip_count = sum(1 for i in issues if i["severity"] == "Tip")

        return {
            "quality_score": round(quality_score, 1),
            "potential_score": round(potential_score, 1),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "tip_count": tip_count,
            "total_issues": len(issues),
            "issues": issues,
            "deductions": deductions,
        }

    def _check_contact_info(self, contact: Dict[str, Any], full_text: str, issues: List[Dict[str, Any]]):
        # Email Check
        email = contact.get("email", "")
        if not email:
            issues.append({
                "category": "Contact Information",
                "severity": "Critical",
                "location": "Header / Contact Info",
                "issue": "No email address detected.",
                "why": "Recruiters and automated ATS systems cannot contact you for interview invitations without an email.",
                "fix": "Add a prominent professional email address (e.g., firstname.lastname@gmail.com) directly in the header."
            })
        else:
            # Unprofessional email check
            user_part = email.split("@")[0].lower()
            unprofessional_keywords = ["cool", "gamer", "sexy", "hot", "party", "420", "69", "ninja", "hacker", "dude", "player"]
            if any(k in user_part for k in unprofessional_keywords):
                issues.append({
                    "category": "Contact Information",
                    "severity": "Critical",
                    "location": f"Email: {email}",
                    "issue": "Unprofessional email address username detected.",
                    "why": "Casual nicknames, slang, or suggestive terms in email handles create an immediate negative first impression.",
                    "fix": f"Create and use a clean professional address like {user_part.replace('cool', '').replace('party', '') or 'yourname'}@gmail.com."
                })

        # Phone Check
        if not contact.get("phone"):
            issues.append({
                "category": "Contact Information",
                "severity": "Critical",
                "location": "Header / Contact Info",
                "issue": "No phone number detected.",
                "why": "Recruiters often conduct initial screening calls via phone.",
                "fix": "Include your mobile number with country/area code: e.g., +1 (555) 019-2834."
            })

        # LinkedIn Check
        if not contact.get("linkedin"):
            issues.append({
                "category": "Contact Information",
                "severity": "Warning",
                "location": "Header / Social Links",
                "issue": "Missing LinkedIn profile URL.",
                "why": "Over 90% of technical recruiters review LinkedIn profiles to verify background and recommendations.",
                "fix": "Add your customized LinkedIn URL: linkedin.com/in/yourname."
            })

        # GitHub Check
        if not contact.get("github") and ("developer" in full_text.lower() or "software" in full_text.lower() or "engineer" in full_text.lower()):
            issues.append({
                "category": "Contact Information",
                "severity": "Warning",
                "location": "Header / Links",
                "issue": "Missing GitHub profile link for a technical candidate.",
                "why": "Engineering hiring teams want to inspect your real code, project commits, and documentation standards.",
                "fix": "Add a link to your active GitHub profile: github.com/yourhandle."
            })

    def _check_sections(self, sections: Dict[str, str], issues: List[Dict[str, Any]]):
        required_sections = [
            ("summary", "Summary / Objective", "Warning", "A 2-3 sentence executive summary anchors your profile and highlights your strongest strengths."),
            ("skills", "Skills Section", "Critical", "Without a dedicated technical skills section, ATS keyword matchers may miss your core proficiencies."),
            ("experience", "Work Experience", "Critical", "Work experience is the primary section hiring managers evaluate for evidence of competence."),
            ("education", "Education", "Critical", "Education details verify required degree benchmarks or academic certifications.")
        ]

        for sec_key, sec_name, sev, reason in required_sections:
            if sec_key not in sections or len(sections[sec_key].strip()) < 15:
                issues.append({
                    "category": "Resume Structure",
                    "severity": sev,
                    "location": f"Missing Section: {sec_name}",
                    "issue": f"The '{sec_name}' section was not found or is empty.",
                    "why": reason,
                    "fix": f"Add a clearly labeled '{sec_name}' section with standardized heading formatting."
                })

        # Optional Projects section
        if "projects" not in sections:
            issues.append({
                "category": "Resume Structure",
                "severity": "Tip",
                "location": "Missing Section: Projects",
                "issue": "No dedicated 'Projects' section identified.",
                "why": "Projects demonstrate hands-on application of skills outside of company-restricted codebases.",
                "fix": "Include 2-3 notable projects with tech stacks used, live links, and measurable outcomes."
            })

    def _check_length(self, metadata: Dict[str, Any], full_text: str, issues: List[Dict[str, Any]]):
        word_count = metadata.get("word_count", len(full_text.split()))
        page_count = metadata.get("page_count", 1)

        if word_count < 180:
            issues.append({
                "category": "Resume Length",
                "severity": "Critical",
                "location": f"Word Count: {word_count} words",
                "issue": "Resume is too short and lacks sufficient technical depth.",
                "why": "Resumes under 200 words fail to demonstrate required breadth and usually miss critical ATS keywords.",
                "fix": "Expand your experience bullets with details on technologies used, problems solved, and measurable impact."
            })
        elif word_count > 1100:
            issues.append({
                "category": "Resume Length",
                "severity": "Warning",
                "location": f"Word Count: {word_count} words (~{page_count} pages)",
                "issue": "Resume is overly verbose for typical screening review.",
                "why": "Recruiters spend an average of 7 seconds reviewing a resume. Excessive length dilutes key accomplishments.",
                "fix": "Condense bullets, remove redundant legacy history, and aim for a tight 1-2 page maximum."
            })

    def _check_action_verbs(self, sections: Dict[str, str], full_text: str, issues: List[Dict[str, Any]]):
        exp_text = (sections.get("experience", "") + "\n" + sections.get("projects", "")).strip() or full_text
        lines = [l.strip() for l in exp_text.splitlines() if l.strip()]

        found_weak_count = 0
        for line in lines:
            line_lower = line.lower()
            for weak in self.weak_phrases:
                if weak in line_lower:
                    found_weak_count += 1
                    sugg = self.replacements.get(weak, ["Spearheaded", "Architected", "Delivered"])[0]
                    clean_quote = line[:85] + "..." if len(line) > 85 else line
                    if found_weak_count <= 3:  # Report top 3 occurrences
                        issues.append({
                            "category": "Action Verbs",
                            "severity": "Warning",
                            "location": f"Bullet: \"{clean_quote}\"",
                            "issue": f"Passive phrasing detected ('{weak}').",
                            "why": "Phrases like 'responsible for' describe job descriptions rather than your personal achievements and ownership.",
                            "fix": f"Replace '{weak}' with strong action verbs like '{sugg}' or 'Engineered'."
                        })
                    break

    def _check_measurable_results(self, sections: Dict[str, str], full_text: str, issues: List[Dict[str, Any]]):
        exp_text = (sections.get("experience", "") + "\n" + sections.get("projects", "")).strip() or full_text
        lines = [l.strip() for l in exp_text.splitlines() if len(l.strip()) > 30]

        unmeasured_lines = []
        for line in lines:
            # Check if line looks like a bullet
            clean_line = re.sub(r"^\(cid:\d+\)\s*", "", line)
            if line.startswith(("-", "*", "•", "–")) or "(cid:" in line or any(clean_line.lower().startswith(v) for v in ["built", "developed", "led", "created", "worked", "responsible", "assisted", "handled"]):
                # Clean font artifacts like (cid:127) and date years (2020, 2024) before checking for quantifiable metrics
                text_for_metrics = re.sub(r"\(cid:\d+\)", "", line)
                text_for_metrics = re.sub(r"\b(19|20)\d{2}\b", "", text_for_metrics)
                has_metric = bool(re.search(r"(\d+[\d,.]*|\b\d+%\b|\$[\d,]+|\b\d+x\b)", text_for_metrics))
                if not has_metric:
                    unmeasured_lines.append(line)

        if len(unmeasured_lines) >= 2:
            sample_bullet = unmeasured_lines[0]
            clean_sample = sample_bullet[:80] + "..." if len(sample_bullet) > 80 else sample_bullet
            issues.append({
                "category": "Measurable Impact",
                "severity": "Warning",
                "location": f"Bullet: \"{clean_sample}\"",
                "issue": "Bullet point lacks quantifiable metrics, percentages, or measurable outcomes.",
                "why": "Top-tier resumes use the Google XYZ formula: 'Accomplished [X] as measured by [Y], by doing [Z]'. Without metrics, claims are unverifiable.",
                "fix": "Add numbers: latency reduced (e.g. 40%), users supported (e.g. 10,000+), revenue generated, or sprint velocity improvement."
            })

    def _check_undemonstrated_skills(self, extracted_skills: Dict[str, Any], sections: Dict[str, str], issues: List[Dict[str, Any]]):
        flat_skills = extracted_skills.get("flat_skills", [])
        undemonstrated = [s["name"] for s in flat_skills if not s.get("demonstrated", True)]

        if undemonstrated and sections.get("experience"):
            top_sample = ", ".join(undemonstrated[:4])
            issues.append({
                "category": "Skill Demonstration",
                "severity": "Warning",
                "location": "Skills Section vs. Experience",
                "issue": f"{len(undemonstrated)} skills are listed in your Skills section but never mentioned in Experience or Projects.",
                "why": f"Hiring managers discount 'keyword dumping' if skills ({top_sample}) aren't demonstrated with real work context.",
                "fix": f"Integrate {undemonstrated[0]} into your work experience or project bullets showing how you applied it."
            })

    def _check_buzzwords(self, full_text: str, issues: List[Dict[str, Any]]):
        full_lower = full_text.lower()
        found_buzzwords = []

        for b in self.buzzwords:
            term = b["term"]
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, full_lower):
                found_buzzwords.append(b)

        for b in found_buzzwords[:3]:  # Top 3 buzzwords
            issues.append({
                "category": "Clichés & Buzzwords",
                "severity": "Tip",
                "location": f"Keyword: \"{b['term']}\"",
                "issue": f"Overused buzzword '{b['term']}' found.",
                "why": b["reason"],
                "fix": f"Replace with: \"{b['replacement']}\""
            })

    def _check_inappropriate_info(self, full_text: str, issues: List[Dict[str, Any]]):
        # Age / DOB
        if re.search(r"\b(date of birth|dob|age:\s*\d{2}|born in \d{4})\b", full_text, re.I):
            issues.append({
                "category": "Personal Info",
                "severity": "Critical",
                "location": "Header / Personal Details",
                "issue": "Age or Date of Birth included.",
                "why": "Modern hiring laws prohibit age bias. Including birth dates or age can trigger compliance disqualifications.",
                "fix": "Remove age, date of birth, and graduation years older than 15 years."
            })

        # Marital Status / Gender / Religion
        if re.search(r"\b(marital status|single|married|gender:\s*(male|female)|nationality:)\b", full_text, re.I):
            issues.append({
                "category": "Personal Info",
                "severity": "Critical",
                "location": "Personal Info Section",
                "issue": "Inappropriate demographic or marital information detected.",
                "why": "Personal details like marital status or gender are completely irrelevant to job qualification and cause bias.",
                "fix": "Remove marital status, gender, religion, and nationality from your resume."
            })

        # Photo mention
        if re.search(r"\b(photo attached|my photo|see photo)\b", full_text, re.I):
            issues.append({
                "category": "ATS Readability",
                "severity": "Warning",
                "location": "Resume Body",
                "issue": "Reference to headshot or photo found.",
                "why": "US and UK ATS systems often reject resumes with photos to avoid anti-discrimination liability.",
                "fix": "Remove headshots and photo references for US/UK/global tech roles."
            })

    def _check_style_and_pronouns(self, sections: Dict[str, str], full_text: str, issues: List[Dict[str, Any]]):
        # First-person pronouns (I, my, me)
        exp_text = sections.get("experience", "") + "\n" + sections.get("projects", "") + "\n" + sections.get("summary", "")
        pronouns_found = re.findall(r"\b(I|my|me|we|our)\b", exp_text)
        if len(pronouns_found) >= 3:
            issues.append({
                "category": "Writing Style",
                "severity": "Warning",
                "location": "Experience / Summary Bullets",
                "issue": f"Frequent first-person pronouns detected ({len(pronouns_found)} occurrences of 'I', 'my', 'we').",
                "why": "Resumes should be written in telegraphic professional tone starting directly with active verbs, avoiding 'I'.",
                "fix": "Drop 'I created...' or 'My role was...' and write: 'Engineered high-throughput API endpoints...'"
            })

        # Overly long paragraphs
        lines = full_text.splitlines()
        for line in lines:
            if len(line.split()) > 60:
                clean_p = line[:80] + "..."
                issues.append({
                    "category": "Formatting",
                    "severity": "Tip",
                    "location": f"Paragraph: \"{clean_p}\"",
                    "issue": "Overly long text block detected (>60 words in a single block).",
                    "why": "Dense paragraphs of text are skipped by recruiters. Bullet points provide 3x higher readability.",
                    "fix": "Break this paragraph into 2-3 crisp, one-sentence bullet points."
                })
                break

    def _check_spelling_and_repetition(self, full_text: str, issues: List[Dict[str, Any]]):
        # Repeated consecutive words (e.g. "the the", "with with")
        repeat_match = re.search(r"\b([a-zA-Z]{3,})\s+\1\b", full_text, re.I)
        if repeat_match:
            word = repeat_match.group(1)
            issues.append({
                "category": "Proofreading",
                "severity": "Warning",
                "location": f"Text: \"{word} {word}\"",
                "issue": f"Accidental duplicated word '{word} {word}' found.",
                "why": "Typographical errors signal a lack of attention to detail to hiring managers.",
                "fix": f"Delete the repeated word '{word}'."
            })

        # Basic spell checker on alphabetic tokens
        words = re.findall(r"\b[a-zA-Z]{4,15}\b", full_text)
        sample_words = [w.lower() for w in words[:150] if w.lower() not in TECH_WHITELIST]
        unknown = spell.unknown(sample_words)

        # Filter out common names or acronyms
        filtered_misspelled = [w for w in unknown if not w.isupper() and len(w) > 3]
        if filtered_misspelled:
            bad_word = list(filtered_misspelled)[0]
            candidate_fix = spell.correction(bad_word) or "correct spelling"
            issues.append({
                "category": "Proofreading",
                "severity": "Tip",
                "location": f"Word: '{bad_word}'",
                "issue": f"Potential spelling mistake detected: '{bad_word}'.",
                "why": "Spelling errors can reduce recruiter confidence in your written communication skills.",
                "fix": f"Did you mean '{candidate_fix}'?"
            })

    def _check_ats_friendliness(self, metadata: Dict[str, Any], full_text: str, target_role: Optional[str], issues: List[Dict[str, Any]]):
        if metadata.get("has_tables", False):
            issues.append({
                "category": "ATS Readability",
                "severity": "Tip",
                "location": "Document Layout",
                "issue": "Tables or multi-column grids detected.",
                "why": "Older Applicant Tracking Systems (ATS) may parse multi-column tables in horizontal reading order, scrambling text.",
                "fix": "Use a clean, single-column linear layout with standard left-aligned text."
            })

    def _calculate_quality_score(self, issues: List[Dict[str, Any]]) -> (float, Dict[str, float]):
        score = 100.0
        deductions = {"critical": 0.0, "warning": 0.0, "tip": 0.0}

        for issue in issues:
            sev = issue["severity"]
            if sev == "Critical":
                deduction = 12.0
                deductions["critical"] += deduction
            elif sev == "Warning":
                deduction = 6.0
                deductions["warning"] += deduction
            else:
                deduction = 2.5
                deductions["tip"] += deduction
            score -= deduction

        score = max(15.0, min(100.0, score))
        return score, deductions


# Singleton resume checker
resume_checker = ResumeChecker()
