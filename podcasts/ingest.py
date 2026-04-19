"""Ingest a raw source (epub/pdf/txt) into the Obsidian vault.

Writes a plain-text version to vault/sources/<slug>.txt for easy Grep access
and emits a starter vault/books/<slug>.md. Concept-page extraction is left to
Claude's `/ingest` skill — this tool just provides the plumbing.

Usage:
    python -m podcasts.ingest path/to/book.epub
    python -m podcasts.ingest path/to/paper.pdf --title "Статья про X"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from slugify import slugify

from podcasts.config import load_config
from podcasts.util.logging import configure as configure_logging
from podcasts.util.logging import get_logger

log = get_logger(__name__)


def extract_text(source: Path) -> str:
    """Plain-text extraction. Dispatches by extension."""
    suffix = source.suffix.lower()
    if suffix == ".txt":
        return source.read_text(encoding="utf-8")
    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(source))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix == ".epub":
        from ebooklib import ITEM_DOCUMENT, epub
        from bs4 import BeautifulSoup

        book = epub.read_epub(str(source))
        chunks: list[str] = []
        for item in book.get_items():
            if item.get_type() == ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "lxml")
                chunks.append(soup.get_text(separator="\n"))
        return "\n\n".join(chunks)
    raise ValueError(f"Unsupported source format: {suffix}")


def ingest(source: Path, title: str | None = None) -> tuple[Path, Path]:
    """Extract text, write to vault/sources/<slug>.txt and vault/books/<slug>.md stub."""
    cfg = load_config()
    vault = cfg.vault_path
    effective_title = title or source.stem
    slug = slugify(effective_title, allow_unicode=False, lowercase=True)

    text = extract_text(source)
    log.info("ingest.extracted", source=str(source), chars=len(text))

    sources_dir = vault / "sources"
    books_dir = vault / "books"
    sources_dir.mkdir(parents=True, exist_ok=True)
    books_dir.mkdir(parents=True, exist_ok=True)

    txt_path = sources_dir / f"{slug}.txt"
    book_path = books_dir / f"{slug}.md"

    txt_path.write_text(text, encoding="utf-8")
    if not book_path.exists():
        book_path.write_text(
            _book_stub(effective_title, source, slug, len(text)),
            encoding="utf-8",
        )

    log.info("ingest.done", txt=str(txt_path), book_md=str(book_path))
    return txt_path, book_path


def _book_stub(title: str, source: Path, slug: str, n_chars: int) -> str:
    return f"""---
title: {title}
source_file: {source.name}
source_text: sources/{slug}.txt
char_count: {n_chars}
ingested_at: auto
status: needs-concept-extraction
---

# {title}

> Автоматически созданная страница при ингесте. Claude должен дополнить её оглавлением,
> списком ключевых концептов (каждый — `[[ссылка]]` на `concepts/<concept>.md`), и
> краткой аннотацией в духе стиля `documentary`.

## Источник

- Файл: `sources/{slug}.txt` (plain text, {n_chars} символов)
- Исходный формат: `{source.suffix.lstrip('.')}`

## Ключевые концепты

_Claude, заполни этот раздел при первом упоминании книги в эпизоде. Каждый концепт — `[[Название]]`._

## Упоминания в эпизодах

_Автопополняется при генерации эпизодов._
"""


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description="Ingest a source file into the vault.")
    parser.add_argument("source", type=Path, help="Path to .txt / .pdf / .epub")
    parser.add_argument("--title", type=str, default=None, help="Override inferred title")
    args = parser.parse_args()

    if not args.source.exists():
        print(f"Source not found: {args.source}", file=sys.stderr)
        return 1

    txt_path, book_path = ingest(args.source, title=args.title)
    print(f"Text:  {txt_path}")
    print(f"Book:  {book_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
