"""
Tests del regression_test runner.
"""
import sys
import pytest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from regression_test import check_thresholds, THRESHOLDS


def test_perfect_chaining_passes():
    """Si chaining_rate=1.0 y hay 5+ chains, no debe haber fallos."""
    data = {
        "summary": {"chaining_rate": 1.0, "pass": 5, "partial": 0, "fail": 0},
        "results": [
            {"chain_count": 2, "tools_expected": 2, "found_tools": ["a", "b"]},
            {"chain_count": 2, "tools_expected": 2, "found_tools": ["a", "b"]},
            {"chain_count": 3, "tools_expected": 3, "found_tools": ["a", "b", "c"]},
            {"chain_count": 2, "tools_expected": 2, "found_tools": ["a", "b"]},
            {"chain_count": 2, "tools_expected": 2, "found_tools": ["a", "b"]},
        ],
    }
    failures = check_thresholds(data)
    assert failures == []


def test_low_chaining_rate_fails():
    """Si chaining_rate < threshold, debe fallar."""
    data = {
        "summary": {"chaining_rate": 0.6, "pass": 3, "partial": 0, "fail": 2},
        "results": [{"chain_count": 0}] * 5,
    }
    failures = check_thresholds(data)
    assert any("chaining_rate" in f for f in failures)


def test_too_few_chains_fails():
    """Si hay menos de N chains testeados, falla."""
    data = {
        "summary": {"chaining_rate": 1.0, "pass": 3, "partial": 0, "fail": 0},
        "results": [
            {"chain_count": 2, "tools_expected": 2, "found_tools": ["a", "b"]},
            {"chain_count": 2, "tools_expected": 2, "found_tools": ["a", "b"]},
            {"chain_count": 2, "tools_expected": 2, "found_tools": ["a", "b"]},
        ],
    }
    failures = check_thresholds(data)
    assert any("chains_tested" in f for f in failures)


def test_no_tool_calls_fails():
    """Si ninguna query dispara tools, falla por tool_call_rate."""
    data = {
        "summary": {"chaining_rate": 1.0, "pass": 5, "partial": 0, "fail": 0},
        "results": [{"chain_count": 0, "tools_expected": 0, "found_tools": []}] * 5,
    }
    failures = check_thresholds(data)
    assert any("tool_call_rate" in f for f in failures)


def test_none_data_fails():
    """Si data es None (eval fallo), devuelve un fallo claro."""
    failures = check_thresholds(None)
    assert len(failures) >= 1
    assert "eval_chain" in failures[0]


def test_thresholds_are_sane():
    """Los thresholds tienen sentido (>=0 y <=1 para rates)."""
    assert 0 <= THRESHOLDS["multi_tool_chaining"]["min_pass_rate"] <= 1
    assert THRESHOLDS["multi_tool_chaining"]["min_chains_tested"] >= 1
    assert 0 <= THRESHOLDS["tool_call_rate"]["min"] <= 1
