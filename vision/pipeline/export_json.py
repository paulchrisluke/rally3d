#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path
import subprocess
import sys


REQUIRED_FILES = ["court.json", "players.json", "ball.json", "events.json"]
OPTIONAL_FILES = ["ball_2d.json"]


def ensure_sample_data(src_dir: Path):
    tool_path = Path(__file__).resolve().parents[1] / "tools" / "generate_sample_data.py"
    if not tool_path.exists():
        raise SystemExit("Sample data tool not found.")
    subprocess.run([sys.executable, str(tool_path), "--output-dir", str(src_dir)], check=True)


def main():
    parser = argparse.ArgumentParser(description="Copy outputs to viewer/public/data.")
    parser.add_argument("--src", default="../outputs", help="Source output dir.")
    parser.add_argument("--dest", default="../../viewer/public/data", help="Destination dir.")
    parser.add_argument("--generate-sample", action="store_true", help="Generate sample data if missing.")
    args = parser.parse_args()

    src_dir = Path(args.src)
    dest_dir = Path(args.dest)
    dest_dir.mkdir(parents=True, exist_ok=True)

    if args.generate_sample:
        missing = [name for name in REQUIRED_FILES if not (src_dir / name).exists()]
        if missing:
            print("Missing outputs, generating sample data...")
            ensure_sample_data(src_dir)

    copied = []
    for name in REQUIRED_FILES + OPTIONAL_FILES:
        src = src_dir / name
        if src.exists():
            shutil.copy2(src, dest_dir / name)
            copied.append(name)

    if copied:
        print(f"Copied: {', '.join(copied)}")
    else:
        print("No JSON files found to copy.")


if __name__ == "__main__":
    main()
