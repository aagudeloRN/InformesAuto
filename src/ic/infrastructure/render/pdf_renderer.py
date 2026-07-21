"""Convierte .docx a .pdf usando LibreOffice headless.

Motor elegido: LibreOffice (disponible en el entorno — /usr/bin/soffice).
Documentado en ADR-011.
"""

import subprocess
from pathlib import Path


def convert_docx_to_pdf(docx_path: str, timeout: int = 60) -> str:
    """Convierte docx_path a PDF. Retorna la ruta del .pdf generado."""
    outdir = str(Path(docx_path).parent)
    result = subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            outdir,
            docx_path,
        ],
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise RuntimeError(f"LibreOffice falló (rc={result.returncode}): {stderr[:200]}")
    return docx_path.replace(".docx", ".pdf")
