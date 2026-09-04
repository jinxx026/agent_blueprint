"""Safe, text-only PDF ingestion for enterprise knowledge bases."""

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

MAX_PDF_BYTES = 10 * 1024 * 1024
MAX_PDF_PAGES = 300


class PdfIngestionError(ValueError):
    """Raised when an uploaded PDF cannot safely become a knowledge document."""


@dataclass(frozen=True)
class ParsedPdf:
    content: str
    page_count: int
    character_count: int


def parse_pdf(data: bytes) -> ParsedPdf:
    if not data:
        raise PdfIngestionError("PDF 文件为空")
    if len(data) > MAX_PDF_BYTES:
        raise PdfIngestionError("PDF 不能超过 10 MB")
    if not data.startswith(b"%PDF-"):
        raise PdfIngestionError("文件不是有效的 PDF")
    try:
        reader = PdfReader(BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise PdfIngestionError("暂不支持加密 PDF，请先解除密码保护")
        if len(reader.pages) > MAX_PDF_PAGES:
            raise PdfIngestionError("PDF 页数不能超过 300 页")
        pages: list[str] = []
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").replace("\x00", " ").strip()
            if text:
                pages.append(f"# 第 {number} 页\n{text}")
    except PdfIngestionError:
        raise
    except Exception as exc:
        raise PdfIngestionError("PDF 解析失败，文件可能已损坏") from exc
    content = "\n\n".join(pages).strip()
    if not content:
        raise PdfIngestionError("PDF 中没有可提取文字；扫描件请先进行 OCR")
    return ParsedPdf(content=content, page_count=len(reader.pages), character_count=len(content))
