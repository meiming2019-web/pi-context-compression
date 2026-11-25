"""Export full offline grader rows from the Verified parquet in frozen manifest order."""
import argparse
import json
from pathlib import Path

import pyarrow.parquet as pq


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parquet", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--task-file", type=Path, default=Path(__file__).parent / "tasks/holdout50.json")
    args = parser.parse_args()
    tasks = json.loads(args.task_file.read_text())["tasks"]
    rows = pq.read_table(args.parquet).to_pylist()
    by_id = {row["instance_id"]: row for row in rows}
    if len(by_id) != len(rows) or len({t["instance_id"] for t in tasks}) != len(tasks):
        parser.error("Duplicate instance IDs")
    selected = []
    for task in tasks:
        row = by_id.get(task["instance_id"])
        if row is None or any(row[k] != task[k] for k in ("repo", "base_commit", "image")):
            parser.error(f"Dataset does not match manifest for {task['instance_id']}")
        selected.append({"row": row, "truncated_cells": []})
    args.output.write_text(json.dumps({"rows": selected}) + "\n")
    print(f"Exported {len(selected)} complete rows")


if __name__ == "__main__":
    main()
