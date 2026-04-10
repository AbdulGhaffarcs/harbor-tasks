"""
tests/test_outputs.py
Blind, deterministic scoring for the Chromatic Sorting Matrix task.
"""
import json
import pathlib
import pytest

TESTS_DIR = pathlib.Path("/tests")
AGENT_FILE = pathlib.Path("/task/output.json")
TRUTH_FILE = pathlib.Path("/task/expected_output.json")

def test_deterministic_routing():
    """Blind evaluation of the agent's multi-layered simulation."""
    assert AGENT_FILE.exists(), "Output file not found: The agent must write output.json to /task/output.json"
    
    try:
        with open(AGENT_FILE, 'r') as f:
            agent_data = json.load(f)
    except json.JSONDecodeError as e:
        pytest.fail(f"/task/output.json is not valid JSON: {e}")
        
    with open(TRUTH_FILE, 'r') as f:
        truth_data = json.load(f)

    correct_bins = 0
    for bin_name in ["BIN_A", "BIN_B", "BIN_C", "BIN_D"]:
        assert bin_name in agent_data, f"Missing {bin_name} key in output."
        if agent_data[bin_name] == truth_data[bin_name]:
            correct_bins += 1

    # Score calculation (25 points per correct bin)
    score = (correct_bins / 4.0) * 100
    
    score_file = TESTS_DIR / "score.txt"
    score_file.write_text(str(score))
    
    assert correct_bins == 4, (
        f"Routing simulation failed. Agent got {correct_bins}/4 bins correct. "
        "This indicates a failure to accurately track the visual state mutation."
    )

def test_print_final_score(capsys):
    """Prints the final computed score to the console."""
    score_file = TESTS_DIR / "score.txt"
    if score_file.exists():
        score = float(score_file.read_text())
        with capsys.disabled():
            print(f"\n{'='*52}")
            print(f"  FINAL SCORE  : {score:.2f} / 100")
            print(f"{'='*52}")
    assert True