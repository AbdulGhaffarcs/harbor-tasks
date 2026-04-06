# Floor Plan Room Connections

## Your Task

You are given a residential floor plan image. Your job is to carefully examine
the plan and identify which rooms are directly connected to each other via a
doorway.

## Input File

| File | Path | Description |
|------|------|-------------|
| Floor plan | `/task/floorplan.jpg` | Residential floor plan (1930s Australian state house) |

## What to Extract

1. **Room names** — read every room label visible in the plan exactly as written
2. **Adjacency** — identify which pairs of rooms share a direct door connection

Two rooms are **adjacent** if there is a visible door (arc symbol or gap in the
wall) between them. Rooms that share a wall with **no door** are **not** adjacent.

Look carefully — some door arcs are small and easy to miss on first inspection.
Re-examine the image multiple times to ensure you haven't missed any doors.

## Output

Write your answer to **`/task/adjacency.json`** in this format:

```json
{
  "rooms": ["Hall", "Bed Room 1", "Kitchen", ...],
  "adjacency": [
    ["Hall", "Bed Room 1"],
    ["Hall", "Kitchen"],
    ...
  ]
}
```

Rules:
- Each adjacency pair must be a list of **exactly two room names**
- Each pair must appear **once only**
- Room names must match **exactly** as written in the floor plan (capitalisation, spacing)
- List **all rooms** in the `rooms` array, even if a room has no door connections

## Scoring

- **Precision**: fraction of your reported pairs that are correct
- **Recall**: fraction of true pairs that you reported
- **Score** = F1 of precision and recall × 100

## Suggested Approach

1. Open `/task/floorplan.jpg` and list every room name you can read
2. Examine every wall between rooms — look for door arc symbols
3. Record each pair of rooms that share a doorway
4. Re-examine the image to check for any missed doors
5. Write `adjacency.json` with your findings
