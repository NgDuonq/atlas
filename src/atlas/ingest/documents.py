"""Text and page-aware PDF import. No execution of uploaded content."""
from io import BytesIO
from pathlib import Path

MAX_BYTES = 20 * 1024 * 1024
CHUNK_CHARS = 2400


def text_chunks(text, page=None):
    result = []
    # Split exceptionally long lines too, retaining the actual original line number.
    pending, size, start, end = [], 0, 1, 1
    for number, line in enumerate(text.splitlines(), 1):
        for offset in range(0, max(1, len(line)), CHUNK_CHARS):
            part = line[offset:offset + CHUNK_CHARS]
            if pending and size + len(part) + 1 > CHUNK_CHARS:
                result.append(dict(text="\n".join(pending), page=page, line_start=start, line_end=end))
                pending, size = [], 0
            if not pending:
                start = number
            pending.append(part)
            size += len(part) + 1
            end = number
    if pending and "\n".join(pending).strip():
        result.append(dict(text="\n".join(pending), page=page, line_start=start, line_end=end))
    return [c for c in result if c["text"].strip()]


def extract(filename, data):
    if len(data) > MAX_BYTES:
        raise ValueError("File exceeds the 20 MiB import limit")
    suffix = Path(filename).suffix.lower()
    warnings = []
    if suffix in {".txt", ".md"}:
        try:
            chunks = text_chunks(data.decode("utf-8-sig"))
        except UnicodeDecodeError as exc:
            raise ValueError("Text files must use UTF-8 encoding") from exc
    elif suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("Encrypted PDF is not supported; import an unlocked copy")
        chunks = []
        if len(reader.pages) > 500:
            raise ValueError("PDF exceeds the 500 page limit")
        for page_number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                warnings.append(f"Page {page_number}: no extractable text (OCR is not available)")
            chunks.extend(text_chunks(text, page_number))
    else:
        raise ValueError("Supported formats: .txt, .md, .pdf")
    if not chunks:
        raise ValueError("No text extracted. Scanned PDFs need OCR before import")
    # Preserve extraction gaps in every packet that uses this source.
    return chunks, warnings
