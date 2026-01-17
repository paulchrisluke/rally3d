# rally3d

MVP pipeline + viewer to replay a single tennis rally in simplified 3D.

## What's here

- `rally3d_build_plan.md` and `BUILD_PLAN.md`: project plan and specs
- `vision/`: scripts/tools/pipeline for calibration and tracking
- `viewer/`: Three.js viewer (Vite)

## Quick start (viewer with sample data)

```bash
cd viewer
npm install
npm run dev
```

Then open the local dev URL printed by Vite.

## Pipeline notes

The vision pipeline is intentionally lightweight and modular. Manual court
calibration and overlay validation are implemented; detection/tracking stages are
stubbed and ready to be wired to your preferred models.

### Download + frames

```bash
cd vision/scripts
./00_download_clip.sh
./01_extract_frames.sh
```

### Manual court calibration

```bash
cd ../tools
python calibrate_manual.py --frame ../frames/frame_00120.jpg
python validate_overlay.py --frame ../frames/frame_00120.jpg
```

Outputs are written to `vision/outputs/` and can be copied to
`viewer/public/data/`.

## Data format

All JSON outputs follow the per-frame timeline contract in the build plan.

## License

MIT
