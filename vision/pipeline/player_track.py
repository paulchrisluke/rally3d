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


def load_homography(path: Path):
    if not path.exists():
        raise SystemExit(f"court.json not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("homography_img_to_court")


def apply_homography(h, u, v):
    x = h[0][0] * u + h[0][1] * v + h[0][2]
    y = h[1][0] * u + h[1][1] * v + h[1][2]
    w = h[2][0] * u + h[2][1] * v + h[2][2]
    if abs(w) < 1e-9:
        raise ValueError(f"Degenerate homography: w={w} at ({u}, {v})")
    return x / w, y / w


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
    parser = argparse.ArgumentParser(description="Generate players.json from manual annotations.")
    parser.add_argument("--annotations", default="vision/annotations/points.json", help="Annotation JSON path (relative to repo root).")
    parser.add_argument("--court-json", default="vision/outputs/court.json", help="court.json path (relative to repo root).")
    parser.add_argument("--output", default="vision/outputs/players.json", help="Output players.json path (relative to repo root).")
    parser.add_argument("--fps", type=int, default=None, help="Override fps.")
    parser.add_argument("--height-a", type=float, default=1.8, help="Height for player A.")
    parser.add_argument("--height-b", type=float, default=1.85, help="Height for player B.")
    args = parser.parse_args()

    annotations_path = resolve_path(args.annotations)
    court_json_path = resolve_path(args.court_json)
    output_path = resolve_path(args.output)

    data, frames = load_annotations(annotations_path)
    fps = int(args.fps or data.get("fps", 30))
    if fps <= 0:
        raise SystemExit(f"Invalid fps value: {fps}. Must be positive.")
    frame_count = int(data.get("frame_count", len(frames)))
    frame_count = min(frame_count, len(frames))

    homography = load_homography(court_json_path)
    if homography is None:
        raise SystemExit("homography_img_to_court missing in court.json")

    points_a = [frame.get("A") for frame in frames]
    points_b = [frame.get("B") for frame in frames]

    points_a_filled, _ = interpolate_points(points_a)
    points_b_filled, _ = interpolate_points(points_b)

    output_frames = []
    for i in range(frame_count):
        t = round(i / fps, 6)
        players = []

        if points_a_filled[i] is not None:
            ax, ay = apply_homography(homography, points_a_filled[i][0], points_a_filled[i][1])
        else:
            ax, ay = 0.0, 0.0
        if points_b_filled[i] is not None:
            bx, by = apply_homography(homography, points_b_filled[i][0], points_b_filled[i][1])
        else:
            bx, by = 0.0, 0.0

        players.append({"id": "A", "x": round(ax, 3), "y": round(ay, 3), "height": args.height_a})
        players.append({"id": "B", "x": round(bx, 3), "y": round(by, 3), "height": args.height_b})

        output_frames.append({"frame": i, "t": t, "players": players})

    output = {
        "fps": fps,
        "frame_count": frame_count,
        "default_height_m": args.height_a,
        "frames": output_frames,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
