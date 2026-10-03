import io
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)


def generate_pdf_report(analysis_dict: Dict[str, Any]) -> bytes:
    """
    Generates a professional PDF audit report using ReportLab.
    Returns the PDF as raw bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=12
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )

    meta_bold = ParagraphStyle(
        "MetaBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # Title & Metadata
    candidate_info = analysis_dict.get("contact_info", {})
    candidate_name = candidate_info.get("name") or "Candidate"
    target_role = analysis_dict.get("selected_role", "Software Engineer")
    match_score = analysis_dict.get("match_score", 0.0)
    quality_score = analysis_dict.get("quality_score", 0.0)
    created_at = analysis_dict.get("created_at", "")[:10]

    story.append(Paragraph("AI Resume Analyzer", title_style))
    story.append(Paragraph(f"Comprehensive Audit Report & Career Roadmap • Generated {created_at}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=12))

    # Candidate & Score Summary Table
    meta_table_data = [
        [
            Paragraph("<b>Candidate Name:</b>", meta_bold),
            Paragraph(candidate_name, body_style),
            Paragraph("<b>Target Role:</b>", meta_bold),
            Paragraph(target_role, body_style),
        ],
        [
            Paragraph("<b>Email:</b>", meta_bold),
            Paragraph(candidate_info.get("email") or "Not detected", body_style),
            Paragraph("<b>Match Score:</b>", meta_bold),
            Paragraph(f"<b>{match_score}%</b>", ParagraphStyle("MatchH", parent=body_style, textColor=colors.HexColor("#2563eb"))),
        ],
        [
            Paragraph("<b>Phone:</b>", meta_bold),
            Paragraph(candidate_info.get("phone") or "Not detected", body_style),
            Paragraph("<b>Quality Score:</b>", meta_bold),
            Paragraph(f"<b>{quality_score} / 100</b>", ParagraphStyle("QualH", parent=body_style, textColor=colors.HexColor("#16a34a"))),
        ],
    ]

    meta_table = Table(meta_table_data, colWidths=[100, 170, 100, 170])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Executive Summary
    llm_summary = analysis_dict.get("llm_summary", "")
    if llm_summary:
        story.append(Paragraph("Executive Coaching Summary", h2_style))
        for para in llm_summary.split("\n\n"):
            clean_para = para.replace("**", "<b>").replace("<b>", "<b>", 1)  # standard bold
            # replace pairs of **
            clean_para = re_replace_bold(clean_para)
            story.append(Paragraph(clean_para, body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    # Skills Breakdown Table
    story.append(Paragraph("Extracted Skills Overview", h2_style))
    skills_data = analysis_dict.get("skills", {})
    categorized = skills_data.get("categorized", {})
    
    skill_rows = [["Category", "Demonstrated in Work Experience", "Listed in Skills Section Only"]]
    for cat_name, skill_items in categorized.items():
        dem_list = [s["name"] for s in skill_items if s.get("demonstrated")]
        listed_list = [s["name"] for s in skill_items if not s.get("demonstrated")]
        skill_rows.append([
            Paragraph(f"<b>{cat_name}</b>", meta_bold),
            Paragraph(", ".join(dem_list) if dem_list else "None demonstrated", body_style),
            Paragraph(", ".join(listed_list) if listed_list else "—", body_style),
        ])

    if len(skill_rows) > 1:
        skills_table = Table(skill_rows, colWidths=[120, 210, 210])
        skills_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(skills_table)
    else:
        story.append(Paragraph("No technical skills were identified.", body_style))

    story.append(Spacer(1, 10))

    # Top Recommended Roles
    recs = analysis_dict.get("recommended_roles", [])
    if recs:
        story.append(Paragraph("Top Recommended Roles Ranking", h2_style))
        rec_rows = [["Role Title", "Fit Score", "Rationale & Top Matched Skills"]]
        for r in recs[:5]:
            matched_str = ", ".join(r.get("matched_skills", [])[:4])
            rec_rows.append([
                Paragraph(f"<b>{r.get('title')}</b>", meta_bold),
                Paragraph(f"<b>{r.get('fit_percentage')}%</b>", ParagraphStyle("FitP", parent=body_style, textColor=colors.HexColor("#2563eb"))),
                Paragraph(f"{r.get('reason')} ({matched_str})", body_style),
            ])
        rec_table = Table(rec_rows, colWidths=[140, 70, 330])
        rec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(rec_table)
        story.append(Spacer(1, 10))

    # 30/60/90 Day Roadmap
    learning_plan = analysis_dict.get("learning_plan", {})
    timeline = learning_plan.get("timeline", {})
    if timeline:
        story.append(Paragraph("Skill Roadmap & 30/60/90-Day Plan", h2_style))
        headline = learning_plan.get("headline", "")
        if headline:
            story.append(Paragraph(f"<b>Target Trajectory:</b> {headline}", body_style))
            story.append(Spacer(1, 4))

        plan_rows = [["Milestone", "Focus Skills", "Key Deliverables & Action Items"]]
        for month_key in ["month_1", "month_2", "month_3"]:
            month_data = timeline.get(month_key, {})
            if month_data:
                plan_rows.append([
                    Paragraph(f"<b>{month_data.get('title')}</b>", meta_bold),
                    Paragraph(", ".join(month_data.get("focus_skills", [])), body_style),
                    Paragraph(f"{month_data.get('description')}<br/><b>Milestone:</b> {month_data.get('milestone')}", body_style),
                ])
        plan_table = Table(plan_rows, colWidths=[130, 110, 300])
        plan_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(plan_table)
        story.append(Spacer(1, 10))

    # Resume Mistakes & Recommended Fixes
    mistakes = analysis_dict.get("mistakes", [])
    if mistakes:
        story.append(Paragraph("Resume Mistakes & Actionable Fixes", h2_style))
        mistake_rows = [["Severity", "Location & Issue", "Why It Matters", "Recommended Fix"]]
        for m in mistakes[:10]:  # Up to top 10 mistakes in PDF
            sev = m.get("severity", "Tip")
            sev_color = colors.HexColor("#dc2626") if sev == "Critical" else (colors.HexColor("#d97706") if sev == "Warning" else colors.HexColor("#2563eb"))
            
            mistake_rows.append([
                Paragraph(f"<b>{sev}</b>", ParagraphStyle("SevS", parent=body_style, textColor=sev_color)),
                Paragraph(f"<b>{m.get('category')}</b><br/>{m.get('location')}<br/>{m.get('issue')}", body_style),
                Paragraph(m.get("why", ""), body_style),
                Paragraph(m.get("fix", ""), body_style),
            ])

        mistake_table = Table(mistake_rows, colWidths=[65, 165, 155, 155])
        mistake_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ]))
        story.append(mistake_table)

    doc.build(story)
    return buffer.getvalue()


def re_replace_bold(text: str) -> str:
    """Helper to convert markdown bold **text** to HTML <b>text</b> for reportlab."""
    import re
    return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)
