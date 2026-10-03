from datetime import datetime
import json
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    google_id = Column(String(100), nullable=True, index=True)
    name = Column(String(100), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    analyses = relationship(
        "Analysis",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(Analysis.created_at)"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "name": self.name or self.username,
            "has_password": bool(self.password_hash),
            "google_id": self.google_id,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False, default="pdf")
    selected_role = Column(String(100), nullable=False, default="Full Stack Developer")
    match_score = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, nullable=False, default=0.0)

    # Serialized JSON fields
    parsed_text = Column(Text, nullable=True)
    contact_info_json = Column(Text, nullable=True, default="{}")
    skills_json = Column(Text, nullable=True, default="{}")
    recommended_roles_json = Column(Text, nullable=True, default="[]")
    match_details_json = Column(Text, nullable=True, default="{}")
    learning_plan_json = Column(Text, nullable=True, default="{}")
    mistakes_json = Column(Text, nullable=True, default="[]")
    llm_summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="analyses")

    def get_contact_info(self):
        try:
            return json.loads(self.contact_info_json or "{}")
        except Exception:
            return {}

    def get_skills(self):
        try:
            return json.loads(self.skills_json or "{}")
        except Exception:
            return {}

    def get_recommended_roles(self):
        try:
            return json.loads(self.recommended_roles_json or "[]")
        except Exception:
            return []

    def get_match_details(self):
        try:
            return json.loads(self.match_details_json or "{}")
        except Exception:
            return {}

    def get_learning_plan(self):
        try:
            return json.loads(self.learning_plan_json or "{}")
        except Exception:
            return {}

    def get_mistakes(self):
        try:
            return json.loads(self.mistakes_json or "[]")
        except Exception:
            return []

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "selected_role": self.selected_role,
            "match_score": self.match_score,
            "quality_score": self.quality_score,
            "contact_info": self.get_contact_info(),
            "skills": self.get_skills(),
            "recommended_roles": self.get_recommended_roles(),
            "match_details": self.get_match_details(),
            "learning_plan": self.get_learning_plan(),
            "mistakes": self.get_mistakes(),
            "llm_summary": self.llm_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
