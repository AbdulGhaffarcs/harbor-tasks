# Task: Chromatic Sorting Matrix Simulation

You are managing an automated sorting facility. Analyze the provided image: `sorting_network.png` (located in your current working directory).

### 1. Visual Topology & State Extraction
The image displays a network of colored nodes (RED, BLUE, GREEN) and final destination Bins. 
* Each node is labeled with an ID and contains a white diverter arrow pointing Left (L) or Right (R).
* Paths connecting nodes are explicitly labeled L or R.
* At the top of the image is the **Incoming Queue**. Packages drop into Node 0 sequentially, starting with the package labeled `1`.

### 2. The Routing Simulation Rules
Simulate the packages passing through the network:
1. When a package arrives at a node, it routes down the path indicated by the node's **current** diverter arrow (L or R).
2. **State Mutation:** Immediately after a package passes through a node, if the package's color **MATCHES** the node's color, the node's diverter arrow **FLIPS** (L becomes R, R becomes L). If colors do not match, the arrow remains unchanged.

### Your Goal & Output Artifacts
You must write **TWO** files to your current working directory.

**File 1: `topology.dot`**
A strict Graphviz DOT file representing the initial, unmutated topology extracted from the image. 
*Use exact syntax:*
```dot
digraph Conveyor {
    0 [color="RED", arrow="L"];
    1 [color="BLUE", arrow="R"];
    0 -> 1 [label="L"];
    0 -> 2 [label="R"];
    3 -> BIN_A [label="L"];
}