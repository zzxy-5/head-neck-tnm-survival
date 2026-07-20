from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.cohorts import CohortBundle
from era_survival.schema import SITE_SLUGS, TNMRecord
from scripts.build_artifacts import main, remove_stale_json_artifacts, write_artifacts_atomically
from tests.python.test_validation import expected_site_counts, valid_artifact_set


def record_for(site: str) -> TNMRecord:
    return TNMRecord(
        2016, "Female", site, "SCC", "40-49", "<60", 60, False,
        "T1", "N0", "M0", "SEER Combined TNM",
    )


def exact_bundle() -> CohortBundle:
    counts = expected_site_counts()
    records = [
        record
        for site, count in counts.items()
        for record in [record_for(site)] * count
    ]
    source_counts = {
        "export_C00-C09.csv": 500_000,
        "export_C10-C14.csv": 100_000,
        "export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv": 800_000,
        "export_C73-C75.csv": 408_471,
    }
    flow_counts = {
        "source_rows": 1_808_471,
        "non_target_site_excluded": 1_000_000,
        "outside_tnm_years_excluded": 597_311,
        "tnm_cohort": 211_160,
    }
    return CohortBundle(records, flow_counts, source_counts)


class BuildArtifactsIntegrationTests(unittest.TestCase):
    def test_main_writes_only_three_core_files_and_thirteen_lookup_shards(self):
        metadata, _options, manifest, shards = valid_artifact_set()
        bundle = exact_bundle()

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "data"
            lookup = output / "lookup"
            lookup.mkdir(parents=True)
            (output / ".gitkeep").touch()
            (output / "._ignored-sidecar").touch()
            for stale in (
                "summary_lookup.json",
                "tnm_lookup.json",
                "descriptive_2018_2023.json",
            ):
                (output / stale).write_text("stale", encoding="utf-8")
            (lookup / "stale-site.json").write_text("stale", encoding="utf-8")

            stdout = io.StringIO()
            with mock.patch("scripts.build_artifacts.load_cohort", return_value=bundle), mock.patch(
                "scripts.build_artifacts.build_site_shards", return_value=(shards, manifest)
            ), redirect_stdout(stdout):
                result = main(["--input", "one.csv", "--output", str(output)])

            self.assertEqual(result, 0)
            expected = {
                "metadata.json",
                "options.json",
                "site_manifest.json",
                *{f"lookup/{slug}.json" for slug in SITE_SLUGS.values()},
            }
            actual = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*.json")
            }
            self.assertEqual(actual, expected)
            built_metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(built_metadata["source_counts"], metadata["source_counts"])
            self.assertEqual(built_metadata["eligible_record_count"], 211_160)
            self.assertEqual(built_metadata["site_record_counts"], expected_site_counts())
            self.assertEqual(json.loads(stdout.getvalue())["site_shards"], 13)
            self.assertFalse(any(path.name.endswith((".tmp", ".bak")) for path in output.rglob("*")))

    def test_validation_failure_preserves_every_stale_public_artifact(self):
        metadata, _options, manifest, shards = valid_artifact_set()
        bundle = exact_bundle()

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            stale = {
                output / "summary_lookup.json": "summary",
                output / "tnm_lookup.json": "tnm",
                output / "descriptive_2018_2023.json": "eod",
            }
            for path, contents in stale.items():
                path.write_text(contents, encoding="utf-8")

            with mock.patch("scripts.build_artifacts.load_cohort", return_value=bundle), mock.patch(
                "scripts.build_artifacts.build_site_shards", return_value=(shards, manifest)
            ), mock.patch(
                "scripts.build_artifacts.validate_artifact_set",
                side_effect=ValueError("focused artifact set invalid"),
            ):
                with self.assertRaisesRegex(ValueError, "focused artifact set invalid"):
                    main(["--input", "one.csv", "--output", str(output)])

            self.assertEqual({path: path.read_text(encoding="utf-8") for path in stale}, stale)
            self.assertFalse((output / "metadata.json").exists())

    def test_duplicate_resolved_input_paths_are_rejected_before_loading(self):
        stderr = io.StringIO()
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "fixture.csv"
            duplicate = fixture.parent / "." / fixture.name
            with mock.patch("scripts.build_artifacts.load_cohort") as load_cohort:
                with self.assertRaises(SystemExit) as raised, redirect_stderr(stderr):
                    main(["--input", str(fixture), "--input", str(duplicate)])

        self.assertEqual(raised.exception.code, 2)
        self.assertIn("duplicate input path", stderr.getvalue())
        load_cohort.assert_not_called()


class AtomicArtifactWriteTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = (
            ("metadata.json", {"name": "new-metadata"}),
            ("options.json", {"name": "new-options"}),
            ("site_manifest.json", {"name": "new-manifest"}),
            ("lookup/larynx.json", {"name": "new-larynx"}),
        )

    def assert_no_transaction_files(self, output: Path) -> None:
        self.assertFalse(any(path.name.endswith((".tmp", ".bak")) for path in output.rglob("*")))

    def test_nested_artifacts_are_written_to_temporary_siblings(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_artifacts_atomically(self.artifacts, output)

            self.assertEqual(
                json.loads((output / "lookup/larynx.json").read_text(encoding="utf-8")),
                {"name": "new-larynx"},
            )
            self.assert_no_transaction_files(output)

    def test_preparation_failure_leaves_all_targets_unchanged_and_cleans_temps(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "lookup").mkdir()
            old_contents = {}
            for name, _payload in self.artifacts:
                old_contents[name] = f"old-{name}"
                (output / name).write_text(old_contents[name], encoding="utf-8")
            original_dump = json.dump
            calls = 0

            def fail_second_dump(payload, handle, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise TypeError("serialization failed")
                return original_dump(payload, handle, **kwargs)

            with mock.patch("scripts.build_artifacts.json.dump", side_effect=fail_second_dump):
                with self.assertRaisesRegex(TypeError, "serialization failed"):
                    write_artifacts_atomically(self.artifacts, output)

            self.assertEqual(
                {name: (output / name).read_text(encoding="utf-8") for name in old_contents},
                old_contents,
            )
            self.assert_no_transaction_files(output)

    def test_replacement_failure_rolls_back_old_targets_and_removes_new_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "lookup").mkdir()
            (output / "options.json").write_text("old-options", encoding="utf-8")
            original_replace = Path.replace
            failed = False

            def fail_second_target(source: Path, target: Path):
                nonlocal failed
                if source.name == "options.json.tmp" and not failed:
                    failed = True
                    raise OSError("replacement failed")
                return original_replace(source, target)

            with mock.patch.object(Path, "replace", autospec=True, side_effect=fail_second_target):
                with self.assertRaisesRegex(OSError, "replacement failed"):
                    write_artifacts_atomically(self.artifacts, output)

            self.assertFalse((output / "metadata.json").exists())
            self.assertEqual((output / "options.json").read_text(encoding="utf-8"), "old-options")
            self.assertFalse((output / "site_manifest.json").exists())
            self.assertFalse((output / "lookup/larynx.json").exists())
            self.assert_no_transaction_files(output)

    def test_stale_cleanup_tolerates_a_path_that_disappears_during_iteration(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / "stale.json").write_text("stale", encoding="utf-8")

            def disappear(_path: Path, *, missing_ok: bool = False):
                if not missing_ok:
                    raise FileNotFoundError("sidecar already removed")

            with mock.patch.object(Path, "unlink", autospec=True, side_effect=disappear) as unlink:
                remove_stale_json_artifacts(output, set())

            unlink.assert_called_once_with(output / "stale.json", missing_ok=True)


if __name__ == "__main__":
    unittest.main()
