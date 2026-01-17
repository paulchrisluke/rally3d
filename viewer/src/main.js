import "./style.css";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { createCourt } from "./scene/court.js";
import { createPlayerSystem } from "./scene/players.js";
import { createBall } from "./scene/ball.js";
import { setupTimeline } from "./ui/timeline.js";

const canvas = document.getElementById("three-canvas");
const statusEl = document.getElementById("status");

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x000000, 0);

const scene = new THREE.Scene();

const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 200);
camera.position.set(0, 8, -18);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.minPolarAngle = 0.2;
controls.maxPolarAngle = Math.PI / 2.1;
controls.minDistance = 6;
controls.maxDistance = 40;
controls.target.set(0, 1.2, 0);
controls.update();

const hemiLight = new THREE.HemisphereLight(0xffffff, 0x445544, 0.7);
scene.add(hemiLight);

const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(5, 12, -6);
scene.add(dirLight);

let playersData;
let ballData;
let eventsData;
let frameCount = 0;
let fps = 30;
let uiControls = null;

const playersSystem = createPlayerSystem();
scene.add(playersSystem.group);

const ball = createBall();
scene.add(ball);

function setStatus(message) {
  statusEl.textContent = message;
}

async function loadJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Failed to load ${path}`);
  }
  return response.json();
}

async function loadJsonOptional(path) {
  try {
    return await loadJson(path);
  } catch (_err) {
    return null;
  }
}

function updateScene(frameIndex) {
  if (!playersData || !ballData) {
    return;
  }

  const safeIndex = Math.max(0, Math.min(frameIndex, frameCount - 1));
  const playerFrame = playersData.frames[safeIndex];
  const ballFrame = ballData.frames[safeIndex];

  if (playerFrame) {
    playersSystem.update(playerFrame);
  }

  if (ballFrame) {
    ball.position.set(ballFrame.x, ballFrame.z, ballFrame.y);
  }

  return safeIndex;
}

function resize() {
  const { innerWidth, innerHeight } = window;
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
}

window.addEventListener("resize", resize);

async function init() {
  setStatus("Loading data...");
  try {
    const [courtData, players, ball] = await Promise.all([
      loadJson("/data/court.json"),
      loadJson("/data/players.json"),
      loadJson("/data/ball.json")
    ]);

    eventsData = await loadJsonOptional("/data/events.json");
    playersData = players;
    ballData = ball;
    frameCount = playersData.frame_count || ballData.frame_count || 0;
    fps = playersData.fps || ballData.fps || 30;

    const court = createCourt(courtData);
    scene.add(court);

    const halfLength = courtData?.court_dims_m?.half_length ?? 11.885;
    camera.position.set(0, 8, -(halfLength + 6));
    controls.target.set(0, 1.2, 0);
    controls.update();

    uiControls = setupTimeline({
      frameCount,
      fps,
      events: eventsData,
      onFrameChange: (frame) => {
        currentFrame = frame;
        const idx = updateScene(frame);
        uiControls.setFrame(idx ?? frame);
      },
      onPlayToggle: () => {
        isPlaying = !isPlaying;
        uiControls.setPlaying(isPlaying);
        if (!isPlaying) {
          lastTime = 0;
        }
      }
    });

    setStatus(`Loaded ${frameCount} frames @ ${fps} fps`);

    currentFrame = 0;
    updateScene(0);
    uiControls.setFrame(0);
    uiControls.setPlaying(isPlaying);
  } catch (err) {
    console.error(err);
    setStatus("Failed to load data. Check viewer/public/data.");
  }
}

let currentFrame = 0;
let lastTime = 0;
let isPlaying = false;
let lastRenderedFrame = -1;

function animate(time) {
  requestAnimationFrame(animate);

  if (isPlaying && frameCount > 0) {
    if (!lastTime) {
      lastTime = time;
    }
    const delta = (time - lastTime) / 1000;
    lastTime = time;
    currentFrame += delta * fps;
    if (currentFrame >= frameCount) {
      currentFrame = 0;
    }
  } else {
    lastTime = time;
  }

  const frameIndex = Math.floor(currentFrame);
  if (frameIndex !== lastRenderedFrame) {
    lastRenderedFrame = updateScene(frameIndex) ?? frameIndex;
    if (uiControls) {
      uiControls.setFrame(lastRenderedFrame);
    }
  }

  controls.update();
  renderer.render(scene, camera);
}

init();
animate(0);
