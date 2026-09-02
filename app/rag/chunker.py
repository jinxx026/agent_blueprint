"""Structure-aware chunking that enriches every fragment with document context."""

import hashlib
import re

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.rag.models import ContextualChunk, RagDocument

HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$")


class ContextualChunker:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 80) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            add_start_index=True,
            separators=[
                "\n\n",
                "\n",
                "。",
                "！",
                "？",
                "；",
                ".",
                "!",
                "?",
                ";",
                "，",
                ",",
                "、",
                " ",
            ],
        )

    def split(self, document: RagDocument) -> tuple[ContextualChunk, ...]:
        pieces: list[tuple[str, str, int]] = []
        for section, content, section_start in self._sections(document.content):
            for split in self._splitter.create_documents([content]):
                raw = split.page_content.strip()
                if raw:
                    pieces.append(
                        (section, raw, section_start + int(split.metadata.get("start_index", 0)))
                    )

        summary = self._summary(document.content)
        chunks = []
        for index, (section, raw, start) in enumerate(pieces):
            previous = pieces[index - 1][1][-100:] if index else ""
            following = pieces[index + 1][1][:100] if index + 1 < len(pieces) else ""
            context = (
                f"[文档: {document.title}]\n[章节: {section}]\n[文档概览: {summary}]\n"
                f"[相邻内容: {previous} | {following}]\n[正文]\n{raw}"
            )
            digest = hashlib.sha256(
                f"{document.tenant_id}:{document.source_id}:{document.document_id}:"
                f"{start}:{raw}".encode()
            ).hexdigest()[:16]
            chunks.append(
                ContextualChunk(
                    chunk_id=digest,
                    tenant_id=document.tenant_id,
                    source_id=document.source_id,
                    document_id=document.document_id,
                    title=document.title,
                    section=section,
                    raw_content=raw,
                    contextual_content=context,
                    allowed_roles=document.allowed_roles,
                    citation=f"{document.citation_base}#chunk={digest}",
                    start_index=start,
                )
            )
        return tuple(chunks)

    @staticmethod
    def _sections(text: str) -> list[tuple[str, str, int]]:
        sections: list[tuple[str, str, int]] = []
        current_heading = "正文"
        current_lines: list[str] = []
        current_start = 0
        offset = 0
        for line in text.splitlines(keepends=True):
            match = HEADING.match(line.strip())
            if match:
                if current_lines:
                    sections.append((current_heading, "".join(current_lines), current_start))
                current_heading = match.group(1)
                current_lines = []
                current_start = offset + len(line)
            else:
                if not current_lines:
                    current_start = offset
                current_lines.append(line)
            offset += len(line)
        if current_lines:
            sections.append((current_heading, "".join(current_lines), current_start))
        return sections or [("正文", text, 0)]

    @staticmethod
    def _summary(text: str) -> str:
        compact = " ".join(part.strip() for part in text.splitlines() if part.strip())
        return compact[:180]
