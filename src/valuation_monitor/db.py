"""DuckDB connection and SQL-folder runner shared by every pipeline stage."""

from pathlib import Path
from string import Template

import duckdb

from valuation_monitor.config import PROJECT_ROOT, load_config

SQL_ROOT = PROJECT_ROOT / "sql"


def connect(config: dict | None = None, read_only: bool = False) -> duckdb.DuckDBPyConnection:
    """Open the project database and make sure the study_area table matches the config."""
    config = config or load_config()
    database = PROJECT_ROOT / config["paths"]["database"]
    database.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(database), read_only=read_only)
    if not read_only:
        create_study_area(con, config)
    return con


def create_study_area(con: duckdb.DuckDBPyConnection, config: dict) -> None:
    """Write the study-area local authorities from the config into a table."""
    rows = [
        (la["code"], la["name"], la["market"]) for la in config["study_area"]["local_authorities"]
    ]
    con.execute(
        "CREATE OR REPLACE TABLE study_area (lad_code VARCHAR, lad_name VARCHAR, market VARCHAR)"
    )
    con.executemany("INSERT INTO study_area VALUES (?, ?, ?)", rows)


def sql_params(config: dict) -> dict[str, str]:
    """Values substituted for ${name} placeholders in SQL files (forward-slash paths)."""
    params = {key: (PROJECT_ROOT / value).as_posix() for key, value in config["paths"].items()}
    params["start_date"] = str(config["study_area"]["start_date"])
    features = config["features"]
    params["info_lag_months"] = str(int(features["info_lag_months"]))
    params["history_window_months"] = str(int(features["history_window_months"]))
    params["min_comparables"] = str(int(features["min_comparables"]))
    params["floor_area_min"], params["floor_area_max"] = (
        str(float(x)) for x in features["floor_area_range"]
    )
    params.update({key: str(value) for key, value in config["validation"]["periods"].items()})
    return params


def run_sql_folder(
    con: duckdb.DuckDBPyConnection, folder: str, params: dict[str, str], verbose: bool = True
) -> list[Path]:
    """Run every NN_*.sql file in sql/<folder>/ in numerical order."""
    files = sorted((SQL_ROOT / folder).glob("[0-9][0-9]_*.sql"))
    for path in files:
        sql = Template(path.read_text(encoding="utf-8")).substitute(params)
        con.execute(sql)
        if verbose:
            print(f"  ran   {folder}/{path.name}")
    return files
