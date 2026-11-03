import json
import csv
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import duckdb
from load import ROOT, read_records, load


class LoadTests(unittest.TestCase):
    def test_cached_inputs_still_validate_the_codebook(self):
        with TemporaryDirectory(dir=ROOT) as tmp, duckdb.connect() as con:
            folder = Path(tmp)
            seeds = folder / "dbt/seeds"
            seeds.mkdir(parents=True)
            (seeds / "variables.csv").write_text("variable\nnews\n")
            book = seeds / "codebook.csv"
            header = "variable,source_code,label\n"
            book.write_text(header + "news,1,Every day\n")
            raw = folder / "cut.json"
            raw.write_text(json.dumps({"data":{"year":["2014"],"id_":[1],"news":["Every day"]},
                "codes":{"news":{"variable_name":"news","CodeLabel":{"1":"Every day"}}}}))
            with patch("load.ROOT", folder):
                load(con, [raw])
                book.write_text(header + "news,1,Never\n")
                with self.assertRaisesRegex(ValueError, "codebook drift"):
                    load(con, [raw])
                self.assertEqual(con.execute("select count(*) from raw.records").fetchone(), (1,))

    def test_reviewed_manifest_rejects_truncation_and_accepts_a_reviewed_revision(self):
        with TemporaryDirectory(dir=ROOT) as tmp:
            folder = Path(tmp)
            raw = folder / "cut.json"
            manifest = folder / "extracts.csv"
            def write_answer(answer):
                raw.write_text(json.dumps({"data":{"year":["2014"],"id_":[1],"postlife":[answer]},"codes":{}}))
            def review():
                with manifest.open("w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["filename","sha256","row_count","years"])
                    writer.writerow([raw.name, hashlib.sha256(raw.read_bytes()).hexdigest(),1,"2014"])
            write_answer("YES")
            review()
            with duckdb.connect() as con:
                load(con,[raw],manifest)
            write_answer("NO")
            with duckdb.connect() as con:
                with self.assertRaisesRegex(ValueError,"SHA-256"):
                    load(con,[raw],manifest)
            review()
            with duckdb.connect() as con:
                load(con,[raw],manifest)
                self.assertEqual(con.execute("select payload->>'postlife' from raw.records").fetchone(),("NO",))

    def test_reject_bad_input(self):
        for content in ['{', '{"data":{"year":[],"year":[]}}',
                        '{"data":{"year":["2014"],"id_":[]},"codes":{}}',
                        '{"data":{"year":["2014"],"id_":[true]},"codes":{}}']:
            with self.subTest(content=content), self.assertRaises(ValueError):
                read_records(content.encode())

    def test_conflict_rolls_back_file(self):
        with TemporaryDirectory(dir=ROOT) as folder, duckdb.connect() as con:
            a, b = [Path(folder) / name for name in ("a.json","b.json")]
            def write(path, value):
                path.write_text(json.dumps({"data":{"year":["2014"], "id_":[1],
                                                     "news":[value]}, "codes":{}}))
            write(a, "Never")
            write(b, "Every day")
            load(con, [a])
            with self.assertRaisesRegex(ValueError, "conflicting overlap"):
                load(con, [a, b])
            self.assertEqual(con.execute("select count(*) from raw.files").fetchone(), (1,))
            self.assertEqual(con.execute("select count(*) from raw.records").fetchone(), (1,))
            write(b, "Never")
            with self.assertRaisesRegex(ValueError, "identical content"):
                load(con, [a, b])
            with self.assertRaisesRegex(ValueError, "missing or renamed"):
                load(con, [b])
            load(con, [a])
            self.assertEqual(con.execute("select count(*) from raw.records").fetchone(), (1,))

    def test_real_cuts_in_either_order_and_twice(self):
        paths = sorted((ROOT / "source/data/raw").glob("yaqeen_cut_*.json"))
        signatures = []
        for order in (paths, paths[::-1]):
            with duckdb.connect() as con:
                load(con, order)
                load(con, order)
                rows = con.execute("select filename, ordinal, payload from raw.records order by 1,2").fetchall()
                interviews = {(r["year"], r["id_"]) for _, _, p in rows for r in [json.loads(p)]}
                self.assertEqual((len(rows),len(interviews)), (10620,7753))
                signatures.append(rows)
        self.assertEqual(*signatures)


if __name__ == "__main__":
    unittest.main()
