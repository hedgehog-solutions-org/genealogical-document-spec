"""The examples are the test suite: every valid one passes, every invalid one fails for
the reason its name gives, in the reference validator and (where a schema can say it) in
the JSON Schemas."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import migrate  # noqa: E402
import validate  # noqa: E402

VALID = sorted((ROOT / "examples" / "valid").glob("*.json"))
# file name -> (a piece of the expected problem, whether the JSON Schema catches it too)
INVALID = {
    "missing-spec": ("missing key: spec", True),
    "missing-authors": ("missing keys: authors", True),
    "author-without-email": ("email must be an e-mail address", True),
    "licenseref-without-url": ("needs licenseUrl", True),
    "unknown-key": ("unknown keys: notes", True),
    "year-outside-book": ("outside the book's years", False),
    "year-outside-part": ("year 1921 is outside the part's years", False),
    "part-years-outside-book": ("years 1918–1919 are outside the book's years", False),
    "part-year-alone": ("yearFrom and yearTo are given together", True),
    "archive-without-name": ("archive: name must be non-empty text", True),
    "title-of-spaces": ("title must be non-empty text", True),
    "type-not-a-word": ("type 'Birth of a child' must be a word", True),
    "undeclared-field": ("'father' is not declared", False),
    "field-of-another-part": ("'note' is not declared in this part", False),
    "missing-record-id": ("missing keys: id", True),
    "duplicate-record-id": ("is also the id of part 'births', record 1", False),
    "no-parts": ("at least one part", True),
    "duplicate-part-id": ("part id is used twice", False),
    "status-on-the-book": ("unknown keys: status", True),
    "empty-headline": ("first field 'entry' is empty", True),
    "scan-not-matching-pattern": ("does not match scanSource.idPattern", False),
    "labels-in-different-languages": ("same languages", False),
    "created-after-updated": ("createdAt is after updatedAt", False),
    "duplicate-field-key": ("declared twice", False),
    "id-not-file-name": ("does not match the file name", False),
}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ReferenceValidator(unittest.TestCase):
    def test_valid_examples_pass(self):
        self.assertGreaterEqual(len(VALID), 4)
        for path in VALID:
            with self.subTest(path.name):
                records = sum(len(part["records"]) for part in load(path)["parts"])
                self.assertEqual(validate.validate_file(path, published=True), ([], records))

    def test_every_invalid_example_is_listed(self):
        names = {p.stem for p in (ROOT / "examples" / "invalid").glob("*.json")}
        self.assertEqual(names, set(INVALID))

    def test_invalid_examples_fail_for_their_reason(self):
        for name, (expected, _) in INVALID.items():
            with self.subTest(name):
                problems, _ = validate.validate_file(ROOT / "examples" / "invalid" / f"{name}.json", published=True)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(expected, problems[0])

    def test_the_file_name_is_checked_only_for_a_published_collection(self):
        import contextlib
        import io
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            for name in ("t.json", "copy.json"):
                shutil.copy(VALID[0], Path(folder) / name)
            self.assertEqual(validate.validate_file(Path(folder) / "t.json"), ([], 4))
            self.assertIn("does not match the file name", validate.validate_file(Path(folder) / "t.json", True)[0][0])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(validate.main([folder]), 0)
                self.assertEqual(validate.main(["--collection", folder]), 1)
            self.assertEqual(out.getvalue().count("does not match the file name"), 2)

    def test_ids_are_unique_in_a_collection(self):
        import contextlib
        import io
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "a").mkdir()
            for target in (Path(folder), Path(folder) / "a"):
                shutil.copy(VALID[0], target / VALID[0].name)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(validate.main([folder]), 0)
                self.assertEqual(validate.main(["--collection", folder]), 1)
            self.assertIn("is also used by", out.getvalue())

    def test_a_record_needs_no_type_and_no_year(self):
        book = load(ROOT / "examples" / "valid" / "minimal.json")
        record = book["parts"][0]["records"][0]
        del record["type"], record["year"]
        self.assertEqual(validate.validate_book(book), [])
        record["type"] = "household"  # a word of the collection's own
        self.assertEqual(validate.validate_book(book), [])
        for bad in ("", "Household", "two words", 3, None):
            record["type"] = bad
            self.assertIn("must be a word", validate.validate_book(book)[0], bad)
        del record["type"]
        record["year"] = "1850"
        self.assertIn("year must be an integer", validate.validate_book(book)[0])

    def test_a_part_may_have_a_place_of_its_own(self):
        book = load(ROOT / "examples" / "valid" / "tsdiak-990-1-291.json")
        self.assertEqual([part["place"] for part in book["parts"]], ["Домоткань", "Бородаївка"])
        book["parts"][0]["place"] = " "
        self.assertIn("place must be non-empty text", validate.validate_book(book)[0])
        del book["parts"][0]["place"]
        self.assertEqual(validate.validate_book(book), [])

    def test_extension_keys_are_allowed_on_book_and_record(self):
        book = load(ROOT / "examples" / "valid" / "minimal.json")
        book["x-price"] = {"amount": 5}
        book["parts"][0]["x-pages"] = "1-40"
        book["parts"][0]["records"][0]["x-box"] = [0, 0, 1, 1]
        self.assertEqual(validate.validate_book(book), [])

    def test_a_record_names_its_part_place_and_nothing_else(self):
        book = load(ROOT / "examples" / "valid" / "dadno-193-2-205.json")
        book["parts"][1]["records"][0]["year"] = 1800
        self.assertEqual(validate.validate_book(book),
                         ["part 'marriages', record 1: year 1800 is outside the part's years"])

    def test_the_same_field_key_may_be_declared_in_two_parts(self):
        book = load(ROOT / "examples" / "valid" / "dadno-193-2-205.json")
        book["parts"][2]["fields"].append(book["parts"][0]["fields"][-1])  # notes
        self.assertEqual(validate.validate_book(book), [])

    def test_a_document_needs_no_archive(self):
        book = load(ROOT / "examples" / "valid" / "dadno-193-2-205.json")
        del book["archive"]
        self.assertEqual(validate.validate_book(book), [])
        book["archive"] = {"name": "ДАДнО"}
        self.assertEqual(validate.validate_book(book), [])
        book["archive"] = {"name": "ДАДнО", "fonds": "", "shelf": "3"}
        self.assertEqual(validate.validate_book(book),
                         ["archive: unknown keys: shelf",
                          "archive: fonds must be non-empty text; leave it out when there is none"])
        book["archive"] = "ДАДнО"
        self.assertIn("archive must be an object", validate.validate_book(book)[0])

    def test_a_part_may_cover_fewer_years_than_the_book(self):
        book = load(ROOT / "examples" / "valid" / "dadno-193-2-205.json")
        births = book["parts"][0]
        self.assertNotIn("yearFrom", births)  # without them the book's years hold
        births["records"][0]["year"] = 1921
        self.assertEqual(validate.validate_book(book), [])
        births.update(yearFrom=1919, yearTo=1920)
        self.assertEqual(validate.validate_book(book),
                         ["part 'births', record 1: year 1921 is outside the part's years",
                          "part 'births', record 2: year 1921 is outside the part's years"])
        births.update(yearFrom=1920, yearTo=1919)
        self.assertEqual(validate.validate_book(book), ["part 'births': yearFrom is after yearTo"])
        births.update(yearFrom="1919", yearTo=1920)
        self.assertEqual(validate.validate_book(book), ["part 'births': yearFrom and yearTo must be integers"])

    def test_record_ids_are_unique_across_parts(self):
        book = load(ROOT / "examples" / "valid" / "dadno-193-2-205.json")
        book["parts"][2]["records"][0]["id"] = book["parts"][0]["records"][0]["id"]
        self.assertIn("is also the id of part 'births', record 1", validate.validate_book(book)[0])

    def test_record_id_shape(self):
        book = load(ROOT / "examples" / "valid" / "minimal.json")
        for bad in ("", "A1", "a-1", "x" * 33, 7):
            book["parts"][0]["records"][0]["id"] = bad
            self.assertIn("lower-case Latin letters and digits", validate.validate_book(book)[0], bad)

    def test_labels_share_languages_across_parts(self):
        book = load(ROOT / "examples" / "valid" / "dadno-193-2-205.json")
        del book["parts"][1]["fields"][0]["label"]["en"]
        self.assertIn("same languages", validate.validate_book(book)[0])

    def test_all_records_runs_through_the_parts(self):
        book = load(ROOT / "examples" / "valid" / "dadno-193-2-205.json")
        self.assertEqual([r["type"] for r in validate.all_records(book)], ["birth", "other", "marriage", "death"])

    def test_other_major_version_is_refused(self):
        book = load(ROOT / "examples" / "valid" / "minimal.json")
        book["spec"] = "2.0"
        self.assertEqual(validate.validate_book(book), ["spec 2.0: this validator checks version 1.x only"])

    def test_newer_minor_is_reported(self):
        book = load(ROOT / "examples" / "valid" / "minimal.json")
        book["spec"] = "1.7"
        self.assertIn("newer than this validator", validate.validate_book(book)[0])

    def test_marks_are_counted(self):
        self.assertEqual(validate.count_marks("__a__ b ~~c~~ [unreadable] __"), 3)

    def test_cli(self):
        self.assertEqual(validate.main([str(ROOT / "examples" / "valid")]), 0)
        self.assertEqual(validate.main([str(ROOT / "examples" / "invalid")]), 1)
        self.assertEqual(validate.main(["--collection", str(ROOT / "examples" / "valid")]), 0)

    def test_order_covers_every_schema_key(self):
        schema = load(ROOT / "schemas" / "v1" / "book.schema.json")
        self.assertEqual(set(schema["properties"]), set(validate.BOOK_ORDER))
        self.assertEqual(sorted(schema["required"]), sorted(validate.BOOK_REQUIRED))
        part = schema["definitions"]["part"]
        self.assertEqual(list(part["properties"]), validate.PART_ORDER)
        self.assertEqual(part["required"], validate.PART_REQUIRED)
        archive = schema["properties"]["archive"]
        self.assertEqual(list(archive["properties"]), validate.ARCHIVE_ORDER)
        record = load(ROOT / "schemas" / "v1" / "record.schema.json")
        self.assertEqual(list(record["properties"]), validate.RECORD_ORDER)
        self.assertEqual(sorted(record["required"]), sorted(validate.RECORD_REQUIRED))


AUTHOR = {"name": "A", "email": "a@example.org"}
OLD = {
    "id": "old", "place": "Kyiv", "archive": "ЦДІАК", "fonds": "127", "inventory": "1012",
    "file": "", "title": "Parish register, 1850", "description": "A file from before version 1.", "kind": "church",
    "yearFrom": 1850, "yearTo": 1850, "x-note": "kept", "createdAt": "2026-11-26", "updatedAt": "2026-11-26",
    "status": "done",
    "fields": [{"key": "entry", "label": {"en": "Entry"}}],
    "records": [
        {"type": "birth", "year": 1850, "no": "1", "scans": ["p1"], "fields": {"entry": "Ivan"}, "x-box": [1]},
        {"type": "other", "year": 1850, "scans": [], "fields": {"entry": "A note"}},
    ],
}


class Migration(unittest.TestCase):
    def test_old_file_becomes_one_part_with_record_ids(self):
        new = migrate.migrate(copy.deepcopy(OLD), AUTHOR, "CC0-1.0")
        self.assertEqual(validate.validate_book(new), [])
        self.assertEqual((new["spec"], new["authors"], new["license"]), ("1.0", [AUTHOR], "CC0-1.0"))
        self.assertEqual(new["archive"], {"name": "ЦДІАК", "fonds": "127", "inventory": "1012"})
        for gone in ("fonds", "inventory", "file"):
            self.assertNotIn(gone, new)
        self.assertEqual(list(new)[:4], ["spec", "id", "place", "archive"])
        self.assertNotIn("kind", new)
        self.assertEqual(list(new)[-2:], ["parts", "x-note"])
        for gone in ("status", "fields", "records"):
            self.assertNotIn(gone, new)
        (part,) = new["parts"]
        self.assertEqual(list(part), validate.PART_REQUIRED)
        self.assertEqual((part["id"], part["title"], part["status"]), ("births", "Births", "done"))
        self.assertEqual(part["fields"], OLD["fields"])
        ids = [r["id"] for r in part["records"]]
        self.assertEqual(len(set(ids)), 2)
        for record_id in ids:
            self.assertRegex(record_id, r"^[a-z0-9]{12}$")
        self.assertEqual(list(part["records"][0]), ["id", "type", "year", "no", "scans", "fields", "x-box"])
        self.assertEqual([{k: v for k, v in r.items() if k != "id"} for r in part["records"]], OLD["records"])

    def test_the_part_is_named_after_what_it_holds(self):
        uk = [{"key": "entry", "label": {"uk": "Запис", "en": "Entry"}}]
        en = OLD["fields"]
        of = lambda *types: [{"type": t} for t in types]  # noqa: E731
        self.assertEqual(migrate.part_name(of("death", "other", "death"), en), ("deaths", "Deaths"))
        self.assertEqual(migrate.part_name(of("marriage"), uk), ("marriages", "Шлюби"))
        self.assertEqual(migrate.part_name(of("birth", "death"), uk), ("records", "Записи"))
        self.assertEqual(migrate.part_name(of("other"), en), ("records", "Records"))
        new = migrate.migrate(copy.deepcopy(OLD), AUTHOR, "CC0-1.0", part_id="book-1", part_title="Book one")
        self.assertEqual((new["parts"][0]["id"], new["parts"][0]["title"]), ("book-1", "Book one"))

    def test_a_file_with_no_archive_gets_none(self):
        old = copy.deepcopy(OLD)
        for key in ("archive", "fonds", "inventory", "file"):
            del old[key]
        new = migrate.migrate(old, AUTHOR, "CC0-1.0")
        self.assertNotIn("archive", new)
        self.assertEqual(validate.validate_book(new), [])

    def test_new_record_ids_avoid_the_taken_ones(self):
        taken = {migrate.new_record_id() for _ in range(200)}
        self.assertEqual(len(taken), 200)
        self.assertNotIn(migrate.new_record_id(taken), taken)

    def test_empty_values_are_left_out_and_familysearch_is_named(self):
        old = copy.deepcopy(OLD)
        old["records"][0]["no"] = ""
        old["records"][0]["scans"] = ["007805907_00638"]
        old["records"][1]["fields"]["notes"] = ""
        old["fields"].append({"key": "notes", "label": {"en": "Notes"}})
        new = migrate.migrate(old, AUTHOR, "CC-BY-4.0", True)
        self.assertEqual(validate.validate_book(new), [])
        self.assertEqual(list(new)[:2], ["spec", "id"])
        self.assertNotIn("no", new["parts"][0]["records"][0])
        self.assertNotIn("notes", new["parts"][0]["records"][1]["fields"])
        self.assertEqual(new["scanSource"]["name"], "FamilySearch")

    def test_a_flat_file_with_spec_is_upgraded_without_asking_again(self):
        old = copy.deepcopy(OLD)
        old.update(spec="1.0", authors=[AUTHOR], license="CC0-1.0")
        new = migrate.migrate(old)
        self.assertEqual(validate.validate_book(new), [])
        self.assertEqual((new["authors"], new["license"]), ([AUTHOR], "CC0-1.0"))
        self.assertEqual(len(new["parts"][0]["records"]), 2)

    def test_cli_asks_for_author_and_licence_only_when_missing(self):
        import contextlib
        import io
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            bare, signed = Path(folder) / "bare.json", Path(folder) / "signed.json"
            bare.write_text(json.dumps(OLD, ensure_ascii=False), encoding="utf-8")
            signed.write_text(json.dumps({**OLD, "spec": "1.0", "authors": [AUTHOR], "license": "CC0-1.0"},
                                         ensure_ascii=False), encoding="utf-8")
            before = bare.read_text(encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(migrate.main([str(bare)]), 1)
                self.assertEqual(migrate.main([str(signed)]), 0)
                upgraded = signed.read_text(encoding="utf-8")
                self.assertEqual(migrate.main([str(signed)]), 0)
            self.assertIn("needs --author, --email and --license", out.getvalue())
            self.assertIn("skipped (already has parts", out.getvalue())
            self.assertEqual(bare.read_text(encoding="utf-8"), before)
            self.assertIn("parts", json.loads(upgraded))
            self.assertEqual(signed.read_text(encoding="utf-8"), upgraded)

    def test_cli_upgrades_once_and_leaves_an_upgraded_file_alone(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "t.json"
            path.write_text(json.dumps(OLD, ensure_ascii=False), encoding="utf-8")
            run = ["--author", "A", "--email", "a@example.org", "--license", "CC0-1.0", str(path)]
            self.assertEqual(migrate.main(run), 0)
            first = path.read_text(encoding="utf-8")
            self.assertEqual(validate.validate_file(path), ([], 2))
            self.assertEqual(migrate.main(run), 0)
            self.assertEqual(path.read_text(encoding="utf-8"), first)


try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:  # the schemas are checked in CI, where jsonschema is installed
    jsonschema = None


@unittest.skipUnless(jsonschema, "jsonschema is not installed")
class Schemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        book = load(ROOT / "schemas" / "v1" / "book.schema.json")
        record = load(ROOT / "schemas" / "v1" / "record.schema.json")
        for schema in (book, record):
            jsonschema.Draft7Validator.check_schema(schema)
        registry = Registry().with_resources(
            [(s["$id"], Resource.from_contents(s)) for s in (book, record)])
        cls.validator = jsonschema.Draft7Validator(book, registry=registry)

    def test_valid_examples_pass(self):
        for path in VALID:
            with self.subTest(path.name):
                self.assertEqual([e.message for e in self.validator.iter_errors(load(path))], [])

    def test_invalid_examples(self):
        for name, (_, in_schema) in INVALID.items():
            with self.subTest(name):
                book = load(ROOT / "examples" / "invalid" / f"{name}.json")
                self.assertEqual(self.validator.is_valid(book), not in_schema)


if __name__ == "__main__":
    unittest.main()
