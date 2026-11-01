import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import duckdb
from load import ROOT, read_records, load


class LoadTests(unittest.TestCase):
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
                load(con, [b])
            self.assertEqual(con.execute("select count(*) from raw.files").fetchone(), (1,))
            self.assertEqual(con.execute("select count(*) from raw.records").fetchone(), (1,))
            write(b, "Never")
            load(con, [b])
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
