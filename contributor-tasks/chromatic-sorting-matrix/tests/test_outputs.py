"""
chromatic-sorting-matrix — deterministic scoring.

Output files expected at /task/:
  /task/topology.dot   — Graphviz DOT of extracted topology
  /task/trace.csv      — per-package simulation trace

Scoring (100pts):
  - Topology nodes correct: 30pts (5pts each × 6 nodes)
  - Topology edges correct: 30pts (2pts each × 15 edges)
  - Trace final_bin correct: 30pts (3pts each × 10 packages)
  - Trace route correct: 10pts (1pt each × 10 packages)

Continuous — natural spread at every quality level.
"""
import csv, re, pathlib, pytest

TESTS_DIR  = pathlib.Path("/tests")
AGENT_DOT  = pathlib.Path("/task/topology.dot")
AGENT_CSV  = pathlib.Path("/task/trace.csv")
TRUTH_DOT  = TESTS_DIR / "solution/expected_topology.dot"
TRUTH_CSV  = TESTS_DIR / "solution/expected_trace.csv"
SCORE_FILE = TESTS_DIR / "score.txt"


def parse_dot(filepath):
    content = filepath.read_text()
    nodes = {}
    edges = set()
    for m in re.finditer(r'(\d+)\s*\[color="([A-Z]+)",\s*arrow="([LR])"\]', content):
        nodes[m.group(1)] = {"color": m.group(2), "arrow": m.group(3)}
    for m in re.finditer(r'(\d+|BIN_[A-D])\s*->\s*(\d+|BIN_[A-D])\s*\[label="([LR])"\]', content):
        edges.add((m.group(1), m.group(2), m.group(3)))
    return nodes, edges


class TestFormat:
    def test_dot_exists(self):
        assert AGENT_DOT.exists(), \
            "topology.dot not found at /task/topology.dot"

    def test_csv_exists(self):
        assert AGENT_CSV.exists(), \
            "trace.csv not found at /task/trace.csv"

    def test_csv_has_10_rows(self):
        if not AGENT_CSV.exists(): pytest.skip("no csv")
        rows = list(csv.DictReader(open(AGENT_CSV)))
        assert len(rows) == 10, f"trace.csv must have 10 rows, got {len(rows)}"

    def test_dot_has_nodes(self):
        if not AGENT_DOT.exists(): pytest.skip("no dot")
        nodes, _ = parse_dot(AGENT_DOT)
        assert len(nodes) >= 3, "topology.dot has fewer than 3 nodes"


class TestAccuracy:
    def test_node_colors_partially_correct(self):
        if not AGENT_DOT.exists(): pytest.skip("no dot")
        a_nodes, _ = parse_dot(AGENT_DOT)
        t_nodes, _ = parse_dot(TRUTH_DOT)
        corrxect = sum(1 for nid,v in t_nodes.items()
                      if a_nodes.get(nid,{}).get("color") == v["color"])
        assert correct >= 2, f"Only {correct}/6 node colors correct"

    def test_at_least_one_trace_bin_correct(self):
        if not AGENT_CSV.exists(): pytest.skip("no csv")
        truth = list(csv.DictReader(open(TRUTH_CSV)))
        agent = list(csv.DictReader(open(AGENT_CSV)))
        correct = sum(1 for i in range(min(len(agent),len(truth)))
                      if agent[i].get("final_bin")==truth[i]["final_bin"])
        assert correct >= 1, "No correct final_bin in trace.csv"


class TestScore:
    def test_print_final_score(self, capsys):
        pts = 0.0

        # ── Topology: nodes (30pts) ───────────────────────────────────────
        if AGENT_DOT.exists():
            a_nodes, a_edges = parse_dot(AGENT_DOT)
            t_nodes, t_edges = parse_dot(TRUTH_DOT)

            # 5pts per correct node (color + arrow both right)
            for nid, tv in t_nodes.items():
                av = a_nodes.get(nid, {})
                if av.get("color") == tv["color"]:   pts += 2.5
                if av.get("arrow") == tv["arrow"]:   pts += 2.5

            # ── Topology: edges (30pts) ────────────────────────────────────
            # 2.5pts per correct edge (12 edges × 2.5 = 30pts)
            for edge in t_edges:
                if edge in a_edges: pts += 2.5

        # ── Trace: final_bin (30pts) + route (10pts) ─────────────────────
        if AGENT_CSV.exists():
            try:
                truth = list(csv.DictReader(open(TRUTH_CSV)))
                agent = list(csv.DictReader(open(AGENT_CSV)))
                n = min(len(agent), len(truth))
                for i in range(n):
                    if agent[i].get("final_bin") == truth[i]["final_bin"]:
                        pts += 3.0
                    if agent[i].get("route") == truth[i]["route"]:
                        pts += 1.0
            except Exception:
                pass

        score = round(min(100.0, pts), 2)

        with capsys.disabled():
            print(f"\n{'='*56}")
            print(f"  FINAL SCORE  : {score:.2f} / 100")
            print(f"  Topology nodes (30pts) + edges (30pts)")
            print(f"  Trace bins (30pts) + routes (10pts)")
            print(f"  Deterministic: YES — exact string match")
            print(f"{'='*56}")

        SCORE_FILE.write_text(str(score))
        assert True
