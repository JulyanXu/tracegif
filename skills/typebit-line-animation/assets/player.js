/* TypeBit 0.1.0 — MIT. Native, self-contained SVG playback. */
(() => {
  "use strict";

  const svg = document.getElementById("typebit-scene");
  const art = document.getElementById("typebit-art");
  const traces = document.getElementById("typebit-traces");
  const control = document.getElementById("typebit-control");
  const configNode = document.getElementById("typebit-config");
  if (!svg || !art || !traces || !control || !configNode) {
    throw new Error("TypeBit: the exported player is missing a required element.");
  }
  const config = JSON.parse(configNode.textContent);
  const finite = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) : fallback;
  const duration = Math.max(0.1, finite(config.duration, 10));
  const fillStart = Math.max(0, Math.min(duration - 0.001, finite(config.fill_start, duration * 0.85)));
  const brand = typeof config.brand_color === "string" ? config.brand_color : "#2563EB";
  const clamp = (value, low = 0, high = 1) => Math.min(high, Math.max(low, value));
  const ease = value => value * value * (3 - 2 * value);
  const geometrySelector = "path,rect,circle,ellipse,line,polyline,polygon";
  const definitionSelector = "defs,clipPath,mask,marker,pattern,symbol";
  const layers = Array.isArray(config.layers) ? config.layers : [];
  const viewBox = svg.viewBox.baseVal;
  const unit = Math.max(viewBox.width, viewBox.height, 1);
  let status = "idle";
  let time = 0;
  let baseline = 0;
  let startedAt = 0;
  let frame = null;

  // Definition geometry must stay intact: changing it can break a source mask.
  traces.querySelectorAll("text,image,foreignObject").forEach(element => {
    if (!element.closest(definitionSelector)) element.style.setProperty("display", "none", "important");
  });
  const shapes = Array.from(traces.querySelectorAll(geometrySelector))
    .filter(element => !element.closest(definitionSelector));
  const schedule = new Map();
  for (const layer of layers) {
    const target = document.getElementById(`trace-${layer.id}`);
    if (!target || !traces.contains(target)) continue;
    const members = target.matches(geometrySelector)
      ? [target]
      : Array.from(target.querySelectorAll(geometrySelector));
    const start = clamp(finite(layer.start, 0), 0, fillStart);
    const span = Math.max(0.001, Math.min(fillStart - start || 0.001, finite(layer.duration, 1)));
    for (const shape of members) {
      if (!shape.closest(definitionSelector)) schedule.set(shape, {start, duration: span});
    }
  }

  const strokes = shapes.map((element, index) => {
    const computed = getComputedStyle(element);
    const stroke = computed.stroke && computed.stroke !== "none" ? computed.stroke : brand;
    const originalWidth = Number.parseFloat(computed.strokeWidth);
    const width = computed.stroke !== "none" && originalWidth > 0 ? originalWidth : unit / 350;
    let length = 0;
    try { length = element.getTotalLength(); } catch (_) { /* Degenerate source shape. */ }
    if (!Number.isFinite(length) || length <= 0) {
      element.style.setProperty("visibility", "hidden", "important");
      return null;
    }
    // getTotalLength uses geometric units; a source pathLength changes dash units.
    element.removeAttribute("pathLength");
    element.style.setProperty("fill", "none", "important");
    element.style.setProperty("stroke", stroke, "important");
    element.style.setProperty("stroke-width", String(width), "important");
    element.style.setProperty("stroke-linecap", "round", "important");
    element.style.setProperty("stroke-linejoin", "round", "important");
    element.style.setProperty("stroke-dasharray", `${length} ${length}`, "important");
    element.style.setProperty("stroke-dashoffset", String(length), "important");
    const fallbackSpan = fillStart / Math.max(shapes.length, 1);
    return {element, length, ...(schedule.get(element) || {start: index * fallbackSpan, duration: fallbackSpan})};
  }).filter(Boolean);

  let doodle = document.getElementById("typebit-doodle");
  if (!doodle) {
    doodle = document.createElementNS("http://www.w3.org/2000/svg", "g");
    doodle.id = "typebit-doodle";
  }
  // The decoration always sits behind the subject, including imported scenes.
  svg.insertBefore(doodle, art);
  if (!doodle.hasChildNodes() && config.doodle !== false) {
    const x = viewBox.x;
    const y = viewBox.y;
    const w = viewBox.width || 640;
    const h = viewBox.height || 480;
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", `M ${x + w * 0.17} ${y + h * 0.76} C ${x + w * 0.31} ${y + h * 0.7}, ${x + w * 0.65} ${y + h * 0.83}, ${x + w * 0.82} ${y + h * 0.74} M ${x + w * 0.23} ${y + h * 0.82} Q ${x + w * 0.48} ${y + h * 0.76}, ${x + w * 0.73} ${y + h * 0.84}`);
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", brand);
    path.setAttribute("stroke-width", String(unit / 45));
    path.setAttribute("stroke-linecap", "round");
    path.setAttribute("stroke-linejoin", "round");
    doodle.appendChild(path);
  }
  const doodleStrokes = Array.from(doodle.querySelectorAll(geometrySelector)).map(element => {
    let length = 0;
    try { length = element.getTotalLength(); } catch (_) { /* Ignore non-path decorations. */ }
    if (!(length > 0)) return null;
    element.style.strokeDasharray = `${length} ${length}`;
    return {element, length};
  }).filter(Boolean);

  control.setAttribute("type", "button");
  control.setAttribute("aria-keyshortcuts", "ArrowRight Space R");
  control.title = "Right arrow: play or replay · Space: pause or continue · R: restart";
  const labels = {idle: "Play", playing: "Pause", paused: "Continue", completed: "Replay"};
  let lastLabel = "";
  const clock = () => status === "playing" ? clamp(baseline + (performance.now() - startedAt) / 1000, 0, duration) : time;

  function render() {
    const fill = ease(clamp((time - fillStart) / (duration - fillStart)));
    art.style.opacity = String(fill);
    traces.style.opacity = String(1 - fill);
    for (const stroke of strokes) {
      const progress = clamp((time - stroke.start) / stroke.duration);
      stroke.element.style.setProperty("visibility", progress > 0 ? "visible" : "hidden", "important");
      stroke.element.style.setProperty("stroke-dashoffset", String(stroke.length * (1 - progress)), "important");
    }
    const doodleProgress = clamp(time / Math.min(1.4, duration * 0.2));
    doodle.style.opacity = String(config.doodle === false ? 0 : 0.24 * doodleProgress);
    for (const stroke of doodleStrokes) {
      stroke.element.style.strokeDashoffset = String(stroke.length * (1 - doodleProgress));
    }
    const label = labels[status];
    if (label !== lastLabel) {
      control.textContent = label;
      control.setAttribute("aria-label", `${label} animation`);
      lastLabel = label;
    }
    control.dataset.state = status;
    svg.dataset.state = status;
    svg.dataset.time = time.toFixed(6);
  }

  function cancelFrame() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
  }

  function tick() {
    frame = null;
    if (status !== "playing") return;
    time = clock();
    if (time >= duration) {
      time = duration;
      status = "completed";
    }
    render();
    if (status === "playing") frame = requestAnimationFrame(tick);
  }

  function play() {
    if (status === "playing") return;
    if (status === "completed" || time >= duration) time = 0;
    baseline = time;
    startedAt = performance.now();
    status = "playing";
    render();
    cancelFrame();
    frame = requestAnimationFrame(tick);
  }

  function pause() {
    if (status !== "playing") return;
    time = clock();
    status = time >= duration ? "completed" : "paused";
    cancelFrame();
    render();
  }

  function restart() {
    cancelFrame();
    time = 0;
    status = "idle";
    play();
  }

  function seek(seconds) {
    const value = Number(seconds);
    if (!Number.isFinite(value)) throw new TypeError("TypeBit.seek expects a finite number of seconds.");
    cancelFrame();
    time = clamp(value, 0, duration);
    status = time === 0 ? "idle" : time === duration ? "completed" : "paused";
    render();
    return getState();
  }

  function getState() {
    const current = clock();
    return {status: current >= duration ? "completed" : status, time: current, duration};
  }

  function editableTarget(target) {
    return target instanceof Element && (target.closest("input,textarea,select,[role=textbox]") || target.isContentEditable);
  }

  document.addEventListener("keydown", event => {
    if (event.defaultPrevented || event.repeat || event.ctrlKey || event.metaKey || event.altKey || editableTarget(event.target)) return;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      play();
    } else if (event.code === "Space" || event.key === " ") {
      event.preventDefault();
      if (status === "playing") pause();
      else if (status === "paused") play();
    } else if (event.key.toLowerCase() === "r") {
      event.preventDefault();
      restart();
    }
  });

  control.addEventListener("click", () => status === "playing" ? pause() : play());
  window.typebit = Object.freeze({
    play,
    pause,
    restart,
    seek,
    getState,
    setControlsVisible(visible) {
      control.hidden = !visible;
    }
  });
  render();
})();
