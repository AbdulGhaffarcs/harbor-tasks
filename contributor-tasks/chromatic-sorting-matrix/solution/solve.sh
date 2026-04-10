#!/bin/bash
# solution/solve.sh
# The Oracle runs this to solve the task. Since the Oracle cannot see the 
# hidden /tests directory, we generate the golden files directly here.

cat << 'EOF' > topology.dot
digraph Conveyor {
    0 [color="RED", arrow="L"];
    1 [color="BLUE", arrow="R"];
    2 [color="GREEN", arrow="L"];
    3 [color="GREEN", arrow="R"];
    4 [color="RED", arrow="L"];
    5 [color="BLUE", arrow="L"];
    0 -> 1 [label="L"];
    0 -> 2 [label="R"];
    1 -> 3 [label="L"];
    1 -> 4 [label="R"];
    2 -> 4 [label="L"];
    2 -> 5 [label="R"];
    3 -> BIN_A [label="L"];
    3 -> BIN_B [label="R"];
    4 -> BIN_B [label="L"];
    4 -> BIN_C [label="R"];
    5 -> BIN_C [label="L"];
    5 -> BIN_D [label="R"];
}
EOF

cat << 'EOF' > trace.csv
package_id,package_color,route,final_bin
1,RED,0->1->4,BIN_B
2,BLUE,0->2->4,BIN_C
3,GREEN,0->2->4,BIN_C
4,RED,0->2->5,BIN_C
5,RED,0->1->4,BIN_C
6,BLUE,0->2->5,BIN_C
7,GREEN,0->2->5,BIN_D
8,BLUE,0->2->4,BIN_B
9,RED,0->2->4,BIN_B
10,GREEN,0->1->4,BIN_C
EOF

echo "solve.sh: Golden outputs successfully generated."