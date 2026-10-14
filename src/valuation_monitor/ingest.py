"""Load raw downloads into DuckDB staging tables (Week 1).

Planned responsibilities:
- Price Paid Data: load the files and keep the release month and record status
  (A = added, C = changed, D = deleted), so the monitor can replay data as it was known
  at the time.
- EPC: filter the national bulk file to the study area (implemented below), then stage it.
- UK House Price Index: load the regional index used by the baseline.

The staging SQL lives in sql/01_staging/; this module only runs it in order.

Usage:
    python -m valuation_monitor.ingest epc     # filter EPC certificates to the study area
    python -m valuation_monitor.ingest stage   # build the staging tables (default)
"""

import sys
import time
import zipfile
from pathlib import Path

import duckdb

from valuation_monitor.config import PROJECT_ROOT, load_config
from valuation_monitor.db import connect, run_sql_folder, sql_params
from valuation_monitor.download import sha256, write_manifest


def _paths(config: dict) -> dict[str, Path]:
    return {key: PROJECT_ROOT / value for key, value in config["paths"].items()}


def postcode_lookup_csv(config: dict) -> Path:
    """Return the path of the extracted ONS postcode lookup CSV."""
    stem = Path(config["sources"]["postcode_lookup"]["filename"]).stem
    folder = _paths(config)["raw_geography"] / stem
    return max(folder.glob("*.csv"), key=lambda p: p.stat().st_size)


def extract_epc_study_area(config: dict) -> Path:
    """Filter the national EPC bulk file to study-area postcodes, one year at a time.

    The national file is about 8 GB zipped and nearly 100 GB unzipped, so it is never
    unpacked in full. Each certificates-YYYY.csv is extracted to a temporary file, filtered
    with DuckDB by joining on the study-area postcodes from the ONS lookup, written to
    Parquet, and deleted. Reading each member to the end also verifies its CRC checksum.
    Recommendation files are not needed and are skipped. Columns stay as text here; types
    are applied in sql/01_staging/.
    """
    paths = _paths(config)
    archive = paths["raw_epc"] / config["sources"]["epc"]["filename"]
    out_dir = paths["interim"] / "epc_study_area"
    tmp_dir = paths["interim"] / "_tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    codes = [la["code"] for la in config["study_area"]["local_authorities"]]

    con = duckdb.connect()
    con.execute(
        """
        CREATE TABLE study_postcodes AS
        SELECT DISTINCT upper(replace(pcds, ' ', '')) AS postcode_key, ladcd AS lad_code
        FROM read_csv(?, header = true, all_varchar = true)
        WHERE ladcd IN (SELECT unnest(?::VARCHAR[]))
        """,
        [str(postcode_lookup_csv(config)), codes],
    )
    n_postcodes = con.execute("SELECT count(*) FROM study_postcodes").fetchone()[0]
    print(f"Study-area postcodes: {n_postcodes:,}")

    with zipfile.ZipFile(archive) as zf:
        members = sorted(m for m in zf.namelist() if m.startswith("certificates-"))
        for member in members:
            target = out_dir / member.replace(".csv", ".parquet")
            if target.exists():
                print(f"  skip  {target.name}")
                continue
            started = time.perf_counter()
            tmp_csv = Path(zf.extract(member, tmp_dir))
            try:
                partial = target.with_suffix(".parquet.part")
                con.execute(
                    f"""
                    COPY (
                        SELECT e.*, p.lad_code AS study_lad_code
                        FROM read_csv('{tmp_csv.as_posix()}', header = true, all_varchar = true,
                                      quote = '"', escape = '"', strict_mode = false) AS e
                        JOIN study_postcodes AS p
                          ON upper(replace(e.postcode, ' ', '')) = p.postcode_key
                    ) TO '{partial.as_posix()}' (FORMAT parquet, COMPRESSION zstd)
                    """
                )
                partial.replace(target)
            finally:
                tmp_csv.unlink(missing_ok=True)
            rows = con.execute(f"SELECT count(*) FROM '{target.as_posix()}'").fetchone()[0]
            seconds = time.perf_counter() - started
            print(f"  done  {target.name}: {rows:,} certificates ({seconds:.0f}s)")
    tmp_dir.rmdir()

    total = con.execute(f"SELECT count(*) FROM '{(out_dir / '*.parquet').as_posix()}'").fetchone()
    print(f"Total study-area certificates: {total[0]:,}")
    return out_dir


def record_epc_download(config: dict) -> None:
    """Add the manually downloaded EPC archive to docs/data_downloads.md."""
    archive = _paths(config)["raw_epc"] / config["sources"]["epc"]["filename"]
    stamp = time.strftime("%Y-%m-%d %H:%M", time.gmtime(archive.stat().st_mtime))
    write_manifest(
        [
            {
                "file": archive.relative_to(PROJECT_ROOT).as_posix(),
                "group": "epc",
                "bytes": archive.stat().st_size,
                "sha256": sha256(archive),
                "downloaded": stamp,
                "source": config["sources"]["epc"]["url"],
            }
        ]
    )


def run_staging(config: dict) -> None:
    """Build the typed staging tables in the project database (sql/01_staging/)."""
    params = sql_params(config)
    params["postcode_lookup_csv"] = postcode_lookup_csv(config).as_posix()
    with connect(config) as con:
        run_sql_folder(con, "01_staging", params)
        for table in [
            "stg_postcode_lookup",
            "stg_price_paid",
            "stg_price_paid_changes",
            "stg_epc",
            "stg_hpi",
        ]:
            rows = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {rows:,} rows")


def main(tasks: list[str]) -> None:
    config = load_config()
    for task in tasks or ["stage"]:
        if task == "epc":
            record_epc_download(config)
            extract_epc_study_area(config)
        elif task == "stage":
            run_staging(config)
        else:
            raise SystemExit(f"Unknown task: {task}")


if __name__ == "__main__":
    main(sys.argv[1:])
