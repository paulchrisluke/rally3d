#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (ROOT_DIR / path).resolve()


def load_annotations(path: Path):
    if not path.exists():
        raise SystemExit(f"Annotations not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    frames = data.get("frames", [])
    if not frames:
        raise SystemExit("No frames found in annotations.")
    return data, frames


def interpolate_points(points):
    count = len(points)
    filled = [None] * count
    conf = [0.0] * count
    known = [i for i, p in enumerate(points) if p is not None]
    if not known:
        return filled, conf

    for i in known:
        filled[i] = points[i]
        conf[i] = 1.0

    first = known[0]
    for i in range(0, first):
        filled[i] = points[first]
        conf[i] = 0.2

    for idx in range(len(known) - 1):
        start = known[idx]
        end = known[idx + 1]
        p0 = points[start]
        p1 = points[end]
        gap = end - start
        for i in range(start + 1, end):
            t = (i - start) / gap
            filled[i] = [
                p0[0] + (p1[0] - p0[0]) * t,
                p0[1] + (p1[1] - p0[1]) * t,
            ]
            conf[i] = 0.2

    last = known[-1]
    for i in range(last + 1, count):
        filled[i] = points[last]
        conf[i] = 0.2

    return filled, conf


def main():
    parser = argparse.ArgumentParser(description="Generate ball_2d.json from manual annotations.")
    parser.add_argument("--annotations", default="vision/annotations/points.json", help="Annotation JSON path (relative to repo root).")
    parser.add_argument("--output", default="vision/outputs/ball_2d.json", help="Output ball_2d.json path (relative to repo root).")
    parser.add_argument("--fps", type=int, default=None, help="Override fps.")
    args = parser.parse_args()

    annotations_path = resolve_path(args.annotations)
    output_path = resolve_path(args.output)

    data, frames = load_annotations(annotations_path)
    fps = int(args.fps or data.get("fps", 30))
    if fps <= 0:
        raise SystemExit(f"Invalid fps value: {fps}. Must be positive.")
    frame_count = int(data.get("frame_count", len(frames)))
    frame_count = min(frame_count, len(frames))

    points = [frame.get("ball") for frame in frames]
    points_filled, conf = interpolate_points(points)

    if all(p is None for p in points_filled):
        raise SystemExit("No ball points found in annotations.")

    output_frames = []
    for i in range(frame_count):
        t = round(i / fps, 6)
        point = points_filled[i]
        if point is None:
            u, v = None, None
            confidence = 0.0
        else:
            u, v = float(point[0]), float(point[1])
            confidence = conf[i]
        output_frames.append({"frame": i, "t": t, "u": u, "v": v, "confidence": confidence})

    output = {"fps": fps, "frame_count": frame_count, "frames": output_frames}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
