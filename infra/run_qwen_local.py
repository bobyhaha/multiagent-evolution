#!/usr/bin/env python3
"""Run on an already allocated GPU node. No cloud resources are provisioned.

Starts a loopback-only vLLM service, waits for readiness, runs one bounded pilot,
and terminates the service on exit. The node itself must still be stopped through
SF Compute. Wall time limits compute duration, not provider billing/minimum charges.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", default="Qwen/Qwen3-8B")
    p.add_argument("--project", choices=("capital", "teams", "institutions"), default="capital")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--wall-seconds", type=int, default=1800)
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--episodes", type=int, default=4)
    p.add_argument("--max-calls", type=int, default=150)
    p.add_argument("--tensor-parallel-size", type=int, default=1)
    args = p.parse_args()
    if args.wall_seconds < 60 or args.max_calls < 1 or args.episodes < 1:
        p.error("Use >=60 wall seconds and positive episode/call limits")
    if args.out.exists():
        p.error("Choose a new output path")
    root = Path(__file__).resolve().parents[1]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    log = args.out.with_suffix(".vllm.log")
    base = f"http://127.0.0.1:{args.port}"
    # Refuse to borrow an existing process belonging to another experiment.
    try:
        urllib.request.urlopen(base + "/health", timeout=2).close()
    except urllib.error.URLError:
        pass
    else:
        p.error("Port is already serving a model; choose a different --port")
    start = time.monotonic()
    with log.open("w") as stream:
        server = subprocess.Popen(
            [
                "vllm",
                "serve",
                args.model,
                "--host",
                "127.0.0.1",
                "--port",
                str(args.port),
                "--max-model-len",
                "8192",
                "--gpu-memory-utilization",
                "0.85",
                "--tensor-parallel-size",
                str(args.tensor_parallel_size),
            ],
            stdout=stream,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            while time.monotonic() - start < min(600, args.wall_seconds):
                if server.poll() is not None:
                    raise RuntimeError(f"vLLM exited; inspect {log}")
                try:
                    with urllib.request.urlopen(base + "/v1/models", timeout=2) as response:
                        available = json.load(response)
                    if any(m["id"] == args.model for m in available["data"]):
                        break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(2)
            else:
                raise TimeoutError("Model did not become ready within the startup budget")
            remaining = args.wall_seconds - (time.monotonic() - start)
            command = [
                sys.executable,
                str(root / "test.py"),
                "run",
                "--project",
                args.project,
                "--provider",
                "compatible",
                "--base-url",
                base + "/v1",
                "--model",
                args.model,
                "--api-key-env",
                "SOCIETY_LOCAL_UNUSED_KEY",
                "--episodes",
                str(args.episodes),
                "--eval-episodes",
                "2",
                "--agents",
                "4",
                "--steps",
                "16",
                "--max-calls",
                str(args.max_calls),
                "--max-usd",
                "10",
                "--out",
                str(args.out),
            ]
            # The USD reservation here is a token-equivalent guard, not an estimate
            # of GPU rent. The real limits are wall time and max_calls.
            return subprocess.run(command, timeout=max(1, remaining), check=False).returncode
        finally:
            if server.poll() is None:
                os.killpg(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait()


if __name__ == "__main__":
    raise SystemExit(main())
