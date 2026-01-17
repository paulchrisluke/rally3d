#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path


COURT_HALF_WIDTH = 4.115
COURT_HALF_LENGTH = 11.885
NET_HEIGHT = 0.914


def make_court_json(fps: int, frame_count: int):
    return {
        "fps": fps,
        "frame_count": frame_count,
        "coordinate_system": {
            "origin": "net_center",
            "axes": {"x": "right_sideline", "y": "toward_far_baseline", "z": "up"},
            "units": "meters",
        },
        "court_dims_m": {
            "half_width_singles": COURT_HALF_WIDTH,
            "half_length": COURT_HALF_LENGTH,
            "net_height": NET_HEIGHT,
        },
        "homography_img_to_court": [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
    }


def make_players_json(fps: int, frame_count: int):
    dt = 1.0 / fps
    frames = []
    for i in range(frame_count):
        t = i * dt
        a_x = 1.5 * math.sin(t * 1.4)
        a_y = -7.0 + 0.6 * math.sin(t * 0.9)
        b_x = -1.2 * math.cos(t * 1.1)
        b_y = 7.0 + 0.6 * math.cos(t * 0.8)
        frames.append(
            {
                "frame": i,
                "t": round(t, 6),
                "players": [
                    {"id": "A", "x": round(a_x, 3), "y": round(a_y, 3), "height": 1.8},
                    {"id": "B", "x": round(b_x, 3), "y": round(b_y, 3), "height": 1.85},
                ],
            }
        )
    return {
        "fps": fps,
        "frame_count": frame_count,
        "default_height_m": 1.8,
        "frames": frames,
    }


def make_ball_json(fps: int, frame_count: int):
    dt = 1.0 / fps
    frames = []
    half = frame_count // 2
    for i in range(frame_count):
        t = i * dt
        if i <= half:
            phase = i / max(1, half)
            x = 1.2 * math.sin(phase * math.pi)
            y = -6.0 + 12.0 * phase
            z = 0.4 + 2.2 * math.sin(phase * math.pi)
        else:
            j = i - half
            phase = j / max(1, frame_count - half - 1)
            x = -1.0 * math.sin(phase * math.pi)
            y = 6.0 - 12.0 * phase
            z = 0.4 + 2.0 * math.sin(phase * math.pi)
        frames.append(
            {
                "frame": i,
                "t": round(t, 6),
                "x": round(x, 3),
                "y": round(y, 3),
                "z": round(max(z, 0.05), 3),
            }
        )
    return {"fps": fps, "frame_count": frame_count, "frames": frames}


def make_events_json(fps: int, frame_count: int):
    dt = 1.0 / fps
    hits = [
        {"frame": 0, "t": 0.0, "player": "A"},
        {"frame": frame_count // 2, "t": round((frame_count // 2) * dt, 6), "player": "B"},
    ]
    bounces = [
        {"frame": frame_count // 4, "t": round((frame_count // 4) * dt, 6)},
        {"frame": (3 * frame_count) // 4, "t": round(((3 * frame_count) // 4) * dt, 6)},
    ]
    return {"fps": fps, "hits": hits, "bounces": bounces}


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Generate sample JSON outputs for the viewer.")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--frame-count", type=int, default=120)
    parser.add_argument("--output-dir", default="../outputs")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    fps = int(args.fps)
    frame_count = int(args.frame_count)

    write_json(output_dir / "court.json", make_court_json(fps, frame_count))
    write_json(output_dir / "players.json", make_players_json(fps, frame_count))
    write_json(output_dir / "ball.json", make_ball_json(fps, frame_count))
    write_json(output_dir / "events.json", make_events_json(fps, frame_count))

    print(f"Wrote sample data to: {output_dir}")


if __name__ == "__main__":
    main()
