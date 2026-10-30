// ============================================================
// Vyoma Handless™ — Official Production JavaScript
// Light Cream Theme | 3D Canvas Orb | Mobile & Android Handler
// Hostinger (handless.vyomagroup.online)
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  initOrbCanvas();
  initVoiceSimulator();
  initFaqAccordion();
  initMobileSupport();
});

// ------------------------------------------------------------
// 1. 3D Geometric Canvas Orb Animation (Cream Theme Palette)
// ------------------------------------------------------------
function initOrbCanvas() {
  const canvas = document.getElementById("orbCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  // Handle Retina displays
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const width = rect.width;
  const height = rect.height;
  const cx = width / 2;
  const cy = height / 2;
  const radius = width * 0.35;

  // Generate points on a sphere (Fibonacci sphere algorithm)
  const numPoints = 120;
  const points = [];
  const phi = (1 + Math.sqrt(5)) / 2; // Golden ratio

  for (let i = 0; i < numPoints; i++) {
    const theta = 2 * Math.PI * i / phi;
    const y = 1 - (i / (numPoints - 1)) * 2;
    const radiusAtY = Math.sqrt(1 - y * y);
    const x = Math.cos(theta) * radiusAtY;
    const z = Math.sin(theta) * radiusAtY;
    points.push({ x: x * radius, y: y * radius, z: z * radius });
  }

  let angleX = 0;
  let angleY = 0;
  let pulse = 0;

  function render() {
    ctx.clearRect(0, 0, width, height);

    angleX += 0.005;
    angleY += 0.008;
    pulse += 0.035;
    const pulseFactor = 1 + Math.sin(pulse) * 0.04;

    const projected = [];
    const cosX = Math.cos(angleX);
    const sinX = Math.sin(angleX);
    const cosY = Math.cos(angleY);
    const sinY = Math.sin(angleY);

    for (let i = 0; i < points.length; i++) {
      const p = points[i];

      // Rotate Y
      let x1 = p.x * cosY + p.z * sinY;
      let y1 = p.y;
      let z1 = -p.x * sinY + p.z * cosY;

      // Rotate X
      let x2 = x1;
      let y2 = y1 * cosX - z1 * sinX;
      let z2 = y1 * sinX + z1 * cosX;

      // Pulse scaling
      x2 *= pulseFactor;
      y2 *= pulseFactor;
      z2 *= pulseFactor;

      // Perspective projection
      const distance = 420;
      const fov = distance / (distance + z2);
      const px = cx + x2 * fov;
      const py = cy + y2 * fov;
      const alpha = (z2 + radius) / (2 * radius);

      projected.push({ x: px, y: py, z: z2, alpha: Math.max(0.18, Math.min(1, alpha)) });
    }

    // Sort points back to front
    projected.sort((a, b) => a.z - b.z);

    // Draw connecting lines (refined warm violet/indigo against cream)
    ctx.lineWidth = 0.85;
    for (let i = 0; i < projected.length; i++) {
      for (let j = i + 1; j < projected.length; j++) {
        const dx = projected[i].x - projected[j].x;
        const dy = projected[i].y - projected[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 40) {
          const lineAlpha = (1 - dist / 40) * 0.28 * projected[i].alpha;
          ctx.strokeStyle = `rgba(109, 40, 217, ${lineAlpha})`;
          ctx.beginPath();
          ctx.moveTo(projected[i].x, projected[i].y);
          ctx.lineTo(projected[j].x, projected[j].y);
          ctx.stroke();
        }
      }
    }

    // Draw points (rich violet/indigo nodes)
    for (let i = 0; i < projected.length; i++) {
      const p = projected[i];
      const pRadius = Math.max(1.2, 2.5 * (p.z + radius) / (2 * radius));

      ctx.beginPath();
      ctx.arc(p.x, p.y, pRadius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(91, 33, 182, ${p.alpha * 0.85})`;
      ctx.shadowColor = "rgba(109, 40, 217, 0.4)";
      ctx.shadowBlur = 6;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    requestAnimationFrame(render);
  }

  render();
}

// ------------------------------------------------------------
// 2. Interactive Voice Simulator (Light Cream Styled)
// ------------------------------------------------------------
const SIM_COMMANDS = {
  set_volume: {
    title: "Windows 11 Desktop — Master Audio Control",
    tier: "Tier 1: Local Rule (<5ms)",
    state: "Done ✓",
    transcript: '"Set my volume to 80%"',
    logs: [
      { icon: "⚡", text: "Matched Rule: SetVolume(80)" },
      { icon: "🔊", text: "IAudioEndpointVolume: 0.80 applied" }
    ],
    render: () => `
      <div class="hud-box">
        <div class="hud-slider-track">
          <div class="hud-slider-fill" style="width: 80%;"></div>
        </div>
        <span class="hud-label">🔊 Master Volume Adjusted to 80%</span>
      </div>
    `
  },
  whatsapp_msg: {
    title: "WhatsApp Web (Chrome CDP Pierced) — Vyoma Handless",
    tier: "Tier 1: Local Chained Rule (<15ms)",
    state: "Chained Done ✓",
    transcript: '"Select Vaishu and type hi"',
    logs: [
      { icon: "🔗", text: "Chained 2 actions: Click contact -> Type text" },
      { icon: "👉", text: "Clicked contact: 'Vaishu' (WhatsApp list item)" },
      { icon: "⌨️", text: "Typed 'hi' into 'Type a message' box" }
    ],
    render: () => `
      <div style="width: 100%; max-width: 460px; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid rgba(80,60,40,0.12); box-shadow: var(--shadow-md); font-family: sans-serif;">
        <div style="background: #f0ebe1; padding: 10px 14px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(80,60,40,0.08);">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: #059669; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white; font-size: 13px;">V</div>
          <div>
            <div style="color: #1c1917; font-size: 13px; font-weight: 700;">Vaishu</div>
            <div style="color: #78716c; font-size: 11px;">online • Handless Selected Target</div>
          </div>
        </div>
        <div style="height: 130px; padding: 12px; background: #faf7f2; display: flex; flex-direction: column; justify-content: flex-end; gap: 8px;">
          <div style="align-self: flex-start; background: #ffffff; color: #1c1917; padding: 6px 12px; border-radius: 8px; font-size: 12px; max-width: 80%; border: 1px solid rgba(80,60,40,0.08);">
            Hey, are we still meeting today?
          </div>
          <div style="align-self: flex-end; background: #d1fae5; color: #065f46; padding: 6px 12px; border-radius: 8px; font-size: 12px; max-width: 80%; display: flex; align-items: center; gap: 4px; border: 1px solid #a7f3d0;">
            <span style="font-weight: 600;">hi</span>
            <span style="font-size: 9px; opacity: 0.7; margin-left: 4px;">Just now ✓✓</span>
          </div>
        </div>
        <div style="background: #ffffff; padding: 8px 12px; display: flex; align-items: center; gap: 8px; border-top: 1px solid rgba(80,60,40,0.08);">
          <div style="flex: 1; background: #f5f0e8; border-radius: 8px; padding: 6px 12px; color: #1c1917; font-size: 12px; display: flex; align-items: center;">
            <span style="opacity: 0.6;">Type a message</span>
            <span style="width: 2px; height: 14px; background: #059669; margin-left: 2px; animation: pulse 1s infinite;"></span>
          </div>
          <div style="color: #78716c; font-size: 16px;">🎤</div>
        </div>
      </div>
    `
  },
  snap_left: {
    title: "Windows 11 Snap Assist — Layout Manager",
    tier: "Tier 1: System Hotkey (Win+Left)",
    state: "Snapped ✓",
    transcript: '"Snap window to the left"',
    logs: [
      { icon: "🪟", text: "Target active window: Chrome" },
      { icon: "⚡", text: "Dispatched hotkey: Win + Left" }
    ],
    render: () => `
      <div style="width: 100%; max-width: 460px; height: 200px; background: #ffffff; border-radius: 12px; border: 1px solid rgba(80,60,40,0.12); display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 8px; box-shadow: var(--shadow-md);">
        <div style="background: #ede9fe; border: 2px solid #6d28d9; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;">
          <div style="font-size: 22px;">🪟</div>
          <span style="font-size: 12px; font-weight: 700; color: #5b21b6;">Chrome (Snapped 50% Left)</span>
          <span style="font-size: 10px; color: #78716c;">Bounds: (0, 0, 960, 1080)</span>
        </div>
        <div style="background: #faf7f2; border: 1px dashed rgba(80,60,40,0.2); border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px;">
          <span style="font-size: 11px; font-weight: 600; color: #78716c;">Desktop / Snap Assist</span>
          <span style="font-size: 9px; color: #a8a29e;">Choose secondary app</span>
        </div>
      </div>
    `
  },
  screen_lens: {
    title: "Screen Lens — Gemini 2.5 Flash Vision Grounding",
    tier: "Tier 3: Cloud Gemini Vision (420ms)",
    state: "Analyzed 👁️",
    transcript: '"Screen lens: explain this error"',
    logs: [
      { icon: "📸", text: "Captured screen bitmap (1920x1080)" },
      { icon: "🧠", text: "Gemini Vision parsed stacktrace in 420ms" }
    ],
    render: () => `
      <div style="width: 100%; max-width: 460px; background: #ffffff; border-radius: 12px; border: 1px solid rgba(109,40,217,0.3); padding: 16px; box-shadow: var(--shadow-md); font-family: monospace;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
          <span style="color: #dc2626; font-size: 12px; font-weight: bold;">● TypeError: Cannot read property 'map' of undefined</span>
          <span style="font-size: 10px; padding: 2px 6px; background: #ede9fe; color: #6d28d9; border-radius: 4px; font-weight: bold;">Screen Lens OCR</span>
        </div>
        <div style="background: #f5f0e8; padding: 8px 10px; border-radius: 6px; font-size: 11px; color: #44403c; margin-bottom: 12px; border-left: 3px solid #dc2626;">
          at UserList (components/Users.tsx:42:15)<br>
          at renderWithHooks (react-dom.development.js:16305)
        </div>
        <div style="background: #faf5ff; border-radius: 6px; padding: 10px; font-size: 12px; color: #1c1917; font-family: var(--font-sans); border: 1px solid #ddd6fe;">
          <strong style="color: #6d28d9;">💡 Handless AI Solution:</strong>
          <p style="margin-top: 4px; font-size: 11px; color: #44403c; line-height: 1.45;">
            Your <code style="color: #5b21b6; background: #ede9fe; padding: 1px 4px; border-radius: 3px;">users</code> state variable is <code style="color: #5b21b6;">undefined</code> prior to fetch completion. Update line 42 to <code style="color: #059669; font-weight: bold;">users?.map(...)</code> or initialize state as <code style="color: #059669; font-weight: bold;">[]</code>.
          </p>
        </div>
      </div>
    `
  },
  spec_dictation: {
    title: "Wispr Flow Dictation — Sub-100ms Speculative Streaming",
    tier: "Speculative Engine (<100ms)",
    state: "Typing ⚡",
    transcript: '"Hold F8: The market response to autonomous desktop workflows has exceeded our expectations..."',
    logs: [
      { icon: "🎙️", text: "F8 key down: Speculative streaming chunk 1 & 2" },
      { icon: "⚡", text: "Whisper Large v3 pre-transcription completed" },
      { icon: "🚀", text: "F8 released: Typed 14 words in 68ms" }
    ],
    render: () => `
      <div style="width: 100%; max-width: 460px; background: #ffffff; border-radius: 12px; border: 1px solid rgba(80,60,40,0.12); padding: 18px; box-shadow: var(--shadow-md);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid rgba(80,60,40,0.08);">
          <span style="font-size: 12px; font-weight: 700; color: #1c1917;">Active Document — WordPad</span>
          <span style="font-size: 10px; padding: 2px 8px; background: #ecfdf5; color: #047857; border-radius: 10px; font-weight: 700;">Sub-100ms Realtime</span>
        </div>
        <p style="font-size: 13.5px; line-height: 1.6; color: #292524; font-family: serif;">
          The market response to autonomous desktop workflows has exceeded our expectations. By combining native OS accessibility with speculative transcription, Handless completely eliminates friction<span style="display: inline-block; width: 2px; height: 16px; background: #6d28d9; vertical-align: middle; margin-left: 2px; animation: pulse 0.8s infinite;"></span>
        </p>
      </div>
    `
  }
};

function initVoiceSimulator() {
  const pills = document.querySelectorAll(".cmd-pill");
  const simTitle = document.getElementById("simTitle");
  const simTierBadge = document.getElementById("simTierBadge");
  const simActionState = document.getElementById("simActionState");
  const simTranscript = document.getElementById("simTranscript");
  const simActionLog = document.getElementById("simActionLog");
  const stagePlaceholder = document.getElementById("stagePlaceholder");

  if (!pills.length || !stagePlaceholder) return;

  pills.forEach(pill => {
    pill.addEventListener("click", () => {
      pills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");

      const cmdKey = pill.getAttribute("data-cmd");
      const cmd = SIM_COMMANDS[cmdKey];
      if (!cmd) return;

      if (simTitle) simTitle.textContent = cmd.title;
      if (simTierBadge) simTierBadge.textContent = cmd.tier;
      if (simActionState) simActionState.textContent = cmd.state;
      if (simTranscript) simTranscript.textContent = cmd.transcript;

      if (simActionLog) {
        simActionLog.innerHTML = cmd.logs
          .map(log => `
            <div class="log-entry">
              <span class="log-icon">${log.icon}</span>
              <span class="log-text">${log.text}</span>
            </div>
          `)
          .join("");
      }

      stagePlaceholder.innerHTML = cmd.render();
    });
  });
}

// ------------------------------------------------------------
// 3. FAQ Accordion Interactivity
// ------------------------------------------------------------
function initFaqAccordion() {
  const faqItems = document.querySelectorAll(".faq-item");

  faqItems.forEach(item => {
    const btn = item.querySelector(".faq-question");
    if (!btn) return;

    btn.addEventListener("click", () => {
      const isActive = item.classList.contains("active");
      faqItems.forEach(other => other.classList.remove("active"));
      if (!isActive) {
        item.classList.add("active");
      }
    });
  });
}

// ------------------------------------------------------------
// 4. Clipboard Copy Functionality
// ------------------------------------------------------------
function copyCode() {
  const codeEl = document.getElementById("installCode");
  if (!codeEl) return;

  const text = codeEl.innerText;
  navigator.clipboard.writeText(text).then(() => {
    const copyBtn = document.querySelector(".btn-copy");
    if (copyBtn) {
      const originalText = copyBtn.innerText;
      copyBtn.innerText = "Copied!";
      copyBtn.style.background = "#059669";
      copyBtn.style.color = "#fff";

      setTimeout(() => {
        copyBtn.innerText = originalText;
        copyBtn.style.background = "";
        copyBtn.style.color = "";
      }, 2000);
    }
  }).catch(err => {
    console.error("Failed to copy code:", err);
  });
}

window.copyCode = copyCode;

// ------------------------------------------------------------
// 5. Mobile & Android Experience Handler
// ------------------------------------------------------------
function initMobileSupport() {
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth <= 820;
  const isAndroid = /Android/i.test(navigator.userAgent);

  const banner = document.getElementById("mobileDeviceBanner");
  const bannerClose = document.getElementById("bannerClose");
  const toggleBtn = document.getElementById("mobileToggleBtn");
  const drawer = document.getElementById("mobileNavDrawer");
  const modal = document.getElementById("mobileModal");
  const modalClose = document.getElementById("modalClose");
  const btnCopyDesktop = document.getElementById("btnCopyDesktopLink");

  // Show banner if mobile
  if (banner) {
    if (sessionStorage.getItem("handless_mobile_banner_closed") === "true") {
      banner.style.display = "none";
    } else {
      banner.style.display = "block";
    }

    if (bannerClose) {
      bannerClose.addEventListener("click", () => {
        banner.style.display = "none";
        sessionStorage.setItem("handless_mobile_banner_closed", "true");
      });
    }
  }

  // Mobile Hamburger Navigation Drawer
  if (toggleBtn && drawer) {
    toggleBtn.addEventListener("click", () => {
      const isOpen = drawer.classList.contains("open");
      if (isOpen) {
        drawer.classList.remove("open");
        toggleBtn.classList.remove("open");
      } else {
        drawer.classList.add("open");
        toggleBtn.classList.add("open");
      }
    });

    const drawerLinks = drawer.querySelectorAll(".drawer-link");
    drawerLinks.forEach(link => {
      link.addEventListener("click", () => {
        drawer.classList.remove("open");
        toggleBtn.classList.remove("open");
      });
    });
  }

  // Intercept Download clicks on Mobile / Android
  const downloadTriggers = document.querySelectorAll(".download-trigger");
  downloadTriggers.forEach(btn => {
    btn.addEventListener("click", (e) => {
      if (isMobile || isAndroid) {
        e.preventDefault();
        if (modal) {
          modal.classList.add("open");
        }
      }
    });
  });

  // Modal Close Listeners
  if (modalClose && modal) {
    modalClose.addEventListener("click", () => {
      modal.classList.remove("open");
    });

    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        modal.classList.remove("open");
      }
    });
  }

  // Copy Desktop Link Handler
  if (btnCopyDesktop) {
    btnCopyDesktop.addEventListener("click", () => {
      const url = "https://handless.vyomagroup.online/downloads/VyomaHandless-v0.1.0-windows-x64.zip";
      navigator.clipboard.writeText(url).then(() => {
        const originalText = btnCopyDesktop.innerText;
        btnCopyDesktop.innerText = "✓ Direct PC Link Copied!";
        btnCopyDesktop.style.background = "#059669";
        btnCopyDesktop.style.color = "#ffffff";

        setTimeout(() => {
          btnCopyDesktop.innerText = originalText;
          btnCopyDesktop.style.background = "";
          btnCopyDesktop.style.color = "";
        }, 2500);
      }).catch(err => {
        console.error("Failed to copy link:", err);
      });
    });
  }
}

