from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from era_survival.cohorts import CohortBundle, load_cohort
from era_survival.lookup_builder import THRESHOLDS, build_site_shards
from era_survival.schema import DEFAULT_SOURCE_PATHS, PUBLIC_DATA_DIR, SITE_SLUGS, TNMRecord
from era_survival.validation import (
    FIXED_TIME_POLICY,
    MX_POLICY,
    STAGE_SOURCE_POLICY,
    validate_artifact_set,
)

AGE_GROUPS = ["<40", "40-49", "50-59", "60-69", "70-79", "80+"]
T_STAGES = ["T0", "T1", "T2", "T3", "T4", "Unknown"]
N_STAGES = ["N0", "N1", "N2", "N3", "Unknown"]
M_STAGES = ["M0", "M1", "Unknown"]


def build_metadata(bundle: CohortBundle) -> dict:
    site_record_counts = Counter(record.site for record in bundle.records)
    exclusion_counts = {
        field: count
        for field, count in bundle.flow_counts.items()
        if field.endswith("_excluded")
    }
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "version": 1,
        "generated_at": generated_at,
        "source_counts": dict(sorted(bundle.source_counts.items())),
        "flow_counts": dict(bundle.flow_counts),
        "exclusion_counts": exclusion_counts,
        "eligible_record_count": len(bundle.records),
        "site_record_counts": {
            site: site_record_counts.get(site, 0)
            for site in SITE_SLUGS
        },
        "stage_source_policy": dict(STAGE_SOURCE_POLICY),
        "mx_policy": MX_POLICY,
        "fixed_time_policy": FIXED_TIME_POLICY,
        "thresholds": dict(THRESHOLDS),
    }


def build_options(records: Sequence[TNMRecord]) -> dict:
    return {
        "version": 1,
        "sites": list(SITE_SLUGS),
        "sexes": sorted({record.sex for record in records}),
        "histology_groups": sorted({record.histology_group for record in records}),
        "age_groups": list(AGE_GROUPS),
        "t_stages": list(T_STAGES),
        "n_stages": list(N_STAGES),
        "m_stages": list(M_STAGES),
    }


def write_artifacts_atomically(
    artifacts: Sequence[tuple[str, dict]],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, _payload in artifacts:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        entries.append({
            "target": target,
            "temporary": target.with_name(f"{target.name}.tmp"),
            "backup": target.with_name(f"{target.name}.bak"),
            "had_prior": False,
            "replaced": False,
        })

    existing_backups = [entry["backup"] for entry in entries if entry["backup"].exists()]
    if existing_backups:
        names = ", ".join(str(path) for path in existing_backups)
        raise RuntimeError(f"recovery required: pre-existing artifact backup(s): {names}")

    try:
        for entry in entries:
            entry["temporary"].unlink(missing_ok=True)
        for (_name, payload), entry in zip(artifacts, entries):
            with entry["temporary"].open("w", encoding="utf-8") as handle:
                json.dump(
                    payload,
                    handle,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                )
    except Exception:
        for entry in entries:
            entry["temporary"].unlink(missing_ok=True)
        raise

    try:
        for entry in entries:
            target = entry["target"]
            backup = entry["backup"]
            entry["had_prior"] = target.exists()
            if entry["had_prior"]:
                target.replace(backup)
            entry["temporary"].replace(target)
            entry["replaced"] = True
    except Exception as error:
        rollback_failures = []
        restored_entries = []
        for entry in reversed(entries):
            target = entry["target"]
            backup = entry["backup"]
            try:
                if entry["replaced"] and target.exists():
                    target.unlink()
                if backup.exists():
                    if target.exists():
                        target.unlink()
                    backup.replace(target)
                restored_entries.append(entry)
            except Exception as rollback_error:
                rollback_failures.append(f"{target.name}: {rollback_error}")

        for entry in entries:
            entry["temporary"].unlink(missing_ok=True)
        for entry in restored_entries:
            entry["backup"].unlink(missing_ok=True)
        if rollback_failures:
            details = "; ".join(rollback_failures)
            raise RuntimeError(
                f"artifact write failed ({error}); rollback failures: {details}"
            ) from error
        raise
    else:
        for entry in entries:
            entry["temporary"].unlink(missing_ok=True)
            entry["backup"].unlink(missing_ok=True)


def remove_stale_json_artifacts(output: Path, expected_names: set[str]) -> None:
    for path in output.rglob("*.json"):
        if path.relative_to(output).as_posix() not in expected_names:
            path.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build focused detailed-TNM artifacts")
    parser.add_argument("--input", action="append", dest="inputs")
    parser.add_argument("--output", type=Path, default=PUBLIC_DATA_DIR)
    args = parser.parse_args(argv)
    paths = tuple(Path(value) for value in args.inputs) if args.inputs else DEFAULT_SOURCE_PATHS
    paths = tuple(path.expanduser().resolve() for path in paths)
    if len(set(paths)) != len(paths):
        parser.error("duplicate input path after resolution")

    bundle = load_cohort(paths)
    shards, manifest = build_site_shards(bundle.records)
    metadata = build_metadata(bundle)
    options = build_options(bundle.records)
    validate_artifact_set(metadata, options, manifest, shards)

    artifacts = [
        ("metadata.json", metadata),
        ("options.json", options),
        ("site_manifest.json", manifest),
    ]
    artifacts.extend(
        (f"lookup/{manifest['sites'][site]}", shards[site])
        for site in SITE_SLUGS
    )
    write_artifacts_atomically(artifacts, args.output)
    expected_names = {name for name, _payload in artifacts}
    remove_stale_json_artifacts(args.output, expected_names)

    print(json.dumps({
        "output": str(args.output),
        "source_rows": bundle.flow_counts["source_rows"],
        "eligible_records": len(bundle.records),
        "site_shards": len(shards),
        "site_record_counts": metadata["site_record_counts"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
