from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def generate_pdf(output_path, resume_fields, matched, missing, match_percent):
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, height - 50, "📄 Smart ATS - Resume Match Report")

    c.setFont("Helvetica", 12)
    c.drawString(40, height - 100, f"Email: {resume_fields['email']}")
    c.drawString(40, height - 120, f"Phone: {resume_fields['phone']}")
    c.drawString(40, height - 140, f"Match Percentage: {match_percent}%")

    c.drawString(40, height - 180, "✅ Matched Skills:")
    y = height - 200
    for skill in matched:
        c.drawString(60, y, f"- {skill}")
        y -= 15

    c.drawString(40, y - 10, "❌ Missing Skills:")
    y -= 30
    for skill in missing:
        c.drawString(60, y, f"- {skill}")
        y -= 15

    c.save()
