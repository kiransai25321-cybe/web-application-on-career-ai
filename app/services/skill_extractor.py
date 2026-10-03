import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import spacy
from spacy.matcher import PhraseMatcher
from app.config import settings

# Load spaCy NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = spacy.blank("en")


class SkillExtractor:
    def __init__(self, skills_data_path: Optional[Path] = None):
        if skills_data_path is None:
            skills_data_path = settings.BASE_DIR / "app" / "data" / "skills.json"

        with open(skills_data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.categories_data = data.get("categories", {})
        self.canonical_skills: Dict[str, str] = {}  # skill_name -> category
        self.alias_to_canonical: Dict[str, str] = {}  # alias_lower -> canonical_name

        self.matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

        for category, skills_list in self.categories_data.items():
            for item in skills_list:
                c_name = item["name"]
                self.canonical_skills[c_name] = category
                self.alias_to_canonical[c_name.lower()] = c_name
                
                patterns = [nlp.make_doc(c_name)]
                for alias in item.get("aliases", []):
                    self.alias_to_canonical[alias.lower()] = c_name
                    patterns.append(nlp.make_doc(alias))

                self.matcher.add(c_name, patterns)

    def extract_skills_from_text(self, text: str) -> Set[str]:
        """Extracts unique canonical skill names from a string of text."""
        doc = nlp(text)
        matches = self.matcher(doc)
        found_skills: Set[str] = set()

        for match_id, start, end in matches:
            rule_id = nlp.vocab.strings[match_id]
            if rule_id in self.canonical_skills:
                found_skills.add(rule_id)
            else:
                span_text = doc[start:end].text.lower()
                canonical = self.alias_to_canonical.get(span_text, rule_id)
                found_skills.add(canonical)

        return found_skills

    def extract_and_attribute_skills(
        self,
        full_text: str,
        sections: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Extracts skills and attributes whether each skill is demonstrated in Experience/Projects
        or merely listed in Skills/Summary.
        """
        all_skills = self.extract_skills_from_text(full_text)

        skills_section_text = sections.get("skills", "") + "\n" + sections.get("summary", "")
        experience_section_text = sections.get("experience", "") + "\n" + sections.get("projects", "")

        skills_section_found = self.extract_skills_from_text(skills_section_text)
        experience_found = self.extract_skills_from_text(experience_section_text)

        categorized: Dict[str, List[Dict[str, Any]]] = {}
        for cat in self.categories_data.keys():
            categorized[cat] = []

        total_demonstrated = 0
        total_listed_only = 0
        flat_skills: List[Dict[str, Any]] = []

        for skill in sorted(all_skills):
            category = self.canonical_skills.get(skill, "Other")
            if category not in categorized:
                categorized[category] = []

            # Demonstrated if it appears in experience/projects or if no explicit sections were parsed
            is_demonstrated = (skill in experience_found) or (not experience_section_text.strip())
            
            # If resume has an experience section, but the skill ONLY appears in skills list
            if experience_section_text.strip() and (skill not in experience_found) and (skill in skills_section_found or skill in all_skills):
                is_demonstrated = False

            if is_demonstrated:
                total_demonstrated += 1
            else:
                total_listed_only += 1

            skill_entry = {
                "name": skill,
                "category": category,
                "demonstrated": is_demonstrated,
                "location": "Experience/Projects" if is_demonstrated else "Skills Section Only"
            }
            categorized[category].append(skill_entry)
            flat_skills.append(skill_entry)

        # Filter empty categories
        categorized = {k: v for k, v in categorized.items() if v}

        return {
            "all_skills": sorted(list(all_skills)),
            "flat_skills": flat_skills,
            "categorized": categorized,
            "total_count": len(all_skills),
            "demonstrated_count": total_demonstrated,
            "listed_only_count": total_listed_only,
        }

    def extract_candidate_metadata(self, full_text: str, sections: Dict[str, str]) -> Dict[str, Any]:
        """
        Extracts candidate's Name, Email, Phone, Links, and estimated Years of Experience.
        """
        # Email
        email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b", full_text)
        email = email_match.group(0) if email_match else ""

        # Phone
        phone_match = re.search(
            r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b",
            full_text
        )
        phone = phone_match.group(0).strip() if phone_match else ""

        # Links (LinkedIn, GitHub, Portfolio)
        linkedin_match = re.search(r"(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/[A-Za-z0-9_-]+", full_text, re.I)
        linkedin = linkedin_match.group(0) if linkedin_match else ""

        github_match = re.search(r"(?:https?:\/\/)?(?:www\.)?github\.com\/[A-Za-z0-9_-]+", full_text, re.I)
        github = github_match.group(0) if github_match else ""

        # Candidate Name Extraction
        header_text = sections.get("header", "")
        candidate_name = ""

        # Try spaCy NER on header
        if header_text:
            doc_header = nlp(header_text[:300])
            for ent in doc_header.ents:
                if ent.label_ == "PERSON" and len(ent.text.split()) >= 2 and not any(ch.isdigit() for ch in ent.text):
                    candidate_name = ent.text.strip()
                    break

        # Fallback to first non-empty line of resume if name not found by NER
        if not candidate_name:
            lines = [l.strip() for l in full_text.splitlines() if l.strip()]
            for l in lines[:5]:
                # If line is short, doesn't contain @ or http or digits
                if 2 <= len(l.split()) <= 4 and "@" not in l and "http" not in l and not any(c.isdigit() for c in l):
                    candidate_name = l
                    break

        # Estimated Years of Experience
        years_of_experience = self._estimate_experience_years(full_text, sections.get("experience", ""))

        return {
            "name": candidate_name or "Candidate",
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github,
            "years_of_experience": years_of_experience,
        }

    def _estimate_experience_years(self, full_text: str, experience_text: str) -> float:
        """
        Estimates total years of experience from date patterns or explicit mentions.
        """
        # Check for explicit mention like "5+ years of experience" or "over 3 years"
        explicit_match = re.search(r"(\d+(?:\.\d+)?)\+?\s*years(?:\s+of)?\s+experience", full_text, re.I)
        if explicit_match:
            try:
                return float(explicit_match.group(1))
            except ValueError:
                pass

        target_text = experience_text if experience_text.strip() else full_text
        year_matches = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", target_text)]
        
        if year_matches:
            # Filter reasonable range
            valid_years = [y for y in year_matches if 1990 <= y <= 2030]
            if valid_years:
                min_year = min(valid_years)
                # If "present" or "current" in experience, max year is current year (2026)
                if re.search(r"\b(present|current|now)\b", target_text, re.I):
                    max_year = 2026
                else:
                    max_year = max(valid_years)
                
                diff = max_year - min_year
                if 0 <= diff <= 40:
                    return float(diff) if diff > 0 else 1.0

        return 1.0


# Singleton extractor
skill_extractor = SkillExtractor()
