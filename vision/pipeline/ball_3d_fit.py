#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


def load_json(path: Path):
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_homography(path: Path):
    data = load_json(path)
    h = data.get("homography_img_to_court")
    if h is None:
        raise SystemExit("homography_img_to_court missing in court.json")
    return h


def apply_homography(h, u, v):
    x = h[0][0] * u + h[0][1] * v + h[0][2]
    y = h[1][0] * u + h[1][1] * v + h[1][2]
    w = h[2][0] * u + h[2][1] * v + h[2][2]
    if w == 0:
        return 0.0, 0.0
    return x / w, y / w


def smooth(values, window=5):
    if window <= 1:
        return values
    half = window // 2
    out = []
    for i in range(len(values)):
        start = max(0, i - half)
        end = min(len(values), i + half + 1)
        segment = values[start:end]
        out.append(sum(segment) / len(segment))
    return out


def estimate_height(v_values, min_height=0.1, max_height=3.0):
    if not v_values:
        return []
    min_v = min(v_values)
    max_v = max(v_values)
    denom = max(max_v - min_v, 1e-6)

    heights = []
    for v in v_values:
        norm = (max_v - v) / denom
        z = min_height + norm * (max_height - min_height)
        heights.append(max(z, 0.05))
    return heights


def detect_bounces(z_values, fps, threshold=0.15):
    bounces = []
    for i in range(1, len(z_values) - 1):
        dz_prev = z_values[i] - z_values[i - 1]
        dz_next = z_values[i + 1] - z_values[i]
        if dz_prev < 0 and dz_next > 0 and z_values[i] < threshold:
            t = round(i / fps, 6)
            bounces.append({"frame": i, "t": t})
    return bounces


def detect_hits(xyz, fps, players):
    if not players:
        return []
    hits = []
    last_hit = -999
    min_gap = 5
    for i in range(1, len(xyz) - 1):
        v_prev = (
            xyz[i][0] - xyz[i - 1][0],
            xyz[i][1] - xyz[i - 1][1],
            xyz[i][2] - xyz[i - 1][2],
        )
        v_next = (
            xyz[i + 1][0] - xyz[i][0],
            xyz[i + 1][1] - xyz[i][1],
            xyz[i + 1][2] - xyz[i][2],
        )
        mag_prev = math.sqrt(sum(v * v for v in v_prev))
        mag_next = math.sqrt(sum(v * v for v in v_next))
        if mag_prev < 1e-6 or mag_next < 1e-6:
            continue

        dot = sum(v_prev[j] * v_next[j] for j in range(3))
        cos_angle = max(-1.0, min(1.0, dot / (mag_prev * mag_next)))
        angle = math.acos(cos_angle)
        if angle < math.radians(100):
            continue

        frame_players = players[i]
        if not frame_players:
            continue

        nearest = None
        nearest_dist = 999.0
        for pid, (px, py) in frame_players.items():
            dx = xyz[i][0] - px
            dy = xyz[i][1] - py
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = pid

        if nearest and nearest_dist < 1.6 and (i - last_hit) >= min_gap:
            hits.append({"frame": i, "t": round(i / fps, 6), "player": nearest})
            last_hit = i

    return hits


def load_players(players_path: Path, frame_count: int):
    if not players_path.exists():
        return None
    data = load_json(players_path)
    frames = data.get("frames", [])
    players_by_frame = []
    for i in range(frame_count):
        if i >= len(frames):
            players_by_frame.append({})
            continue
        frame = frames[i]
        mapping = {}
        for p in frame.get("players", []):
            mapping[p.get("id")] = (p.get("x", 0.0), p.get("y", 0.0))
        players_by_frame.append(mapping)
    return players_by_frame


def main():
    parser = argparse.ArgumentParser(description="Estimate ball 3D trajectory from ball_2d.json.")
    parser.add_argument("--ball-2d", default="../outputs/ball_2d.json", help="ball_2d.json path.")
    parser.add_argument("--court-json", default="../outputs/court.json", help="court.json path.")
    parser.add_argument("--players-json", default="../outputs/players.json", help="players.json path (optional).")
    parser.add_argument("--ball-output", default="../outputs/ball.json", help="Output ball.json path.")
    parser.add_argument("--events-output", default="../outputs/events.json", help="Output events.json path.")
    args = parser.parse_args()

    ball_2d = load_json(Path(args.ball_2d))
    frames = ball_2d.get("frames", [])
    if not frames:
        raise SystemExit("ball_2d.json has no frames")

    fps = int(ball_2d.get("fps", 30))
    frame_count = int(ball_2d.get("frame_count", len(frames)))
    frame_count = min(frame_count, len(frames))
    frames = frames[:frame_count]

    homography = load_homography(Path(args.court_json))

    u_values = []
    v_values = []
    for frame in frames:
        u_values.append(frame.get("u"))
        v_values.append(frame.get("v"))

    if all(v is None for v in v_values):
        raise SystemExit("ball_2d.json has no ball positions")

    heights = estimate_height([v for v in v_values if v is not None])
    if not heights:
        raise SystemExit("Failed to estimate heights")

    height_iter = iter(heights)
    z_raw = []
    for v in v_values:
        if v is None:
            z_raw.append(z_raw[-1] if z_raw else 0.2)
        else:
            z_raw.append(next(height_iter))

    z_smoothed = smooth(z_raw, window=5)

    output_frames = []
    xyz = []
    for i in range(frame_count):
        u = u_values[i]
        v = v_values[i]
        if u is None or v is None:
            x, y = (0.0, 0.0)
        else:
            x, y = apply_homography(homography, u, v)
        z = z_smoothed[i]
        xyz.append((x, y, z))
        output_frames.append(
            {
                "frame": i,
                "t": round(i / fps, 6),
                "x": round(x, 3),
                "y": round(y, 3),
                "z": round(z, 3),
            }
        )

    players_by_frame = load_players(Path(args.players_json), frame_count)
    bounces = detect_bounces(z_smoothed, fps)
    hits = detect_hits(xyz, fps, players_by_frame)

    ball_output = {"fps": fps, "frame_count": frame_count, "frames": output_frames}
    events_output = {"fps": fps, "hits": hits, "bounces": bounces}

    ball_path = Path(args.ball_output)
    ball_path.parent.mkdir(parents=True, exist_ok=True)
    with ball_path.open("w", encoding="utf-8") as f:
        json.dump(ball_output, f, indent=2)

    events_path = Path(args.events_output)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("w", encoding="utf-8") as f:
        json.dump(events_output, f, indent=2)

    print(f"Saved: {ball_path}")
    print(f"Saved: {events_path}")


if __name__ == "__main__":
    main()
