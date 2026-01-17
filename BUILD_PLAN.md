# rally3d — MVP Build Plan

## 0. MVP Goal

**Input:** 8-second tennis rally clip (8:28–8:36) from broadcast video  
**Source:** https://youtu.be/UnwYdF8a5ws?si=3Sky_1LbEt_GhibJ  
**Output:** A Three.js web viewer that replays the rally in a simplified 3D court with a free/orbit camera and timeline scrub.

**Hard constraints**

* Single rally (8:28–8:36)
* Single camera segment (handle cuts by splitting if needed)
* Simplified 3D: flat court, capsule/cylinder players, sphere ball
* "Believable" > "perfectly accurate"

---

## 1. Coordinate System (Must be explicit)

Define a single world coordinate system used by all exported JSON:

* Court plane is **Z = 0**
* **Origin (0,0,0)** = **net center**
* **+X** = toward the **right sideline** (from near-side player POV)
* **+Y** = toward the **far baseline**
* **+Z** = up

Court dimensions are real tennis values (singles) in meters:

* Net-to-baseline = 11.885 m
* Singles sideline half-width = 4.115 m

---

## 2. Inputs & Outputs

### Input artifacts

* `rally.mp4` (8 seconds, extracted from YouTube)
* `frames/frame_%05d.jpg` extracted at 30 FPS

### Output artifacts (to `vision/outputs/`)

* `court.json`
* `players.json`
* `ball.json`
* `events.json` (optional but recommended)

All outputs must share:

* `fps: 30`
* `frame_count: N`
* **A full per-frame timeline** (see Section 6)

---

## 3. Repository Layout

```
rally3d/
  README.md
  BUILD_PLAN.md (this file)
  vision/
    scripts/
      00_download_clip.sh
      01_extract_frames.sh
    tools/
      calibrate_manual.py
      validate_overlay.py
    pipeline/
      court_calib_auto.py
      court_calib_manual.py
      player_detect_pose.py
      player_track.py
      ball_detect.py
      ball_track.py
      ball_3d_fit.py
      export_json.py
    outputs/
      court.json
      players.json
      ball.json
      events.json
  viewer/
    public/
      data/   (copy outputs here)
    src/
      main.js
      scene/
        court.js
        players.js
        ball.js
      ui/
        timeline.js
    package.json
    vite.config.js
```

---

## 4. Video Preprocessing

### 4.1 Clip extraction

Download and extract rally segment:

```bash
# Using yt-dlp
yt-dlp -f "bestvideo[ext=mp4]" --download-sections "*8:28-8:36" \
  "https://youtu.be/UnwYdF8a5ws" -o "rally.mp4"
```

### 4.2 Frame extraction

Extract frames at fixed FPS = 30:

```bash
ffmpeg -i rally.mp4 -vf fps=30 frames/frame_%05d.jpg
```

Ensure deterministic naming and consistent frame count (should be ~240 frames for 8 seconds).

---

## 5. Court Calibration (Anchor Module)

### 5.1 Automatic mode (default)

**Goal:** Compute homography mapping **image pixels → court plane (X,Y)**.

**Approach:**

* Detect court lines (Canny edge detection + Hough line transform)
* Match detected lines to known court template (baselines, sidelines, service lines)
* Estimate homography `H_img_to_court` using line correspondences
* Temporal smoothing: homography should not jitter between frames
* If camera is static (likely for this clip), use single homography for all frames

**Implementation notes:**

* Use OpenCV's `cv2.findHomography()` with RANSAC
* Court template: singles court with known dimensions
* May need to adjust for doubles court lines (ignore outer sidelines)

### 5.2 Manual fallback (required)

Because broadcast footage can be brittle, implement manual calibration tool.

**Manual UI tool (`calibrate_manual.py`):**

* Show a representative frame (middle of rally)
* User clicks **4 known points** in order:
  1. Near-left singles corner (baseline-sideline intersection)
  2. Near-right singles corner
  3. Far-right singles corner
  4. Far-left singles corner

* Map these to world coordinates:
  * (-4.115, -11.885, 0)
  * (+4.115, -11.885, 0)
  * (+4.115, +11.885, 0)
  * (-4.115, +11.885, 0)

* Compute homography from these correspondences
* Save to `court.json`

### 5.3 Validation overlay (required)

**Tool:** `validate_overlay.py`

* Load homography
* Draw projected court lines back onto the frame
* Display overlaid image for visual verification
* If overlay is visually aligned, calibration is acceptable

### Output: `court.json`

```json
{
  "fps": 30,
  "frame_count": 240,
  "coordinate_system": {
    "origin": "net_center",
    "axes": { 
      "x": "right_sideline", 
      "y": "toward_far_baseline", 
      "z": "up" 
    },
    "units": "meters"
  },
  "court_dims_m": { 
    "half_width_singles": 4.115, 
    "half_length": 11.885,
    "net_height": 0.914
  },
  "homography_img_to_court": [
    [h00, h01, h02],
    [h10, h11, h12],
    [h20, h21, h22]
  ]
}
```

If calibration changes mid-clip due to zoom/cut: split into segments and export one homography per segment with frame ranges.

---

## 6. Timeline & Sync Contract (Non-negotiable)

To keep the viewer simple: **every output JSON must have per-frame samples**.

**Define:**

* `dt = 1 / fps = 0.033333...` seconds
* For frame index `i` in `[0..N-1]`, timestamp `t = i * dt`

**Requirement:** `players.json` and `ball.json` must include entries for *all* frames.

If detection fails on a frame, fill with:

* Interpolated values (linear for position, slerp for orientation), or
* Last-known + smoothing, or
* Explicit `null` with viewer-side interpolation

**Best MVP approach:** Always export filled values using interpolation.

---

## 7. Player Detection & Tracking

### 7.1 Detect + pose

**Recommended approach:**

* Use a pose estimation model (e.g., MediaPipe Pose, OpenPose, or YOLOv8-pose)
* Extract full skeleton keypoints, focusing on:
  * Ankles/feet for ground contact
  * Center of mass for body position
  * Optional: racket hand for hit detection

**Alternative (simpler):**

* Use person detector (YOLOv8) for bounding boxes
* Approximate footpoint as bottom-center of bbox

### 7.2 Track identities

**Goal:** Maintain consistent IDs `A` and `B` across frames.

**Approach:**

* Frame 0: Detect two players, assign IDs based on court position
  * Player A = near-side (smaller Y value)
  * Player B = far-side (larger Y value)
* Subsequent frames: Match detections using:
  * IoU (Intersection over Union) of bboxes
  * Distance in court coordinates (after projection)
  * Kalman filter for motion prediction
  * Hungarian algorithm for assignment

**Handle occlusions:**

* If only one player detected, use motion prediction for missing player
* Interpolate positions during brief occlusions (1-3 frames)

### 7.3 Project to court plane (cheap 3D)

**Steps:**

1. Extract foot contact point from pose (lowest ankle/foot keypoint)
2. Convert pixel footpoint → court (X,Y) using homography from `court.json`
3. Smooth trajectories using moving average or Kalman filter
4. Z-coordinate is always 0 (feet on ground)
5. Estimate player height from pose (distance from feet to head in pixels, scale using known court dimensions)

### Output: `players.json`

```json
{
  "fps": 30,
  "frame_count": 240,
  "default_height_m": 1.8,
  "frames": [
    {
      "frame": 0,
      "t": 0.0,
      "players": [
        {
          "id": "A",
          "x": 2.3,
          "y": -6.1,
          "height": 1.80
        },
        {
          "id": "B",
          "x": 1.2,
          "y": 7.4,
          "height": 1.85
        }
      ]
    },
    {
      "frame": 1,
      "t": 0.0333,
      "players": [...]
    }
  ]
}
```

**Note:** Players' Z-coordinate is implied (base at Z=0). Viewer uses `height` to scale cylinder geometry.

---

## 8. Ball Detection & Tracking

### 8.1 Detection strategy (MVP: hybrid)

Use a staged approach; start simple and upgrade only if needed.

**Stage 1 (fast baseline):**

* **Motion-based candidate extraction:**
  * Frame differencing or optical flow magnitude
  * Threshold to find fast-moving objects
* **Constrain search region:**
  * Within court area mask (from calibration)
  * Near last-known ball position (if tracking)
  * Height range in image (ball won't be at top of frame)
* **Filter candidates:**
  * Size constraint (tennis ball ~65mm diameter, scale based on court depth)
  * Circularity/roundness
  * Color filter (tennis ball is typically yellow-green)
  * High contrast against background

**Stage 2 (if Stage 1 fails often):**

* Use lightweight detector (YOLOv8-nano) trained/fine-tuned for tennis ball
* Still keep motion prior + search window to reduce false positives
* Consider TrackNet or similar sports ball tracking models

**MVP Recommendation:** Start with Stage 1. Only implement Stage 2 if detection rate < 70%.

### 8.2 Tracking

**Approach:**

* Kalman filter on (u,v) image coordinates
* Predict next position based on velocity
* Associate detections with predictions using nearest-neighbor + distance threshold
* Bridge gaps with interpolation (up to 5 frames)
* Optional: Re-detect when confidence drops or prediction error is high

**Handle missed detections:**

* Short gaps (1-5 frames): Linear interpolation
* Long gaps: Flag for manual review or trajectory fitting

### 8.3 Output: `ball_2d.json` (internal, optional)

Not required by viewer; used for debugging and 3D fitting.

```json
{
  "fps": 30,
  "frame_count": 240,
  "frames": [
    {
      "frame": 0,
      "t": 0.0,
      "u": 412,
      "v": 218,
      "confidence": 0.95
    }
  ]
}
```

---

## 9. Ball 3D Reconstruction (Believable, constrained)

**Goal:** Produce per-frame (x, y, z) in world coordinates.

### 9.1 Convert 2D to court-plane XY

**When ball is on/near ground (bounce):**

* Use homography to project (u,v) → (x,y) on court plane
* This gives XY anchor points

**When ball is airborne:**

* XY position is less certain (no ground constraint)
* Use trajectory fitting to estimate XY based on physics

### 9.2 Height inference

**Approach: Fit piecewise parabolic arcs under gravity**

1. **Segment trajectory by events:**
   * **Bounce:** Ball approaches z=0, then reverses vertical velocity
   * **Hit:** Direction change + proximity to player position

2. **For each segment (between events):**
   * Fit parabolic trajectory under gravity (g = 9.81 m/s²)
   * Constrain:
     * z ≥ 0 (ball can't go underground)
     * Realistic peak height (< 5m for tennis)
     * Smooth velocity (no instantaneous jumps except at hits)
     * Ball must pass near player position at hit events

3. **Optimization:**
   * Use least-squares fitting for parabola coefficients
   * Anchor points from homography when ball is near ground
   * Enforce continuity at segment boundaries (except hits)

**Physics constraints:**

* Launch angle typically 10-30° for groundstrokes
* Ball speed typically 15-35 m/s
* Bounce damping factor ~0.7-0.8 (energy loss)

### Output: `ball.json`

```json
{
  "fps": 30,
  "frame_count": 240,
  "frames": [
    {
      "frame": 0,
      "t": 0.000,
      "x": 1.9,
      "y": -2.2,
      "z": 1.1
    },
    {
      "frame": 1,
      "t": 0.033,
      "x": 2.1,
      "y": -1.8,
      "z": 1.3
    }
  ]
}
```

---

## 10. Events (Optional but recommended)

**Infer:**

* **Hits:** Ball direction changes + near player position
* **Bounces:** z near 0 + vertical velocity sign flip

**Detection logic:**

* **Bounce detection:**
  * z < 0.1 m
  * Previous frame: dz/dt < 0 (falling)
  * Next frame: dz/dt > 0 (rising)

* **Hit detection:**
  * Distance from ball to player < 1.5 m
  * Significant change in ball velocity direction (> 90°)
  * Optional: Ball is within racket swing zone

### Output: `events.json`

```json
{
  "fps": 30,
  "hits": [
    {"frame": 13, "t": 0.43, "player": "A"},
    {"frame": 65, "t": 2.18, "player": "B"}
  ],
  "bounces": [
    {"frame": 34, "t": 1.12}
  ]
}
```

---

## 11. Three.js Viewer

### 11.1 Scene Components

**Court:**

* Flat rectangle mesh at Z=0
* Green texture or solid color
* White line markings (baselines, sidelines, service lines, net line)
* Net: Thin vertical plane at Y=0, height 0.914m

**Players:**

* **Geometry:** CylinderGeometry (body) + SphereGeometry (head)
  * Cylinder: radius 0.3m, height from player data
  * Sphere: radius 0.15m, positioned at top of cylinder
* **Material:** Simple colored material (Player A = blue, Player B = red)
* **Position:** Updated each frame from `players.json`

**Ball:**

* SphereGeometry, radius 0.033m (tennis ball)
* Yellow material
* Position updated each frame from `ball.json`

### 11.2 Playback System

**Data loading:**

```javascript
// Load all JSON files
const courtData = await fetch('/data/court.json').then(r => r.json());
const playersData = await fetch('/data/players.json').then(r => r.json());
const ballData = await fetch('/data/ball.json').then(r => r.json());
const eventsData = await fetch('/data/events.json').then(r => r.json());
```

**Frame management:**

```javascript
let currentFrame = 0;
const totalFrames = playersData.frame_count;
const fps = playersData.fps;

function updateScene(frameIndex) {
  // Update player positions
  const frameData = playersData.frames[frameIndex];
  frameData.players.forEach(p => {
    updatePlayer(p.id, p.x, p.y, p.height);
  });
  
  // Update ball position
  const ballFrame = ballData.frames[frameIndex];
  updateBall(ballFrame.x, ballFrame.y, ballFrame.z);
}
```

**Animation loop:**

```javascript
let isPlaying = false;
let lastTime = 0;

function animate(time) {
  requestAnimationFrame(animate);
  
  if (isPlaying) {
    const deltaTime = (time - lastTime) / 1000;
    lastTime = time;
    
    currentFrame += deltaTime * fps;
    if (currentFrame >= totalFrames) {
      currentFrame = 0; // Loop or pause
    }
    
    updateScene(Math.floor(currentFrame));
  }
  
  renderer.render(scene, camera);
}
```

### 11.3 Controls

**Camera:**

* OrbitControls (Three.js addon)
* Initial position: Offset from court, looking at net center
* Constrain: Don't allow camera to go below ground (min polar angle)

**Timeline:**

* HTML range input slider
* Value: 0 to totalFrames-1
* On input: Update currentFrame and call updateScene()
* Display current time in seconds

**Play/Pause:**

* Button to toggle isPlaying state
* Keyboard shortcut: Space bar

**Event Markers (optional):**

* Visual markers on timeline for hits and bounces
* Click marker to jump to that frame

### 11.4 UI Layout

```html
<div id="viewer">
  <canvas id="three-canvas"></canvas>
  <div id="controls">
    <button id="play-pause">Play</button>
    <input type="range" id="timeline" min="0" max="239" value="0">
    <span id="time-display">0.00s / 8.00s</span>
  </div>
</div>
```

---

## 12. Build Order (Critical Path)

Follow this sequence strictly:

1. **Extract clip + frames**
   * Download rally from YouTube (8:28-8:36)
   * Extract frames at 30 FPS
   * Verify frame count (~240 frames)

2. **Court calibration (automatic)**
   * Implement line detection
   * Compute homography
   * Test on middle frame

3. **Manual calibration fallback tool**
   * Build UI for clicking points
   * Generate homography from manual points
   * Save to `court.json`

4. **Validation overlay tool**
   * Load homography
   * Draw court lines on frame
   * Verify alignment visually

5. **Player detect + track**
   * Run pose estimation on all frames
   * Track two players (A and B)
   * Project to court coordinates
   * Export `players.json`

6. **Ball detect + track (2D)**
   * Detect ball in each frame
   * Track across frames
   * Export `ball_2d.json` (internal)

7. **Ball 3D trajectory fitting**
   * Infer events (hits, bounces)
   * Fit parabolic arcs
   * Export `ball.json`
   * Export `events.json`

8. **Viewer: Static scene**
   * Set up Three.js
   * Render court mesh
   * Place two player cylinders
   * Place ball sphere
   * No animation yet

9. **Viewer: Animation**
   * Load JSON data
   * Implement frame update logic
   * Add play/pause

10. **Viewer: Timeline + camera**
    * Add timeline scrubber
    * Wire up OrbitControls
    * Add event markers (optional)

---

## 13. Acceptance Test (Ship Criteria)

Before declaring MVP complete, verify:

✅ **Video preprocessing**
   * 240 frames extracted at 30 FPS
   * Frames are clear and sequential

✅ **Court calibration**
   * Validation overlay shows accurate line alignment
   * Manual calibration tool works as fallback

✅ **Player tracking**
   * Both players detected in all frames
   * IDs remain consistent (no swapping)
   * Positions look correct on court
   * Movement is smooth (no jitter)

✅ **Ball tracking**
   * Ball detected in >80% of frames
   * Trajectory is continuous (interpolation works)
   * 3D arc is believable (no underground, no crazy spikes)

✅ **Viewer functionality**
   * Open `viewer/` in browser
   * Press play → players + ball move smoothly for full 8 seconds
   * Drag timeline → scene updates **frame-accurately**
   * Orbit camera → court stays stable/oriented, objects remain on court
   * Ball trajectory passes near players at hit events

✅ **Visual quality**
   * Court is correctly scaled and oriented
   * Players move realistically
   * Ball arc looks natural
   * No obvious glitches or artifacts

---

## 14. Technology Stack

**Vision Pipeline:**

* Python 3.10+
* OpenCV (cv2) for image processing
* NumPy for numerical operations
* MediaPipe or YOLOv8 for pose/object detection
* SciPy for trajectory optimization
* Matplotlib for visualization/debugging

**Viewer:**

* Three.js r128+ (use latest stable, r150+ recommended for better features)
* Vite for dev server and bundling
* Vanilla JavaScript (or TypeScript if preferred)
* OrbitControls from three/examples/jsm/controls/OrbitControls

---

## 15. Implementation Recommendations

### Court Calibration

**Simplest approach:**
1. Try automatic line detection first
2. If fails, use manual tool immediately
3. Don't spend hours tuning automatic method

**Manual tool UI:**
```python
import cv2
import numpy as np

# Load middle frame
frame = cv2.imread('frames/frame_00120.jpg')

# Display and collect clicks
points_img = []  # Will store 4 clicked points
points_court = np.array([
    [-4.115, -11.885],
    [4.115, -11.885],
    [4.115, 11.885],
    [-4.115, 11.885]
], dtype=np.float32)

# OpenCV window + mouse callback
# User clicks 4 corners in order
# Compute homography: cv2.getPerspectiveTransform(points_img, points_court)
```

### Ball Detection

**Start with this simple approach:**

```python
# For each frame
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# Yellow-green color mask
lower = np.array([25, 50, 50])
upper = np.array([35, 255, 255])
mask = cv2.inRange(hsv, lower, upper)

# Find circles
circles = cv2.HoughCircles(mask, cv2.HOUGH_GRADIENT, 1, 20,
                          param1=50, param2=15,
                          minRadius=3, maxRadius=20)

# Pick best candidate (closest to predicted position)
```

If this doesn't work well, switch to YOLOv8 trained on tennis balls.

### Ball 3D Fitting

**Simplified approach:**

1. Detect bounces where z is minimum
2. Detect hits from player proximity and velocity change
3. For each segment between events:
   ```python
   # Fit: z(t) = z0 + v0*t - 0.5*g*t^2
   # Where z0 = initial height, v0 = initial vertical velocity
   # Minimize error to 2D detections projected via homography
   ```

### Three.js Player Geometry

Since CapsuleGeometry may not be available:

```javascript
function createPlayer(height, color) {
  const group = new THREE.Group();
  
  // Body (cylinder)
  const bodyGeometry = new THREE.CylinderGeometry(0.3, 0.3, height * 0.8);
  const bodyMaterial = new THREE.MeshPhongMaterial({ color });
  const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
  body.position.y = height * 0.4; // Raise to sit on ground
  group.add(body);
  
  // Head (sphere)
  const headGeometry = new THREE.SphereGeometry(0.15);
  const head = new THREE.Mesh(headGeometry, bodyMaterial);
  head.position.y = height * 0.9;
  group.add(head);
  
  return group;
}
```

---

## 16. Explicit Non-Goals

**Out of scope for MVP:**

* ❌ Photorealistic humans (stick figures/capsules are fine)
* ❌ Full match coverage (just one rally)
* ❌ True free-viewpoint/NeRF rendering
* ❌ Multi-camera fusion
* ❌ Robustness across all broadcasts
* ❌ Real-time processing
* ❌ Mobile optimization
* ❌ VR/AR support
* ❌ Replay from any angle (limited orbit range is fine)

---

## 17. Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Ball detection fails | High | Manual annotation tool for ball positions |
| Camera zoom/movement | Medium | Use per-frame homography or split into segments |
| Player occlusion | Medium | Temporal interpolation, use last known position |
| Broadcast cuts | High | Detect cuts, split rally if needed |
| Court line visibility | Medium | Manual calibration fallback |
| Ball leaves frame | Low | Flag frames, interpolate trajectory |

---

## 18. Success Metrics

**Quantitative:**

* Player detection rate: >95%
* Ball detection rate: >80%
* Court alignment error: <10 pixels RMSE
* Processing time: <10 minutes for full pipeline
* Viewer FPS: >30 on modern laptop

**Qualitative:**

* "Does it look believable?"
* "Can I follow the rally?"
* "Does the 3D perspective help me understand the play?"

---

## 19. Future Extensions (Post-MVP)

Ideas for v2:

* Multiple rallies stitched together
* Player skeleton animation (not just capsules)
* Racket detection and swing analysis
* Ball spin visualization
* Shot speed and trajectory metrics
* Compare different camera angles
* Export to video file
* Other sports (volleyball, badminton, table tennis)

---

## 20. Getting Started

### Quick Start Commands

```bash
# 1. Set up repository
git clone <your-repo>
cd rally3d

# 2. Download rally clip
cd vision/scripts
./00_download_clip.sh

# 3. Extract frames
./01_extract_frames.sh

# 4. Run vision pipeline
cd ../pipeline
python court_calib_manual.py  # If auto fails
python player_track.py
python ball_detect.py
python ball_3d_fit.py
python export_json.py

# 5. Copy outputs to viewer
cp ../outputs/*.json ../../viewer/public/data/

# 6. Start viewer
cd ../../viewer
npm install
npm run dev
```

### First Milestone (Day 1)

* ✅ Frames extracted
* ✅ Court calibrated (manual is fine)
* ✅ Validation overlay looks good
* ✅ Basic viewer shows static court

### Second Milestone (Day 2-3)

* ✅ Players tracked and displayed
* ✅ Ball detected and 3D trajectory computed
* ✅ Animation working

### Ship Criteria

* ✅ All acceptance tests pass
* ✅ README with demo GIF/video
* ✅ Code is clean enough to extend

---

## License

MIT License - This is a learning/demo project.

---

**Remember:** Perfect is the enemy of done. Ship the MVP, then iterate.