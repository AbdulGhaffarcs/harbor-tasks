# Task: Chromatic Sorting Matrix Simulation

You are managing an automated sorting facility. You are provided with an image of the conveyor network: `/task/sorting_network.png`.

### The Visual Network
* Packages enter at **Node 0** (Top).
* The network consists of colored circular nodes (RED, BLUE, GREEN).
* Each node has a diverter arrow currently pointing **Left (<--)** or **Right (-->)**.
* Packages travel down the black lines to either another node or a final Bin (A, B, C, or D).

### The Routing Rules
1. When a package arrives at a node, it exits down the branch indicated by the node's current arrow (L or R).
2. **The Mutation Rule:** Immediately after a package passes through a node, if the package's color **MATCHES** the node's color, the node's diverter arrow **FLIPS** to the opposite direction (L becomes R, R becomes L). 
3. If the package color does NOT match the node color, the arrow remains unchanged.

### The Input Sequence
The following 10 packages are dropped into Node 0, one at a time, in this exact sequence:
`["RED", "BLUE", "GREEN", "RED", "RED", "BLUE", "GREEN", "BLUE", "RED", "GREEN"]`

### Your Goal
Simulate the routing of all 10 packages through the network. Keep track of how the nodes change state over time. Count how many packages end up in each of the 4 bins.

Write your final counts to `/task/output.json` in this exact format:
```json
{
  "BIN_A": 0,
  "BIN_B": 0,
  "BIN_C": 0,
  "BIN_D": 0
}