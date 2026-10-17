"""Tests for scoring the matching methods against hand-checked labels (match_accuracy.py)."""

import pandas as pd
import pytest

from valuation_monitor.match_accuracy import load_labels, truth_sets, weighted_scores


def test_load_labels_rejects_blank_and_invalid_answers(tmp_path):
    path = tmp_path / "sheet.csv"
    pd.DataFrame({"review_id": [1, 2, 3], "answer": ["1", "", "9"]}).to_csv(path, index=False)
    with pytest.raises(SystemExit, match="1 blank and 1 invalid"):
        load_labels(path)


def test_load_labels_accepts_numbers_and_question_mark(tmp_path):
    path = tmp_path / "sheet.csv"
    pd.DataFrame({"review_id": [1, 2, 3], "answer": [" 2", "0", "?"]}).to_csv(path, index=False)
    assert load_labels(path)["answer"].tolist() == ["2", "0", "?"]


def test_identical_addresses_are_both_accepted():
    labels = pd.DataFrame({"review_id": [1, 2, 3], "answer": ["1", "0", "?"]})
    candidates = pd.DataFrame(
        {
            "review_id": [1, 1, 1, 2],
            "candidate_number": [1, 2, 3, 1],
            "property_key": ["U1", "U1B", "U2", "U9"],
            "line_norm": ["7 ELM ROAD", "7 ELM ROAD", "9 ELM ROAD", "1 ASH ROAD"],
        }
    )
    truth = truth_sets(labels, candidates).set_index("review_id")["truth"]
    assert truth[1] == frozenset({"U1", "U1B"})
    assert truth[2] == frozenset()
    assert truth[3] == frozenset()


def test_weighted_precision_and_recall():
    df = pd.DataFrame(
        {
            "truth": [frozenset({"A"}), frozenset({"B"}), frozenset({"C"}), frozenset()],
            "method": ["A", "X", None, "D"],  # correct, wrong, missed, false link
            "sample_weight": [10.0, 1.0, 1.0, 2.0],
        }
    )
    scores = weighted_scores(df, "method")
    assert scores["precision"] == pytest.approx(10 / 13)
    assert scores["recall"] == pytest.approx(10 / 12)
