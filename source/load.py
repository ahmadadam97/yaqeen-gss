"""Validate and ingest the Explorer's column-oriented JSON, retaining file membership."""
import csv
import hashlib
import json
import logging
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"repeated JSON property {key}")
        result[key] = value
    return result


def read_records(content):
    doc = json.loads(content, object_pairs_hook=unique_keys)
    data = doc["data"]
    if not isinstance(data, dict) or not {"year", "id_"} <= data.keys():
        raise ValueError("expected column arrays including year and id_")
    with (ROOT / "dbt/seeds/variables.csv").open(encoding="utf8") as f:
        variables = {r["variable"]: r for r in csv.DictReader(f)}
    unknown = data.keys() - variables.keys() - {"year", "id_"}
    if unknown:
        raise ValueError(f"define new variable(s) before loading: {sorted(unknown)}")
    with (ROOT / "dbt/seeds/codebook.csv").open(encoding="utf8") as f:
        meanings = {(r["variable"], r["source_code"]): r["label"] for r in csv.DictReader(f)}
    for entry in doc["codes"].values():
        for code, label in entry["CodeLabel"].items():
            if meanings.get((entry["variable_name"], code)) != label:
                raise ValueError(f"codebook drift for {entry['variable_name']} code {code}")
    if not all(isinstance(values, list) for values in data.values()) or not data["year"]:
        raise ValueError("expected nonempty arrays")
    seen = set()
    rows = []
    for ordinal, values in enumerate(zip(*data.values(), strict=True), 1):
        record = dict(zip(data, values))
        year, respondent = record["year"], record["id_"]
        if not re.fullmatch(r"[0-9]{4}", str(year)) or type(respondent) is not int or respondent < 1:
            raise ValueError(f"invalid survey key at row {ordinal}")
        key = (int(year), respondent)
        if key in seen:
            raise ValueError(f"duplicate interview {key}")
        seen.add(key)
        if any(type(v) not in (str, int, float, type(None)) for v in values):
            raise ValueError(f"unexpected nested value at row {ordinal}")
        rows.append(json.dumps(record, allow_nan=False))
    return rows


def load(con, paths, manifest_path=None):
    if not paths:
        raise ValueError("no raw JSON files found")
    expected = None
    if manifest_path is not None:
        with Path(manifest_path).open(encoding="utf8", newline="") as f:
            entries = list(csv.DictReader(f))
        expected = {r["filename"]: r for r in entries}
        if len(expected) != len(entries) or set(expected) != {p.name for p in paths}:
            raise ValueError("raw files differ from reviewed extract manifest")
    con.execute("begin")
    try:
        con.execute("""create schema if not exists raw;
            create table if not exists raw.files(filename varchar primary key, sha256 varchar unique, row_count int);
            create table if not exists raw.records(filename varchar, ordinal int, payload json,
                primary key(filename, ordinal))""")
        known = dict(con.execute("select filename, sha256 from raw.files").fetchall())
        missing = known.keys() - {path.name for path in paths}
        if missing:
            raise ValueError(f"previously loaded files missing or renamed: {sorted(missing)}")
        for path in paths:
            content = path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            if expected and digest != expected[path.name]["sha256"]:
                raise ValueError(f"{path.name}: SHA-256 differs from reviewed extract manifest")
            previous = known.get(path.name)
            if previous and previous != digest:
                raise ValueError(f"{path.name} has changed; investigate the version")
            if previous != digest and digest in known.values():
                raise ValueError(f"{path.name}: identical content under another filename")
            try:
                rows = read_records(content)
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                raise ValueError(f"{path.name}: {exc}") from exc
            if expected:
                entry = expected[path.name]
                years = sorted({str(json.loads(r)["year"]) for r in rows})
                if len(rows) != int(entry["row_count"]) or "|".join(years) != entry["years"]:
                    raise ValueError(f"{path.name}: row count or years differ from extract manifest")
            if previous == digest:
                logging.info("validated unchanged %s rows=%d sha256=%s; skip insert", path.name, len(rows), digest)
                continue
            con.execute("insert into raw.files values (?,?,?)", [path.name, digest, len(rows)])
            con.execute("""insert into raw.records
                select ?, generate_subscripts(items, 1), unnest(items)
                from (select from_json(?, '["JSON"]') as items)""",
                        [path.name, "[" + ",".join(rows) + "]"])
            logging.info("staged %s rows=%d sha256=%s", path.name, len(rows), digest)
            known[path.name] = digest
        conflict = con.execute("""select payload->>'year' as yr, payload->>'id_' as id, field.key
            from raw.records, lateral json_each(payload) field
            group by all having count(distinct field.value) > 1 limit 1""").fetchone()
        if conflict:
            raise ValueError(f"conflicting overlap at year, ID, variable {conflict}")
        con.execute("commit")
    except Exception:
        con.execute("rollback")
        raise
