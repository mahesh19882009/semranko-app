import logging
import io
import csv
from datetime import datetime
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models import Keyword, RankResult, Competitor, Project

logger = logging.getLogger(__name__)


def generate_csv_report(project_id: str, start_date: str, end_date: str) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["RankCare Export Report"])
    writer.writerow([f"Project ID: {project_id}"])
    writer.writerow([f"Date Range: {start_date} to {end_date}"])
    writer.writerow([f"Generated: {datetime.utcnow().isoformat()}"])
    writer.writerow([])

    writer.writerow(["Keywords"])
    writer.writerow(["Keyword", "KD", "CPC", "Competition", "Backlinks", "Domains", "Intent", "Position", "AI"])
    writer.writerow([])

    return output.getvalue().encode("utf-8")


def stream_project_keywords_csv(db: Session, project_id: str) -> io.StringIO:
    keywords = db.scalars(
        select(Keyword).where(Keyword.projectId == project_id)
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Keyword", "KD", "CPC", "Competition", "Backlinks", "Domains", "Intent", "Position", "AI"])

    for kw in keywords:
        writer.writerow([
            kw.keyword,
            kw.kd or "",
            kw.cpc or "",
            kw.competition or "",
            kw.backlinks or "",
            kw.referring_domains or "",
            kw.intent or "",
            kw.position or "",
            kw.ai_badge or "",
        ])

    output.seek(0)
    return output


def generate_pdf_report(project_id: str, start_date: str, end_date: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("RankCare Export Report", styles["Title"]))
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph(f"Project ID: {project_id}", styles["Normal"]))
    story.append(Paragraph(f"Date Range: {start_date} to {end_date}", styles["Normal"]))
    story.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * inch))

    data = [["Keyword", "Location", "Volume", "KD", "CPC", "Competition"]]
    table = Table(data, colWidths=[1.5 * inch] * 6)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 12),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
