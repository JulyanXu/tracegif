/* TraceGIF live showcase. The embedded file is the same self-contained player users download. */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const info = {
    "night-market": ["🏮", "complex", "Urban panorama", "城市全景", "A richly layered street scene: architecture, storefronts and the little details that make a night market feel alive.", "层叠建筑、沿街店铺与夜市细节，让整条街景从线条中逐步展开。"],
    "camera-exploded": ["📷", "complex", "Product breakdown", "产品结构", "An exploded camera illustration. Follow its separated components, mechanical details and alignment guides.", "通过分解部件、机械细节和引导线，逐步看清相机的结构。"],
    "greenhouse-study": ["🌿", "complex", "Botanical study", "植物空间", "Glass structure, branching plants and layered foliage come together in a detailed greenhouse composition.", "玻璃结构、分枝植物与层叠叶片，共同组成丰富的温室画面。"],
    "courtyard-house": ["🏡", "story", "Architecture", "建筑展示", "A courtyard home takes shape: building volumes, windows, the entrance and the surrounding garden.", "从建筑体块到门窗庭院，按层次呈现一栋住宅的轮廓与色彩。"],
    "city-route": ["🗺️", "story", "Travel & wayfinding", "旅行路线", "An imaginary city map reveals its river, landmarks, walking route and numbered stops.", "从河流和地标到步行路线与站点，用一张虚构地图讲述城市漫游。"],
    "orbit-lesson": ["🪐", "story", "Learning & explanation", "课堂科普", "Orbit guides, a central star and small planets reveal a classroom illustration. Illustrative only; not to scale.", "轨道、恒星与行星依次出现，适合课堂讲解的示意图，不代表真实比例。"],
    "celebration-card": ["🎈", "story", "Event invitation", "活动邀请", "An arched invitation, balloons and hand-drawn lettering reveal a small celebration, one detail at a time.", "拱形邀请卡、气球和路径文字逐步出现，让活动邀请多一点仪式感。"],
    "leaf-studio": ["🍃", "brand", "Brand identity", "品牌标识", "A botanical mark grows from its stem to leaf shapes, delicate veins and a restrained green-and-gold finish.", "先枝干与叶形，再细小叶脉，最后呈现绿色与金色的植物标识。"],
    "coffee-story": ["☕", "brand", "Product illustration", "产品插画", "Cup, saucer, steam and coffee beans: a warm product story with editable contours and original colors.", "杯碟、蒸汽与咖啡豆，保留轮廓和原始配色的一则温暖产品故事。"],
    "white-letter-badge": ["✳️", "brand", "White detail preservation", "白字保真", "A transparent PNG badge with supplied contours. The white lettering stays intact and the original pixels return in the final frame.", "提供轮廓的透明 PNG 徽章，保留白色文字，终帧还原原始像素。"]
  };
  const orderedSlugs = Object.keys(info);
  const strings = {
    ready: ["Ready when you are · no autoplay", "准备好了 · 不自动播放"],
    playing: ["Drawing in real time", "正在实时描绘"],
    paused: ["Paused · continue in the player", "已暂停 · 可在播放器继续"],
    ended: ["Complete · replay or export", "已完成 · 可重播或导出"],
    exporting: ["Exporting · see progress in the player", "正在导出 · 查看播放器进度"],
    loading: ["Opening scene…", "正在加载场景…"],
    failed: ["Scene unavailable · try again", "场景暂不可用 · 请重试"],
    complex: ["Detailed scene", "复杂场景"],
    svg: ["Editable SVG", "可编辑 SVG"],
    raster: ["Original PNG", "原始 PNG"],
    verified: ["Offline checked", "离线已验证"],
    unavailable: ["This example is not available yet. Choose another scene from the collection.", "此示例暂未上线，请从案例集中选择其他场景。"]
  };
  const params = new URLSearchParams(location.search);
  let language = params.get("lang") === "zh" ? "zh" : "en";
  try { if (!params.has("lang")) language = localStorage.getItem("tracegif-language") === "zh" ? "zh" : "en"; } catch (_) { /* Storage is optional. */ }
  let cases = [], selected = null, filter = "all", api = null, loadTimer = null, lastStatus = "", generation = 0;
  let controlsObserver = null;
  const t = key => (strings[key] || [key, key])[language === "zh" ? 1 : 0];
  const metadata = item => info[item.slug] || ["✏️", "story", "Line animation", "线条动画", item.method || "Original editable animation.", "可编辑的原创线条动画。"];

  function applyLanguage() {
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
    document.querySelectorAll("[data-en][data-zh]").forEach(node => { node.textContent = node.dataset[language]; });
    $("language-toggle").textContent = language === "zh" ? "EN" : "中文";
    $("language-toggle").setAttribute("aria-label", language === "zh" ? "Switch to English" : "切换为中文");
    $("demo-frame").title = language === "zh" ? "TraceGIF 实际动画播放器" : "TraceGIF live animation player";
    $("scene-list").setAttribute("aria-label", language === "zh" ? "选择动画场景" : "Choose an animation scene");
    document.title = language === "zh" ? "TraceGIF — 让每一笔，都有故事。" : "TraceGIF — Make every line move.";
    renderCases();
    if (selected) describeCase(selected);
    lastStatus = "";
    updateStatus();
  }

  function renderCases() {
    const list = $("scene-list");
    list.replaceChildren();
    cases.filter(item => filter === "all" || metadata(item)[1] === filter).forEach(item => {
      const meta = metadata(item);
      const button = document.createElement("button");
      button.type = "button"; button.className = "scene-button"; button.dataset.case = item.slug;
      button.setAttribute("aria-pressed", String(selected?.slug === item.slug));
      const icon = document.createElement("span"); icon.className = "scene-emoji"; icon.setAttribute("aria-hidden", "true"); icon.textContent = meta[0];
      const copy = document.createElement("span"); copy.className = "scene-text";
      const name = document.createElement("strong"); name.textContent = language === "zh" ? item.title_zh || item.title : item.title;
      const detail = document.createElement("small"); detail.textContent = meta[language === "zh" ? 3 : 2];
      if (Number.isInteger(item.layer_count) && item.layer_count > 0) detail.textContent += language === "zh" ? ` · ${item.layer_count} 条路径` : ` · ${item.layer_count} paths`;
      copy.append(name, detail);
      const arrow = document.createElement("span"); arrow.className = "scene-arrow"; arrow.setAttribute("aria-hidden", "true"); arrow.textContent = "↗";
      button.append(icon, copy, arrow);
      button.addEventListener("click", () => selectCase(item));
      list.append(button);
    });
    $("case-count").textContent = String(cases.length).padStart(2, "0");
  }

  function describeCase(item) {
    const meta = metadata(item);
    $("demo-title").textContent = language === "zh" ? item.title_zh || item.title : item.title;
    $("scene-description").textContent = meta[language === "zh" ? 5 : 4];
    const facts = [t(item.kind === "svg" ? "svg" : "raster")];
    if (Number.isInteger(item.layer_count) && item.layer_count > 0) facts.push(language === "zh" ? `${item.layer_count} 条路径` : `${item.layer_count} paths`);
    else if (meta[1] === "complex") facts.push(t("complex"));
    if (item.automated_status === "passed") facts.push(t("verified"));
    $("scene-facts").replaceChildren(...facts.map(value => { const span = document.createElement("span"); span.textContent = value; return span; }));
    const base = `cases/${encodeURIComponent(item.slug)}/`;
    $("open-player").href = `${base}animation.html`;
    $("download-html").href = `${base}animation.html`;
    $("download-gif").href = `${base}animation.gif`;
    $("download-png").href = `${base}final.png`;
    $("download-project").hidden = !item.assets?.["project.zip"];
    if (item.assets?.["project.zip"]) $("download-project").href = `${base}project.zip`;
    else $("download-project").removeAttribute("href");
    $("verification-link").href = `${base}report.json`;
    $("player-shell").style.backgroundColor = /^#[0-9a-f]{6}$/i.test(item.matte || "") ? item.matte : "#f8f6ed";
  }

  function setStatus(key) {
    const message = t(key);
    if (message !== lastStatus) { $("player-status").textContent = message; lastStatus = message; }
  }

  function showFailure() {
    api = null;
    controlsObserver?.disconnect();
    clearTimeout(loadTimer);
    $("player-shell").setAttribute("aria-busy", "false");
    $("player-loading").hidden = true;
    $("player-welcome").hidden = true;
    $("load-error").hidden = false;
    setStatus("failed");
  }

  function selectCase(item, updateUrl = true) {
    if (!item || !/^[a-z0-9][a-z0-9-]*$/.test(item.slug)) return;
    try { api?.pause(); } catch (_) { /* The previous iframe may already be gone. */ }
    selected = item; api = null; generation++;
    controlsObserver?.disconnect();
    $("player-shell").style.minHeight = "";
    clearTimeout(loadTimer);
    describeCase(item); renderCases();
    $("player-loading").hidden = false; $("load-error").hidden = true; $("player-welcome").hidden = true;
    $("player-shell").setAttribute("aria-busy", "true");
    setStatus("loading");
    $("demo-frame").src = `cases/${encodeURIComponent(item.slug)}/animation.html`;
    const currentGeneration = generation;
    loadTimer = setTimeout(() => { if (generation === currentGeneration) showFailure(); }, 18000);
    if (updateUrl) {
      const url = new URL(location.href); url.searchParams.set("scene", item.slug); url.searchParams.delete("case"); url.searchParams.set("lang", language);
      history.replaceState(null, "", url);
    }
  }

  function updateStatus() {
    if (!api) { if (!$("load-error").hidden) setStatus("failed"); else setStatus("loading"); return; }
    try {
      const state = api.getState();
      $("player-welcome").hidden = state.status !== "idle" || state.exporting;
      setStatus(state.exporting ? "exporting" : state.status === "idle" ? "ready" : state.status === "completed" ? "ended" : state.status === "playing" ? "playing" : "paused");
    } catch (_) { showFailure(); }
  }

  function fitEmbeddedPlayer() {
    const doc = $("demo-frame").contentDocument;
    const controls = doc.getElementById("typebit-controls");
    if (!controls) return;
    // Only the surrounding stage changes. SVG coordinates and the native export
    // routines stay intact. Save HTML clones the player's pre-load pristineDocument,
    // so this host-only stylesheet is not copied into the downloaded HTML.
    const style = doc.createElement("style");
    style.id = "tracegif-embed-layout";
    style.textContent = `
      body { display: block; }
      #typebit-stage {
        height: calc(100dvh - var(--tracegif-embed-controls-space, 132px));
        min-height: 0;
      }
    `;
    doc.head.append(style);
    const reserve = () => {
      const space = Math.ceil(controls.getBoundingClientRect().height) + 32;
      doc.documentElement.style.setProperty("--tracegif-embed-controls-space", `${space}px`);
      // Keep a small artwork area even when the optional GIF settings expand on mobile.
      $("player-shell").style.minHeight = `${space + 200}px`;
    };
    controlsObserver = new ResizeObserver(reserve);
    controlsObserver.observe(controls);
    reserve();
  }

  $("demo-frame").addEventListener("load", () => {
    if (!selected) return;
    try {
      const candidate = $("demo-frame").contentWindow.tracegif;
      if (!candidate || typeof candidate.getState !== "function") { showFailure(); return; }
      api = candidate;
      clearTimeout(loadTimer);
      $("player-shell").setAttribute("aria-busy", "false");
      $("player-loading").hidden = true; $("load-error").hidden = true;
      fitEmbeddedPlayer();
      updateStatus();
    } catch (_) { showFailure(); }
  });
  $("demo-frame").addEventListener("error", showFailure);
  $("start-demo").addEventListener("click", () => { if (api) { api.play(); updateStatus(); $("demo-frame").contentWindow.focus(); } });
  $("retry-load").addEventListener("click", () => { if (selected) selectCase(selected, false); else loadManifest(); });
  $("language-toggle").addEventListener("click", () => {
    language = language === "en" ? "zh" : "en";
    try { localStorage.setItem("tracegif-language", language); } catch (_) { /* Storage is optional. */ }
    const url = new URL(location.href); url.searchParams.set("lang", language); history.replaceState(null, "", url);
    applyLanguage();
  });
  document.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click", () => {
    filter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach(other => { const active = other === button; other.classList.toggle("active", active); other.setAttribute("aria-pressed", String(active)); });
    renderCases();
  }));
  document.querySelectorAll("[data-scene]").forEach(button => button.addEventListener("click", () => {
    const item = cases.find(entry => entry.slug === button.dataset.scene);
    if (!item) { $("player-status").textContent = t("unavailable"); $("playground").scrollIntoView({behavior: "smooth"}); return; }
    filter = "all";
    document.querySelectorAll("[data-filter]").forEach(other => { const active = other.dataset.filter === filter; other.classList.toggle("active", active); other.setAttribute("aria-pressed", String(active)); });
    selectCase(item); $("playground").scrollIntoView({behavior: "smooth"}); $("demo-title").focus({preventScroll: true});
  }));
  document.addEventListener("visibilitychange", () => { if (document.hidden && api) { api.pause(); updateStatus(); } });

  async function loadManifest() {
    $("player-loading").hidden = false; $("load-error").hidden = true;
    $("player-shell").setAttribute("aria-busy", "true"); setStatus("loading");
    try {
      const response = await fetch("cases/manifest.json");
      if (!response.ok) throw new Error("Manifest unavailable");
      const manifest = await response.json();
      if (!Array.isArray(manifest.cases)) throw new Error("Invalid collection");
      cases = manifest.cases.filter(item => item && /^[a-z0-9][a-z0-9-]*$/.test(item.slug) && typeof item.title === "string");
      cases.sort((a, b) => { const rank = slug => orderedSlugs.includes(slug) ? orderedSlugs.indexOf(slug) : 100; return rank(a.slug) - rank(b.slug); });
      if (!cases.length) throw new Error("Empty collection");
      const requested = params.get("scene") || params.get("case");
      selectCase(cases.find(item => item.slug === requested) || cases.find(item => item.slug === "night-market") || cases.find(item => item.slug === "courtyard-house") || cases[0], false);
    } catch (_) { showFailure(); }
  }
  applyLanguage();
  loadManifest();
  setInterval(updateStatus, 200);
})();
