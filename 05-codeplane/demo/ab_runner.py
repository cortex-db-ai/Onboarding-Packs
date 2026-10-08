#!/usr/bin/env python3
"""A/B runner: your coding agent with vs without CortexDB Codeplane.

Runs one prompt N times per arm with `claude -p --output-format stream-json`,
fresh session per run, auto memory disabled on both arms, and writes one CSV
row per run. Works on two clones/worktrees of the same commit:

  arm A = --dir-a  (stock: no .mcp.json, no CortexDB rules block)
  arm B = --dir-b  (CortexDB: .mcp.json + rules block, repo registered)

Tasks file (JSON):
  {"tasks": [{"id": "FIND1", "prompt": "..."}]}

Usage:
  python3 ab_runner.py --dir-a ../repo-a --dir-b ../repo-b \
      --tasks tasks.json --runs 5 --model <model> --out ab.csv

Fairness contract baked in: identical flags on both arms, auto memory off,
repo state reset between runs, one CSV row per run, raw streams kept.
"""

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


def reset_worktree(path: Path) -> None:
    """Restore pristine tracked state WITHOUT deleting untracked wiring
    (.mcp.json, CLAUDE.md, .claude/) - those carry the arm's treatment."""
    subprocess.run(["git", "-C", str(path), "reset", "--hard", "-q"], check=False)
    subprocess.run(["git", "-C", str(path), "clean", "-fdq",
                    "-e", ".mcp.json", "-e", "CLAUDE.md", "-e", ".claude"], check=False)


def parse_stream(stream_path: Path) -> dict:
    metrics = {"tool_calls": {}, "files_read": set(), "files_edited": set(),
                "bash": 0, "grep_glob": 0, "mcp_calls": 0, "turns": 0}
    usage = cost = duration = None
    result_text = ""
    for line in stream_path.read_text().splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            metrics["turns"] += 1
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") != "tool_use":
                    continue
                name = block.get("name", "?")
                inp = block.get("input", {}) or {}
                metrics["tool_calls"][name] = metrics["tool_calls"].get(name, 0) + 1
                if name == "Read" and inp.get("file_path"):
                    metrics["files_read"].add(inp["file_path"])
                elif name in ("Edit", "Write", "NotebookEdit") and (inp.get("file_path") or inp.get("notebook_path")):
                    metrics["files_edited"].add(inp.get("file_path") or inp.get("notebook_path"))
                elif name == "Bash":
                    metrics["bash"] += 1
                    first = (inp.get("command") or "").split()[:1]
                    if first and first[0] in ("grep", "rg", "find", "fgrep", "ag"):
                        metrics["grep_glob"] += 1
                elif name in ("Glob", "Grep"):
                    metrics["grep_glob"] += 1
                elif name.startswith("mcp__"):
                    metrics["mcp_calls"] += 1
        elif ev.get("type") == "result":
            usage, cost, duration = ev.get("usage"), ev.get("total_cost_usd"), ev.get("duration_ms")
            result_text = ev.get("result", "")
    return metrics, usage, cost, duration, result_text


def run_one(task_id, arm, workdir, prompt, model, run_idx, outdir, extra_env=None):
    reset_worktree(workdir)
    run_dir = outdir / f"{task_id}-{arm}-{run_idx}"
    run_dir.mkdir(parents=True, exist_ok=True)
    stream_path = run_dir / "stream.jsonl"
    env = {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
           "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"}
    if extra_env:
        env.update(extra_env)
    # Hermetic MCP: arm B loads ONLY its project .mcp.json; arm A gets an
    # empty config so a global user-level MCP of the same name can never
    # leak into either arm.
    mcp_flags = ["--strict-mcp-config"]
    if (workdir / ".mcp.json").exists():
        mcp_flags += ["--mcp-config", str(workdir / ".mcp.json")]
    else:
        empty = run_dir / "empty-mcp.json"
        if not empty.exists():
            empty.write_text('{"mcpServers": {}}')
        mcp_flags += ["--mcp-config", str(empty)]
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--model", model,
           "--allowedTools", "Bash", "Edit", "Write", "Read", "Glob", "Grep",
           "NotebookEdit", "mcp__cortexdb"] + mcp_flags
    t0 = time.time()
    with stream_path.open("w") as fh:
        proc = subprocess.run(cmd, cwd=str(workdir), env=env, stdout=fh,
                              stderr=subprocess.PIPE, text=True, timeout=1800)
    wall = time.time() - t0
    if proc.returncode != 0:
        (run_dir / "stderr.txt").write_text(proc.stderr or "")
    metrics, usage, cost, duration, result_text = parse_stream(stream_path)
    (run_dir / "result.txt").write_text(result_text or "")
    u = usage or {}
    total = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) \
        + (u.get("cache_creation_input_tokens") or 0) + (u.get("output_tokens") or 0)
    rel = lambda p: str(p).replace(str(workdir) + "/", "")
    return {
        "task": task_id, "arm": arm, "run": run_idx,
        "status": "ok" if proc.returncode == 0 else f"exit{proc.returncode}",
        "input_tokens": u.get("input_tokens"),
        "cache_read": u.get("cache_read_input_tokens"),
        "cache_write": u.get("cache_creation_input_tokens"),
        "output_tokens": u.get("output_tokens"),
        "total_tokens": total,
        "cost_usd": cost, "num_turns": metrics["turns"], "duration_ms": duration,
        "wall_s": round(wall, 1),
        "tool_calls_total": sum(metrics["tool_calls"].values()),
        "bash": metrics["bash"], "grep_glob": metrics["grep_glob"],
        "read": len(metrics["files_read"]), "edit": len(metrics["files_edited"]),
        "mcp_calls": metrics["mcp_calls"],
        "tool_mix": json.dumps(metrics["tool_calls"], sort_keys=True),
        "files_read": "|".join(sorted(map(rel, metrics["files_read"])))[:2000],
        "files_edited": "|".join(sorted(map(rel, metrics["files_edited"])))[:2000],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir-a", required=True, help="stock arm directory")
    ap.add_argument("--dir-b", required=True, help="CortexDB arm directory")
    ap.add_argument("--tasks", required=True, help="tasks JSON file")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--model", default="glm-5.3")
    ap.add_argument("--only-task", default=None)
    ap.add_argument("--out", default="ab.csv")
    args = ap.parse_args()

    tasks = json.loads(Path(args.tasks).read_text())["tasks"]
    if args.only_task:
        tasks = [t for t in tasks if t["id"] == args.only_task]
    outdir = Path("runs")
    outdir.mkdir(exist_ok=True)
    fieldnames = None
    for task in tasks:
        for arm, wd in (("A", Path(args.dir_a)), ("B", Path(args.dir_b))):
            for i in range(1, args.runs + 1):
                print(f"==> {task['id']} arm {arm} run {i}", flush=True)
                row = run_one(task["id"], arm, wd, task["prompt"], args.model, i, outdir)
                fieldnames = list(row.keys())
                with open(args.out, "a", newline="") as fh:
                    w = csv.DictWriter(fh, fieldnames=fieldnames)
                    if fh.tell() == 0:
                        w.writeheader()
                    w.writerow(row)
                print("    tokens=%s turns=%s mcp=%s" %
                      (row["total_tokens"], row["num_turns"], row["mcp_calls"]), flush=True)


if __name__ == "__main__":
    main()
