#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import cv2

LABELS = [
    ("A", (70, 120, 255)),
    ("B", (255, 120, 120)),
    ("ball", (0, 220, 220)),
]


def load_frames(frames_dir: Path):
    frames = sorted(frames_dir.glob("frame_*.jpg"))
    if not frames:
        raise SystemExit(f"No frames found in {frames_dir}")
    return frames


def load_existing(output_path: Path, frame_count: int):
    if not output_path.exists():
        return [{"frame": i, "A": None, "B": None, "ball": None} for i in range(frame_count)]
    with output_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    frames = data.get("frames", [])
    if len(frames) != frame_count:
        return [{"frame": i, "A": None, "B": None, "ball": None} for i in range(frame_count)]
    return frames


def save_annotations(output_path: Path, fps: int, frame_count: int, frames):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "fps": fps,
        "frame_count": frame_count,
        "frames": frames,
    }
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def draw_overlay(img, frame_index, frame_count, active_label, frame_data, frame_path):
    cv2.putText(
        img,
        f"Frame {frame_index + 1}/{frame_count}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 0, 0),
        4,
    )
    cv2.putText(
        img,
        f"Frame {frame_index + 1}/{frame_count}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        1,
    )

    label_text = active_label if active_label else "none"
    cv2.putText(
        img,
        f"Active: {label_text}",
        (20, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        3,
    )
    cv2.putText(
        img,
        f"Active: {label_text}",
        (20, 58),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (255, 255, 255),
        1,
    )

    instructions = "1=A 2=B 3=ball | n/p next/prev | c clear | s save | q quit"
    cv2.putText(img, instructions, (20, img.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
    cv2.putText(img, instructions, (20, img.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    cv2.putText(img, str(frame_path.name), (20, img.shape[0] - 46), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
    cv2.putText(img, str(frame_path.name), (20, img.shape[0] - 46), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    for label, color in LABELS:
        point = frame_data.get(label)
        if point:
            x, y = int(point[0]), int(point[1])
            cv2.circle(img, (x, y), 6, color, -1)
            cv2.putText(img, label, (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3)
            cv2.putText(img, label, (x + 8, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)


def main():
    parser = argparse.ArgumentParser(description="Annotate player/ball points per frame.")
    parser.add_argument("--frames-dir", default="../frames", help="Directory with frame_*.jpg files.")
    parser.add_argument("--output", default="../annotations/points.json", help="Output annotation JSON.")
    parser.add_argument("--fps", type=int, default=30, help="Frames per second.")
    args = parser.parse_args()

    frames_dir = Path(args.frames_dir)
    frames = load_frames(frames_dir)
    frame_count = len(frames)
    frames_data = load_existing(Path(args.output), frame_count)

    current_index = 0
    active_label = None

    def on_mouse(event, x, y, _flags, _param):
        nonlocal frames_data, active_label
        if event == cv2.EVENT_LBUTTONDOWN and active_label:
            frames_data[current_index][active_label] = [int(x), int(y)]

    window = "rally3d annotation"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window, on_mouse)

    while True:
        frame_path = frames[current_index]
        frame = cv2.imread(str(frame_path))
        if frame is None:
            raise SystemExit(f"Failed to read frame: {frame_path}")

        display = frame.copy()
        draw_overlay(display, current_index, frame_count, active_label, frames_data[current_index], frame_path)
        cv2.imshow(window, display)

        key = cv2.waitKey(20) & 0xFF
        if key == 27 or key == ord("q"):
            save_annotations(Path(args.output), args.fps, frame_count, frames_data)
            break
        if key == ord("s"):
            save_annotations(Path(args.output), args.fps, frame_count, frames_data)
        elif key == ord("n"):
            current_index = min(current_index + 1, frame_count - 1)
        elif key == ord("p"):
            current_index = max(current_index - 1, 0)
        elif key == ord("c"):
            frames_data[current_index] = {"frame": current_index, "A": None, "B": None, "ball": None}
        elif key == ord("1"):
            active_label = "A"
        elif key == ord("2"):
            active_label = "B"
        elif key == ord("3"):
            active_label = "ball"

    cv2.destroyAllWindows()
    print(f"Saved annotations to: {args.output}")


if __name__ == "__main__":
    main()
