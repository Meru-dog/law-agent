"""Evaluation harness CLI for RAG system quality metrics.

Computes Recall@5/10, MRR, citation coverage, and abstain rate.
Exits with code 1 if thresholds not met (for CI/CD gating).
"""

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings
from app.database import build_engine, build_session_factory
from app.logging import configure_logging, get_logger
from app.models import Base
from app.workflow import QueryState, run_workflow


@dataclass
class GoldenExample:
    """A golden evaluation example."""

    question: str
    matter_id: str
    expected_docs: list[str]
    expected_anchors: list[str]
    expected_answer_contains: list[str]


@dataclass
class EvalMetrics:
    """Computed evaluation metrics."""

    recall_at_5: float
    recall_at_10: float
    mrr: float  # Mean Reciprocal Rank
    citation_coverage: float
    abstain_rate: float
    total_examples: int


def load_golden_set(path: str) -> list[GoldenExample]:
    """Load golden evaluation examples from JSONL file.

    Args:
        path: Path to golden set JSONL file.

    Returns:
        List of GoldenExample objects.
    """
    examples = []
    with open(path, "r") as f:
        for line in f:
            if line.strip():
                data = json.loads(line)
                examples.append(
                    GoldenExample(
                        question=data["question"],
                        matter_id=data["matter_id"],
                        expected_docs=data.get("expected_docs", []),
                        expected_anchors=data.get("expected_anchors", []),
                        expected_answer_contains=data.get("expected_answer_contains", []),
                    )
                )
    return examples


def load_thresholds(path: str) -> dict[str, float]:
    """Load metric thresholds from YAML file.

    Args:
        path: Path to thresholds YAML file.

    Returns:
        Dict of metric name to threshold value.
    """
    with open(path, "r") as f:
        return yaml.safe_load(f)


def compute_recall_at_k(
    retrieved: list[str], expected: list[str], k: int
) -> float:
    """Compute Recall@K metric.

    Args:
        retrieved: List of retrieved anchor IDs (in rank order).
        expected: List of expected anchor IDs.
        k: Cutoff rank.

    Returns:
        Recall@K score (0.0 to 1.0).
    """
    if not expected:
        return 1.0  # No expected anchors = perfect recall

    retrieved_at_k = set(retrieved[:k])
    expected_set = set(expected)

    hits = len(retrieved_at_k & expected_set)
    return hits / len(expected_set)


def compute_mrr(retrieved: list[str], expected: list[str]) -> float:
    """Compute Mean Reciprocal Rank.

    Args:
        retrieved: List of retrieved anchor IDs (in rank order).
        expected: List of expected anchor IDs.

    Returns:
        Reciprocal rank (0.0 to 1.0).
    """
    if not expected:
        return 1.0

    expected_set = set(expected)

    for rank, anchor in enumerate(retrieved, start=1):
        if anchor in expected_set:
            return 1.0 / rank

    return 0.0  # None of the expected anchors found


def compute_citation_coverage(answer: str) -> float:
    """Compute citation coverage (% of sentences with citations).

    Args:
        answer: Generated answer text.

    Returns:
        Citation coverage ratio (0.0 to 1.0).
    """
    if not answer or len(answer.strip()) < 10:
        return 0.0

    # Simple sentence splitting (improved heuristic)
    sentences = [s.strip() for s in answer.split(".") if s.strip()]
    if not sentences:
        return 0.0

    # Count sentences with citations [#]
    cited_sentences = sum(1 for sent in sentences if "[" in sent and "]" in sent)

    return cited_sentences / len(sentences)


def run_evaluation(examples: list[GoldenExample]) -> EvalMetrics:
    """Run evaluation on golden examples.

    Args:
        examples: List of golden examples.

    Returns:
        Computed metrics.
    """
    logger = get_logger(__name__)
    settings = get_settings()
    configure_logging(settings)

    # Setup database
    engine = build_engine(settings)
    Base.metadata.create_all(bind=engine)
    session_factory = build_session_factory(engine)

    recall_at_5_scores = []
    recall_at_10_scores = []
    mrr_scores = []
    citation_coverage_scores = []
    abstain_count = 0

    for i, example in enumerate(examples, start=1):
        logger.info(f"Evaluating example {i}/{len(examples)}", question=example.question)

        session = session_factory()
        try:
            # Run query through workflow
            state = QueryState(
                query_id=f"eval-{i}",
                user_id="eval-user",
                matter_id=example.matter_id,
                query=example.question,
            )

            final_state = run_workflow(state, session, settings)

            # Extract retrieved anchors (in rank order)
            retrieved_anchors = []
            if final_state.retrieved_chunks:
                retrieved_anchors = [
                    chunk.anchor_start for chunk in final_state.retrieved_chunks
                ]

            # Compute retrieval metrics
            recall_5 = compute_recall_at_k(
                retrieved_anchors, example.expected_anchors, k=5
            )
            recall_10 = compute_recall_at_k(
                retrieved_anchors, example.expected_anchors, k=10
            )
            mrr = compute_mrr(retrieved_anchors, example.expected_anchors)

            recall_at_5_scores.append(recall_5)
            recall_at_10_scores.append(recall_10)
            mrr_scores.append(mrr)

            # Compute answer metrics
            if final_state.answer:
                citation_cov = compute_citation_coverage(final_state.answer)
                citation_coverage_scores.append(citation_cov)

            if final_state.abstained:
                abstain_count += 1

            logger.info(
                f"Example {i} results",
                recall_at_5=recall_5,
                recall_at_10=recall_10,
                mrr=mrr,
                abstained=final_state.abstained,
            )

        except Exception as e:
            logger.error(f"Evaluation failed for example {i}", error=str(e))
            # Record zeros for failed examples
            recall_at_5_scores.append(0.0)
            recall_at_10_scores.append(0.0)
            mrr_scores.append(0.0)
            citation_coverage_scores.append(0.0)

        finally:
            session.close()

    # Aggregate metrics
    metrics = EvalMetrics(
        recall_at_5=sum(recall_at_5_scores) / len(examples) if examples else 0.0,
        recall_at_10=sum(recall_at_10_scores) / len(examples) if examples else 0.0,
        mrr=sum(mrr_scores) / len(examples) if examples else 0.0,
        citation_coverage=sum(citation_coverage_scores) / len(citation_coverage_scores)
        if citation_coverage_scores
        else 0.0,
        abstain_rate=abstain_count / len(examples) if examples else 0.0,
        total_examples=len(examples),
    )

    engine.dispose()
    return metrics


def print_results(metrics: EvalMetrics, thresholds: dict[str, float]):
    """Print evaluation results with pass/fail indicators.

    Args:
        metrics: Computed metrics.
        thresholds: Threshold values.
    """
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total Examples: {metrics.total_examples}\n")

    # Format and print each metric with threshold check
    metrics_to_check = [
        ("Recall@5", metrics.recall_at_5, thresholds.get("recall_at_5")),
        ("Recall@10", metrics.recall_at_10, thresholds.get("recall_at_10")),
        ("MRR", metrics.mrr, thresholds.get("mrr")),
        (
            "Citation Coverage",
            metrics.citation_coverage,
            thresholds.get("citation_coverage"),
        ),
        ("Abstain Rate", metrics.abstain_rate, thresholds.get("max_abstain_rate")),
    ]

    all_passed = True

    for metric_name, value, threshold in metrics_to_check:
        if threshold is not None:
            # For abstain rate, lower is better
            if metric_name == "Abstain Rate":
                passed = value <= threshold
            else:
                passed = value >= threshold

            status = "✓ PASS" if passed else "✗ FAIL"
            print(
                f"{metric_name:20s}: {value:.3f}  (threshold: {threshold:.3f})  {status}"
            )

            if not passed:
                all_passed = False
        else:
            print(f"{metric_name:20s}: {value:.3f}")

    print("=" * 60)

    if all_passed:
        print("✓ ALL THRESHOLDS MET")
    else:
        print("✗ SOME THRESHOLDS NOT MET")

    print("=" * 60 + "\n")

    return all_passed


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluate RAG system against golden dataset"
    )
    parser.add_argument(
        "--golden-set",
        type=str,
        required=True,
        help="Path to golden set JSONL file",
    )
    parser.add_argument(
        "--thresholds",
        type=str,
        required=True,
        help="Path to thresholds YAML file",
    )

    args = parser.parse_args()

    # Validate files exist
    if not Path(args.golden_set).exists():
        print(f"Error: Golden set file not found: {args.golden_set}", file=sys.stderr)
        sys.exit(2)

    if not Path(args.thresholds).exists():
        print(f"Error: Thresholds file not found: {args.thresholds}", file=sys.stderr)
        sys.exit(2)

    try:
        # Load data
        print(f"Loading golden set from: {args.golden_set}")
        examples = load_golden_set(args.golden_set)
        print(f"Loaded {len(examples)} examples")

        print(f"Loading thresholds from: {args.thresholds}")
        thresholds = load_thresholds(args.thresholds)

        # Run evaluation
        print("\nRunning evaluation...")
        metrics = run_evaluation(examples)

        # Print and check results
        all_passed = print_results(metrics, thresholds)

        # Exit with appropriate code
        sys.exit(0 if all_passed else 1)

    except Exception as e:
        print(f"Error during evaluation: {str(e)}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
