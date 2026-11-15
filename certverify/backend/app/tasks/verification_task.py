import asyncio
from datetime import datetime
import os
import tempfile
from urllib.parse import urlparse
import fitz  # PyMuPDF
import httpx
from sqlalchemy.orm import Session

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import sync_engine
from app.models.certificates import Certificate
from app.models.verification import (
    CertificateFingerprint,
    JobStatus,
    ModuleStatus,
    RiskAssessment,
    VerificationJob,
    VerificationResult,
)
from app.services.ai import (
    classifier_service,
    deepfake_detector,
    document_forensics,
    entity_extractor,
    ocr_service,
)
from app.services.ai.logo_similarity import compare_logo
from app.services.verification import company_intelligence, duplicate_detector, qr_verification, risk_engine, signature_verifier


def execute_verification_pipeline(job_id: str, certificate_id: str) -> None:
    temp_files = []
    with Session(sync_engine) as db:
        job = db.get(VerificationJob, job_id)
        if not job:
            return

        job.status = JobStatus.PROCESSING
        job.started_at = datetime.utcnow()
        job.progress_percentage = 5
        job.current_step = "Document Classification"
        job.error_message = None
        db.commit()

        try:
            cert = db.get(Certificate, certificate_id)
            if not cert:
                raise ValueError(f"Certificate {certificate_id} not found in database")

            # STEP 1: Obtain local file for processing
            file_ext = (
                ".pdf"
                if (cert.mime_type == "application/pdf" or cert.original_filename.lower().endswith(".pdf"))
                else ".jpg"
            )
            uploads_dir = os.path.join(settings.STORAGE_DIR, "uploads")
            temp_dir = os.path.join(settings.STORAGE_DIR, "temp")
            os.makedirs(uploads_dir, exist_ok=True)
            os.makedirs(temp_dir, exist_ok=True)

            local_file_path = os.path.join(temp_dir, f"{certificate_id}{file_ext}")

            # 1. Search locally in persistent storage/uploads first (ZERO-LATENCY, BYPASSES NETWORK/CDN ACLs)
            candidates = [
                os.path.join(uploads_dir, f"{certificate_id}{file_ext}"),
                os.path.join(uploads_dir, cert.original_filename),
            ]
            if cert.file_url and "/static/uploads/" in cert.file_url:
                candidates.append(os.path.join(uploads_dir, os.path.basename(cert.file_url)))

            # Also check for any file ending with _{cert.original_filename}
            if os.path.exists(uploads_dir):
                for fname in os.listdir(uploads_dir):
                    if fname.endswith(f"_{cert.original_filename}") or fname == cert.original_filename:
                        candidates.append(os.path.join(uploads_dir, fname))

            found_local = False
            for cand in candidates:
                if os.path.exists(cand) and os.path.getsize(cand) > 100:
                    try:
                        with open(cand, "rb") as rf:
                            header = rf.read(16)
                            if file_ext == ".pdf" and not header.startswith(b"%PDF"):
                                continue
                            rf.seek(0)
                            with open(local_file_path, "wb") as wf:
                                wf.write(rf.read())
                            found_local = True
                            break
                    except Exception:
                        continue

            # 2. If not found locally, download from remote URL with authenticated Cloudinary fallback
            if not found_local:
                if not cert.file_url or not cert.file_url.startswith("http"):
                    raise RuntimeError(f"Certificate file not found locally and file_url is invalid: {cert.file_url}")

                try:
                    r = httpx.get(cert.file_url, timeout=30.0, follow_redirects=True)
                    
                    # If Cloudinary returns 401 ACL deny or non-200, use authenticated private download
                    is_cld_deny = (
                        r.status_code == 401
                        or (r.content and (r.content.startswith(b'{"success":false') or r.content.startswith(b'{"error"')))
                    )
                    if is_cld_deny or (r.status_code != 200 and "cloudinary" in cert.file_url.lower()):
                        cld_pub_id = cert.cloudinary_public_id
                        if not cld_pub_id and "res.cloudinary.com" in cert.file_url:
                            import re
                            m = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.[a-zA-Z0-9]+)?$', cert.file_url)
                            if m:
                                cld_pub_id = m.group(1)

                        if cld_pub_id and settings.CLOUDINARY_API_SECRET:
                            import cloudinary
                            import cloudinary.utils
                            cloudinary.config(
                                cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                                api_key=settings.CLOUDINARY_API_KEY,
                                api_secret=settings.CLOUDINARY_API_SECRET,
                                secure=True,
                            )
                            fmt = file_ext.lstrip(".")
                            # 1. Try image resource type
                            try:
                                priv_url = cloudinary.utils.private_download_url(
                                    cld_pub_id,
                                    fmt,
                                    resource_type="image",
                                    type="upload",
                                )
                                r_priv = httpx.get(priv_url, timeout=30.0, follow_redirects=True)
                                if r_priv.status_code == 200 and len(r_priv.content) > 100:
                                    r = r_priv
                            except Exception:
                                pass

                            # 2. Try raw resource type if not 200
                            if r.status_code != 200:
                                try:
                                    priv_url_raw = cloudinary.utils.private_download_url(
                                        cld_pub_id,
                                        fmt,
                                        resource_type="raw",
                                        type="upload",
                                    )
                                    r_raw = httpx.get(priv_url_raw, timeout=30.0, follow_redirects=True)
                                    if r_raw.status_code == 200 and len(r_raw.content) > 100:
                                        r = r_raw
                                except Exception:
                                    pass

                    if r.status_code != 200:
                        raise RuntimeError(f"HTTP {r.status_code} error downloading certificate from {cert.file_url}")

                    if file_ext == ".pdf" and not r.content.startswith(b"%PDF"):
                        raise RuntimeError(f"Downloaded file is not a valid PDF document (header: {r.content[:30]!r})")

                    with open(local_file_path, "wb") as wf:
                        wf.write(r.content)

                    # Cache in uploads_dir for subsequent verification passes
                    try:
                        cached_path = os.path.join(uploads_dir, f"{certificate_id}{file_ext}")
                        with open(cached_path, "wb") as wf:
                            wf.write(r.content)
                    except Exception:
                        pass
                except Exception as exc:
                    raise RuntimeError(f"Unable to fetch certificate file: {exc}")

            temp_files.append(local_file_path)

            # STEP 2: OCR Extraction
            ocr_res = ocr_service.extract_text(local_file_path)
            ocr_status = ModuleStatus.PASS if ocr_res.avg_confidence > 0.5 else (ModuleStatus.WARNING if ocr_res.block_count > 0 else ModuleStatus.FAIL)
            finding_ocr = f"{ocr_res.block_count} text blocks extracted with {ocr_res.avg_confidence:.0%} confidence" if ocr_res.block_count > 0 else "No text extracted from document"
            
            db.add(
                VerificationResult(
                    job_id=job.id,
                    module_name="OCR_EXTRACTION",
                    status=ocr_status,
                    finding_summary=finding_ocr,
                    confidence_score=ocr_res.avg_confidence,
                    details={
                        "full_text": ocr_res.full_text,
                        "block_count": ocr_res.block_count,
                        "avg_confidence": ocr_res.avg_confidence,
                    },
                )
            )

            # STEP 3: Classification
            cls = classifier_service.classify(ocr_res.full_text)
            cls_status = ModuleStatus.PASS if cls.confidence > 0.4 else ModuleStatus.WARNING
            db.add(
                VerificationResult(
                    job_id=job.id,
                    module_name="CLASSIFICATION",
                    status=cls_status,
                    finding_summary=f"{cls.cert_type.replace('_', ' ')} ({cls.confidence:.0%} confidence)",
                    confidence_score=cls.confidence,
                    details={
                        "cert_type": cls.cert_type,
                        "confidence": cls.confidence,
                        "all_scores": cls.all_scores,
                    },
                )
            )

            # STEP 4: Entity Extraction
            entities = entity_extractor.extract(
                ocr_res.full_text, getattr(ocr_res, "layout_blocks", None)
            )
            has_key_entities = bool(entities.get("candidate_name") or entities.get("organization_name"))
            entity_status = ModuleStatus.PASS if has_key_entities else ModuleStatus.WARNING
            if entities.get("is_expired"):
                entity_status = ModuleStatus.WARNING
            
            summary_parts = []
            if has_key_entities:
                summary_parts.append("Key credential entities identified")
            else:
                summary_parts.append("Partial or limited entity detection")
            if entities.get("standard_code"):
                summary_parts.append(f"Standard: {entities['standard_code']}")
            if entities.get("is_expired"):
                summary_parts.append(f"EXPIRED on {entities.get('expiry_date')}")

            db.add(
                VerificationResult(
                    job_id=job.id,
                    module_name="ENTITY_EXTRACTION",
                    status=entity_status,
                    finding_summary=" | ".join(summary_parts),
                    confidence_score=0.95 if has_key_entities else 0.40,
                    details=entities,
                )
            )

            job.progress_percentage = 25
            job.current_step = "Company Verification"
            db.commit()

            # STEP 6-7: Company Intelligence
            org_name = entities.get("organization_name") or ""
            website = entities.get("website")
            cv = asyncio.run(company_intelligence.verify_company(org_name, website))
            ci_status = (
                ModuleStatus.PASS
                if cv.confidence_score > 0.5
                else ModuleStatus.WARNING
                if cv.confidence_score > 0.2
                else ModuleStatus.FAIL
            )
            db.add(
                VerificationResult(
                    job_id=job.id,
                    module_name="COMPANY_INTELLIGENCE",
                    status=ci_status,
                    finding_summary=f"Issuing organization {'verified online' if cv.online_presence_found else 'not verified in public records'}",
                    confidence_score=cv.confidence_score,
                    details=cv.__dict__,
                )
            )

            # STEP 8: ISO Verification
            iso = asyncio.run(company_intelligence.verify_iso(org_name, ocr_res.full_text))
            iso_status = (
                ModuleStatus.SKIPPED
                if not iso.claimed
                else (ModuleStatus.PASS if iso.evidence_found else ModuleStatus.WARNING)
            )
            db.add(
                VerificationResult(
                    job_id=job.id,
                    module_name="ISO_VERIFICATION",
                    status=iso_status,
                    finding_summary=iso.status.replace("_", " "),
                    confidence_score=0.9 if iso.evidence_found else (None if not iso.claimed else 0.3),
                    details=iso.__dict__,
                )
            )

            # STEP 9: Logo Similarity
            logo_img_path = local_file_path
            if local_file_path.endswith(".pdf"):
                try:
                    doc = fitz.open(local_file_path)
                    if len(doc) > 0:
                        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
                        tmp_logo_img = local_file_path.replace(".pdf", "_logo_tmp.png")
                        pix.save(tmp_logo_img)
                        temp_files.append(tmp_logo_img)
                        logo_img_path = tmp_logo_img
                except Exception:
                    pass

            logo = asyncio.run(compare_logo(logo_img_path, website))
            logo_status = (
                ModuleStatus.PASS
                if logo.similarity_score > 0.6
                else ModuleStatus.WARNING
                if logo.favicon_found
                else ModuleStatus.SKIPPED
            )
            db.add(
                VerificationResult(
                    job_id=job.id,
                    module_name="LOGO_SIMILARITY",
                    status=logo_status,
                    finding_summary=f"Visual brand match: {logo.similarity_score:.0%}" if logo.favicon_found else "Favicon/Brand icon not matched",
                    confidence_score=logo.similarity_score if logo.favicon_found else None,
                    details=logo.__dict__,
                )
            )

            job.progress_percentage = 45
            job.current_step = "Document Forensics"
            db.commit()

            # STEP 11: PDF Forensics
            if local_file_path.endswith(".pdf"):
                pdf_data = document_forensics.analyze_pdf_metadata(local_file_path)
                has_critical_pdf_tamper = (
                    pdf_data.get("whiteout_data", {}).get("whiteout_detected", False)
                    or pdf_data.get("confidence_score", 0) >= 0.60
                )
                pdf_status = (
                    ModuleStatus.FAIL
                    if has_critical_pdf_tamper
                    else ModuleStatus.WARNING
                    if pdf_data.get("suspicious_flags")
                    else ModuleStatus.PASS
                )
                db.add(
                    VerificationResult(
                        job_id=job.id,
                        module_name="PDF_FORENSICS",
                        status=pdf_status,
                        finding_summary="; ".join(pdf_data["suspicious_flags"]) or "Pristine PDF document structure (Zero metadata tampering)",
                        confidence_score=pdf_data["confidence_score"],
                        details=pdf_data,
                    )
                )
            else:
                db.add(
                    VerificationResult(
                        job_id=job.id,
                        module_name="PDF_FORENSICS",
                        status=ModuleStatus.SKIPPED,
                        finding_summary="Non-PDF document",
                        details={"applicable": False},
                    )
                )

            # STEP 12-13: Image Forensics & ELA
            forensics_img_path = local_file_path
            is_vector_doc = local_file_path.endswith(".pdf") and not getattr(ocr_res, "is_scanned", False)
            if local_file_path.endswith(".pdf"):
                try:
                    doc = fitz.open(local_file_path)
                    if len(doc) > 0:
                        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2, 2))
                        pdf_page_img = local_file_path.replace(".pdf", "_page.png")
                        pix.save(pdf_page_img)
                        temp_files.append(pdf_page_img)
                        forensics_img_path = pdf_page_img
                except Exception:
                    pass

            ela_data = document_forensics.perform_ela(forensics_img_path, is_vector_pdf=is_vector_doc)
            exif_data = document_forensics.analyze_exif(forensics_img_path)
            deepfake_data = deepfake_detector.run_deepfake_and_manipulation_audit(forensics_img_path, certificate_id)
            annotated_url = document_forensics.create_annotated_image(forensics_img_path, ela_data, certificate_id)

            flags = []
            if ela_data["ela_suspicious"]:
                flags.append(f"ELA detected compression artifact anomalies (score: {ela_data['ela_mean']:.1f})")
            if exif_data["editing_software_detected"]:
                flags.append(f"Editing software signature found: {exif_data['editing_software_detected']}")
            if deepfake_data.get("is_ai_generated"):
                flags.append("FFT spectrum detected synthetic AI generator frequencies")
            if deepfake_data.get("font_data", {}).get("baseline_anomaly"):
                flags.append("Typography baseline variance detected")

            img_status = (
                ModuleStatus.FAIL
                if (ela_data["ela_suspicious"] and exif_data["editing_software_detected"]) or deepfake_data.get("is_ai_generated")
                else ModuleStatus.WARNING
                if flags
                else ModuleStatus.PASS
            )

            db.add(
                VerificationResult(
                    job_id=job.id,
                    module_name="IMAGE_FORENSICS",
                    status=img_status,
                    finding_summary="; ".join(flags) or "No image tampering or manipulation detected (FFT Spectral & Physical Integrity Verified)",
                    confidence_score=0.95 if not flags else 0.4,
                    details={
                        **ela_data,
                        **exif_data,
                        "deepfake_audit": deepfake_data,
                        "annotated_image_url": annotated_url,
                    },
                )
            )

            job.progress_percentage = 65
            job.current_step = "QR Verification"
            db.commit()

            # STEP 15-16: QR Code Verification
            qr_img_path = forensics_img_path
            org_domain = urlparse(website).netloc if website else None
            qr_list = qr_verification.scan_qr(qr_img_path)
            if qr_list:
                qr_results = [asyncio.run(qr_verification.verify_qr_url(q.data, org_domain)) for q in qr_list]
                all_suspicious = any(r.is_suspicious for r in qr_results)
                db.add(
                    VerificationResult(
                        job_id=job.id,
                        module_name="QR_CODE",
                        status=ModuleStatus.FAIL if all_suspicious else ModuleStatus.PASS,
                        finding_summary=f"{len(qr_list)} QR code(s) verified",
                        confidence_score=0.95,
                        details={"qr_results": [r.__dict__ for r in qr_results]},
                    )
                )
            else:
                db.add(
                    VerificationResult(
                        job_id=job.id,
                        module_name="QR_CODE",
                        status=ModuleStatus.SKIPPED,
                        finding_summary="No QR code present on certificate",
                        details={"qr_count": 0},
                    )
                )

            # STEP 17: PDF Signature
            sig = signature_verifier.check_pdf_signature(local_file_path)
            if sig.applicable:
                sig_status = ModuleStatus.PASS if sig.is_signed else ModuleStatus.WARNING
                db.add(
                    VerificationResult(
                        job_id=job.id,
                        module_name="DIGITAL_SIGNATURE",
                        status=sig_status,
                        finding_summary="Digitally signed" if sig.is_signed else "Signature field present but unsigned",
                        confidence_score=1.0 if sig.is_signed else 0.5,
                        details=sig.__dict__,
                    )
                )
            else:
                db.add(
                    VerificationResult(
                        job_id=job.id,
                        module_name="DIGITAL_SIGNATURE",
                        status=ModuleStatus.SKIPPED,
                        finding_summary="Not a PDF or no signature field",
                        details=sig.__dict__,
                    )
                )

            job.progress_percentage = 75
            job.current_step = "Duplicate Detection"
            db.commit()

            # STEP 19-22: Duplicate Detection
            fp = duplicate_detector.compute_fingerprint(forensics_img_path, ocr_res.full_text)
            existing_fp = db.query(CertificateFingerprint).filter_by(certificate_id=cert.id).first()
            if not existing_fp:
                db.add(
                    CertificateFingerprint(
                        certificate_id=cert.id,
                        phash=fp.phash,
                        dhash=fp.dhash,
                        text_hash=fp.text_hash,
                    )
                )
                db.commit()

            matches = duplicate_detector.find_duplicates(str(cert.id), fp, ocr_res.full_text, db)
            if matches:
                db.add(
                    VerificationResult(
                        job_id=job.id,
                        module_name="DUPLICATE_DETECTION",
                        status=ModuleStatus.WARNING,
                        finding_summary=f"{len(matches)} similar certificate(s) detected in database",
                        confidence_score=0.85,
                        details={"matches": [m.__dict__ for m in matches]},
                    )
                )
            else:
                db.add(
                    VerificationResult(
                        job_id=job.id,
                        module_name="DUPLICATE_DETECTION",
                        status=ModuleStatus.PASS,
                        finding_summary="No duplicate or templated matches found",
                        confidence_score=1.0,
                        details={"matches": []},
                    )
                )

            job.progress_percentage = 85
            job.current_step = "Risk Assessment"
            db.commit()

            # STEP 24: Risk Assessment Calculation
            all_results = db.query(VerificationResult).filter_by(job_id=job.id).all()
            calc = risk_engine.calculate_risk(all_results)
            reasoning = risk_engine.generate_reasoning(all_results, calc)

            existing_ra = db.query(RiskAssessment).filter_by(job_id=job.id).first()
            if not existing_ra:
                db.add(
                    RiskAssessment(
                        job_id=job.id,
                        risk_score=calc.risk_score,
                        risk_level=calc.risk_level,
                        final_verdict=calc.final_verdict,
                        reasoning=reasoning,
                    )
                )

            job.status = JobStatus.COMPLETED
            job.progress_percentage = 100
            job.current_step = "Completed"
            job.completed_at = datetime.utcnow()
            db.commit()

            # Dispatch B2B Webhook Event if configured
            try:
                from app.services.webhook_service import dispatch_webhook_sync
                dispatch_webhook_sync(
                    user_id=str(cert.user_id),
                    event_type="certificate.verified",
                    payload={
                        "certificate_id": str(cert.id),
                        "job_id": str(job.id),
                        "filename": cert.original_filename,
                        "status": "COMPLETED",
                        "risk_score": calc.risk_score,
                        "risk_level": calc.risk_level.value,
                        "final_verdict": calc.final_verdict.value,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    },
                )
            except Exception:
                pass

        except Exception as exc:
            db.rollback()
            job = db.get(VerificationJob, job_id)
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                db.commit()
            raise exc
        finally:
            for p in temp_files:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass


@celery_app.task(bind=True, name="run_verification", max_retries=2)
def run_verification(self, job_id: str, certificate_id: str):
    try:
        execute_verification_pipeline(job_id, certificate_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=15)


