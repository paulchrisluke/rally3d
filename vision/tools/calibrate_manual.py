#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


COURT_HALF_WIDTH = 4.115
COURT_HALF_LENGTH = 11.885
NET_HEIGHT = 0.914
ROOT_DIR = Path(__file__).resolve().parents[2]
POINT_LABELS = [
    "near-left (singles)",
    "near-right (singles)",
    "far-right (singles)",
    "far-left (singles)",
]


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (ROOT_DIR / path).resolve()


def count_frames(frames_dir: Path) -> int:
    if not frames_dir.exists():
        return 0
    return len(list(frames_dir.glob("frame_*.jpg")))

def pick_default_frame(frames_dir: Path) -> Path:
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if not frames:
        raise SystemExit("No frames found. Provide --frame explicitly.")
    return frames[len(frames) // 2]


def draw_instructions(img, points):
    text = "Click singles corners clockwise: near-left -> near-right -> far-right -> far-left"
    cv2.putText(img, text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
    cv2.putText(img, text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    text2 = "Near = bottom of image. Use inner (singles) sidelines."
    cv2.putText(img, text2, (20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
    cv2.putText(img, text2, (20, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    next_label = POINT_LABELS[len(points)] if len(points) < len(POINT_LABELS) else "done"
    text3 = f"Next click: {next_label}"
    cv2.putText(img, text3, (20, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
    cv2.putText(img, text3, (20, 82), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    for idx, (x, y) in enumerate(points):
        cv2.circle(img, (int(x), int(y)), 6, (0, 255, 0), -1)
        cv2.putText(img, str(idx + 1), (int(x) + 8, int(y) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
        cv2.putText(img, str(idx + 1), (int(x) + 8, int(y) - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)


def main():
    parser = argparse.ArgumentParser(description="Manual court calibration tool.")
    parser.add_argument("--frame", default=None, help="Path to a representative frame (relative to repo root).")
    parser.add_argument("--frames-dir", default="frames", help="Frames dir for frame_count/default frame (relative to repo root).")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second.")
    parser.add_argument("--frame-count", type=int, default=None, help="Override frame count.")
    parser.add_argument("--output", default="vision/outputs/court.json", help="Output court.json path (relative to repo root).")
    args = parser.parse_args()

    frames_dir = resolve_path(args.frames_dir)
    frame_path = resolve_path(args.frame) if args.frame else pick_default_frame(frames_dir)
    if not frame_path.exists():
        raise SystemExit(f"Frame not found: {frame_path}")

    print("Manual calibration: click singles court corners clockwise.")
    print("Order: near-left -> near-right -> far-right -> far-left.")
    print("Near = bottom of image. Use inner (singles) sidelines.")
    print("Press ESC to cancel.")

    frame = cv2.imread(str(frame_path))
    if frame is None:
        raise SystemExit(f"Failed to read frame: {frame_path}")

    points_img = []

    def on_mouse(event, x, y, _flags, _param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points_img) < 4:
            points_img.append((x, y))

    window = "rally3d manual calibration"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, on_mouse)

    while True:
        display = frame.copy()
        draw_instructions(display, points_img)
        cv2.imshow(window, display)
        key = cv2.waitKey(20) & 0xFF
        if key == 27:  # ESC
            cv2.destroyAllWindows()
            raise SystemExit("Calibration cancelled.")
        if len(points_img) >= 4:
            break

    cv2.destroyAllWindows()

    points_img_np = np.array(points_img, dtype=np.float32)
    points_court = np.array(
        [
            [-COURT_HALF_WIDTH, -COURT_HALF_LENGTH],
            [COURT_HALF_WIDTH, -COURT_HALF_LENGTH],
            [COURT_HALF_WIDTH, COURT_HALF_LENGTH],
            [-COURT_HALF_WIDTH, COURT_HALF_LENGTH],
        ],
        dtype=np.float32,
    )

    homography = cv2.getPerspectiveTransform(points_img_np, points_court)

    frame_count = args.frame_count
    if frame_count is None:
        frame_count = count_frames(frames_dir)

    output = {
        "fps": int(args.fps),
        "frame_count": int(frame_count),
        "coordinate_system": {
            "origin": "net_center",
            "axes": {
                "x": "right_sideline",
                "y": "toward_far_baseline",
                "z": "up",
            },
            "units": "meters",
        },
        "court_dims_m": {
            "half_width_singles": COURT_HALF_WIDTH,
            "half_length": COURT_HALF_LENGTH,
            "net_height": NET_HEIGHT,
        },
        "homography_img_to_court": homography.tolist(),
    }

    output_path = resolve_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
