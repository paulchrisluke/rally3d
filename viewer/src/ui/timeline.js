export function setupTimeline({ frameCount, fps, events, onFrameChange, onPlayToggle }) {
  const timeline = document.getElementById("timeline");
  const playButton = document.getElementById("play-pause");
  const timeDisplay = document.getElementById("time-display");
  const markers = document.getElementById("timeline-markers");

  const totalSeconds = Math.max(0, (frameCount - 1) / fps);

  timeline.max = Math.max(0, frameCount - 1);
  timeline.value = 0;

  function formatTime(value) {
    return value.toFixed(2);
  }

  function updateTime(frame) {
    const t = Math.min(frame / fps, totalSeconds);
    timeDisplay.textContent = `${formatTime(t)}s / ${formatTime(totalSeconds)}s`;
  }

  function setFrame(frame) {
    const clamped = Math.max(0, Math.min(frame, frameCount - 1));
    timeline.value = clamped;
    updateTime(clamped);
  }

  function setPlaying(isPlaying) {
    playButton.textContent = isPlaying ? "Pause" : "Play";
  }

  timeline.addEventListener("input", (event) => {
    const frame = Number(event.target.value);
    onFrameChange(frame);
  });

  playButton.addEventListener("click", () => {
    onPlayToggle();
  });

  window.addEventListener("keydown", (event) => {
    if (event.code === "Space") {
      event.preventDefault();
      onPlayToggle();
    }
  });

  markers.innerHTML = "";
  if (events) {
    const allMarkers = []
      .concat((events.hits || []).map((hit) => ({ ...hit, type: "hit" })))
      .concat((events.bounces || []).map((bounce) => ({ ...bounce, type: "bounce" })));

    allMarkers.forEach((marker) => {
      const el = document.createElement("span");
      el.className = `marker ${marker.type}`;
      const percent = frameCount > 1 ? marker.frame / (frameCount - 1) : 0;
      el.style.left = `${percent * 100}%`;
      el.addEventListener("click", () => onFrameChange(marker.frame));
      markers.appendChild(el);
    });
  }

  updateTime(0);

  return { setFrame, setPlaying };
}
