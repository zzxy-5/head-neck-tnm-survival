from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from era_survival.cohorts import CohortBundle, load_cohort
from era_survival.lookup_builder import THRESHOLDS, build_site_shards
from era_survival.schema import DEFAULT_SOURCE_PATHS, PUBLIC_DATA_DIR, SITE_SLUGS, TNMRecord
from era_survival.site_mapping import (
    SITE_V2_ALL_SITES,
    SITE_V2_EXCLUDED_SITES,
    SITE_V2_MAPPING_POLICY,
    SITE_V2_SLUGS,
)
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


def build_metadata(
    bundle: CohortBundle,
    *,
    production_records: Sequence[TNMRecord] | None = None,
    site_slugs: dict[str, str] = SITE_SLUGS,
    cohort_version: str = "site_v1",
) -> dict:
    records = list(bundle.records if production_records is None else production_records)
    site_record_counts = Counter(record.site for record in records)
    exclusion_counts = {
        field: count
        for field, count in bundle.flow_counts.items()
        if field.endswith("_excluded")
    }
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metadata = {
        "version": 1,
        "generated_at": generated_at,
        "source_counts": dict(sorted(bundle.source_counts.items())),
        "flow_counts": dict(bundle.flow_counts),
        "exclusion_counts": exclusion_counts,
        "cohort_version": cohort_version,
        "source_eligible_record_count": len(bundle.records),
        "eligible_record_count": len(records),
        "site_record_counts": {
            site: site_record_counts.get(site, 0)
            for site in site_slugs
        },
        "stage_source_policy": dict(STAGE_SOURCE_POLICY),
        "mx_policy": MX_POLICY,
        "fixed_time_policy": FIXED_TIME_POLICY,
        "thresholds": dict(THRESHOLDS),
    }
    has_site_v2 = [
        (record.site_v2 is not None, record.main_analysis_included is not None)
        for record in bundle.records
    ]
    all_legacy = not has_site_v2 or all(not site and not flag for site, flag in has_site_v2)
    all_complete = all(site and flag for site, flag in has_site_v2)
    if not all_legacy and not all_complete:
        raise ValueError(
            "site-v2 metadata cannot be built from mixed or partially populated "
            "site_v2/main_analysis_included fields"
        )
    if all_complete:
        site_v2_record_counts = Counter(record.site_v2 for record in bundle.records)
        excluded_v2_counts = Counter(
            record.site_v2
            for record in bundle.records
            if record.main_analysis_included is False
        )
        metadata.update({
            "site_v2_record_counts": {
                site: site_v2_record_counts.get(site, 0)
                for site in SITE_V2_ALL_SITES
            },
            "main_analysis_record_count": sum(
                1 for record in bundle.records if record.main_analysis_included is True
            ),
            "site_v2_excluded_site_counts": {
                site: excluded_v2_counts.get(site, 0)
                for site in SITE_V2_EXCLUDED_SITES
            },
            "site_v2_mapping_policy": SITE_V2_MAPPING_POLICY,
        })
    return metadata


def build_options(
    records: Sequence[TNMRecord],
    *,
    site_slugs: dict[str, str] = SITE_SLUGS,
) -> dict:
    return {
        "version": 1,
        "sites": list(site_slugs),
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
    parser.add_argument(
        "--site-v2-main",
        action="store_true",
        help="build the frozen 10-site site-v2 main-analysis production cohort",
    )
    args = parser.parse_args(argv)
    paths = tuple(Path(value) for value in args.inputs) if args.inputs else DEFAULT_SOURCE_PATHS
    paths = tuple(path.expanduser().resolve() for path in paths)
    if len(set(paths)) != len(paths):
        parser.error("duplicate input path after resolution")

    bundle = load_cohort(paths)
    if args.site_v2_main:
        incomplete = [
            record
            for record in bundle.records
            if record.site_v2 is None or record.main_analysis_included is None
        ]
        if incomplete:
            raise ValueError("site-v2 main build requires complete site-v2 fields")
        records = [
            replace(record, site=str(record.site_v2))
            for record in bundle.records
            if record.main_analysis_included is True
        ]
        site_slugs = SITE_V2_SLUGS
        cohort_version = "site_v2_main"
    else:
        records = bundle.records
        site_slugs = SITE_SLUGS
        cohort_version = "site_v1"

    shards, manifest = build_site_shards(records, site_slugs=site_slugs)
    metadata = build_metadata(
        bundle,
        production_records=records,
        site_slugs=site_slugs,
        cohort_version=cohort_version,
    )
    if args.site_v2_main:
        metadata.update({
            "precomputed_combination_count": sum(
                len(shard["rows"]) for shard in shards.values()
            ),
            "returnable_combination_count": sum(
                row["sample_size"] >= THRESHOLDS["minimum_sample"]
                for shard in shards.values()
                for row in shard["rows"]
            ),
        })
    options = build_options(records, site_slugs=site_slugs)
    validate_artifact_set(
        metadata,
        options,
        manifest,
        shards,
        site_slugs=site_slugs,
        expected_eligible_record_count=len(records),
        cohort_version=cohort_version,
    )

    artifacts = [
        ("metadata.json", metadata),
        ("options.json", options),
        ("site_manifest.json", manifest),
    ]
    artifacts.extend(
        (f"lookup/{manifest['sites'][site]}", shards[site])
        for site in site_slugs
    )
    write_artifacts_atomically(artifacts, args.output)
    expected_names = {name for name, _payload in artifacts}
    remove_stale_json_artifacts(args.output, expected_names)

    print(json.dumps({
        "output": str(args.output),
        "source_rows": bundle.flow_counts["source_rows"],
        "source_eligible_records": len(bundle.records),
        "eligible_records": len(records),
        "cohort_version": cohort_version,
        "site_shards": len(shards),
        "site_record_counts": metadata["site_record_counts"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
