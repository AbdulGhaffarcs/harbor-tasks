"""
tests/test_outputs.py

Blind, deterministic scoring for "Floor Plan Room Connections".
Scoring: F1 on the set of room adjacency pairs.
"""

import json
import pathlib
import pytest

TESTS_DIR    = pathlib.Path("/tests")
GROUND_TRUTH = TESTS_DIR / "ground_truth.json"
OUTPUT       = pathlib.Path("/task/adjacency.json")
SCORE_FILE   = TESTS_DIR / "score.txt"


def load_ground_truth():
    return json.loads(GROUND_TRUTH.read_text())


def load_agent_output():
    return json.loads(OUTPUT.read_text())


def normalise_pair(pair):
    return tuple(sorted(str(x) for x in pair))


def compute_f1(gt_pairs, agent_pairs):
    gt_set    = set(normalise_pair(p) for p in gt_pairs)
    agent_set = set(normalise_pair(p) for p in agent_pairs)
    tp = len(gt_set & agent_set)
    fp = len(agent_set - gt_set)
    fn = len(gt_set  - agent_set)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) \
         if (precision + recall) > 0 else 0.0
    return precision, recall, f1


class TestFormat:

    def test_output_file_exists(self):
        assert OUTPUT.exists(), f"adjacency.json not found at {OUTPUT}"

    def test_output_is_valid_json(self):
        try:
            load_agent_output()
        except json.JSONDecodeError as e:
            pytest.fail(f"adjacency.json is not valid JSON: {e}")

    def test_output_has_rooms_key(self):
        assert "rooms" in load_agent_output(), '"rooms" key missing'

    def test_output_has_adjacency_key(self):
        assert "adjacency" in load_agent_output(), '"adjacency" key missing'

    def test_adjacency_is_list(self):
        assert isinstance(load_agent_output()["adjacency"], list), \
            '"adjacency" must be a list'

    def test_each_pair_has_two_rooms(self):
        for i, pair in enumerate(load_agent_output()["adjacency"]):
            assert len(pair) == 2, \
                f"Pair {i} has {len(pair)} elements — needs exactly 2 room names"

    def test_no_duplicate_pairs(self):
        norms = [normalise_pair(p) for p in load_agent_output()["adjacency"]]
        assert len(norms) == len(set(norms)), "Duplicate pairs found"

    def test_rooms_list_not_empty(self):
        assert len(load_agent_output().get("rooms", [])) > 0, \
            '"rooms" list is empty'


class TestAccuracy:

    def test_at_least_one_pair_correct(self):
        gt = load_ground_truth()
        data = load_agent_output()
        _, _, f1 = compute_f1(gt["adjacency"], data.get("adjacency", []))
        assert f1 > 0, "No adjacency pairs matched ground truth"

    def test_majority_pairs_correct(self):
        gt = load_ground_truth()
        data = load_agent_output()
        _, recall, _ = compute_f1(gt["adjacency"], data.get("adjacency", []))
        assert recall >= 0.50, \
            f"Recall {recall*100:.0f}% — need at least 50% of true pairs"

    def test_most_pairs_correct(self):
        gt = load_ground_truth()
        data = load_agent_output()
        _, recall, _ = compute_f1(gt["adjacency"], data.get("adjacency", []))
        assert recall >= 0.75, \
            f"Recall {recall*100:.0f}% — need at least 75% of true pairs"


class TestScore:
    def test_print_final_score(self, capsys):
        gt = load_ground_truth()

        if not OUTPUT.exists():
            score = 0.0
        else:
            data = load_agent_output()
            agent_pairs = data.get("adjacency", [])
            precision, recall, f1 = compute_f1(gt["adjacency"], agent_pairs)
            score = round(f1 * 100, 2)

            gt_set    = set(normalise_pair(p) for p in gt["adjacency"])
            agent_set = set(normalise_pair(p) for p in agent_pairs)

            with capsys.disabled():
                print(f"\n{'='*54}")
                print(f"  FINAL SCORE  : {score:.2f} / 100")
                print(f"  Precision    : {precision*100:.0f}%")
                print(f"  Recall       : {recall*100:.0f}%")
                print(f"  F1           : {f1*100:.0f}%")
                print(f"\n  Correct ({len(gt_set & agent_set)}):")
                for p in sorted(gt_set & agent_set):
                    print(f"    ✅ {p[0]} ↔ {p[1]}")
                if gt_set - agent_set:
                    print(f"  Missed ({len(gt_set - agent_set)}):")
                    for p in sorted(gt_set - agent_set):
                        print(f"    ❌ {p[0]} ↔ {p[1]}")
                if agent_set - gt_set:
                    print(f"  False ({len(agent_set - gt_set)}):")
                    for p in sorted(agent_set - gt_set):
                        print(f"    ⚠️  {p[0]} ↔ {p[1]}")
                print(f"{'='*54}")

        SCORE_FILE.write_text(str(score))
        assert True
