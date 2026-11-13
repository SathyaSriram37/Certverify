from datetime import datetime
from io import BytesIO
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
    PageBreak,
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor

from app.models.certificates import Certificate
from app.models.verification import (
    VerificationJob,
    VerificationResult,
    RiskAssessment,
    FinalVerdict,
    ModuleStatus,
)
from app.services.storage_service import storage_service

VERDICT_COLORS = {
    FinalVerdict.VERIFIED: HexColor("#27ae60"),
    FinalVerdict.SUSPICIOUS: HexColor("#e74c3c"),
    FinalVerdict.UNABLE_TO_VERIFY: HexColor("#7f8c8d"),
}

STATUS_BG = {
    ModuleStatus.PASS: HexColor("#eafaf1"),
    ModuleStatus.FAIL: HexColor("#fce9e8"),
    ModuleStatus.WARNING: HexColor("#fef9e7"),
    ModuleStatus.SKIPPED: HexColor("#f2f3f4"),
    ModuleStatus.ERROR: HexColor("#fce9e8"),
}

STATUS_MARK = {
    ModuleStatus.PASS: "[PASS]",
    ModuleStatus.FAIL: "[FAIL]",
    ModuleStatus.WARNING: "[WARN]",
    ModuleStatus.SKIPPED: "[SKIP]",
    ModuleStatus.ERROR: "[ERR]",
}


async def generate_report(job_id: str, db: AsyncSession) -> str:
    job = await db.get(VerificationJob, job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found")

    cert = await db.get(Certificate, job.certificate_id)
    results_res = await db.execute(
        select(VerificationResult).where(VerificationResult.job_id == job_id)
    )
    results = results_res.scalars().all()

    risk_res = await db.execute(
        select(RiskAssessment).where(RiskAssessment.job_id == job_id)
    )
    risk = risk_res.scalar_one_or_none()
    if not risk:
        raise ValueError(f"Risk assessment not found for job {job_id}")

    entity_res = next((r for r in results if r.module_name == "ENTITY_EXTRACTION"), None)
    entities = entity_res.details if entity_res else {}
    cls_res = next((r for r in results if r.module_name == "CLASSIFICATION"), None)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Title"],
        fontSize=24,
        leading=28,
        textColor=HexColor("#1e293b"),
    )
    h1_style = ParagraphStyle(
        "CertH1",
        parent=styles["Heading1"],
        fontSize=16,
        leading=20,
        textColor=HexColor("#334155"),
    )
    h2_style = ParagraphStyle(
        "CertH2",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=HexColor("#0f172a"),
    )
    verdict_style = ParagraphStyle(
        "VerdictText",
        parent=styles["Normal"],
        fontSize=15,
        leading=18,
        textColor=colors.white,
        alignment=1,
    )

    story = []

    # PAGE 1 — Header
    story.append(Paragraph("<b>CertVerify AI</b>", title_style))
    story.append(Paragraph("Certificate Verification & Forensic Audit Report", h1_style))
    story.append(
        Paragraph(
            f"Report ID: {str(job_id)[:8].upper()} | Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}",
            styles["Normal"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cbd5e1")))
    story.append(Spacer(1, 0.4 * cm))

    # Certificate details table
    cert_type = cls_res.finding_summary if cls_res else "Standard Certificate"
    cert_data = [
        ["Field", "Verified Value"],
        ["Certificate Type", cert_type],
        ["Candidate Name", entities.get("candidate_name") or "—"],
        ["Organization", entities.get("organization_name") or "—"],
        ["Issue Date", entities.get("issue_date") or "—"],
        ["Certificate Number", entities.get("cert_number") or "—"],
        ["Filename", cert.original_filename if cert else "—"],
        ["Upload Date", cert.created_at.strftime("%d %b %Y, %H:%M") if cert else "—"],
    ]
    ct = Table(cert_data, colWidths=[5 * cm, 12 * cm])
    ct.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f1f5f9")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (-1, -1), HexColor("#1e293b")),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(ct)
    story.append(Spacer(1, 0.6 * cm))

    # Verdict box
    story.append(
        Paragraph(
            f"Risk Score: <b>{risk.risk_score} / 100</b> — <b>{risk.risk_level.value} RISK</b>",
            h2_style,
        )
    )
    story.append(Spacer(1, 0.2 * cm))

    verdict_color = VERDICT_COLORS.get(risk.final_verdict, HexColor("#7f8c8d"))
    vt = Table(
        [[Paragraph(f"<b>FINAL VERDICT: {risk.final_verdict.value.replace('_', ' ')}</b>", verdict_style)]],
        colWidths=[17 * cm],
    )
    vt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), verdict_color),
                ("ALIGN", (0, 0), (0, 0), "CENTER"),
                ("TOPPADDING", (0, 0), (0, 0), 10),
                ("BOTTOMPADDING", (0, 0), (0, 0), 10),
            ]
        )
    )
    story.append(vt)
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"<b>Analysis Summary:</b> {risk.reasoning}", styles["Normal"]))
    story.append(PageBreak())

    # PAGE 2 — Module Analysis
    story.append(Paragraph("Verification Module Breakdown", h1_style))
    story.append(Spacer(1, 0.2 * cm))

    mod_data = [["Module", "Status", "Finding", "Confidence"]]
    for r in results:
        conf = f"{r.confidence_score:.0%}" if r.confidence_score is not None else "—"
        mod_data.append(
            [
                r.module_name.replace("_", " ").title(),
                f"{STATUS_MARK.get(r.status, '')} {r.status.value}",
                r.finding_summary[:50] + ("..." if len(r.finding_summary) > 50 else ""),
                conf,
            ]
        )

    mt = Table(mod_data, colWidths=[4.5 * cm, 2.8 * cm, 8.2 * cm, 1.5 * cm])
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#e2e8f0")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, r in enumerate(results, 1):
        bg = STATUS_BG.get(r.status, colors.white)
        style_cmds.append(("BACKGROUND", (0, i), (-1, i), bg))
    mt.setStyle(TableStyle(style_cmds))
    story.append(mt)
    story.append(Spacer(1, 0.6 * cm))

    # Limitations
    story.append(Paragraph("Important Notice & Limitations", h2_style))
    story.append(
        Paragraph(
            "This report is generated by CertVerify AI automated multi-layer forensic analysis and does not constitute a legal subpoena or government warranty. "
            "Public web scraping and machine learning estimates are utilized. ELA compression analysis may exhibit variation on highly compressed JPEGs. "
            "For authoritative legal authentication, verify directly with the named issuing organization.",
            styles["Normal"],
        )
    )

    def add_page_num(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(HexColor("#64748b"))
        canvas.drawRightString(
            A4[0] - 2 * cm,
            1 * cm,
            f"CertVerify AI Enterprise Audit | Page {doc.page} | Confidential",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_num, onLaterPages=add_page_num)
    buf.seek(0)
    pdf_bytes = buf.getvalue()

    # Save to local persistent storage for direct reliable download
    import os
    from app.core.config import settings
    reports_dir = settings.REPORTS_DIR
    os.makedirs(reports_dir, exist_ok=True)
    local_pdf_path = os.path.join(reports_dir, f"report_{str(job_id)}.pdf")
    with open(local_pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Direct streaming URL (guarantees zero CDN ACL / block issues)
    url = f"/api/v1/verify/{str(job_id)}/report/download"

    # Optional Cloudinary upload backup
    if storage_service.is_cloudinary_configured():
        try:
            import cloudinary.uploader
            cloudinary.uploader.upload(
                pdf_bytes,
                resource_type="raw",
                folder="certverify/reports",
                public_id=f"report_{str(job_id)[:8]}",
                format="pdf",
            )
        except Exception:
            pass

    risk.report_url = url
    await db.commit()
    return url

