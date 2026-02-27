"""Tests for evaluation harness."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from app.cli_eval import (
    EvalMetrics,
    GoldenExample,
    compute_citation_coverage,
    compute_mrr,
    compute_recall_at_k,
    load_golden_set,
    load_thresholds,
    print_results,
)


@pytest.fixture
def sample_golden_examples():
    """Sample golden examples."""
    return [
        GoldenExample(
            question="What is the payment term?",
            matter_id="matter-1",
            expected_docs=["doc-123"],
            expected_anchors=["page-5"],
            expected_answer_contains=["30 days"],
        ),
        GoldenExample(
            question="Who are the parties?",
            matter_id="matter-1",
            expected_docs=["doc-123"],
            expected_anchors=["page-1"],
            expected_answer_contains=["buyer", "seller"],
        ),
    ]


def test_load_golden_set(tmp_path):
    """Test loading golden set from JSONL."""
    golden_file = tmp_path / "golden.jsonl"
    golden_file.write_text(
        '{"question": "Q1", "matter_id": "m1", "expected_docs": ["doc1"], "expected_anchors": ["p1"], "expected_answer_contains": ["answer"]}\n'
        '{"question": "Q2", "matter_id": "m2", "expected_docs": ["doc2"], "expected_anchors": ["p2"], "expected_answer_contains": ["text"]}\n'
    )

    examples = load_golden_set(str(golden_file))

    assert len(examples) == 2
    assert examples[0].question == "Q1"
    assert examples[0].matter_id == "m1"
    assert examples[1].question == "Q2"


def test_load_golden_set_empty_lines(tmp_path):
    """Test loading golden set handles empty lines."""
    golden_file = tmp_path / "golden.jsonl"
    golden_file.write_text(
        '{"question": "Q1", "matter_id": "m1", "expected_docs": [], "expected_anchors": [], "expected_answer_contains": []}\n'
        "\n"  # Empty line
        '{"question": "Q2", "matter_id": "m2", "expected_docs": [], "expected_anchors": [], "expected_answer_contains": []}\n'
    )

    examples = load_golden_set(str(golden_file))

    assert len(examples) == 2


def test_load_thresholds(tmp_path):
    """Test loading thresholds from YAML."""
    thresholds_file = tmp_path / "thresholds.yaml"
    thresholds_file.write_text(
        """
recall_at_5: 0.6
recall_at_10: 0.8
mrr: 0.5
citation_coverage: 0.9
max_abstain_rate: 0.2
"""
    )

    thresholds = load_thresholds(str(thresholds_file))

    assert thresholds["recall_at_5"] == 0.6
    assert thresholds["recall_at_10"] == 0.8
    assert thresholds["mrr"] == 0.5
    assert thresholds["citation_coverage"] == 0.9
    assert thresholds["max_abstain_rate"] == 0.2


def test_compute_recall_at_k_perfect():
    """Test Recall@K with perfect retrieval."""
    retrieved = ["page-5", "page-1", "page-10"]
    expected = ["page-5", "page-1"]

    recall = compute_recall_at_k(retrieved, expected, k=5)

    assert recall == 1.0  # Both expected found in top-5


def test_compute_recall_at_k_partial():
    """Test Recall@K with partial retrieval."""
    retrieved = ["page-5", "page-2", "page-3"]
    expected = ["page-5", "page-1", "page-10"]

    recall = compute_recall_at_k(retrieved, expected, k=5)

    assert recall == 1 / 3  # Only 1 of 3 expected found


def test_compute_recall_at_k_cutoff():
    """Test Recall@K respects cutoff."""
    retrieved = ["page-1", "page-2", "page-3", "page-4", "page-5"]
    expected = ["page-5"]

    recall_3 = compute_recall_at_k(retrieved, expected, k=3)
    recall_5 = compute_recall_at_k(retrieved, expected, k=5)

    assert recall_3 == 0.0  # Not in top-3
    assert recall_5 == 1.0  # Found in top-5


def test_compute_recall_at_k_no_expected():
    """Test Recall@K with no expected anchors."""
    retrieved = ["page-1", "page-2"]
    expected = []

    recall = compute_recall_at_k(retrieved, expected, k=5)

    assert recall == 1.0  # Perfect recall when no expectations


def test_compute_mrr_first_position():
    """Test MRR when expected found at rank 1."""
    retrieved = ["page-5", "page-1", "page-2"]
    expected = ["page-5"]

    mrr = compute_mrr(retrieved, expected)

    assert mrr == 1.0


def test_compute_mrr_third_position():
    """Test MRR when expected found at rank 3."""
    retrieved = ["page-1", "page-2", "page-5"]
    expected = ["page-5"]

    mrr = compute_mrr(retrieved, expected)

    assert mrr == 1.0 / 3


def test_compute_mrr_not_found():
    """Test MRR when expected not found."""
    retrieved = ["page-1", "page-2", "page-3"]
    expected = ["page-5"]

    mrr = compute_mrr(retrieved, expected)

    assert mrr == 0.0


def test_compute_mrr_no_expected():
    """Test MRR with no expected anchors."""
    retrieved = ["page-1", "page-2"]
    expected = []

    mrr = compute_mrr(retrieved, expected)

    assert mrr == 1.0


def test_compute_citation_coverage_full():
    """Test citation coverage with all sentences cited."""
    answer = "Payment is 30 days [1]. Late fees apply [2]."

    coverage = compute_citation_coverage(answer)

    assert coverage == 1.0  # 2/2 sentences have citations


def test_compute_citation_coverage_partial():
    """Test citation coverage with partial citations."""
    answer = "Payment is 30 days [1]. Late fees apply. No refunds."

    coverage = compute_citation_coverage(answer)

    assert coverage == 1.0 / 3  # 1/3 sentences have citations


def test_compute_citation_coverage_none():
    """Test citation coverage with no citations."""
    answer = "Payment is 30 days. Late fees apply."

    coverage = compute_citation_coverage(answer)

    assert coverage == 0.0


def test_compute_citation_coverage_empty():
    """Test citation coverage with empty answer."""
    coverage = compute_citation_coverage("")

    assert coverage == 0.0


def test_compute_citation_coverage_short():
    """Test citation coverage with very short answer."""
    coverage = compute_citation_coverage("Yes")

    assert coverage == 0.0


def test_print_results_all_passed(capsys):
    """Test printing results when all thresholds met."""
    metrics = EvalMetrics(
        recall_at_5=0.8,
        recall_at_10=0.9,
        mrr=0.7,
        citation_coverage=0.95,
        abstain_rate=0.1,
        total_examples=10,
    )

    thresholds = {
        "recall_at_5": 0.6,
        "recall_at_10": 0.8,
        "mrr": 0.5,
        "citation_coverage": 0.9,
        "max_abstain_rate": 0.2,
    }

    result = print_results(metrics, thresholds)

    assert result is True
    captured = capsys.readouterr()
    assert "ALL THRESHOLDS MET" in captured.out
    assert "✓ PASS" in captured.out


def test_print_results_some_failed(capsys):
    """Test printing results when some thresholds not met."""
    metrics = EvalMetrics(
        recall_at_5=0.5,  # Below threshold of 0.6
        recall_at_10=0.9,
        mrr=0.7,
        citation_coverage=0.85,  # Below threshold of 0.9
        abstain_rate=0.1,
        total_examples=10,
    )

    thresholds = {
        "recall_at_5": 0.6,
        "recall_at_10": 0.8,
        "mrr": 0.5,
        "citation_coverage": 0.9,
        "max_abstain_rate": 0.2,
    }

    result = print_results(metrics, thresholds)

    assert result is False
    captured = capsys.readouterr()
    assert "SOME THRESHOLDS NOT MET" in captured.out
    assert "✗ FAIL" in captured.out


def test_print_results_abstain_rate_check(capsys):
    """Test abstain rate threshold checking (lower is better)."""
    metrics = EvalMetrics(
        recall_at_5=0.8,
        recall_at_10=0.9,
        mrr=0.7,
        citation_coverage=0.95,
        abstain_rate=0.3,  # Above max threshold of 0.2
        total_examples=10,
    )

    thresholds = {
        "recall_at_5": 0.6,
        "recall_at_10": 0.8,
        "mrr": 0.5,
        "citation_coverage": 0.9,
        "max_abstain_rate": 0.2,
    }

    result = print_results(metrics, thresholds)

    assert result is False  # Should fail due to high abstain rate
    captured = capsys.readouterr()
    assert "Abstain Rate" in captured.out


def test_golden_example_dataclass():
    """Test GoldenExample dataclass."""
    example = GoldenExample(
        question="Test question",
        matter_id="matter-1",
        expected_docs=["doc-1"],
        expected_anchors=["page-1"],
        expected_answer_contains=["keyword"],
    )

    assert example.question == "Test question"
    assert example.matter_id == "matter-1"
    assert len(example.expected_docs) == 1
    assert len(example.expected_anchors) == 1


def test_eval_metrics_dataclass():
    """Test EvalMetrics dataclass."""
    metrics = EvalMetrics(
        recall_at_5=0.8,
        recall_at_10=0.9,
        mrr=0.7,
        citation_coverage=0.95,
        abstain_rate=0.1,
        total_examples=10,
    )

    assert metrics.recall_at_5 == 0.8
    assert metrics.total_examples == 10
