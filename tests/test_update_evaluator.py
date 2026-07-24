"""Test update evaluator."""

from unittest import mock

import pytest

from siun.errors import CriterionError
from siun.models import CriterionArchaudit, CriterionAvailable, CriterionCount, PackageUpdate, V2Threshold
from siun.state import get_merged_criteria
from siun.update_evaluator import UpdateEvaluator


class TestUpdateEvaluator:
    """Test UpdateEvaluator."""

    def test_evaluate_matches_available_criterion(self):
        """Match available criterion when updates exist."""
        criteria_settings = [CriterionAvailable(name="available", weight=1)]
        criteria = get_merged_criteria(criteria_settings=criteria_settings)
        evaluator = UpdateEvaluator()

        matched_criteria, match = evaluator.evaluate(
            criteria_settings=criteria_settings,
            thresholds=[V2Threshold(name="available", score=1, text="Updates available")],
            criteria=criteria,
            available_updates=[PackageUpdate(name="linux", provider="pacman")],
        )

        assert matched_criteria == {"available": {"weight": 1, "is_custom": False, "name_short": "av"}}
        assert match
        assert match.name == "available"

    def test_evaluate_ignores_disabled_criteria(self):
        """Skip criteria with weight 0."""
        criteria_settings = [
            CriterionAvailable(name="available", weight=1),
            CriterionCount(name="count", weight=0, count=1),
        ]
        criteria = get_merged_criteria(criteria_settings=criteria_settings)
        evaluator = UpdateEvaluator()

        matched_criteria, _ = evaluator.evaluate(
            criteria_settings=criteria_settings,
            thresholds=[],
            criteria=criteria,
            available_updates=[PackageUpdate(name="linux", provider="pacman")],
        )

        assert "available" in matched_criteria
        assert "count" not in matched_criteria

    def test_evaluate_raises_for_missing_criterion(self):
        """Raise CriterionError if configured criterion was not loaded."""
        criteria_settings = [CriterionArchaudit(name="archaudit", weight=1)]
        evaluator = UpdateEvaluator()

        with pytest.raises(CriterionError) as excinfo:
            evaluator.evaluate(
                criteria_settings=criteria_settings,
                thresholds=[],
                criteria={},
                available_updates=[],
            )

        assert "Configured criterion 'archaudit' was not loaded" in str(excinfo.value)
        assert "Criterion settings:" not in str(excinfo.value)

    @mock.patch("siun.criteria.subprocess.run")
    def test_evaluate_picks_first_matching_threshold(self, mock_run):
        """Pick the first threshold with score less than or equal to total score."""
        mock_run.return_value = mock.Mock(stdout="linux\n", returncode=0)
        criteria_settings = [
            CriterionAvailable(name="available", weight=1),
            CriterionArchaudit(name="archaudit", weight=1),
        ]
        criteria = get_merged_criteria(criteria_settings=criteria_settings)
        evaluator = UpdateEvaluator()
        thresholds = [
            V2Threshold(name="warning", score=2, text="Updates recommended"),
            V2Threshold(name="available", score=1, text="Updates available"),
        ]

        _, match = evaluator.evaluate(
            criteria_settings=criteria_settings,
            thresholds=thresholds,
            criteria=criteria,
            available_updates=[PackageUpdate(name="linux", provider="pacman")],
        )

        assert match
        assert match.name == "warning"
