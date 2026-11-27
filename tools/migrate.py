#!/usr/bin/env python3
"""Upgrade transcripts written before version 1 of the spec.

    python3 migrate.py --author "Name" --email name@example.org --license CC-BY-4.0 <file> [...]

Adds what version 1 requires and the older format did not have:

- `spec`, `authors` and `license`;
- the archive reference as one object: the older `archive`, `fonds`, `inventory` and
  `file` keys become `archive.name`, `archive.fonds`, `archive.inventory`, `archive.file`;
- `kind` is dropped: version 1 does not sort documents into church and civil ones;
- parts: the book's `status`, `fields` and `records` move into one part, named after
  what it holds: `births`, `marriages` or `deaths` when all its records (leaving `other`
  aside) are of that type, otherwise `records`. Its title is in Ukrainian when the
  field labels have Ukrainian, in English otherwise; --part-id and --part-title set
  them by hand;
- an `id` for every record.

With --familysearch it also adds the scanSource of FamilySearch films, whose ids the
older format assumed. The tool goes by a file's shape: one without `parts` is upgraded,
whatever its `spec` key says, and one that has them is left alone. --author, --email and
--license are needed only for a file that names no author or no licence of its own. Each file is
rewritten in the canonical key order after it passes validation; nothing is written if
it does not. A record's id is given once: keep the upgraded file, do not upgrade the old
one a second time.
"""
import argparse
import json
import os
import secrets
import sys
from pathlib import Path

from validate import ARCHIVE_ORDER, BOOK_ORDER, MAJOR, MINOR, PART_ORDER, RECORD_ORDER, validate_book

FAMILYSEARCH = {"name": "FamilySearch", "url": "https://www.familysearch.org/search/film/",
                "idPattern": "\\d{9}_\\d{5}"}
ID_ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"
ID_LENGTH = 12
# record type -> (part id, title in English, title in Ukrainian)
PART_NAMES = {
    "birth": ("births", "Births", "Народження"),
    "marriage": ("marriages", "Marriages", "Шлюби"),
    "death": ("deaths", "Deaths", "Смерті"),
    None: ("records", "Records", "Записи"),
}


def new_record_id(taken=()) -> str:
    """A record id as the spec asks of software that creates a record: 12 random
    characters from a-z and 0-9, not among `taken`."""
    while True:
        found = "".join(secrets.choice(ID_ALPHABET) for _ in range(ID_LENGTH))
        if found not in taken:
            return found


def _ordered(obj: dict, order: list[str]) -> dict:
    rank = {key: n for n, key in enumerate(order)}
    return dict(sorted(obj.items(), key=lambda kv: rank.get(kv[0], len(rank))))


def part_name(records: list, fields: list) -> tuple[str, str]:
    """The id and title of the one part an older book becomes."""
    types = {r.get("type") for r in records if isinstance(r, dict)} - {"other"}
    part_id, english, ukrainian = PART_NAMES[types.pop() if len(types) == 1 else None]
    label = fields[0].get("label") if fields and isinstance(fields[0], dict) else None
    return part_id, ukrainian if isinstance(label, dict) and "uk" in label else english


def migrate(book: dict, author: dict | None = None, license_id: str | None = None, familysearch: bool = False,
            part_id: str | None = None, part_title: str | None = None) -> dict:
    """Return `book`, a file without parts, as a version 1 document. `author` and
    `license_id` are used only when the file names none of its own."""
    book = dict(book)
    book["spec"] = f"{MAJOR}.{MINOR}"
    if author:
        book.setdefault("authors", [author])
    if license_id:
        book.setdefault("license", license_id)
    if familysearch:
        book.setdefault("scanSource", FAMILYSEARCH)
    book.pop("kind", None)  # version 1 has no such key
    if not isinstance(book.get("archive"), dict):  # four flat keys become one object
        flat = {"name": book.pop("archive", None), **{k: book.pop(k, None) for k in ARCHIVE_ORDER[1:]}}
        flat = {k: v for k, v in flat.items() if isinstance(v, str) and v.strip()}
        if "name" in flat:
            book["archive"] = flat

    records = book.pop("records", [])
    fields = book.pop("fields", [])
    taken = set()
    for n, record in enumerate(records if isinstance(records, list) else []):
        if not isinstance(record, dict):
            continue
        record = dict(record)
        for key in ("no", "date"):  # version 1 leaves empty values out
            if record.get(key) == "":
                del record[key]
        if isinstance(record.get("fields"), dict):
            record["fields"] = {k: v for k, v in record["fields"].items() if v != ""}
        record["id"] = new_record_id(taken)
        taken.add(record["id"])
        records[n] = _ordered(record, RECORD_ORDER)
    default_id, default_title = part_name(records if isinstance(records, list) else [],
                                          fields if isinstance(fields, list) else [])
    part = {"id": part_id or default_id, "title": part_title or default_title,
            "status": book.pop("status", "draft"), "fields": fields, "records": records}
    book["parts"] = [_ordered(part, PART_ORDER)]
    return _ordered(book, BOOK_ORDER)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Upgrade pre-1.0 transcripts to spec version 1.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--author", help="author's name, for a file that names no author")
    parser.add_argument("--email", help="author's e-mail, for a file that names no author")
    parser.add_argument("--license", help="SPDX identifier, e.g. CC-BY-4.0, for a file that names no licence")
    parser.add_argument("--familysearch", action="store_true",
                        help="scan ids are FamilySearch <film>_<frame>")
    parser.add_argument("--part-id", help="id of the part the records go into (default: by record type)")
    parser.add_argument("--part-title", help="title of that part (default: by record type)")
    args = parser.parse_args(argv)
    if bool(args.author) != bool(args.email):
        parser.error("--author and --email go together")
    author = {"name": args.author, "email": args.email} if args.author else None

    failed = False
    for path in args.files:
        book = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(book, dict) or "parts" in book:
            print(f"{path}: skipped (already has parts, or is not a document)")
            continue
        if ("authors" not in book and not author) or ("license" not in book and not args.license):
            failed = True
            print(f"{path}: needs --author, --email and --license")
            continue
        book = migrate(book, author, args.license, args.familysearch, args.part_id, args.part_title)
        problems = validate_book(book)  # the name of a working file is not the spec's business
        if problems:
            failed = True
            for problem in problems:
                print(f"{path}: {problem}")
            continue
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(book, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        print(f"{path}: upgraded")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
