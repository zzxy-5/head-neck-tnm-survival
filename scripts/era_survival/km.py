from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Literal, Optional

CONFIDENCE_Z_95 = 1.959963984540054
FIXED_HORIZONS = (12, 36, 60)
RISK_TABLE_MONTHS = (0, 12, 24, 36, 48, 60)


@dataclass(frozen=True)
class FixedEstimate:
    estimate: Optional[float]
    confidence_interval: Optional[tuple[float, float]]
    status: Literal["estimable", "not_estimable"]

    def to_dict(self) -> dict[str, object]:
        interval = None
        if self.confidence_interval is not None:
            interval = list(self.confidence_interval)
        return {
            "estimate": self.estimate,
            "confidence_interval": interval,
            "status": self.status,
        }


@dataclass(frozen=True)
class KMResult:
    sample_size: int
    event_count: int
    censor_count: int
    median_survival_months: Optional[int]
    median_followup_months: Optional[float]
    maximum_followup_months: int
    fixed: dict[int, FixedEstimate]
    curve_months: list[int]
    curve_survival_probs: list[float]
    curve_ci_lower_probs: list[float]
    curve_ci_upper_probs: list[float]
    censor_months: list[int]
    risk_table_months: list[int]
    risk_table_counts: list[int]

    def to_dict(self) -> dict[str, object]:
        return {
            "sample_size": self.sample_size,
            "event_count": self.event_count,
            "censor_count": self.censor_count,
            "median_survival_months": self.median_survival_months,
            "median_followup_months": self.median_followup_months,
            "maximum_followup_months": self.maximum_followup_months,
            "fixed": {str(month): estimate.to_dict() for month, estimate in self.fixed.items()},
            "curve_months": self.curve_months,
            "curve_survival_probs": self.curve_survival_probs,
            "curve_ci_lower_probs": self.curve_ci_lower_probs,
            "curve_ci_upper_probs": self.curve_ci_upper_probs,
            "censor_months": self.censor_months,
            "risk_table_months": self.risk_table_months,
            "risk_table_counts": self.risk_table_counts,
        }


def _bounded_probability(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 6)


def _log_log_greenwood_ci(survival: float, greenwood_sum: float) -> tuple[float, float]:
    if survival >= 1.0:
        return (1.0, 1.0)
    if survival <= 0.0:
        return (0.0, 0.0)
    if greenwood_sum <= 0.0:
        rounded = _bounded_probability(survival)
        return (rounded, rounded)

    log_survival = math.log(survival)
    standard_error = math.sqrt(greenwood_sum) / abs(log_survival)
    transformed = math.log(-log_survival)
    lower = math.exp(-math.exp(transformed + CONFIDENCE_Z_95 * standard_error))
    upper = math.exp(-math.exp(transformed - CONFIDENCE_Z_95 * standard_error))
    return (_bounded_probability(lower), _bounded_probability(upper))


def fixed_estimate(
    curve_months: list[int],
    survival: list[float],
    lower: list[float],
    upper: list[float],
    maximum_followup: int,
    horizon: int,
) -> FixedEstimate:
    if maximum_followup < horizon:
        return FixedEstimate(None, None, "not_estimable")
    index = max(i for i, month in enumerate(curve_months) if month <= horizon)
    return FixedEstimate(survival[index], (lower[index], upper[index]), "estimable")


def reverse_km_median_followup(
    observations: list[tuple[int, bool]],
) -> Optional[float]:
    """Estimate median follow-up with reverse Kaplan-Meier.

    Original deaths become censorings and original censorings become follow-up
    events. Return None when the reverse-KM curve never reaches 0.5.
    """
    if not observations:
        raise ValueError("Reverse Kaplan-Meier requires at least one observation")
    if any(month < 0 for month, _event in observations):
        raise ValueError("Reverse Kaplan-Meier follow-up months must be nonnegative")

    followup_event_counts = Counter(
        month for month, death_event in observations if not death_event
    )
    death_censor_counts = Counter(
        month for month, death_event in observations if death_event
    )
    observed_months = sorted(set(followup_event_counts) | set(death_censor_counts))
    at_risk = len(observations)
    followup_survival = 1.0

    for month in observed_months:
        events = followup_event_counts[month]
        censored = death_censor_counts[month]
        if events:
            followup_survival *= 1.0 - events / at_risk
            if followup_survival <= 0.5:
                return float(month)
        at_risk -= events + censored

    return None


def kaplan_meier(observations: list[tuple[int, bool]]) -> KMResult:
    """Compute a Kaplan-Meier estimate from (follow-up month, death event) pairs."""
    if not observations:
        raise ValueError("Kaplan-Meier requires at least one observation")
    if any(month < 0 for month, _event in observations):
        raise ValueError("Kaplan-Meier follow-up months must be nonnegative")

    event_counts = Counter(month for month, event in observations if event)
    censor_counts = Counter(month for month, event in observations if not event)
    observed_months = sorted(set(event_counts) | set(censor_counts))
    sample_size = len(observations)
    at_risk = sample_size
    survival = 1.0
    greenwood_sum = 0.0
    median_survival = None
    curve_months = [0]
    curve_survival_probs = [1.0]
    curve_ci_lower_probs = [1.0]
    curve_ci_upper_probs = [1.0]

    for month in observed_months:
        events = event_counts[month]
        censored = censor_counts[month]
        if events:
            survival *= 1.0 - events / at_risk
            if at_risk > events:
                greenwood_sum += events / (at_risk * (at_risk - events))
            ci_lower, ci_upper = _log_log_greenwood_ci(survival, greenwood_sum)
            curve_months.append(month)
            curve_survival_probs.append(_bounded_probability(survival))
            curve_ci_lower_probs.append(ci_lower)
            curve_ci_upper_probs.append(ci_upper)
            if median_survival is None and survival <= 0.5:
                median_survival = month
        at_risk -= events + censored

    maximum_followup = max(observed_months)
    if curve_months[-1] < maximum_followup:
        curve_months.append(maximum_followup)
        curve_survival_probs.append(curve_survival_probs[-1])
        curve_ci_lower_probs.append(curve_ci_lower_probs[-1])
        curve_ci_upper_probs.append(curve_ci_upper_probs[-1])
    fixed = {
        horizon: fixed_estimate(
            curve_months,
            curve_survival_probs,
            curve_ci_lower_probs,
            curve_ci_upper_probs,
            maximum_followup,
            horizon,
        )
        for horizon in FIXED_HORIZONS
    }

    return KMResult(
        sample_size=sample_size,
        event_count=sum(event_counts.values()),
        censor_count=sum(censor_counts.values()),
        median_survival_months=median_survival,
        median_followup_months=reverse_km_median_followup(observations),
        maximum_followup_months=maximum_followup,
        fixed=fixed,
        curve_months=curve_months,
        curve_survival_probs=curve_survival_probs,
        curve_ci_lower_probs=curve_ci_lower_probs,
        curve_ci_upper_probs=curve_ci_upper_probs,
        censor_months=sorted(censor_counts),
        risk_table_months=list(RISK_TABLE_MONTHS),
        risk_table_counts=[
            sum(1 for month, _event in observations if month >= horizon)
            for horizon in RISK_TABLE_MONTHS
        ],
    )
