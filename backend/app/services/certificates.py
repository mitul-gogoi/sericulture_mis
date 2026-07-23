"""Training certificate PDF generation — a single decorative page, not a tabular report
(see services/export.py for those). Reuses the same reportlab toolchain."""
import io
from sqlalchemy.orm import Session

from app.models import TrainingCertificate


def next_certificate_number(db: Session) -> str:
    max_num = 0
    for (number,) in db.query(TrainingCertificate.certificate_number).all():
        try:
            num = int(number.rsplit("-", 1)[-1])
        except (ValueError, AttributeError):
            continue
        max_num = max(max_num, num)
    return f"SERI-CERT-{max_num + 1:06d}"


def render_certificate_pdf(certificate_number: str, participant_name: str, training_topic: str,
                           training_dates: str, venue: str, issued_at: str) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=2.5 * cm, bottomMargin=2.5 * cm,
                            leftMargin=2.5 * cm, rightMargin=2.5 * cm)
    styles = getSampleStyleSheet()
    heading = ParagraphStyle("CertHeading", parent=styles["Title"], alignment=TA_CENTER,
                             textColor=colors.HexColor("#2D5134"), fontSize=26)
    subheading = ParagraphStyle("CertSubheading", parent=styles["Normal"], alignment=TA_CENTER,
                                fontSize=13, textColor=colors.HexColor("#555555"))
    name_style = ParagraphStyle("CertName", parent=styles["Title"], alignment=TA_CENTER, fontSize=22)
    body = ParagraphStyle("CertBody", parent=styles["Normal"], alignment=TA_CENTER, fontSize=13, leading=18)
    footer = ParagraphStyle("CertFooter", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10,
                            textColor=colors.HexColor("#777777"))

    elements = [
        Paragraph("Directorate of Sericulture, Government of Assam", subheading),
        Spacer(1, 10),
        Paragraph("Certificate of Participation", heading),
        Spacer(1, 24),
        Paragraph("This is to certify that", body),
        Spacer(1, 10),
        Paragraph(participant_name, name_style),
        Spacer(1, 14),
        Paragraph(f"has participated in the training programme on <b>{training_topic}</b>", body),
        Paragraph(f"held on {training_dates} at {venue}.", body),
        Spacer(1, 36),
        Paragraph(f"Certificate No: {certificate_number}", footer),
        Paragraph(f"Issued: {issued_at}", footer),
    ]
    doc.build(elements)
    return buf.getvalue()
