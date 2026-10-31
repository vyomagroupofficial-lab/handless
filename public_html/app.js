// ============================================================
// Vyoma Handless™ — Landing page scripts
// Warm paper theme | canvas orb, voice simulator, mobile UX
// handless.vyomagroup.online
// ============================================================

const DOWNLOAD_URL = "https://handless.vyomagroup.online/downloads/VyomaHandless-Setup.exe";
const REDUCED_MOTION = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  initReveal();
  initOrbCanvas();
  initVoiceSimulator();
  initCopyInstall();
  initMobileSupport();
});

// Storage can throw in private mode; never let it break the page.
function store(key, value) {
  try {
    if (value === undefined) return sessionStorage.getItem(key);
    sessionStorage.setItem(key, value);
  } catch (e) { return null; }
}

// ------------------------------------------------------------
// 1. Navigation: scrolled state, mobile sheet, active link
// ------------------------------------------------------------
function initNav() {
  const nav = document.getElementById("nav");
  const menuBtn = document.getElementById("menuBtn");
  const menu = document.getElementById("mobileMenu");
  if (!nav) return;

  const onScroll = () => nav.classList.toggle("scrolled", window.scrollY > 8);
  onScroll();
  window.addEventListener("scroll", onScroll, { passive: true });

  const setOpen = (open) => {
    nav.classList.toggle("open", open);
    menuBtn.setAttribute("aria-expanded", String(open));
    menuBtn.setAttribute("aria-label", open ? "Close menu" : "Open menu");
  };

  if (menuBtn && menu) {
    menuBtn.addEventListener("click", () => setOpen(!nav.classList.contains("open")));
    menu.querySelectorAll("a").forEach(a => a.addEventListener("click", () => setOpen(false)));
    document.addEventListener("keydown", e => { if (e.key === "Escape") setOpen(false); });
  }

  // Highlight the section currently in view
  const links = [...document.querySelectorAll(".nav-links a")];
  const sections = links.map(a => document.querySelector(a.getAttribute("href"))).filter(Boolean);
  if (!("IntersectionObserver" in window) || !sections.length) return;

  const spy = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      links.forEach(a => a.classList.toggle("active", a.getAttribute("href") === "#" + entry.target.id));
    });
  }, { rootMargin: "-45% 0px -50% 0px" });
  sections.forEach(s => spy.observe(s));
}

// ------------------------------------------------------------
// 2. Reveal-on-scroll
// ------------------------------------------------------------
function initReveal() {
  const items = document.querySelectorAll(".reveal");
  if (REDUCED_MOTION || !("IntersectionObserver" in window)) {
    items.forEach(el => el.classList.add("in"));
    return;
  }

  const io = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("in");
      io.unobserve(entry.target);
    });
  }, { threshold: 0.12, rootMargin: "0px 0px -40px 0px" });

  items.forEach((el, i) => {
    // Stagger siblings slightly so grids cascade in
    el.style.transitionDelay = `${(i % 4) * 70}ms`;
    io.observe(el);
  });
}

// ------------------------------------------------------------
// 3. Warm constellation orb behind the logo
// ------------------------------------------------------------
function initOrbCanvas() {
  const canvas = document.getElementById("orbCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let width = 0, height = 0, radius = 0;
  const resize = () => {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const rect = canvas.getBoundingClientRect();
    width = rect.width;
    height = rect.height;
    radius = width * 0.4;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  resize();
  window.addEventListener("resize", resize);

  // Fibonacci sphere
  const numPoints = 140;
  const golden = Math.PI * (3 - Math.sqrt(5));
  const unit = [];
  for (let i = 0; i < numPoints; i++) {
    const y = 1 - (i / (numPoints - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    unit.push({ x: Math.cos(golden * i) * r, y, z: Math.sin(golden * i) * r });
  }

  let angleX = 0.4, angleY = 0, pulse = 0, running = true;

  // Pause the animation when the hero is off screen
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([entry]) => {
      const wasRunning = running;
      running = entry.isIntersecting;
      if (running && !wasRunning) requestAnimationFrame(render);
    }).observe(canvas);
  }

  function render() {
    ctx.clearRect(0, 0, width, height);
    const cx = width / 2, cy = height / 2;

    angleX += 0.0022;
    angleY += 0.004;
    pulse += 0.03;
    const scale = radius * (1 + Math.sin(pulse) * 0.03);
    const cosX = Math.cos(angleX), sinX = Math.sin(angleX);
    const cosY = Math.cos(angleY), sinY = Math.sin(angleY);

    const pts = unit.map(p => {
      const x1 = p.x * cosY + p.z * sinY;
      const z1 = -p.x * sinY + p.z * cosY;
      const y2 = p.y * cosX - z1 * sinX;
      const z2 = p.y * sinX + z1 * cosX;
      const depth = (z2 + 1) / 2; // 0 back, 1 front
      const fov = 3 / (3 + z2);
      return { x: cx + x1 * scale * fov, y: cy + y2 * scale * fov, depth };
    });

    const linkDist = width * 0.11;
    ctx.lineWidth = 0.8;
    for (let i = 0; i < pts.length; i++) {
      for (let j = i + 1; j < pts.length; j++) {
        const dx = pts[i].x - pts[j].x, dy = pts[i].y - pts[j].y;
        const d = Math.hypot(dx, dy);
        if (d < linkDist) {
          const a = (1 - d / linkDist) * 0.32 * Math.min(pts[i].depth, pts[j].depth);
          ctx.strokeStyle = `rgba(184, 70, 26, ${a})`;
          ctx.beginPath();
          ctx.moveTo(pts[i].x, pts[i].y);
          ctx.lineTo(pts[j].x, pts[j].y);
          ctx.stroke();
        }
      }
    }

    for (const p of pts) {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 0.8 + p.depth * 1.8, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${Math.round(150 + p.depth * 82)}, ${Math.round(70 + p.depth * 28)}, 30, ${0.18 + p.depth * 0.6})`;
      ctx.fill();
    }

    if (running && !REDUCED_MOTION) requestAnimationFrame(render);
  }

  render();
}

// ------------------------------------------------------------
// 4. Interactive voice simulator
// ------------------------------------------------------------
const ICON = {
  bolt: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>',
  volume: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
  volumeLg: '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>',
  link: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
  cursor: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3l7.07 16.97 2.51-7.39 7.39-2.51L3 3z"/></svg>',
  keyboard: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M6 12h.01M10 12h.01M14 12h.01M18 12h.01M7 16h10"/></svg>',
  window: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M12 3v18"/></svg>',
  windowLg: '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/></svg>',
  camera: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
  spark: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M5.6 18.4l2.8-2.8M15.6 8.4l2.8-2.8"/></svg>',
  mic: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4"/></svg>',
  rocket: '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/></svg>'
};

const SIM_COMMANDS = {
  set_volume: {
    title: "Windows 11 Desktop — Master Audio Control",
    tier: "Tier 1 · Local rule (<5 ms)",
    state: "✓ Done",
    transcript: "“Set my volume to 80%”",
    logs: [
      [ICON.bolt, "Matched rule: SetVolume(80)"],
      [ICON.volume, "IAudioEndpointVolume: 0.80 applied"]
    ],
    render: () => `
      <div class="stage-card hud">
        <div class="hud-row">
          ${ICON.volumeLg}
          <div class="hud-track"><div class="hud-fill" style="--to: 80%"></div></div>
          <span class="hud-num">80%</span>
        </div>
        <p class="hud-label">Master volume adjusted to 80%</p>
      </div>`
  },
  whatsapp_msg: {
    title: "WhatsApp Web (Chrome, CDP pierced)",
    tier: "Tier 1 · Chained rule (<15 ms)",
    state: "✓ Chained",
    transcript: "“Message Design Team: on my way”",
    logs: [
      [ICON.link, "Chained 2 actions: open chat → type message"],
      [ICON.cursor, "Opened chat ‘Design Team’ (list item)"],
      [ICON.keyboard, "Typed ‘on my way’ and pressed Enter"]
    ],
    render: () => `
      <div class="stage-card">
        <div class="chat-head target-ring">
          <span class="avatar">DT</span>
          <div><strong>Design Team</strong><span>4 members · opened by Handless</span></div>
        </div>
        <div class="chat-body">
          <span class="bubble in">Standup moved to 10:30. Can you make it?</span>
          <span class="bubble out">on my way ✓✓</span>
        </div>
        <div class="chat-input">Type a message<span class="caret"></span></div>
      </div>`
  },
  snap_left: {
    title: "Windows 11 Snap Assist — Layout Manager",
    tier: "Tier 1 · System hotkey",
    state: "✓ Snapped",
    transcript: "“Snap this window to the left”",
    logs: [
      [ICON.window, "Target active window: Chrome"],
      [ICON.bolt, "Dispatched hotkey: Win + Left"]
    ],
    render: () => `
      <div class="stage-card snap">
        <div class="snap-pane on">
          ${ICON.windowLg}
          <strong>Chrome · snapped left</strong>
          <code>bounds (0, 0, 960, 1080)</code>
        </div>
        <div class="snap-pane off">Snap Assist<br>choose a second app</div>
      </div>`
  },
  screen_lens: {
    title: "Screen Lens — Gemini 2.5 Flash vision",
    tier: "Tier 3 · Cloud vision (420 ms)",
    state: "◉ Analyzed",
    transcript: "Win + Shift + Space — “What does this error mean?”",
    logs: [
      [ICON.camera, "Captured screen bitmap (1920×1080)"],
      [ICON.spark, "Gemini Vision parsed stack trace in 420 ms"]
    ],
    render: () => `
      <div class="stage-card lens">
        <div class="lens-err">● TypeError: Cannot read property 'map' of undefined <span class="lens-tag">Screen Lens</span></div>
        <div class="lens-stack">at UserList (components/Users.tsx:42:15)<br>at renderWithHooks (react-dom.development.js:16305)</div>
        <div class="lens-fix">
          <span class="scanline"></span>
          <strong>Suggested fix</strong>
          <code>users</code> is <code>undefined</code> until the fetch finishes. Use <code>users?.map(…)</code> on line 42, or initialise the state as <code>[]</code>.
        </div>
      </div>`
  },
  spec_dictation: {
    title: "Speculative dictation — sub-100 ms streaming",
    tier: "Speculative engine (<100 ms)",
    state: "⚡ Typing",
    transcript: "Holding Ctrl + Shift — “The market response to autonomous desktop workflows…”",
    logs: [
      [ICON.mic, "Ctrl + Shift held: streaming chunks 1 & 2"],
      [ICON.bolt, "Whisper Large v3 pre-transcription done"],
      [ICON.rocket, "Keys released: typed 14 words in 68 ms"]
    ],
    render: () => `
      <div class="stage-card doc">
        <div class="doc-head">Active document — WordPad <span>Real-time</span></div>
        <p id="typeTarget"></p>
      </div>`,
    after: (stage) => typeOut(stage.querySelector("#typeTarget"),
      "The market response to autonomous desktop workflows has exceeded our expectations. By combining native OS accessibility with speculative transcription, Handless removes the friction.")
  }
};

let typeTimer = null;
function typeOut(el, text) {
  if (!el) return;
  clearInterval(typeTimer);
  if (REDUCED_MOTION) { el.innerHTML = text + '<span class="caret"></span>'; return; }
  const words = text.split(" ");
  let i = 0;
  typeTimer = setInterval(() => {
    i++;
    el.innerHTML = words.slice(0, i).join(" ") + '<span class="caret"></span>';
    if (i >= words.length) clearInterval(typeTimer);
  }, 70);
}

function initVoiceSimulator() {
  const cmds = document.querySelectorAll(".cmd");
  const stage = document.getElementById("stagePlaceholder");
  const els = {
    title: document.getElementById("simTitle"),
    tier: document.getElementById("simTierBadge"),
    state: document.getElementById("simActionState"),
    transcript: document.getElementById("simTranscript"),
    log: document.getElementById("simActionLog")
  };
  if (!cmds.length || !stage) return;

  const show = (key) => {
    const cmd = SIM_COMMANDS[key];
    if (!cmd) return;
    clearInterval(typeTimer);
    els.title.textContent = cmd.title;
    els.tier.textContent = cmd.tier;
    els.state.textContent = cmd.state;
    els.transcript.textContent = cmd.transcript;
    els.log.innerHTML = cmd.logs
      .map(([icon, text], i) => `<li style="animation-delay:${i * 180}ms">${icon}<span>${text}</span></li>`)
      .join("");
    stage.innerHTML = cmd.render();
    if (cmd.after) cmd.after(stage);
  };

  cmds.forEach(btn => {
    btn.addEventListener("click", () => {
      cmds.forEach(b => {
        b.classList.toggle("active", b === btn);
        b.setAttribute("aria-selected", String(b === btn));
      });
      btn.scrollIntoView({ block: "nearest", inline: "center", behavior: REDUCED_MOTION ? "auto" : "smooth" });
      show(btn.dataset.cmd);
    });
  });

  show("set_volume");
}

// ------------------------------------------------------------
// 5. Clipboard helpers
// ------------------------------------------------------------
function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
  // Fallback for older mobile browsers
  return new Promise((resolve, reject) => {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    ok ? resolve() : reject(new Error("copy failed"));
  });
}

function initCopyInstall() {
  const btn = document.getElementById("copyInstall");
  const code = document.getElementById("installCode");
  if (!btn || !code) return;

  btn.addEventListener("click", () => {
    copyText(code.innerText).then(() => {
      btn.textContent = "Copied";
      btn.classList.add("copied");
      setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 2000);
    }).catch(() => { btn.textContent = "Press Ctrl+C"; });
  });
}

// ------------------------------------------------------------
// 6. Mobile & Android experience
// ------------------------------------------------------------
function initMobileSupport() {
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
    || (navigator.maxTouchPoints > 1 && /Macintosh/.test(navigator.userAgent)); // iPadOS

  const notice = document.getElementById("deviceNotice");
  const noticeClose = document.getElementById("deviceNoticeClose");
  const modal = document.getElementById("mobileModal");
  const modalClose = document.getElementById("modalClose");
  const btnCopyLink = document.getElementById("btnCopyDesktopLink");

  if (notice && isMobile && store("handless_notice_closed") !== "1") {
    notice.hidden = false;
    noticeClose.addEventListener("click", () => {
      notice.hidden = true;
      store("handless_notice_closed", "1");
    });
  }

  if (!modal) return;

  const openModal = () => {
    modal.hidden = false;
    document.body.style.overflow = "hidden";
    modalClose.focus();
  };
  const closeModal = () => {
    modal.hidden = true;
    document.body.style.overflow = "";
  };

  // Phones get a "send it to your PC" sheet instead of a 88 MB download
  document.querySelectorAll(".download-trigger").forEach(btn => {
    btn.addEventListener("click", e => {
      if (!isMobile) return;
      e.preventDefault();
      openModal();
    });
  });

  modalClose.addEventListener("click", closeModal);
  modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });
  document.addEventListener("keydown", e => { if (e.key === "Escape" && !modal.hidden) closeModal(); });

  if (btnCopyLink) {
    const label = btnCopyLink.querySelector("span");
    btnCopyLink.addEventListener("click", () => {
      copyText(DOWNLOAD_URL).then(() => {
        label.textContent = "Link copied — paste it on your PC";
        setTimeout(() => { label.textContent = "Copy PC download link"; }, 2500);
      }).catch(() => { label.textContent = "Couldn't copy — long-press the link below"; });
    });
  }
}
