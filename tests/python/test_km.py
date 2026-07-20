import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.km import kaplan_meier, reverse_km_median_followup
from era_survival.lookup_builder import _survival_fields


class KaplanMeierTests(unittest.TestCase):
    def test_tied_events_are_applied_before_censoring(self):
        result = kaplan_meier([(6, True), (6, False), (12, True), (18, False)])

        self.assertEqual(result.sample_size, 4)
        self.assertEqual(result.event_count, 2)
        self.assertEqual(result.curve_months, [0, 6, 12, 18])
        self.assertEqual(result.curve_survival_probs, [1.0, 0.75, 0.375, 0.375])
        self.assertEqual(result.median_survival_months, 12)

    def test_fixed_estimate_is_null_beyond_observed_followup(self):
        result = kaplan_meier([(5, True), (20, False), (35, False)])

        self.assertIsNotNone(result.fixed[12].estimate)
        self.assertIsNone(result.fixed[36].estimate)
        self.assertEqual(result.fixed[36].status, "not_estimable")
        self.assertIsNone(result.fixed[60].confidence_interval)

    def test_risk_table_is_monotone(self):
        result = kaplan_meier([(0, False), (12, True), (36, False), (60, True)])

        self.assertEqual(result.risk_table_months, [0, 12, 24, 36, 48, 60])
        self.assertEqual(result.risk_table_counts, [4, 3, 2, 2, 1, 1])

    def test_exact_horizon_is_estimable_and_includes_event(self):
        result = kaplan_meier([(12, True), (12, False)])

        self.assertEqual(result.maximum_followup_months, 12)
        self.assertEqual(result.fixed[12].status, "estimable")
        self.assertEqual(result.fixed[12].estimate, 0.5)
        self.assertEqual(result.fixed[36].status, "not_estimable")

    def test_greenwood_log_log_confidence_interval_is_rounded(self):
        result = kaplan_meier([(1, True), (2, False), (3, True), (4, False)])

        self.assertEqual(result.curve_ci_lower_probs[1], 0.127947)
        self.assertEqual(result.curve_ci_upper_probs[1], 0.960549)
        self.assertEqual(result.curve_ci_lower_probs[2], 0.010971)
        self.assertEqual(result.curve_ci_upper_probs[2], 0.808001)
        self.assertIsNone(result.fixed[12].confidence_interval)

    def test_all_censored_curve_stays_at_one(self):
        result = kaplan_meier([(12, False), (60, False)])

        self.assertEqual(result.event_count, 0)
        self.assertEqual(result.censor_count, 2)
        self.assertIsNone(result.median_survival_months)
        self.assertEqual(result.median_followup_months, 12.0)
        self.assertEqual(result.curve_months, [0, 60])
        self.assertEqual(result.curve_survival_probs, [1.0, 1.0])
        self.assertEqual(result.fixed[60].confidence_interval, (1.0, 1.0))
        self.assertEqual(result.censor_months, [12, 60])

    def test_reverse_km_treats_deaths_as_censored_and_original_censors_as_events(self):
        self.assertEqual(
            reverse_km_median_followup([(1, True), (2, True), (100, False)]),
            100.0,
        )

    def test_reverse_km_all_censored_reaches_median_at_first_half_threshold(self):
        self.assertEqual(
            reverse_km_median_followup([(1, False), (2, False), (3, False)]),
            2.0,
        )

    def test_reverse_km_all_deaths_is_not_estimable(self):
        self.assertIsNone(
            reverse_km_median_followup([(1, True), (7, True), (12, True)])
        )

    def test_reverse_km_events_precede_death_censoring_at_a_tied_month(self):
        self.assertEqual(
            reverse_km_median_followup([(6, True), (6, False)]),
            6.0,
        )

    def test_reverse_km_supports_month_zero(self):
        self.assertEqual(
            reverse_km_median_followup([(0, False), (12, True)]),
            0.0,
        )

    def test_reverse_km_late_followup_event_reaches_median_at_maximum(self):
        self.assertEqual(
            reverse_km_median_followup(
                [(1, True), (2, True), (3, True), (10, False)]
            ),
            10.0,
        )

    def test_reverse_km_empty_observations_raise(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            reverse_km_median_followup([])

    def test_empty_observations_raise(self):
        with self.assertRaisesRegex(ValueError, "at least one"):
            kaplan_meier([])

    def test_negative_month_raises(self):
        with self.assertRaisesRegex(ValueError, "nonnegative"):
            kaplan_meier([(1, False), (-1, True)])

    def test_survival_fields_keep_fixed_ci_and_omit_curve_ci_arrays(self):
        fields = _survival_fields(kaplan_meier([(12, True), (24, False), (60, False)]))

        self.assertEqual(
            set(fields) & {
                "fixed_survival", "curve_months", "curve_survival_probs",
                "risk_table_months", "risk_table_counts",
            },
            {
                "fixed_survival", "curve_months", "curve_survival_probs",
                "risk_table_months", "risk_table_counts",
            },
        )
        self.assertEqual(fields["fixed_survival"]["12"]["status"], "estimable")
        self.assertIsNotNone(fields["fixed_survival"]["12"]["confidence_interval"])
        self.assertNotIn("curve_ci_lower_probs", fields)
        self.assertNotIn("curve_ci_upper_probs", fields)
        json.dumps(fields, allow_nan=False)

    def test_to_dict_is_json_compatible(self):
        payload = kaplan_meier([(12, True), (24, False)]).to_dict()

        self.assertEqual(payload["fixed"]["12"]["status"], "estimable")
        self.assertEqual(payload["fixed"]["36"]["estimate"], None)
        self.assertEqual(payload["curve_months"], [0, 12, 24])
        self.assertEqual(payload["risk_table_counts"], [2, 2, 1, 0, 0, 0])
        json.dumps(payload, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
