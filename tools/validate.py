#!/usr/bin/env python3
"""Reference validator for the Genealogical Document Spec, version 1.

    python3 validate.py <file or folder> [...]

A folder is searched for *.json at any depth (hidden files and folders are skipped).
With --collection the files are checked as a collection of published documents: each is
named <id>.json and no two share an id.
Prints "N documents, M records OK", or one line per problem and exits 1.

It checks everything SPEC.md asks for, including the rules a JSON Schema cannot express.
Python 3.10+, standard library only, one file: copy it into a project that needs it.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

SPEC_VERSION = "1.0.0"
MAJOR, MINOR = 1, 0

# Canonical key order, for tools that write documents.
BOOK_ORDER = ["spec", "id", "place", "archive", "title", "description",
              "yearFrom", "yearTo", "language", "authors", "license", "licenseUrl",
              "generator", "scanSource", "createdAt", "updatedAt", "parts"]
PART_ORDER = ["id", "title", "place", "yearFrom", "yearTo", "status", "fields", "records"]
PART_REQUIRED = ["id", "title", "status", "fields", "records"]
ARCHIVE_ORDER = ["name", "fonds", "inventory", "file"]
RECORD_ORDER = ["id", "type", "year", "no", "date", "scans", "fields"]

BOOK_REQUIRED = [k for k in BOOK_ORDER if k not in ("archive", "language", "licenseUrl", "generator", "scanSource")]
TEXT_KEYS = ["place", "title", "description"]
RECORD_REQUIRED = ["id", "scans", "fields"]
STATUSES = ("draft", "done")
TYPES = ("birth", "marriage", "death", "other")  # the values in common use; others are allowed
TYPE = re.compile(r"[a-z][a-z0-9-]*")
ROLES = ("transcriber", "reviewer", "editor")

SPEC = re.compile(r"(\d+)\.(0|[1-9]\d*)")
ID = re.compile(r"[a-z0-9-]+")
RECORD_ID = re.compile(r"[a-z0-9]{1,32}")
FIELD_KEY = re.compile(r"[a-z][a-zA-Z0-9]*")
LANG = re.compile(r"[a-z]{2,3}(-[A-Za-z0-9]{1,8})*")
DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
URL = re.compile(r"https?://\S+")
# The three doubt marks: __uncertain__, ~~guess~~, [unreadable].
MARK = re.compile(r"__(.+?)__|~~(.+?)~~|\[unreadable\]")


def count_marks(text: str) -> int:
    """How many doubt marks a value holds."""
    return len(MARK.findall(text))


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_day(value) -> bool:
    if not isinstance(value, str) or not DAY.fullmatch(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _extra(obj: dict, allowed, extensions: bool) -> list[str]:
    return [k for k in obj if k not in allowed and not (extensions and k.startswith("x-"))]


def _check_authors(authors, problems: list[str]) -> None:
    if not isinstance(authors, list) or not authors:
        problems.append("authors must be a list with at least one author")
        return
    for n, author in enumerate(authors, 1):
        if not isinstance(author, dict):
            problems.append(f"author {n}: not an object")
            continue
        extra = _extra(author, ("name", "email", "url", "role"), False)
        if extra:
            problems.append(f"author {n}: unknown keys: {', '.join(extra)}")
        if not _is_text(author.get("name")):
            problems.append(f"author {n}: name must be non-empty text")
        email = author.get("email")
        if not isinstance(email, str) or not EMAIL.fullmatch(email):
            problems.append(f"author {n}: email must be an e-mail address")
        if "url" in author and not (isinstance(author["url"], str) and URL.fullmatch(author["url"])):
            problems.append(f"author {n}: url must be an http(s) address")
        if "role" in author and author["role"] not in ROLES:
            problems.append(f"author {n}: role {author['role']!r} is not one of: {', '.join(ROLES)}")


def _check_archive(archive, problems: list[str]) -> None:
    if not isinstance(archive, dict):
        problems.append("archive must be an object with the archive's name; leave it out when there is none")
        return
    extra = _extra(archive, ARCHIVE_ORDER, False)
    if extra:
        problems.append(f"archive: unknown keys: {', '.join(extra)}")
    if not _is_text(archive.get("name")):
        problems.append("archive: name must be non-empty text")
    for key in ARCHIVE_ORDER[1:]:
        if key in archive and not _is_text(archive[key]):
            problems.append(f"archive: {key} must be non-empty text; leave it out when there is none")


def _check_scan_source(source, problems: list[str]):
    """Check scanSource; return the compiled idPattern, or None."""
    if not isinstance(source, dict):
        problems.append("scanSource must be an object")
        return None
    extra = _extra(source, ("name", "url", "idPattern", "urlTemplate"), False)
    if extra:
        problems.append(f"scanSource: unknown keys: {', '.join(extra)}")
    if not _is_text(source.get("name")):
        problems.append("scanSource: name must be non-empty text")
    if "url" in source and not (isinstance(source["url"], str) and URL.fullmatch(source["url"])):
        problems.append("scanSource: url must be an http(s) address")
    template = source.get("urlTemplate")
    if "urlTemplate" in source and not (isinstance(template, str) and URL.fullmatch(template)
                                        and "{id}" in template):
        problems.append("scanSource: urlTemplate must be an http(s) address with {id} in it")
    if "idPattern" in source:
        try:
            if not _is_text(source["idPattern"]):
                raise re.error("empty")
            return re.compile(source["idPattern"])
        except re.error as error:
            problems.append(f"scanSource: idPattern is not a regular expression ({error})")
    return None


def _check_fields(fields, languages: list, bad) -> list[str]:
    """Check the fields one part declares; return their keys in order. `languages` holds
    the label languages of the book's first field (in a list, so that it is shared by
    all the parts): every label of the book must be in the same ones."""
    declared = []
    for field in fields if isinstance(fields, list) else []:
        key = field.get("key") if isinstance(field, dict) else None
        label = field.get("label") if isinstance(field, dict) else None
        if not isinstance(key, str) or not FIELD_KEY.fullmatch(key):
            bad(f"bad field key {key!r}")
            continue
        if key in declared:
            bad(f"field key {key!r} is declared twice")
        if set(field) != {"key", "label"} or not isinstance(label, dict) or not label \
                or not all(isinstance(k, str) and LANG.fullmatch(k) and _is_text(v) for k, v in label.items()):
            bad(f"field {key!r} needs exactly key and label; a label is non-empty text "
                f"keyed by language tag")
        elif not languages:
            languages.append(set(label))
        elif set(label) != languages[0]:
            bad(f"field {key!r}: labels must be in the same languages as the book's first "
                f"field's ({', '.join(sorted(languages[0]))})")
        declared.append(key)
    if not declared:
        bad("no fields declared")
    return declared


def _check_record(record, declared: list[str], years: tuple | None, of: str, scan_id, ids: dict, where: str,
                  bad) -> None:
    """`years` is the range the record's year must lie in (None when that range is itself
    wrong), and `of` names whose range it is: the part's or the book's."""
    if not isinstance(record, dict):
        bad("not an object")
        return
    absent = [k for k in RECORD_REQUIRED if k not in record]
    if absent:
        bad(f"missing keys: {', '.join(absent)}")
        return
    unknown = _extra(record, RECORD_ORDER, True)
    if unknown:
        bad(f"unknown keys: {', '.join(unknown)}")
    if not isinstance(record["id"], str) or not RECORD_ID.fullmatch(record["id"]):
        bad(f"id {record['id']!r} must be 1 to 32 lower-case Latin letters and digits")
    elif record["id"] in ids:
        bad(f"id {record['id']!r} is also the id of {ids[record['id']]}")
    else:
        ids[record["id"]] = where
    if "type" in record and not (isinstance(record["type"], str) and TYPE.fullmatch(record["type"])):
        bad(f"type {record['type']!r} must be a word in lower-case Latin letters, digits and hyphens "
            f"({', '.join(TYPES)}, or another); leave it out when no type fits")
    if "year" not in record:
        pass  # an entry whose year is not known
    elif not _is_int(record["year"]):
        bad("year must be an integer; leave it out when it is not known")
    elif years and not years[0] <= record["year"] <= years[1]:
        bad(f"year {record['year']} is outside the {of}'s years")
    for key in ("no", "date"):
        if key in record and not _is_text(record[key]):
            bad(f"{key} must be non-empty text; leave it out when there is none")
    scans = record["scans"]
    if not isinstance(scans, list):
        bad("scans must be a list")
        scans = []
    if len(set(map(str, scans))) != len(scans):
        bad("a scan is listed twice")
    for scan in scans:
        if not isinstance(scan, str) or not scan:
            bad(f"bad scan id {scan!r}")
        elif scan_id and not scan_id.fullmatch(scan):
            bad(f"scan {scan!r} does not match scanSource.idPattern")
    fields = record["fields"]
    if not isinstance(fields, dict):
        bad("fields must be an object")
        return
    for key, value in fields.items():
        if key not in declared:
            bad(f"field {key!r} is not declared in this part")
        if not isinstance(value, str):
            bad(f"field {key!r} must be text")
        elif not value.strip() and key != declared[0]:
            bad(f"field {key!r} is empty; leave it out")
    if not str(fields.get(declared[0], "")).strip():
        bad(f"first field {declared[0]!r} is empty")


def all_records(book: dict) -> list[dict]:
    """Every record of a book, part after part, in the order of the file."""
    parts = book.get("parts") if isinstance(book, dict) else None
    found = []
    for part in parts if isinstance(parts, list) else []:
        records = part.get("records") if isinstance(part, dict) else None
        found += [r for r in records if isinstance(r, dict)] if isinstance(records, list) else []
    return found


def validate_book(book, file_name: str | None = None) -> list[str]:
    """Return the problems of one document (an already parsed JSON value); [] when valid.

    `file_name`, when given, is checked against the id: in a collection of published
    documents each is named <id>.json. Leave it out for a file that is still being
    worked on, whose name is its tool's business.
    """
    if not isinstance(book, dict):
        return ["the file is not a JSON object"]
    problems = []

    version = SPEC.fullmatch(book["spec"]) if isinstance(book.get("spec"), str) else None
    if "spec" not in book:
        problems.append('missing key: spec (the spec version, e.g. "1.0"); '
                        "a file from before version 1 is upgraded with tools/migrate.py")
    elif not version:
        problems.append(f"spec {book['spec']!r} is not a version like \"1.0\"")
    elif int(version[1]) != MAJOR:
        return [f"spec {book['spec']}: this validator checks version {MAJOR}.x only"]
    elif int(version[2]) > MINOR:
        problems.append(f"spec {book['spec']} is newer than this validator ({MAJOR}.{MINOR})")

    missing = [k for k in BOOK_REQUIRED if k not in book and k != "spec"]
    extra = _extra(book, BOOK_ORDER, True)
    if missing:
        problems.append(f"missing keys: {', '.join(missing)}")
    if extra:
        problems.append(f"unknown keys: {', '.join(extra)}")
    if missing:
        return problems

    if not isinstance(book["id"], str) or not ID.fullmatch(book["id"]):
        problems.append(f"id {book['id']!r} must be lower-case Latin letters, digits and hyphens")
    elif file_name and file_name != book["id"] + ".json":
        problems.append(f"id {book['id']!r} does not match the file name {file_name!r}")
    for key in TEXT_KEYS:
        if not _is_text(book[key]):
            problems.append(f"{key} must be non-empty text")
    years_ok = _is_int(book["yearFrom"]) and _is_int(book["yearTo"])
    if not years_ok:
        problems.append("yearFrom and yearTo must be integers")
    elif book["yearFrom"] > book["yearTo"]:
        problems.append("yearFrom is after yearTo")

    if "archive" in book:
        _check_archive(book["archive"], problems)
    if "language" in book:
        tags = book["language"]
        if not isinstance(tags, list) or not tags or len(set(map(str, tags))) != len(tags) \
                or not all(isinstance(t, str) and LANG.fullmatch(t) for t in tags):
            problems.append("language must be a list of distinct language tags, e.g. [\"uk\"]")
    _check_authors(book["authors"], problems)
    if not _is_text(book["license"]) or book["license"] != book["license"].strip():
        problems.append("license must be an SPDX identifier or LicenseRef-<name>")
    elif book["license"].startswith("LicenseRef-") and "licenseUrl" not in book:
        problems.append(f"license {book['license']!r} needs licenseUrl")
    if "licenseUrl" in book and not (isinstance(book["licenseUrl"], str) and URL.fullmatch(book["licenseUrl"])):
        problems.append("licenseUrl must be an http(s) address")
    if "generator" in book:
        generator = book["generator"]
        if not isinstance(generator, dict) or _extra(generator, ("name", "version"), False) \
                or not _is_text(generator.get("name")) \
                or ("version" in generator and not _is_text(generator["version"])):
            problems.append("generator needs name, and may have version; both non-empty text")
    scan_id = _check_scan_source(book["scanSource"], problems) if "scanSource" in book else None

    days_ok = True
    for key in ("createdAt", "updatedAt"):
        if not _is_day(book[key]):
            days_ok = False
            problems.append(f"{key} must be a date, YYYY-MM-DD")
    if days_ok and book["createdAt"] > book["updatedAt"]:
        problems.append("createdAt is after updatedAt")

    parts = book["parts"]
    if not isinstance(parts, list) or not parts:
        problems.append("parts must be a list with at least one part")
        return problems
    part_ids, record_ids, languages = set(), {}, []
    for number, part in enumerate(parts, 1):
        named = isinstance(part, dict) and isinstance(part.get("id"), str) and ID.fullmatch(part["id"])
        name = f"part {part['id']!r}" if named else f"part {number}"

        def bad(message, name=name):
            problems.append(f"{name}: {message}")

        if not isinstance(part, dict):
            bad("not an object")
            continue
        if named:
            if part["id"] in part_ids:
                bad("this part id is used twice")
            part_ids.add(part["id"])
        absent = [k for k in PART_REQUIRED if k not in part]
        if absent:
            bad(f"missing keys: {', '.join(absent)}")
            continue
        unknown = _extra(part, PART_ORDER, True)
        if unknown:
            bad(f"unknown keys: {', '.join(unknown)}")
        if not isinstance(part["id"], str) or not ID.fullmatch(part["id"]):
            bad(f"id {part['id']!r} must be lower-case Latin letters, digits and hyphens")
        if not _is_text(part["title"]):
            bad("title must be non-empty text")
        if "place" in part and not _is_text(part["place"]):
            bad("place must be non-empty text; leave it out when it is the book's")
        years, of = ((book["yearFrom"], book["yearTo"]) if years_ok else None), "book"
        if "yearFrom" in part or "yearTo" in part:
            years, of = None, "part"
            if "yearFrom" not in part or "yearTo" not in part:
                bad("yearFrom and yearTo are given together")
            elif not _is_int(part["yearFrom"]) or not _is_int(part["yearTo"]):
                bad("yearFrom and yearTo must be integers")
            elif part["yearFrom"] > part["yearTo"]:
                bad("yearFrom is after yearTo")
            elif years_ok and not book["yearFrom"] <= part["yearFrom"] <= part["yearTo"] <= book["yearTo"]:
                bad(f"years {part['yearFrom']}–{part['yearTo']} are outside the book's years")
            else:
                years = (part["yearFrom"], part["yearTo"])
        if part["status"] not in STATUSES:
            bad(f"status {part['status']!r} is not one of: {', '.join(STATUSES)}")
        if not isinstance(part["fields"], list):
            bad("fields must be a list")
        declared = _check_fields(part["fields"], languages, bad)
        if not isinstance(part["records"], list):
            bad("records must be a list")
            continue
        if not declared:
            continue
        for place, record in enumerate(part["records"], 1):
            where = f"{name}, record {place}"
            _check_record(record, declared, years, of, scan_id, record_ids, where,
                          lambda message, where=where: problems.append(f"{where}: {message}"))
    return problems


def validate_file(path: Path, published: bool = False) -> tuple[list[str], int]:
    """Return (problems, record count) for one file. `published` also checks that the
    file is named after the document's id."""
    try:
        book = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"not valid JSON: {error}"], 0
    return validate_book(book, Path(path).name if published else None), len(all_records(book))


def find_documents(target: Path) -> list[Path]:
    target = Path(target)
    if target.is_file():
        return [target]
    found = []
    for path in target.rglob("*.json"):
        if path.is_file() and not any(part.startswith(".") for part in path.relative_to(target).parts):
            found.append(path)
    return sorted(found)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=f"Validate documents against the Genealogical "
                                                 f"Document Spec {SPEC_VERSION}.")
    parser.add_argument("paths", nargs="+", type=Path, help="files, or folders searched for *.json")
    parser.add_argument("--collection", action="store_true",
                        help="the files are a collection of published documents: each must be named "
                             "<id>.json, and no two may share an id")
    args = parser.parse_args(argv)

    files = [f for target in args.paths for f in find_documents(target)]
    if not files:
        print("no documents found")
        return 1
    failed, total, ids = False, 0, {}
    for path in files:
        problems, records = validate_file(path, args.collection)
        total += records
        if not problems and args.collection:
            book_id = json.loads(path.read_text(encoding="utf-8"))["id"]
            if book_id in ids:
                problems.append(f"id {book_id!r} is also used by {ids[book_id]}")
            ids.setdefault(book_id, path)
        for problem in problems:
            failed = True
            print(f"{path}: {problem}")
    if failed:
        return 1
    print(f"{len(files)} documents, {total} records OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
