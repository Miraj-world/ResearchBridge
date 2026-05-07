from __future__ import annotations

import re

from backend.models.schemas import SectionChunk

_HEADER_RE = re.compile(r"^(##|###)\s+(?P<header>.+)$")


def _word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def _split_large_section(text: str, target_words: int = 700, overlap_words: int = 100) -> list[str]:
    words = text.split()
    if len(words) <= 800:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + target_words, len(words))
        piece = " ".join(words[start:end]).strip()
        if piece:
            chunks.append(piece)
        if end == len(words):
            break
        start = max(0, end - overlap_words)
    return chunks


def chunk_markdown(markdown: str) -> list[SectionChunk]:
    lines = markdown.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_header = "Document"
    current_lines: list[str] = []

    for line in lines:
        header_match = _HEADER_RE.match(line.strip())
        if header_match:
            if current_lines:
                sections.append((current_header, current_lines))
            current_header = header_match.group("header").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_header, current_lines))

    if not sections:
        sections = [("Document", lines)]

    chunks: list[SectionChunk] = []
    section_index = 0
    for header, section_lines in sections:
        raw_text = "\n".join(section_lines).strip()
        if not raw_text:
            continue
        section_index += 1
        if _word_count(raw_text) <= 800:
            chunks.append(
                SectionChunk(
                    chunk_id=f"section_{section_index}_part_1",
                    header=header,
                    text=raw_text,
                    section_index=section_index,
                )
            )
            continue

        sub_chunks = _split_large_section(raw_text)
        for sub_idx, sub_chunk in enumerate(sub_chunks, start=1):
            chunks.append(
                SectionChunk(
                    chunk_id=f"section_{section_index}_part_{sub_idx}",
                    header=header,
                    text=sub_chunk,
                    section_index=section_index,
                )
            )

    return chunks
