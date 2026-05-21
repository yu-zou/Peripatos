"""Paragraph-aware text chunker."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Chunk:
    id: int
    text: str
    char_start: int
    char_end: int
    section_hint: str | None = None


def _section_hint(text: str) -> str | None:
    first_line = text.splitlines()[0].strip() if text.splitlines() else text.strip()
    if not first_line:
        return None
    if first_line.startswith("#"):
        return first_line
    if len(first_line) < 80:
        return first_line
    letters = [ch for ch in first_line if ch.isalpha()]
    if letters and first_line.upper() == first_line:
        return first_line
    return None


def chunk_text(text: str, *, chunk_size: int = 1000, overlap: int = 200) -> list[Chunk]:
    if not text:
        return []

    paragraphs: list[tuple[str, int, int]] = []
    cursor = 0
    for para in text.split("\n\n"):
        start = text.find(para, cursor)
        if start < 0:
            start = cursor
        end = start + len(para)
        cursor = end + 2
        if para:
            paragraphs.append((para, start, end))

    if not paragraphs:
        return []

    chunks: list[Chunk] = []
    current_text = ""
    current_start = 0
    current_end = 0
    chunk_id = 0

    for para, start, end in paragraphs:
        if current_text and len(current_text) + len(para) > chunk_size:
            chunks.append(
                Chunk(
                    id=chunk_id,
                    text=current_text,
                    char_start=current_start,
                    char_end=current_end,
                    section_hint=_section_hint(current_text),
                )
            )
            chunk_id += 1

            overlap_text = current_text[-overlap:] if overlap > 0 else ""
            current_start = max(current_start, current_end - len(overlap_text))
            current_text = overlap_text + ("\n\n" if overlap_text else "") + para
            current_end = end
            continue

        if current_text:
            current_text += "\n\n" + para
        else:
            current_start = start
            current_text = para
        current_end = end

    if current_text.strip():
        chunks.append(
            Chunk(
                id=chunk_id,
                text=current_text,
                char_start=current_start,
                char_end=current_end,
                section_hint=_section_hint(current_text),
            )
        )

    return chunks
