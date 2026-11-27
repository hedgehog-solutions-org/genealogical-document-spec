# Changelog

All notable changes to the spec are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the versions follow the
rules in [SPEC.md](SPEC.md#versions): a major version can make a valid document invalid,
a minor one cannot.

## [Unreleased]

## [1.0.0] - 2026-11-26

The first published version. It is the format the Reviewer app and the transcribing
skills had been writing, with what a shared standard needs added. Files written before
it are upgraded with `tools/migrate.py`.

### Added

- `spec`: the version of the spec a document follows. Required.
- `parts`: a book is a list of parts, each with its own `id`, `title`, `status`,
  `fields` and `records`. A parish register keeps its births, marriages and deaths in
  one document, each with the fields that fit it. A book whose records all carry the
  same fields has one part.
- A record's `id`: 1 to 32 lower-case letters and digits, unique within the book, given
  once and never given to another record. Software that creates a record generates 12
  random characters. Required.
- A part's `yearFrom` and `yearTo`, for a part that covers fewer years than the book,
  and a part's `place`, for one parish of a volume that binds several together. Optional.
- `authors`: who made the transcript, each with `name` and `email`, and optionally
  `url` and `role`. Required, at least one.
- `license`, with `licenseUrl` for terms that are not an SPDX licence. Required.
- `scanSource`: the document says where its scans come from, what their ids look like
  (`idPattern`) and how to link to one (`urlTemplate`).
- `language`: the languages of the source.
- `generator`: the tool or model that made the machine reading.
- Extension keys: any key that starts with `x-` is allowed on a book, on a part and on
  a record.
- What a reader does with a document of a major version it does not know: it refuses
  the document without changing it and tells the user both versions. Every tool states
  the highest version it supports.
- A reference validator, a migration tool, and valid and invalid example documents.

### Changed

- A record's `type` and `year` are optional: a household of a confession list has no
  type, and an undated entry has no year. `type` takes `birth`, `marriage`, `death`,
  `other` or another lower-case word a collection needs.
- A book's `place` may be of any scale that fits the whole document, up to a province.
- The archive reference is one optional object, `archive`, with `name` and, as far as
  they apply, `fonds`, `inventory` and `file`. Before, `archive`, `fonds`, `inventory`
  and `file` were four required keys of the book, which left no place for a document
  that belongs to no archive.
- `status`, `fields` and `records` moved from the book into its parts. The book has no
  status of its own: it is checked when every part is `done`. Field keys are unique
  within a part.
- Scan ids are no longer required to be FamilySearch `<film>_<frame>` ids. Any non-empty
  text is a scan id; a document that wants a fixed shape declares it in
  `scanSource.idPattern`.
- A field label is keyed by any language tags, at least one, the same set for every
  field of a document. Before, exactly `uk` and `en` were required.
- An empty `no`, `date` or field value is invalid; the key is left out instead.
- The file name rule: a published document is `<id>.json`; `t.json` is the working name
  beside the scans and is exempt.

### Removed

- `kind` (`church` or `civil`): a document that was neither had no valid value.
- The exemption of the file name `t.json`. The name rule now applies to collections of
  published documents only, whatever a working file is called; `tools/validate.py`
  checks it with `--collection`.
- Rules that belong to one website and not to the format: the reserved id `search`, the
  ban on `**` and `|` in values, and the ban on family-tree references. A collection is
  free to add rules of its own on top of the spec.
