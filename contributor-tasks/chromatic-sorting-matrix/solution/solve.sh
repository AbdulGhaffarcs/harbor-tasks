#!/usr/bin/env bash
# solution/solve.sh
# Generates the ground truth mathematically based on the exact 
# starting parameters of the visual state machine.

mkdir -p /task

cat << 'EOF' > /task/solve.py
import json

nodes = {
    0: {"color": "RED",   "arrow": "L", "L": 1, "R": 2},
    1: {"color": "BLUE",  "arrow": "R", "L": 3, "R": 4},
    2: {"color": "GREEN", "arrow": "L", "L": 4, "R": 5},
    3: {"color": "GREEN", "arrow": "R", "L": "BIN_A", "R": "BIN_B"},
    4: {"color": "RED",   "arrow": "L", "L": "BIN_B", "R": "BIN_C"},
    5: {"color": "BLUE",  "arrow": "L", "L": "BIN_C", "R": "BIN_D"},
}

packages = ["RED", "BLUE", "GREEN", "RED", "RED", "BLUE", "GREEN", "BLUE", "RED", "GREEN"]
bins = {"BIN_A": 0, "BIN_B": 0, "BIN_C": 0, "BIN_D": 0}

for pkg in packages:
    curr = 0
    while isinstance(curr, int):
        node = nodes[curr]
        direction = node["arrow"]
        curr = node[direction] # Move to next
        
        # Mutation Logic
        if pkg == node["color"]:
            node["arrow"] = "R" if direction == "L" else "L"
            
    bins[curr] += 1

with open("/task/expected_output.json", "w") as f:
    json.dump(bins, f, indent=2)
EOF

python3 /task/solve.py
echo "Golden solution generated at /task/expected_output.json"