from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "package" / "03_新CG_API_七角色各10"
SERVER = "http://127.0.0.1:8188"


def get_json(path: str) -> dict:
    with urllib.request.urlopen(SERVER + path, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def post_prompt(workflow: dict) -> str:
    data = json.dumps({"prompt": workflow}).encode("utf-8")
    req = urllib.request.Request(SERVER + "/prompt", data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))["prompt_id"]


def wait_idle() -> None:
    while True:
        q = get_json("/queue")
        if not q.get("queue_running") and not q.get("queue_pending"):
            return
        time.sleep(3)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["validate", "all"], default="validate")
    args = p.parse_args()
    files = sorted(ROOT.glob("*/*.json"))
    if args.mode == "validate":
        files = [f for f in files if f.name.startswith("01_")] + [next(f for f in files if "02_Kitchen" in str(f) and f.name.startswith("02_")), next(f for f in files if "05_Nurse" in str(f) and f.name.startswith("03_")), next(f for f in files if "07_Chamber" in str(f) and f.name.startswith("04_"))]
    print(f"queueing {len(files)} workflows")
    for n, f in enumerate(files, 1):
        workflow = json.loads(f.read_text(encoding="utf-8"))
        pid = post_prompt(workflow)
        print(f"{n}/{len(files)} {f.parent.name}/{f.name} -> {pid}")
    wait_idle()
    print("COMPLETED")


if __name__ == "__main__":
    main()
