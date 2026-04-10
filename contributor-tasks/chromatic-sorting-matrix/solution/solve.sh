#!/usr/bin/env bash

mkdir -p /task

cat << 'EOF' > /task/solve.py
import csv

nodes = {
    0: {"color": "RED",   "arrow": "L", "L": 1, "R": 2},
    1: {"color": "BLUE",  "arrow": "R", "L": 3, "R": 4},
    2: {"color": "GREEN", "arrow": "L", "L": 4, "R": 5},
    3: {"color": "GREEN", "arrow": "R", "L": "BIN_A", "R": "BIN_B"},
    4: {"color": "RED",   "arrow": "L", "L": "BIN_B", "R": "BIN_C"},
    5: {"color": "BLUE",  "arrow": "L", "L": "BIN_C", "R": "BIN_D"},
}

# 1. Generate Topology DOT
with open("/task/expected_topology.dot", "w") as f:
    f.write("digraph Conveyor {\n")
    for nid, data in nodes.items():
        f.write(f'    {nid} [color="{data["color"]}", arrow="{data["arrow"]}"];\n')
    for nid, data in nodes.items():
        f.write(f'    {nid} -> {data["L"]} [label="L"];\n')
        f.write(f'    {nid} -> {data["R"]} [label="R"];\n')
    f.write("}\n")

# 2. Generate Trace CSV
queue = ["RED", "BLUE", "GREEN", "RED", "RED", "BLUE", "GREEN", "BLUE", "RED", "GREEN"]
with open("/task/expected_trace.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["package_id", "package_color", "route", "final_bin"])
    
    for i, pkg in enumerate(queue):
        curr = 0
        route = []
        while isinstance(curr, int):
            route.append(str(curr))
            node = nodes[curr]
            direction = node["arrow"]
            curr = node[direction]
            
            # Mutation Logic
            if pkg == node["color"]:
                node["arrow"] = "R" if direction == "L" else "L"
                
        writer.writerow([i+1, pkg, "->".join(route), curr])
EOF

python3 /task/solve.py
echo "Golden artifacts generated."