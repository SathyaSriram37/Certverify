from dataclasses import dataclass
from typing import Optional
import fitz  # PyMuPDF


@dataclass
class SignatureResult:
    applicable: bool
    has_signature_field: bool = False
    is_signed: bool = False
    signer_name: Optional[str] = None


def check_pdf_signature(file_path: str) -> SignatureResult:
    if not file_path.lower().endswith(".pdf"):
        return SignatureResult(applicable=False, has_signature_field=False, is_signed=False)

    try:
        doc = fitz.open(file_path)
        sig_widgets = []
        for page in doc:
            widgets = page.widgets() if hasattr(page, "widgets") else (page.get_widgets() if hasattr(page, "get_widgets") else [])
            for w in widgets:
                if getattr(w, "field_type_string", "") == "Signature":
                    sig_widgets.append(w)

        has_field = len(sig_widgets) > 0
        is_signed = any(bool(getattr(w, "field_value", None)) for w in sig_widgets)
        signer = None
        if is_signed and sig_widgets:
            val = getattr(sig_widgets[0], "field_value", None)
            signer = str(val) if val else None

        return SignatureResult(
            applicable=has_field,
            has_signature_field=has_field,
            is_signed=is_signed,
            signer_name=signer,
        )
    except Exception:
        return SignatureResult(applicable=False, has_signature_field=False, is_signed=False)
