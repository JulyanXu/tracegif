/* TypeBit 0.3.0 — MIT. Native, self-contained SVG playback. */
(() => {
  "use strict";

  const svg = document.getElementById("typebit-scene");
  const art = document.getElementById("typebit-art");
  const traces = document.getElementById("typebit-traces");
  const control = document.getElementById("typebit-control");
  const controls = document.getElementById("typebit-controls");
  const replayControl = document.getElementById("typebit-replay");
  const speedControl = document.getElementById("typebit-speed");
  const progressControl = document.getElementById("typebit-progress");
  const timeLabel = document.getElementById("typebit-time");
  const htmlControl = document.getElementById("typebit-download-html");
  const pngControl = document.getElementById("typebit-download-png");
  const gifControl = document.getElementById("typebit-download-gif");
  const cancelExportControl = document.getElementById("typebit-cancel-export");
  const exportStatus = document.getElementById("typebit-export-status");
  const configNode = document.getElementById("typebit-config");
  if (!svg || !art || !traces || !control || !configNode) {
    throw new Error("TypeBit: the exported player is missing a required element.");
  }
  // Save source markup before runtime dash styles or resolved CSS URLs are added.
  const pristineDocument = document.documentElement.cloneNode(true);
  const config = JSON.parse(configNode.textContent);
  const finite = (value, fallback) => Number.isFinite(Number(value)) ? Number(value) : fallback;
  const duration = Math.max(0.1, finite(config.duration, 10));
  const fillStart = Math.max(0, Math.min(duration - 0.001, finite(config.fill_start, duration * 0.85)));
  const brand = typeof config.brand_color === "string" ? config.brand_color : "#2563EB";
  // Decorations are additions to the source and require an explicit opt-in.
  const doodleEnabled = config.doodle === true;
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
  let playbackRate = clamp(finite(config.playback_rate, 1), 0.25, 4);
  let exportJob = null;
  let activeDownload = false;

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
  if (!doodle.hasChildNodes() && doodleEnabled) {
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
  const clock = () => status === "playing" ? clamp(baseline + (performance.now() - startedAt) / 1000 * playbackRate, 0, duration) : time;
  const formatTime = seconds => `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
  if (progressControl) {
    progressControl.min = "0";
    progressControl.max = String(duration);
    progressControl.step = "0.01";
  }

  function syncSpeedControl() {
    if (!speedControl) return;
    const value = String(playbackRate);
    if (!Array.from(speedControl.options).some(option => option.value === value)) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = `${value}×`;
      speedControl.appendChild(option);
    }
    speedControl.value = value;
  }

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
    doodle.style.opacity = String(doodleEnabled ? 0.24 * doodleProgress : 0);
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
    if (progressControl) {
      progressControl.value = String(time);
      progressControl.setAttribute("aria-valuetext", `${time.toFixed(1)} of ${duration.toFixed(1)} seconds`);
    }
    if (timeLabel) {
      timeLabel.textContent = `${formatTime(time)} / ${formatTime(duration)}`;
      timeLabel.title = `Timeline position · ${(duration / playbackRate).toFixed(1)} seconds at ${playbackRate}×`;
    }
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
    if (exportJob) return;
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
    if (exportJob) return;
    if (status !== "playing") return;
    time = clock();
    status = time >= duration ? "completed" : "paused";
    cancelFrame();
    render();
  }

  function restart() {
    if (exportJob) return;
    cancelFrame();
    time = 0;
    status = "idle";
    play();
  }

  function seek(seconds) {
    if (exportJob) return getState();
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
    return {status: current >= duration ? "completed" : status, time: current, duration,
      playbackRate, effectiveDuration: duration / playbackRate, exporting: Boolean(exportJob)};
  }

  function setPlaybackRate(value) {
    if (exportJob) return getState();
    const next = Number(value);
    if (!Number.isFinite(next) || next < 0.25 || next > 4) {
      throw new RangeError("Playback speed must be between 0.25 and 4.");
    }
    // Settle the old clock before changing its multiplier, so position never jumps.
    time = clock();
    playbackRate = next;
    if (status === "playing") {
      baseline = time;
      startedAt = performance.now();
      if (time >= duration) {
        status = "completed";
        cancelFrame();
      }
    }
    syncSpeedControl();
    render();
    return getState();
  }

  function filename(extension) {
    const stem = (document.title || "typebit-animation").replace(/[<>:"/\\|?*\u0000-\u001f]/g, "-").replace(/[. ]+$/g, "").slice(0, 100);
    return `${stem || "typebit-animation"}.${extension}`;
  }

  function downloadBlob(blob, name) {
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = name;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function downloadHtml() {
    const copy = pristineDocument.cloneNode(true);
    const savedConfig = {...config, playback_rate: playbackRate};
    copy.querySelector("#typebit-config").textContent = JSON.stringify(savedConfig)
      .replace(/</g, "\\u003c").replace(/>/g, "\\u003e").replace(/&/g, "\\u0026");
    copy.querySelectorAll("#typebit-art,#typebit-traces,#typebit-doodle").forEach(node => { node.style.opacity = "0"; });
    const copiedScene = copy.querySelector("#typebit-scene");
    copiedScene.dataset.state = "idle";
    copiedScene.dataset.time = "0";
    const copiedControl = copy.querySelector("#typebit-control");
    copiedControl.textContent = "Play";
    copiedControl.setAttribute("aria-label", "Play animation");
    copiedControl.dataset.state = "idle";
    copiedControl.hidden = false;
    const copiedControls = copy.querySelector("#typebit-controls");
    if (copiedControls) copiedControls.hidden = false;
    copy.querySelectorAll("#typebit-controls button").forEach(button => { button.disabled = false; });
    const copiedStatus = copy.querySelector("#typebit-export-status");
    if (copiedStatus) copiedStatus.textContent = "";
    const copiedProgress = copy.querySelector("#typebit-progress");
    if (copiedProgress) copiedProgress.setAttribute("value", "0");
    const copiedTime = copy.querySelector("#typebit-time");
    if (copiedTime) copiedTime.textContent = `0:00 / ${formatTime(duration)}`;
    // Preview surfaces are never baked into the portable artwork.
    [copy, copy.querySelector("body"), copy.querySelector("#typebit-stage"), copiedScene].forEach(node => {
      node.style.background = "transparent";
    });
    downloadBlob(new Blob(["<!doctype html>\n", copy.outerHTML], {type: "text/html;charset=utf-8"}), filename("html"));
  }

  async function captureCanvas(width, height, matte = null) {
    const copy = svg.cloneNode(true);
    const originals = [svg, ...svg.querySelectorAll("*")];
    const copies = [copy, ...copy.querySelectorAll("*")];
    const properties = ["fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-opacity",
      "stroke-linecap", "stroke-linejoin", "stroke-miterlimit", "stroke-dasharray", "stroke-dashoffset",
      "opacity", "visibility", "display", "color", "font-family", "font-size", "font-weight", "font-style",
      "font-variant", "text-anchor", "dominant-baseline", "alignment-baseline", "letter-spacing", "word-spacing",
      "paint-order", "vector-effect", "clip-path", "mask", "filter", "stop-color", "stop-opacity",
      "flood-color", "flood-opacity", "marker-start", "marker-mid", "marker-end"];
    originals.forEach((node, index) => {
      const computed = getComputedStyle(node);
      for (const property of properties) {
        let value = computed.getPropertyValue(property);
        // CSSOM may expand local paint/clip references to the HTML's file URL.
        value = value.replace(/url\(["']?([^)'"\s]+)["']?\)/g, (whole, ref) => {
          try {
            const resolved = new URL(ref, document.baseURI);
            return resolved.hash && resolved.href.split("#")[0] === document.URL.split("#")[0]
              ? `url(${resolved.hash})` : whole;
          } catch (_) { return whole; }
        });
        if (value) copies[index].style.setProperty(property, value, "important");
      }
    });
    copy.setAttribute("xmlns", "http://www.w3.org/2000/svg");
    copy.setAttribute("width", String(width));
    copy.setAttribute("height", String(height));
    copy.style.width = `${width}px`;
    copy.style.height = `${height}px`;
    copy.style.background = "transparent";
    const fontRules = [];
    for (const sheet of document.styleSheets) {
      try {
        for (const rule of sheet.cssRules) {
          if (rule.type === CSSRule.FONT_FACE_RULE) fontRules.push(rule.cssText);
        }
      } catch (_) { /* A portable TypeBit export has only inline styles. */ }
    }
    if (fontRules.length) {
      const style = document.createElementNS("http://www.w3.org/2000/svg", "style");
      style.textContent = fontRules.join("\n");
      copy.insertBefore(style, copy.firstChild);
    }
    const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(copy)], {type: "image/svg+xml;charset=utf-8"}));
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d", {willReadFrequently: Boolean(matte)});
      if (!context) throw new Error("Image export is unavailable in this browser.");
      if (matte) {
        context.fillStyle = matte;
        context.fillRect(0, 0, width, height);
      }
      context.drawImage(image, 0, 0, width, height);
      return canvas;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async function downloadPng() {
    if (document.fonts) await document.fonts.ready;
    time = clock();
    render();
    const width = Math.max(1, Math.ceil(viewBox.width));
    const height = Math.max(1, Math.ceil(viewBox.height));
    if (width > 8192 || height > 8192 || width * height > 32000000) {
      throw new Error("This image is too large for a browser PNG download. Ask your Agent for a smaller PNG.");
    }
    const canvas = await captureCanvas(width, height);
    const png = await new Promise((resolve, reject) => canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("PNG export failed.")), "image/png"));
    downloadBlob(png, filename("png"));
  }

  function cancelGif() {
    if (!exportJob) return;
    exportJob.cancelled = true;
    if (cancelExportControl) cancelExportControl.disabled = true;
    if (exportStatus) exportStatus.textContent = "Canceling GIF…";
  }

  async function downloadGif() {
    const encoder = window.gifenc;
    if (!encoder || typeof encoder.GIFEncoder !== "function") {
      throw new Error("This HTML is missing its GIF encoder. Ask your Agent to render it again.");
    }
    const rate = playbackRate;
    const width = Math.max(1, Math.min(480, Math.ceil(viewBox.width)));
    const height = Math.max(1, Math.round(width * viewBox.height / viewBox.width));
    const steps = Math.max(1, Math.ceil(duration / rate * 10));
    if (steps + 1 > 600 || width * height * (steps + 1) > 100000000 || height > 4096) {
      throw new Error("GIF exceeds 600 frames or 100 million frame pixels (maximum height 4096). Increase playback speed, or ask your Agent for a smaller GIF.");
    }
    const saved = getState();
    const focus = document.activeElement;
    const disabled = Array.from(controls ? controls.querySelectorAll("button,input,select") : [control])
      .map(element => [element, element === gifControl ? false : element.disabled]);
    const oldBusy = controls && controls.getAttribute("aria-busy");
    const job = {cancelled: false};
    cancelFrame();
    time = saved.time;
    status = saved.status === "playing" ? "paused" : saved.status;
    exportJob = job;
    disabled.forEach(([element]) => { element.disabled = true; });
    if (controls) controls.setAttribute("aria-busy", "true");
    if (cancelExportControl) {
      cancelExportControl.hidden = false;
      cancelExportControl.disabled = false;
      cancelExportControl.focus({preventScroll: true});
    }
    const assertActive = () => {
      if (job.cancelled) throw new DOMException("GIF export canceled.", "AbortError");
    };
    try {
      if (exportStatus) exportStatus.textContent = "Exporting GIF… 0% (white background)";
      if (document.fonts) await document.fonts.ready;
      assertActive();
      const gif = encoder.GIFEncoder();
      for (let index = 0; index <= steps; index++) {
        // Give the browser time to paint progress and accept Cancel between frames.
        await new Promise(resolve => setTimeout(resolve, 0));
        assertActive();
        time = duration * index / steps;
        status = "paused";
        render();
        const canvas = await captureCanvas(width, height, "#FFFFFF");
        assertActive();
        const rgba = canvas.getContext("2d").getImageData(0, 0, width, height).data;
        const palette = encoder.quantize(rgba, 256);
        const pixels = encoder.applyPalette(rgba, palette);
        const start = Math.round(index * duration / rate / steps * 100) * 10;
        const end = Math.round((index + 1) * duration / rate / steps * 100) * 10;
        gif.writeFrame(pixels, width, height, {palette, delay: index === steps ? 800 : end - start, repeat: 0, dispose: 2});
        if (exportStatus) exportStatus.textContent = `Exporting GIF… ${Math.round((index + 1) / (steps + 1) * 100)}% (white background)`;
      }
      assertActive();
      gif.finish();
      downloadBlob(new Blob([gif.bytes()], {type: "image/gif"}), filename("gif"));
      return `GIF saved at ${rate}× with a white background.`;
    } finally {
      exportJob = null;
      disabled.forEach(([element, wasDisabled]) => { element.disabled = wasDisabled; });
      if (cancelExportControl) {
        cancelExportControl.hidden = true;
        cancelExportControl.disabled = false;
      }
      if (controls) {
        if (oldBusy === null) controls.removeAttribute("aria-busy");
        else controls.setAttribute("aria-busy", oldBusy);
      }
      time = saved.time;
      playbackRate = saved.playbackRate;
      status = saved.status === "playing" ? "paused" : saved.status;
      syncSpeedControl();
      render();
      if (saved.status === "playing") play();
      if (focus instanceof HTMLElement && focus.isConnected && !focus.disabled) focus.focus({preventScroll: true});
    }
  }

  function bindDownload(button, action, message) {
    if (!button) return;
    button.addEventListener("click", async () => {
      if (activeDownload || exportJob) return;
      activeDownload = true;
      button.disabled = true;
      if (exportStatus) exportStatus.textContent = "Preparing download…";
      try {
        const result = await action();
        if (exportStatus) exportStatus.textContent = result || message;
      } catch (error) {
        if (exportStatus) exportStatus.textContent = error.message || "Download failed. Please try again.";
      } finally {
        button.disabled = false;
        activeDownload = false;
      }
    });
  }

  function editableTarget(target) {
    return target instanceof Element && (target.closest("input,textarea,select,[role=textbox]") || target.isContentEditable);
  }

  document.addEventListener("keydown", event => {
    if (exportJob) {
      if (event.key === "Escape") cancelGif();
      if (["Escape", "ArrowRight", " ", "r", "R"].includes(event.key)) event.preventDefault();
      return;
    }
    if (event.defaultPrevented || event.repeat || event.ctrlKey || event.metaKey || event.altKey || editableTarget(event.target)) return;
    if ((event.code === "Space" || event.key === " ") && event.target instanceof Element && event.target.closest("button")) return;
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
  if (replayControl) replayControl.addEventListener("click", restart);
  if (speedControl) speedControl.addEventListener("change", () => setPlaybackRate(Number(speedControl.value)));
  if (progressControl) progressControl.addEventListener("input", () => seek(Number(progressControl.value)));
  bindDownload(htmlControl, downloadHtml, "HTML saved with the selected speed. It waits for Play.");
  bindDownload(pngControl, downloadPng, "Current frame saved as a transparent PNG.");
  bindDownload(gifControl, downloadGif, "GIF saved with a white background.");
  if (cancelExportControl) cancelExportControl.addEventListener("click", cancelGif);
  window.typebit = Object.freeze({
    play,
    pause,
    restart,
    seek,
    getState,
    setPlaybackRate,
    setControlsVisible(visible) {
      control.hidden = !visible;
      if (controls) controls.hidden = !visible;
    }
  });
  syncSpeedControl();
  render();
})();
