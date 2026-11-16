
import os
from pathlib import Path

from dotenv import load_dotenv
from reportlab.lib.pdfencrypt import StandardEncryption


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def get_pdf_encryption(require_open_password: bool = False):
    owner_password = os.getenv("HAZINA_PDF_OWNER_PASSWORD")
    user_password = os.getenv("HAZINA_PDF_USER_PASSWORD")

    if not owner_password:
        raise ValueError(
            "HAZINA_PDF_OWNER_PASSWORD must be configured in .env."
        )

    if require_open_password:
        if not user_password:
            raise ValueError(
                "HAZINA_PDF_USER_PASSWORD must be configured "
                "to generate password-protected V2 reports."
            )

        if user_password == owner_password:
            raise ValueError(
                "PDF user and owner passwords must be different."
            )

    return StandardEncryption(
        userPassword=user_password if require_open_password else "",
        ownerPassword=owner_password,
        canPrint=1,
        canModify=0,
        canCopy=0,
        canAnnotate=0,
        strength=128,
    )
