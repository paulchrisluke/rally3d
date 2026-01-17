#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import cv2
import numpy as np


COURT_HALF_WIDTH = 4.115
COURT_HALF_LENGTH = 11.885
SERVICE_LINE = 6.40
ROOT_DIR = Path(__file__).resolve().parents[2]


def resolve_path(path_str: str) -> Path:
    path = Path(path_str)
    if path.is_absolute():
        return path
    return (ROOT_DIR / path).resolve()


def load_homography(court_json_path: Path) -> np.ndarray:
    with court_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return np.array(data["homography_img_to_court"], dtype=np.float64)


def court_lines():
    return [
        [(-COURT_HALF_WIDTH, -COURT_HALF_LENGTH), (COURT_HALF_WIDTH, -COURT_HALF_LENGTH)],
        [(-COURT_HALF_WIDTH, COURT_HALF_LENGTH), (COURT_HALF_WIDTH, COURT_HALF_LENGTH)],
        [(-COURT_HALF_WIDTH, -COURT_HALF_LENGTH), (-COURT_HALF_WIDTH, COURT_HALF_LENGTH)],
        [(COURT_HALF_WIDTH, -COURT_HALF_LENGTH), (COURT_HALF_WIDTH, COURT_HALF_LENGTH)],
        [(-COURT_HALF_WIDTH, -SERVICE_LINE), (COURT_HALF_WIDTH, -SERVICE_LINE)],
        [(-COURT_HALF_WIDTH, SERVICE_LINE), (COURT_HALF_WIDTH, SERVICE_LINE)],
        [(0.0, -SERVICE_LINE), (0.0, SERVICE_LINE)],
        [(-COURT_HALF_WIDTH, 0.0), (COURT_HALF_WIDTH, 0.0)],
    ]


def main():
    parser = argparse.ArgumentParser(description="Overlay court lines for calibration validation.")
    parser.add_argument("--frame", default=None, help="Frame to draw overlay on (relative to repo root).")
    parser.add_argument("--frames-dir", default="frames", help="Frames dir for default frame (relative to repo root).")
    parser.add_argument("--court-json", default="vision/outputs/court.json", help="Path to court.json (relative to repo root).")
    parser.add_argument("--output", default=None, help="Optional output image path.")
    args = parser.parse_args()

    frames_dir = resolve_path(args.frames_dir)
    if args.frame:
        frame_path = resolve_path(args.frame)
    else:
        frames = sorted(frames_dir.glob("frame_*.jpg"))
        if not frames:
            raise SystemExit("No frames found. Provide --frame explicitly.")
        frame_path = frames[len(frames) // 2]
    if not frame_path.exists():
        raise SystemExit(f"Frame not found: {frame_path}")

    frame = cv2.imread(str(frame_path))
    if frame is None:
        raise SystemExit(f"Failed to read frame: {frame_path}")

    court_json_path = resolve_path(args.court_json)
    if not court_json_path.exists():
        raise SystemExit(f"Court JSON not found: {court_json_path}")

    h_img_to_court = load_homography(court_json_path)
    h_court_to_img = np.linalg.inv(h_img_to_court)

    overlay = frame.copy()
    for line in court_lines():
        pts = np.array(line, dtype=np.float32).reshape(-1, 1, 2)
        img_pts = cv2.perspectiveTransform(pts, h_court_to_img)
        p1 = tuple(img_pts[0, 0].astype(int))
        p2 = tuple(img_pts[1, 0].astype(int))
        cv2.line(overlay, p1, p2, (0, 255, 0), 2)

    blended = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

    if args.output:
        out_path = resolve_path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if cv2.imwrite(str(out_path), blended):
            print(f"Saved overlay: {out_path}")
        else:
            raise SystemExit(f"Failed to write image: {out_path}")
    else:
        window = "rally3d court overlay"
        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.imshow(window, blended)
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
