"""Test formatting module."""

import pytest

from siun.formatting import Formatter


@pytest.mark.parametrize(
    "format_object_fixture,expected_output",
    [
        ("format_object_ok", "Ok"),
        ("format_object_available", "Updates available"),
        ("format_object_recommended", "Updates recommended"),
        ("format_object_required", "Updates required"),
    ],
)
def test_plain(request, format_object_fixture, expected_output):
    """Test plain formatter."""
    format_object = request.getfixturevalue(format_object_fixture)
    output, output_kwargs = Formatter.format_plain(format_object)
    assert output == expected_output
    assert output_kwargs == {}


@pytest.mark.parametrize(
    "format_object_fixture,expected_output,expected_kwargs",
    [
        ("format_object_ok", "Ok", {"fg": "green"}),
        ("format_object_available", "Updates available", {"fg": "blue"}),
        ("format_object_recommended", "Updates recommended", {"fg": "yellow"}),
        ("format_object_required", "Updates required", {"fg": "red"}),
    ],
)
def test_fancy(request, format_object_fixture, expected_output, expected_kwargs):
    """Test fancy formatter."""
    format_object = request.getfixturevalue(format_object_fixture)
    output, output_kwargs = Formatter.format_fancy(format_object)
    assert output == expected_output
    assert output_kwargs == expected_kwargs


@pytest.mark.parametrize(
    "format_object_fixture,expected_output,expected_kwargs",
    [
        ("format_object_ok", '{"count": 0, "text_value": "Ok", "score": 0}', {}),
        ("format_object_available", '{"count": 0, "text_value": "Updates available", "score": 0}', {}),
        ("format_object_recommended", '{"count": 0, "text_value": "Updates recommended", "score": 0}', {}),
        ("format_object_required", '{"count": 0, "text_value": "Updates required", "score": 0}', {}),
    ],
)
def test_json(request, format_object_fixture, expected_output, expected_kwargs):
    """Test JSON formatter."""
    format_object = request.getfixturevalue(format_object_fixture)
    output, output_kwargs = Formatter.format_json(format_object)
    assert output == expected_output
    assert output_kwargs == expected_kwargs


def test_json_handles_count_correctly(format_object_factory):
    """Test count for JSON formatter."""
    format_object = format_object_factory(
        available_updates="pkg1, pkg2",
        status_text="Updates recommended",
        update_count=42,
        state_color="yellow",
        state_name="Updates recommended",
    )
    output, output_kwargs = Formatter.format_json(format_object)
    assert output == '{"count": 42, "text_value": "Updates recommended", "score": 0}'
    assert output_kwargs == {}


def test_json_handles_score_correctly(format_object_factory):
    """Test score for JSON formatter."""
    format_object = format_object_factory(
        available_updates="pkg1, important-pkg",
        matched_criteria="available, critical",
        matched_criteria_short="av,cr",
        score=3,
        status_text="Updates recommended",
        update_count=2,
        state_color="yellow",
        state_name="Updates recommended",
    )
    output, output_kwargs = Formatter.format_json(format_object)
    assert output == '{"count": 2, "text_value": "Updates recommended", "score": 3}'
    assert output_kwargs == {}


@pytest.mark.parametrize(
    "format_object_fixture,template_string,expected_output",
    [
        ("format_object_ok", "$status_text: $available_updates", "Ok: "),
        ("format_object_available", "$status_text: $available_updates", "Updates available: "),
        ("format_object_recommended", "$status_text: $available_updates", "Updates recommended: "),
        ("format_object_required", "$status_text: $available_updates", "Updates required: "),
        (
            None,
            "$available_updates | $last_update | $matched_criteria | $matched_criteria_short | $score | $status_text | $update_count",
            "dummy | 2025-01-09T00:00:00+00:00 | available, count | av,co | 7 | Updates available | 1",
        ),
    ],
)
def test_custom(request, format_object_fixture, template_string, expected_output, format_object_factory):
    """Test custom formatter."""
    if format_object_fixture is not None:
        obj = request.getfixturevalue(format_object_fixture)
    else:
        obj = format_object_factory(
            available_updates="dummy",
            last_update="2025-01-09T00:00:00+00:00",
            matched_criteria="available, count",
            matched_criteria_short="av,co",
            score=7,
            status_text="Updates available",
            update_count=1,
            state_color="blue",
            state_name="Updates available",
        )
    output, output_kwargs = Formatter.format_custom(obj, template_string)
    assert output == expected_output
    assert output_kwargs == {}
