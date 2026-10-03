from typing import Dict, Any, List, Optional
from app.services.matcher import job_matcher

SKILL_INSIGHTS: Dict[str, Dict[str, Any]] = {
    "FastAPI": {
        "why": "Standard high-performance async Python framework for modern microservices and AI application APIs.",
        "difficulty": "Intermediate",
        "time": "2-3 weeks",
        "resource": "Official FastAPI Tutorial & Building Production REST APIs",
        "mini_project": "Build an asynchronous CRUD REST API with JWT authentication, dependency injection, and Pydantic validation.",
        "related": ["Python", "Flask", "Django"]
    },
    "Docker": {
        "why": "Essential for containerizing applications, ensuring reproducible builds, and seamless deployment across clouds.",
        "difficulty": "Intermediate",
        "time": "2 weeks",
        "resource": "Docker Docs & Hands-on Containerization Lab",
        "mini_project": "Containerize a multi-container web application with a FastAPI backend, PostgreSQL database, and Redis cache using Docker Compose.",
        "related": ["Linux", "Bash", "CI/CD"]
    },
    "Kubernetes": {
        "why": "The industry standard orchestrator for scaling, managing, and automating containerized microservices in production.",
        "difficulty": "Advanced",
        "time": "4-6 weeks",
        "resource": "Kubernetes The Hard Way & Certified Kubernetes Administrator (CKA) guides",
        "mini_project": "Deploy a containerized application to a local Minikube cluster with Deployments, Services, ConfigMaps, and Ingress routing.",
        "related": ["Docker", "Linux", "Cloud"]
    },
    "PostgreSQL": {
        "why": "The world's most powerful, extensible relational database used by enterprises and startups alike.",
        "difficulty": "Intermediate",
        "time": "2-3 weeks",
        "resource": "PostgreSQL Tutorial & High-Performance Query Optimization Docs",
        "mini_project": "Design a relational e-commerce schema with indexed foreign keys, stored procedures, and complex analytical aggregations.",
        "related": ["SQL", "MySQL", "SQLite"]
    },
    "Redis": {
        "why": "In-memory key-value data store used for sub-millisecond caching, session management, and message queues.",
        "difficulty": "Beginner",
        "time": "1 week",
        "resource": "Redis University & Real-world Caching Patterns",
        "mini_project": "Implement Redis response caching and API rate limiting middleware for high-traffic endpoints.",
        "related": ["PostgreSQL", "FastAPI", "Python"]
    },
    "React": {
        "why": "Dominant frontend library for building modular, responsive, and dynamic user interfaces.",
        "difficulty": "Intermediate",
        "time": "3-4 weeks",
        "resource": "React.dev Interactive Documentation & Scrimba Frontend Path",
        "mini_project": "Develop a responsive dashboard with state management (hooks), dynamic data tables, and client-side filtering.",
        "related": ["JavaScript", "TypeScript", "HTML", "CSS"]
    },
    "TypeScript": {
        "why": "Enforces strict type safety and autocompletion, dramatically reducing bugs in large-scale modern JavaScript projects.",
        "difficulty": "Intermediate",
        "time": "2 weeks",
        "resource": "TypeScript Handbook & Executable Code Exercises",
        "mini_project": "Refactor a JavaScript codebase to strict TypeScript with custom interfaces, generics, and union types.",
        "related": ["JavaScript", "Python", "Java"]
    },
    "AWS": {
        "why": "The largest cloud infrastructure provider offering compute, managed databases, and serverless architectures.",
        "difficulty": "Intermediate",
        "time": "3-5 weeks",
        "resource": "AWS Cloud Practitioner & Solutions Architect documentation",
        "mini_project": "Host a web app on AWS using an EC2 instance or ECS Fargate, S3 static assets, and an RDS PostgreSQL database.",
        "related": ["Linux", "Docker", "DevOps"]
    },
    "CI/CD": {
        "why": "Automates testing, linting, and deployment to deliver reliable software rapidly to users.",
        "difficulty": "Intermediate",
        "time": "1-2 weeks",
        "resource": "GitHub Actions Documentation & Continuous Integration Best Practices",
        "mini_project": "Create a GitHub Actions pipeline that automatically triggers unit tests, builds Docker images, and deploys on merge.",
        "related": ["Git", "GitHub", "Linux", "Docker"]
    },
    "Terraform": {
        "why": "Industry standard declarative Infrastructure as Code (IaC) tool for repeatable cloud provisioning.",
        "difficulty": "Intermediate",
        "time": "2-3 weeks",
        "resource": "HashiCorp Learn Terraform Tutorials",
        "mini_project": "Write Terraform modules to provision a VPC, subnets, security groups, and an EC2 instance with automated state management.",
        "related": ["AWS", "Cloud", "DevOps"]
    },
    "scikit-learn": {
        "why": "The premier Python library for classical machine learning algorithms, preprocessing, and model evaluation.",
        "difficulty": "Intermediate",
        "time": "3 weeks",
        "resource": "Scikit-Learn User Guide & Kaggle Machine Learning Courses",
        "mini_project": "Train and evaluate a supervised classification pipeline with feature scaling, cross-validation, and hyperparameter tuning.",
        "related": ["Python", "pandas", "NumPy"]
    },
    "PyTorch": {
        "why": "Leading deep learning framework for research and production AI, neural networks, and LLM fine-tuning.",
        "difficulty": "Advanced",
        "time": "4-6 weeks",
        "resource": "Deep Learning with PyTorch Book & PyTorch Official Blitz",
        "mini_project": "Train a convolutional neural network for image classification or fine-tune a transformer model for text classification.",
        "related": ["Python", "scikit-learn", "NumPy"]
    },
    "Tableau": {
        "why": "Leading enterprise business intelligence tool for interactive data visualization and storytelling.",
        "difficulty": "Beginner",
        "time": "1-2 weeks",
        "resource": "Tableau Desktop Specialist Training",
        "mini_project": "Build an executive sales dashboard with drill-down filters, calculated fields, and trend forecasts.",
        "related": ["SQL", "Excel", "Data Analysis"]
    }
}


class LearningPlanService:
    @staticmethod
    def generate_roadmap(
        target_role: str,
        current_match_score: float,
        candidate_skills: List[str],
        missing_required: List[str],
        missing_nice_to_have: List[str],
        resume_text: str = ""
    ) -> Dict[str, Any]:
        """
        Generates a comprehensive learning roadmap with:
        - Prioritized missing skills (Must Learn, Should Learn, Trending)
        - Projected match score improvement
        - 30/60/90 day milestone schedule
        - Mini-project ideas for portfolio proof
        """
        candidate_lower = {s.lower() for s in candidate_skills}

        # 1. Must Learn Skills
        must_learn_items = []
        for skill in missing_required:
            must_learn_items.append(
                LearningPlanService._format_skill_insight(skill, "High", candidate_lower)
            )

        # 2. Should Learn Skills
        should_learn_items = []
        for skill in missing_nice_to_have:
            should_learn_items.append(
                LearningPlanService._format_skill_insight(skill, "Medium", candidate_lower)
            )

        # 3. Trending / Bonus Skills
        trending_candidates = ["Large Language Models", "GitHub Actions", "Docker", "FastAPI", "TypeScript"]
        trending_items = []
        for skill in trending_candidates:
            if skill.lower() not in candidate_lower and skill not in missing_required and skill not in missing_nice_to_have:
                trending_items.append(
                    LearningPlanService._format_skill_insight(skill, "Low", candidate_lower)
                )

        # 4. Projected Score Calculation (Learning top 3 missing skills)
        top_3_missing = (missing_required + missing_nice_to_have)[:3]
        simulated_skills = candidate_skills + top_3_missing
        simulated_match = job_matcher.match_role(target_role, resume_text, simulated_skills)
        projected_score = simulated_match["match_score"]
        score_gain = round(max(0.0, projected_score - current_match_score), 1)

        # 5. 30 / 60 / 90 Day Timeline
        day_30_skills = top_3_missing[:1] or (missing_required[:1] if missing_required else ["System Design"])
        day_60_skills = top_3_missing[1:2] or (missing_required[1:2] if len(missing_required) > 1 else ["Testing & CI/CD"])
        day_90_skills = top_3_missing[2:3] or (missing_nice_to_have[:1] if missing_nice_to_have else ["Cloud Deployment"])

        timeline = {
            "month_1": {
                "title": "Month 1 (Days 1–30): Core Foundation & First Proof Project",
                "focus_skills": day_30_skills,
                "description": f"Master the fundamentals of {', '.join(day_30_skills)}. Build a dedicated mini-project showcasing this skill in action.",
                "milestone": f"Complete hands-on project demonstrating {', '.join(day_30_skills)} on GitHub."
            },
            "month_2": {
                "title": "Month 2 (Days 31–60): Architecture & Production Practices",
                "focus_skills": day_60_skills,
                "description": f"Deepen architectural knowledge with {', '.join(day_60_skills)}. Add automated testing, database migrations, and clean documentation.",
                "milestone": f"Integrate {', '.join(day_60_skills)} into an end-to-end multi-tier application."
            },
            "month_3": {
                "title": "Month 3 (Days 61–90): Cloud Deployment & Resume Polishing",
                "focus_skills": day_90_skills,
                "description": f"Bridge the final gap with {', '.join(day_90_skills)}. Deploy live projects with CI/CD and update resume bullets with quantifiable impact metrics.",
                "milestone": f"Publish live demo URL, update resume with new project bullets, and reach target match score of {projected_score}%."
            }
        }

        # Projected impact narrative
        top_skills_names = ", ".join(top_3_missing) if top_3_missing else "key role specializations"
        headline = f"Learn {top_skills_names} to boost your match from {current_match_score}% to {projected_score}% (+{score_gain}%)"

        return {
            "target_role": target_role,
            "current_score": current_match_score,
            "projected_score": projected_score,
            "score_gain": score_gain,
            "headline": headline,
            "top_missing_skills": top_3_missing,
            "must_learn": must_learn_items,
            "should_learn": should_learn_items,
            "trending": trending_items,
            "timeline": timeline,
        }

    @staticmethod
    def _format_skill_insight(skill: str, priority: str, candidate_skills_lower: set) -> Dict[str, Any]:
        info = SKILL_INSIGHTS.get(skill, {
            "why": f"Frequently requested requirement for industry {skill} roles.",
            "difficulty": "Intermediate",
            "time": "2-3 weeks",
            "resource": f"Official {skill} Documentation & Hands-on Projects",
            "mini_project": f"Build and document a production-ready application utilizing {skill}.",
            "related": ["Core Programming", "Software Engineering"]
        })

        # Find helpful related skill user already has
        related_user_has = None
        for r in info.get("related", []):
            if r.lower() in candidate_skills_lower:
                related_user_has = r
                break

        if related_user_has:
            transfer_note = f"Easier to pick up because you already know {related_user_has}."
        else:
            transfer_note = f"Foundational skill with steep learning payoffs."

        return {
            "skill": skill,
            "priority": priority,
            "difficulty": info["difficulty"],
            "time_to_learn": info["time"],
            "why_it_matters": info["why"],
            "resource_type": info["resource"],
            "mini_project_idea": info["mini_project"],
            "related_transfer_note": transfer_note,
        }


# Singleton learning plan service
learning_plan_service = LearningPlanService()
