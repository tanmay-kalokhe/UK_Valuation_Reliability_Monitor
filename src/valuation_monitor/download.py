"""Download the public source data into data/raw/ (reproducible, re-runnable).

Usage:
    python -m valuation_monitor.download                 # everything
    python -m valuation_monitor.download price_paid      # one or more groups
Groups: price_paid, house_price_index, postcode_lookup, boundaries

Files that already exist with the expected size are skipped. Each run rewrites
docs/data_downloads.md with file names, sizes, SHA-256 hashes, sources and dates.
EPC data is downloaded manually (GOV.UK One Login is required); see data/README.md.
"""

import hashlib
import json
import sys
import urllib.parse
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from valuation_monitor.config import PROJECT_ROOT, load_config

USER_AGENT = "UK-Valuation-Reliability-Monitor/0.1 (portfolio research project)"
CHUNK = 1024 * 1024


def _request(url: str) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def remote_size(url: str) -> int | None:
    """Return the Content-Length of a URL, following redirects, or None if unknown."""
    head = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(head, timeout=60) as response:
        length = response.headers.get("Content-Length")
    return int(length) if length else None


def download_file(url: str, target: Path) -> Path:
    """Stream a URL to disk, skipping the download when an identical-size file exists."""
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = remote_size(url)
    if target.exists() and expected is not None and target.stat().st_size == expected:
        print(f"  skip  {target.name} (already downloaded)")
        return target
    partial = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(_request(url), timeout=120) as response, open(partial, "wb") as out:
        done = 0
        while chunk := response.read(CHUNK):
            out.write(chunk)
            done += len(chunk)
            if expected:
                print(f"\r  get   {target.name} {done / expected:6.1%}", end="", flush=True)
    print()
    if expected is not None and partial.stat().st_size != expected:
        raise OSError(f"Incomplete download for {target.name}: {partial.stat().st_size} bytes")
    partial.replace(target)
    return target


def safe_extract(archive: Path, destination: Path) -> list[Path]:
    """Extract a zip file, refusing any member that would land outside the destination."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    extracted = []
    with zipfile.ZipFile(archive) as zf:
        for member in zf.infolist():
            path = (destination / member.filename).resolve()
            if not path.is_relative_to(root):
                raise ValueError(f"Unsafe path in archive: {member.filename}")
            if member.is_dir():
                continue
            if not path.exists() or path.stat().st_size != member.file_size:
                zf.extract(member, destination)
            extracted.append(path)
    return extracted


def download_feature_layer(layer_url: str, target: Path, page_size: int = 2000) -> Path:
    """Download every feature of an ArcGIS feature layer as one GeoJSON file (WGS84)."""
    if target.exists():
        print(f"  skip  {target.name} (already downloaded)")
        return target
    features, offset = [], 0
    while True:
        query = urllib.parse.urlencode(
            {
                "where": "1=1",
                "outFields": "*",
                "outSR": 4326,
                "f": "geojson",
                "resultOffset": offset,
                "resultRecordCount": page_size,
            }
        )
        with urllib.request.urlopen(_request(f"{layer_url}/query?{query}"), timeout=120) as resp:
            page = json.load(resp)
        batch = page.get("features", [])
        features.extend(batch)
        print(f"\r  get   {target.name} {len(features)} features", end="", flush=True)
        if len(batch) < page_size:
            break
        offset += page_size
    print()
    target.parent.mkdir(parents=True, exist_ok=True)
    collection = {"type": "FeatureCollection", "features": features}
    target.write_text(json.dumps(collection), encoding="utf-8")
    return target


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(CHUNK):
            digest.update(chunk)
    return digest.hexdigest()


def plan(config: dict) -> dict[str, list[tuple[str, str, Path]]]:
    """Return, per group, a list of (kind, url, target path) jobs."""
    src = config["sources"]
    paths = {key: PROJECT_ROOT / value for key, value in config["paths"].items()}
    pp = src["price_paid"]
    jobs = {
        "price_paid": [
            ("file", f"{pp['base_url']}/pp-{year}.csv", paths["raw_price_paid"] / f"pp-{year}.csv")
            for year in pp["years"]
        ]
        + [
            (
                "file",
                f"{pp['base_url']}/{pp['monthly_update_file']}",
                paths["raw_price_paid"] / pp["monthly_update_file"],
            )
        ],
        "house_price_index": [
            (
                "file",
                src["house_price_index"]["url"],
                paths["raw_house_price_index"] / src["house_price_index"]["filename"],
            )
        ],
        "postcode_lookup": [
            (
                "zip",
                src["postcode_lookup"]["url"],
                paths["raw_geography"] / src["postcode_lookup"]["filename"],
            )
        ],
        "boundaries": [
            ("layer", layer["url"], paths["raw_geography"] / "boundaries" / layer["filename"])
            for layer in src["boundaries"].values()
        ],
    }
    return jobs


def write_manifest(records: list[dict]) -> Path:
    """Write a committed record of what was downloaded (no data, only metadata)."""
    manifest = PROJECT_ROOT / "docs" / "data_downloads.md"
    previous = {}
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) == 6 and cells[0].startswith("`"):
                previous[cells[0]] = cells
    for record in records:
        key = f"`{record['file']}`"
        previous[key] = [
            key,
            record["group"],
            f"{record['bytes']:,}",
            f"`{record['sha256'][:16]}…`",
            record["downloaded"],
            record["source"],
        ]
    lines = [
        "# Data downloads",
        "",
        "Generated by `python -m valuation_monitor.download`. The files themselves are",
        "git-ignored; this record lets anyone re-download and verify the same snapshot.",
        "",
        "| File | Group | Bytes | SHA-256 (first 16) | Downloaded (UTC) | Source |",
        "|---|---|---|---|---|---|",
    ]
    lines += ["| " + " | ".join(cells) + " |" for _, cells in sorted(previous.items())]
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return manifest


def main(groups: list[str]) -> None:
    config = load_config()
    jobs = plan(config)
    unknown = set(groups) - set(jobs)
    if unknown:
        raise SystemExit(f"Unknown group(s): {', '.join(sorted(unknown))}")
    records = []
    for group in groups or list(jobs):
        print(f"[{group}]")
        for kind, url, target in jobs[group]:
            if kind == "layer":
                path = download_feature_layer(url, target)
            else:
                path = download_file(url, target)
                if kind == "zip":
                    safe_extract(path, path.parent / path.stem)
            records.append(
                {
                    "file": path.relative_to(PROJECT_ROOT).as_posix(),
                    "group": group,
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "downloaded": datetime.fromtimestamp(path.stat().st_mtime, UTC).strftime(
                        "%Y-%m-%d %H:%M"
                    ),
                    "source": url.split("?")[0],
                }
            )
    print(f"Manifest: {write_manifest(records).relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
