# Genealogical Document Spec 1.0

A format for transcripts of documents used in genealogy. This file is the spec:
where it and a schema or a tool disagree, this file is right and the other has a bug.

The words "must" and "must not" mark what makes a document valid. "Should" marks advice.

## The document

A document is one JSON file, UTF-8, holding one object: the transcript of one source,
called a **book**. A source is whatever is kept and cited as one thing: a parish
register, a civil registry book, a confession list, one file (справа) of an archive, a
bundle of letters in a family's hands. Other kinds of documents (gravestones and
others) are planned; see [Versions](#versions) for how they will arrive.

In a collection of published documents each is named `<id>.json`. What a file is called
while it is still being worked on is its tool's business, not the spec's.

A book is made of **parts**, and a part of **records**:

```
book            the source: what it is, who transcribed it, where its scans are
└── parts       runs of records that share their fields: births, marriages, deaths
    └── records the entries, each with an id of its own
```

## The book

| Key | Required | Meaning |
|---|---|---|
| `spec` | yes | Version of this spec the document follows, as `"MAJOR.MINOR"`: `"1.0"` |
| `id` | yes | Identifier, unique within a collection: lower-case Latin letters, digits and hyphens (`dadno-r-6508-14-164`). It should not change once published |
| `place` | yes | The place the book belongs to, at whatever scale fits all of it: a village, a town, a county (повіт), a province (губернія) |
| `archive` | no | Where the original is kept, when it is kept in an archive; see [Archive](#archive) |
| `title` | yes | Short title: what the book records and when |
| `description` | yes | What the book is, in a sentence or two: who kept it, what it holds, and the name it goes by where it is kept |
| `yearFrom`, `yearTo` | yes | Years the book covers, integers; equal for a one-year book |
| `language` | no | Languages the source is written in, as a list of [BCP 47](https://www.rfc-editor.org/info/bcp47) tags, the main one first: `["ru"]`, `["uk", "cu"]` |
| `authors` | yes | Who made the transcript; see [Authors](#authors) |
| `license` | yes | Terms of use; see [Licence](#licence) |
| `licenseUrl` | sometimes | Where the licence text is; see [Licence](#licence) |
| `generator` | no | The tool or model that made the machine reading: `{ "name": "…", "version": "…" }`, `version` optional |
| `scanSource` | no | Where the scans come from; see [Scans](#scans) |
| `createdAt` | yes | Day the transcript was made, `YYYY-MM-DD`. Set once |
| `updatedAt` | yes | Day a reading in it was last changed, `YYYY-MM-DD`; equal to `createdAt` until the first correction |
| `parts` | yes | The parts of the book, at least one, in the order they are shown; see [Parts](#parts) |

No other keys are allowed, except [extension keys](#extension-keys).

Tools that write a document should keep the keys in the order of the tables of this spec
(book, part, record) and use a two-space indent, so that two versions of a file compare
line by line.

### Archive

`archive` says where the original is kept. A document that belongs to no archive (a
letter or a family register in private hands) leaves the key out.

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | The archive, by the abbreviation it is cited with: `ДАДнО`, `ЦДІАК` |
| `fonds` | no | Fonds (фонд), as text: `"Р-6508"` |
| `inventory` | no | Inventory (опис) within the fonds: `"14"` |
| `file` | no | File (справа) within the inventory: `"164"` |

```json
"archive": { "name": "ДАДнО", "fonds": "Р-6508", "inventory": "14", "file": "164" }
```

An archive that cites its holdings in another way gives `name` and as many of the other
three as apply.

### Authors

`authors` is a list of at least one author, the main one first.

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | A person's or an organisation's name |
| `email` | yes | An address at which the author can be reached about the transcript |
| `url` | no | The author's page, `http(s)://…` |
| `role` | no | `transcriber` (made the reading), `reviewer` (checked it against the scans) or `editor` (prepared it for publication) |

The e-mail address is published with the document. Use one you are willing to make
public.

### Licence

`license` says under which terms the transcript may be used. It is one of:

- an [SPDX licence identifier](https://spdx.org/licenses/), such as `CC0-1.0`,
  `CC-BY-4.0` or `CC-BY-NC-4.0`;
- `LicenseRef-<name>` for any other terms (a paid licence, a private agreement). Then
  `licenseUrl` is required and points to the text of the terms.

`licenseUrl` may also be given with an SPDX identifier.

The licence covers the transcript: the reading and its arrangement. It says nothing
about the scans, which stay under the terms of whoever holds them.

### Parts

A part is a run of records that share a list of fields: the births of a parish
register, its marriages, its deaths; the one table of a civil register; a second parish
bound into the same volume.

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | Identifier of the part, unique within the book: lower-case Latin letters, digits and hyphens (`births`, `marriages`, `deaths`, `records`). It should not change once published |
| `title` | yes | Heading of the part, in the language of the collection: «Народження», "Marriages" |
| `place` | no | The place this part belongs to, when it is narrower than the book's: one parish of a volume that binds several together |
| `yearFrom`, `yearTo` | no | Years this part covers, when it covers fewer than the book: integers, given together, within the book's years |
| `status` | yes | `draft`: a machine reading no person has checked. `done`: a person has checked every record of the part against its scan |
| `fields` | yes | The fields this part's records carry; see [Fields](#fields) |
| `records` | yes | The part's records, in the order of the source; see [A record](#a-record). May be empty |

No other keys are allowed, except [extension keys](#extension-keys).

- A book whose records all carry the same fields has one part.
- Parts do not nest.
- The book has no status of its own. It is checked when every part is `done`.
- The book's `yearFrom`–`yearTo` cover the whole document. A part gives years of its own
  when they are narrower: a register for 1900–1919 whose births run from 1902 to 1918
  has `"yearFrom": 1902, "yearTo": 1918` on its births part. A part without them covers
  the book's years.
- The book's `place` covers the whole document, at as wide a scale as that takes. A
  volume of ten villages has one part per village, or one per village and kind of
  record («Домоткань: народження»), each with its own `place`. Parts are a flat list in
  the order of the source; a reader that wants to group them does so by `place`.
- A part is not tied to one type of record. A court decision pasted among the births is
  an `other` record in the births part, and a register written as running entries is
  one part with births, marriages and deaths in the order they were written.

### Fields

Every part declares its own list of record fields, in the order they are shown:

```json
"fields": [
  { "key": "child",  "label": { "uk": "Дитина", "en": "Child" } },
  { "key": "father", "label": { "uk": "Батько", "en": "Father" } }
]
```

- `key` starts with a lower-case Latin letter, then letters and digits (`informant`,
  `causeOfDeath`). Keys are unique within a part; the same key may be declared in
  several parts.
- `label` gives the field's name in one or more languages, keyed by BCP 47 tag. Every
  field of a book, in all its parts, must carry the same set of languages. Labels are the only translated
  part of a document; values are the source's own words.
- **The first field is the headline of a record** and must be filled in every record
  of the part.
  A reader shows it without its label and every further field as «Label: value».
- A part transcribed as running text declares a single field, such as `entry`. A part
  kept on forms or in a table declares one field per column.
- The same thing should have the same key and labels across parts and across books.
  Keys in use: `entry`, `child`, `father`, `mother`, `parents`, `godparents`, `sex`,
  `born`, `baptized`, `groom`, `bride`, `witnesses`, `deceased`, `died`, `buried`,
  `age`, `occupation`, `cause`, `address`, `informant`, `documents`, `certificate`,
  `notes`.

### Scans

A record names the scans it appears on by id. What an id is depends on the book:

- **Without `scanSource`**, a scan id is the name of an image file kept beside the
  document, without its extension: `"120645240_00316"` for `120645240_00316.jpeg`.
- **With `scanSource`**, the book says where its scans are:

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | Name of the source: `FamilySearch`, `ЦДІАК`, a family archive |
| `url` | no | Address of the collection, film or file the scans belong to |
| `idPattern` | no | A regular expression. Every scan id in the document must match it in full |
| `urlTemplate` | no | Address of one scan, with `{id}` where the scan id goes |

```json
"scanSource": {
  "name": "FamilySearch",
  "url": "https://www.familysearch.org/search/film/007805907",
  "idPattern": "\\d{9}_\\d{5}"
}
```

`idPattern` should use only syntax that means the same in ECMAScript and in Python
(character classes, groups, quantifiers), since both kinds of tools read it. A source
whose address cannot be built by putting the id into a template (FamilySearch counts
frames from zero in its addresses) gives `url` and `idPattern` and leaves the link to
the reader.

A document with a `scanSource` may still be kept beside image files named after its
scan ids; the two do not exclude each other.

## A record

| Key | Required | Meaning |
|---|---|---|
| `id` | yes | Identifier of the record; see [Record ids](#record-ids) |
| `type` | no | What the entry records: `birth`, `marriage`, `death`, `other`, or another word a collection needs, in lower-case Latin letters, digits and hyphens. Left out when no type fits (a household of a confession list) |
| `year` | no | Integer within the years of the record's part when the part gives them, otherwise within the book's `yearFrom`–`yearTo`. Left out when it is not known |
| `no` | no | Entry number as written (`"56"`, `"жін. 19"`) |
| `date` | no | Date text as written (`"нар. 3.05, хр. 4.05"`) |
| `scans` | yes | Scan ids, in reading order, none twice. `[]` when there is no scan |
| `fields` | yes | Values keyed by the field keys of the record's part; all text |

No other keys are allowed, except [extension keys](#extension-keys). A key with nothing
to say is left out: an empty `no`, `date` or field value is not valid.

Values are plain text in the source's own words and language. Two things have a fixed
form: a date in a field of its own is `DD.MM.YYYY`, and a field for sex holds the word
the collection has chosen for it, the same in every record.

### Record ids

A record is named by an id of its own, not by its place in the file, so that a link to
it, a note about it or a mark that it was reviewed stays true when records are added,
moved or removed around it.

- `id` is 1 to 32 lower-case Latin letters and digits (`k3f9x2mq7a1c`), unique within
  the book, across all its parts.
- It is given once, when the record is created, and never changes: not when the
  record's text is corrected, and not when the record is moved to another part.
- It is never given to another record. When a record is removed, its id is gone.
- It is opaque: it says nothing about the record's place, order, type or entry number.
  The order of records is their order in the file.
- Software that creates a record generates 12 random characters from `a`–`z` and
  `0`–`9`. No counter is kept: two people adding records to copies of the same book do
  not give out the same id, and no tool has to remember the ids that were removed.
- From outside a document, a record is named by the book's id and its own:
  `dadno-193-2-205` / `k3f9x2mq7a1c`.

## Doubtful readings

A reading the transcriber is not sure of is marked inside the text, in `no`, `date` or
any field value:

| In the file | Meaning |
|---|---|
| `__Слабко__` | Uncertain: the best reading, but another is possible |
| `~~Сират~~` | A guess from a few legible strokes |
| `[unreadable]` | Nothing could be read at this place |

- Mark the smallest piece in doubt, a word, a number or a single letter: `Хлиборо__б__`.
- A mark does not nest and does not cross from one value into another. A lone `__` or
  `~~` is ordinary text.
- A search should ignore the marks: `Хлиборо__б__` is found as «хлибороб».
- A document needs no marks at all, and a `done` document may still have some: a person
  can confirm that a place is unreadable.

## What a document holds

Only what the source says. Conclusions about who is whose ancestor, identifiers from a
family tree, notes about how the transcription went and text formatting do not belong in
a document. A tool or a collection that needs to keep something of its own beside the
transcript uses an extension key or a separate file.

## Extension keys

A key that starts with `x-` is allowed on a book, on a part and on a record, with any
JSON value:

```json
"x-price": { "amount": 5, "currency": "EUR" }
```

A reader must ignore extension keys it does not know, and a tool that rewrites a
document must keep them. A key that proves useful to many can be proposed for the spec
under a plain name.

## Rules

A document is valid when all of these hold. The JSON Schemas in `schemas/v1/` check
rules 1 to 3 (and that a day has the shape `YYYY-MM-DD`, though not that it exists); the
rest need code, and `tools/validate.py` checks them all.

1. The file is valid JSON and holds one object with the keys described above and no
   others, apart from extension keys.
2. Every value has the type and shape its table gives. Text is not empty or made of
   spaces only.
3. A `license` that starts with `LicenseRef-` comes with `licenseUrl`.
4. `spec` has the major version the reader knows.
5. In a collection of published documents, each file is named `<id>.json` and no two
   documents share an id. (`tools/validate.py --collection` checks this; the name of a
   file that is still being worked on is not checked.)
6. `yearFrom` is not after `yearTo`, on the book and on a part. A part's years are given
   together and lie within the book's. A record's `year`, when it has one, lies within
   its part's years when the part gives them, otherwise within the book's.
7. `createdAt` and `updatedAt` are real days, and `createdAt` is not after `updatedAt`.
8. Part ids are unique within the book.
9. Field keys are unique within a part, and every label of the book has the same set of
   languages.
10. Record ids are unique within the book.
11. A record uses only the field keys its own part declares, and its part's first field
    is filled.
12. With `scanSource.idPattern`, every scan id matches it in full.

A collection may add rules of its own (a fixed set of label languages, a fixed scan
source), as long as its documents stay valid by these.

## Versions

The spec has a version of three numbers, `MAJOR.MINOR.PATCH`. A document carries the
first two in `spec`.

| Change | Example | Version |
|---|---|---|
| A valid document becomes invalid, or a key changes its meaning | a key is removed or renamed, an optional key becomes required | major |
| Every valid document stays valid | a new optional key, a new value for `role` or `status`, a new kind of document | minor |
| Nothing about validity changes | clearer wording, a fixed example, a bug in a schema or a tool | patch |

What this asks of tools:

- **Every tool** that reads documents states the highest version of the spec it
  supports, where its user can see it.
- **A reader** refuses a document whose major version it does not know: it does not
  show it, guess at its structure or change it, and it tells the user the document's
  version and the highest version it supports. Refusing one document does not stop
  work on the others.
- **A reader** accepts every document of a major version it knows. In a document with a
  newer minor version than its own it ignores the keys it does not know, and it must not
  fail on a value it does not know in `type`, `status` or `role`: it shows the
  value as it is.
- **A writer** sets `spec` to the lowest version whose features the document uses, and
  keeps the keys it does not know when it rewrites a document. A writer that adds a
  record gives it a new id; one that changes or moves a record keeps its id.
- **A strict validator** (one that guards a collection) may refuse a minor version newer
  than its own.

New kinds of documents (gravestones, letters and others) will each get a schema of their
own and be told apart by a `document` key. A file without that key is a book, so adding
them is a minor change.

Every version is listed in [CHANGELOG.md](CHANGELOG.md).
