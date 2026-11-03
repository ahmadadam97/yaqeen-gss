from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import duckdb
from load import ROOT
from benchmark import break_even_reads, materialization_cost


class BenchmarkTests(unittest.TestCase):
    def test_break_even_accounts_for_build_and_non_improvement(self):
        self.assertEqual(break_even_reads(100,60,20),3)
        self.assertIsNone(break_even_reads(100,20,20))
        self.assertIsNone(break_even_reads(100,10,20))

    def test_build_cost_uses_an_isolated_database(self):
        with TemporaryDirectory(dir=ROOT) as tmp:
            folder = Path(tmp)
            database = folder / "source.duckdb"
            with duckdb.connect(str(database)) as con:
                con.execute("create table example as select range as n from range(1000)")
            before = database.read_bytes()
            cost = materialization_cost(database, "select * from gss.example", folder)
            self.assertEqual(cost["rows"],1000)
            self.assertGreater(cost["build_ms"],0)
            self.assertGreater(cost["incremental_storage_bytes"],0)
            self.assertEqual(database.read_bytes(),before)
