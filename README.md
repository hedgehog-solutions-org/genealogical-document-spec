# Genealogical Document Spec

A JSON format for transcripts of archive documents used in genealogy: parish registers,
civil registry books, confession lists, etc. One JSON describes one archive file:
what it is, who transcribed it and under which licence, where its scans are, and every
record in it, part by part, with each doubtful reading marked in the text.

It is meant to be shared: a transcript written by one tool can be reviewed in another,
published on a site, or passed to someone else, and each of them knows what to expect.

**Current version: 1.0.0** · [The spec](SPEC.md) · [Changelog](CHANGELOG.md)

```json
{
  "spec": "1.0",
  "id": "dadno-193-2-51",
  "place": "Домоткань",
  "archive": { "name": "ДАДнО", "fonds": "193", "inventory": "2", "file": "51" },
  "title": "Метрична книга, 1883–1886",
  "description": "Метрична книга Архангело-Михайлівської церкви с. Домоткань: народження, шлюби, смерті.",
  "yearFrom": 1883,
  "yearTo": 1886,
  "authors": [{ "name": "Олена Бджілка", "email": "olena@acme.inc" }],
  "license": "CC-BY-4.0",
  "createdAt": "2026-01-01",
  "updatedAt": "2026-03-01",
  "parts": [
    {
      "id": "births",
      "title": "Народження",
      "status": "done",
      "fields": [
        { "key": "child", "label": { "uk": "Дитина", "en": "Child" } },
        { "key": "parents", "label": { "uk": "Батьки", "en": "Parents" } }
      ],
      "records": [
        {
          "id": "k3f9x2mq7a1c",
          "type": "birth",
          "year": 1883,
          "no": "жін. 1",
          "scans": ["007806792_00004"],
          "fields": {
            "child": "Василій",
            "parents": "Прокофій Демианов Нестеренко и Васса Сафронова"
          }
        }
      ]
    },
    {
      "id": "marriages",
      "title": "Шлюби",
      "status": "draft",
      "fields": [
        { "key": "groom", "label": { "uk": "Наречений", "en": "Groom" } },
        { "key": "bride", "label": { "uk": "Наречена", "en": "Bride" } }
      ],
      "records": [
        {
          "id": "7hq4v1xb9s3m",
          "type": "marriage",
          "year": 1884,
          "no": "56",
          "date": "10.11.1919",
          "scans": ["007806792_00024"],
          "fields": {
            "groom": "Иванъ Германовъ Коваль, 22",
            "bride": "Анна Михайлова __Бугай__, 19"
          }
        }
      ]
    }
  ]
}
```

## What is here

| Path | What |
|---|---|
| [`SPEC.md`](SPEC.md) | The spec itself: every key, every rule, the doubt marks, the versioning rules |
| [`schemas/v1/`](schemas/v1) | JSON Schemas (draft-07) for a book and for one record |
| [`examples/valid/`](examples/valid), [`examples/invalid/`](examples/invalid) | Documents that pass, and documents that each break one rule |
| [`tools/validate.py`](tools/validate.py) | Reference validator: one file, Python standard library only |
| [`tools/migrate.py`](tools/migrate.py) | Upgrades files written before version 1 |
| [`CHANGELOG.md`](CHANGELOG.md) | What changed in each version |

## Checking a document

```
python3 tools/validate.py path/to/file-or-folder
```

It prints `N documents, M records OK`, or one line per problem. Add `--collection` for a
folder of published documents: each must then be named `<id>.json`, and no two may share
an id. The validator checks
everything in the spec, including what a JSON Schema cannot say (a record's year lies
within the book's years, a record uses only the fields its part declares, no two records
share an id, and so on). To check in
another language, use the schemas and add the rules listed under
[Rules](SPEC.md#rules).

For editor completion, point your editor at the schema:

```
https://raw.githubusercontent.com/hedgehog-solutions-org/genealogical-document-spec/main/schemas/v1/book.schema.json
```

## Upgrading older files

```
python3 tools/migrate.py --author "Your Name" --email you@example.org --license CC-BY-4.0 path/to/t.json
```

A file written before version 1 had one list of fields and one list of records for the
whole book, and no record ids. Its fields and records move into one part, named after
what it holds (`births`, `marriages`, `deaths`, otherwise `records`; `--part-id` and
`--part-title` set the name by hand), and every record gets an id. Upgrade a file once
and keep the result: the ids are random, so a second upgrade of the old file would give
other ones.

Add `--familysearch` when the scan ids are FamilySearch `<film>_<frame>` ids. A file that
already names its authors and its licence needs neither `--author` nor `--license`.

## Using the spec in a project

Copy `tools/validate.py` (or the two schemas) into your project and note the version you
copied. A tool that reads documents says which version it supports, accepts every `1.x`
document and refuses, without changing it, a document of a major version it does not
know; see
[Versions](SPEC.md#versions) for what may change between them.

## Proposing a change

Open an issue that says what you need to record and shows a piece of a real document.
Changes that keep every valid document valid go into the next minor version. Anything
else waits for a major one.

## Development

```
python3 -m unittest discover -s tests   # add `pip install jsonschema` to test the schemas too
ruff check .
```

A release is made by the "Release" workflow, run by hand: it checks that `VERSION` has a
section in the changelog, tags the commit and publishes the section as release notes.

## Licence

The spec text and the examples are under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The schemas and the tools are under the [MIT licence](LICENSE).

Made by [Hedgehog Solutions](https://github.com/hedgehog-solutions-org).
