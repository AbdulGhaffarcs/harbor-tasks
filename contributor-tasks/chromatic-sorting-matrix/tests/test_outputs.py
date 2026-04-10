import csv
import re
import pathlib
import pytest

TESTS_DIR = pathlib.Path("/tests")

AGENT_DOT = pathlib.Path("/task/topology.dot")
AGENT_CSV = pathlib.Path("/task/trace.csv")

TRUTH_DOT = pathlib.Path("/task/expected_topology.dot")
TRUTH_CSV = pathlib.Path("/task/expected_trace.csv")

def parse_dot(filepath):
    """Extracts node states and edges using Regex for dependency-free blind evaluation."""
    content = filepath.read_text()
    nodes = {}
    edges = set()
    
    for match in re.finditer(r'(\d+)\s*\[color="([A-Z]+)",\s*arrow="([LR])"\]', content):
        nodes[match.group(1)] = {"color": match.group(2), "arrow": match.group(3)}
        
    for match in re.finditer(r'(\d+)\s*->\s*([A-Za-z0-9_]+)\s*\[label="([LR])"\]', content):
        edges.add((match.group(1), match.group(2), match.group(3)))
        
    return nodes, edges

def test_topology_extraction():
    """Validates the Graphviz DOT initial state extraction."""
    assert AGENT_DOT.exists(), "Agent failed to produce /task/topology.dot"
    
    a_nodes, a_edges = parse_dot(AGENT_DOT)
    t_nodes, t_edges = parse_dot(TRUTH_DOT)
    
    assert a_nodes == t_nodes, f"Topology Node extraction mismatch. Expected: {t_nodes}, Got: {a_nodes}"
    assert a_edges == t_edges, f"Topology Edge extraction mismatch."

def test_simulation_trace():
    """Validates the exact per-package algorithmic simulation CSV."""
    assert AGENT_CSV.exists(), "Agent failed to produce /task/trace.csv"
    
    with open(AGENT_CSV, 'r') as fa, open(TRUTH_CSV, 'r') as ft:
        agent_reader = list(csv.DictReader(fa))
        truth_reader = list(csv.DictReader(ft))
        
    assert len(agent_reader) == len(truth_reader), "CSV row count mismatch. Did you process all 10 packages?"
    
    correct_rows = 0
    total_rows = len(truth_reader)
    
    for i in range(total_rows):
        a_row = agent_reader[i]
        t_row = truth_reader[i]
        
        # Exact strict matching
        if (a_row.get("package_color") == t_row["package_color"] and
            a_row.get("route") == t_row["route"] and
            a_row.get("final_bin") == t_row["final_bin"]):
            correct_rows += 1
            
    score = (correct_rows / total_rows) * 100.0
    score_file = TESTS_DIR / "score.txt"
    score_file.write_text(str(score))
    
    assert correct_rows == total_rows, f"Simulation Trace mismatch. Agent got {correct_rows}/{total_rows} paths correct."