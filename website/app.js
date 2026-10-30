// ============================================================
// Vyoma Handless™ — Official Landing Page JavaScript
// 3D Canvas Orb | Interactive Voice Simulator | Accordion
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  initOrbCanvas();
  initVoiceSimulator();
  initFaqAccordion();
  initMobileSupport();
});

// ------------------------------------------------------------
// 1. 3D Geometric Canvas Orb Animation (Gemini Live Replica)
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
  const radius = width * 0.36;

  // Generate points on a sphere (Fibonacci sphere algorithm)
  const numPoints = 120;
  const points = [];
  const phi = (1 + Math.sqrt(5)) / 2; // Golden ratio

  for (let i = 0; i < numPoints; i++) {
    const theta = 2 * Math.PI * i / phi;
    const y = 1 - (i / (numPoints - 1)) * 2; // y goes from 1 to -1
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

    angleX += 0.006;
    angleY += 0.009;
    pulse += 0.04;
    const pulseFactor = 1 + Math.sin(pulse) * 0.05;

    // Projected 2D points
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
      const distance = 400;
      const fov = distance / (distance + z2);
      const px = cx + x2 * fov;
      const py = cy + y2 * fov;
      const alpha = (z2 + radius) / (2 * radius); // Depth opacity

      projected.push({ x: px, y: py, z: z2, alpha: Math.max(0.15, Math.min(1, alpha)) });
    }

    // Sort by depth for correct z-index rendering
    projected.sort((a, b) => a.z - b.z);

    // Draw connecting lines between nearby points
    ctx.lineWidth = 0.75;
    for (let i = 0; i < projected.length; i++) {
      for (let j = i + 1; j < projected.length; j++) {
        const dx = projected[i].x - projected[j].x;
        const dy = projected[i].y - projected[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 42) {
          const lineAlpha = (1 - dist / 42) * 0.25 * projected[i].alpha;
          ctx.strokeStyle = `rgba(167, 119, 227, ${lineAlpha})`;
          ctx.beginPath();
          ctx.moveTo(projected[i].x, projected[i].y);
          ctx.lineTo(projected[j].x, projected[j].y);
          ctx.stroke();
        }
      }
    }

    // Draw points
    for (let i = 0; i < projected.length; i++) {
      const p = projected[i];
      const pRadius = Math.max(1.2, 2.4 * (p.z + radius) / (2 * radius));

      ctx.beginPath();
      ctx.arc(p.x, p.y, pRadius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(180, 160, 255, ${p.alpha * 0.9})`;
      ctx.shadowColor = "#9b6cf8";
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;
    }

    requestAnimationFrame(render);
  }

  render();
}

// ------------------------------------------------------------
// 2. Interactive Voice Simulator
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
      <div style="width: 100%; max-width: 480px; background: #111b21; border-radius: 12px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 30px rgba(0,0,0,0.5); font-family: sans-serif;">
        <div style="background: #202c33; padding: 10px 14px; display: flex; align-items: center; gap: 10px; border-bottom: 1px solid rgba(255,255,255,0.06);">
          <div style="width: 32px; height: 32px; border-radius: 50%; background: #00a884; display: flex; align-items: center; justify-content: center; font-weight: bold; color: white; font-size: 13px;">V</div>
          <div>
            <div style="color: #e9edef; font-size: 13px; font-weight: 600;">Vaishu</div>
            <div style="color: #8696a0; font-size: 11px;">online • Selected by Handless</div>
          </div>
        </div>
        <div style="height: 140px; padding: 12px; background: #0b141a; display: flex; flex-direction: column; justify-content: flex-end; gap: 8px;">
          <div style="align-self: flex-start; background: #202c33; color: #e9edef; padding: 6px 12px; border-radius: 8px; font-size: 12px; max-width: 80%;">
            Hey, are we still meeting today?
          </div>
          <div style="align-self: flex-end; background: #005c4b; color: #e9edef; padding: 6px 12px; border-radius: 8px; font-size: 12px; max-width: 80%; display: flex; align-items: center; gap: 4px;">
            <span>hi</span>
            <span style="font-size: 9px; opacity: 0.6; margin-left: 4px;">Just now ✓✓</span>
          </div>
        </div>
        <div style="background: #202c33; padding: 8px 12px; display: flex; align-items: center; gap: 8px;">
          <div style="flex: 1; background: #2a3942; border-radius: 8px; padding: 6px 12px; color: #e9edef; font-size: 12px; display: flex; align-items: center;">
            <span style="opacity: 0.4;">Type a message</span>
            <span style="width: 2px; height: 14px; background: #00a884; margin-left: 2px; animation: pulse 1s infinite;"></span>
          </div>
          <div style="color: #8696a0; font-size: 16px;">🎤</div>
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
      <div style="width: 100%; max-width: 480px; height: 210px; background: #161922; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 8px;">
        <div style="background: rgba(147, 112, 219, 0.15); border: 2px solid #9b6cf8; border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px;">
          <div style="font-size: 24px;">🪟</div>
          <span style="font-size: 12px; font-weight: 700; color: #c4b5fd;">Chrome (Snapped 50% Left)</span>
          <span style="font-size: 10px; color: #959cb3;">Bounds: (0, 0, 960, 1080)</span>
        </div>
        <div style="background: rgba(255,255,255,0.02); border: 1px dashed rgba(255,255,255,0.15); border-radius: 8px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;">
          <span style="font-size: 11px; color: #656b82;">Desktop / Snap Assist</span>
          <span style="font-size: 9px; color: #656b82;">Choose secondary app</span>
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
      <div style="width: 100%; max-width: 480px; background: #0c0d14; border-radius: 12px; border: 1px solid rgba(0,210,255,0.4); padding: 16px; box-shadow: 0 0 25px rgba(0,210,255,0.15); font-family: monospace;">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
          <span style="color: #ff5f56; font-size: 12px; font-weight: bold;">● TypeError: Cannot read property 'map' of undefined</span>
          <span style="font-size: 10px; padding: 2px 6px; background: rgba(0,210,255,0.15); color: #00d2ff; border-radius: 4px;">Screen Lens OCR</span>
        </div>
        <div style="background: rgba(255,255,255,0.03); padding: 10px; border-radius: 6px; font-size: 11px; color: #959cb3; margin-bottom: 12px; border-left: 2px solid #ff5f56;">
          at UserList (components/Users.tsx:42:15)<br>
          at renderWithHooks (react-dom.development.js:16305)
        </div>
        <div style="background: rgba(0,210,255,0.08); border-radius: 6px; padding: 10px; font-size: 12px; color: #e2e8f0; font-family: var(--font-sans); border: 1px solid rgba(0,210,255,0.2);">
          <strong style="color: #00d2ff;">💡 Handless AI Explanation:</strong>
          <p style="margin-top: 4px; font-size: 11px; color: #cbd5e1; line-height: 1.4;">
            Your <code style="color: #c4b5fd;">users</code> state variable is initially <code style="color: #c4b5fd;">undefined</code> before the API request completes. Change line 42 to <code style="color: #38ef7d;">users?.map(...)</code> or provide default value <code style="color: #38ef7d;">[]</code>.
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
      <div style="width: 100%; max-width: 480px; background: #13151f; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.06);">
          <span style="font-size: 12px; font-weight: 700; color: #e2e8f0;">Active Document — Notepad</span>
          <span style="font-size: 10px; padding: 2px 8px; background: rgba(56, 239, 125, 0.15); color: #38ef7d; border-radius: 10px; font-weight: 600;">Sub-100ms Realtime</span>
        </div>
        <p style="font-size: 14px; line-height: 1.6; color: #f0f2f8; font-family: serif;">
          The market response to autonomous desktop workflows has exceeded our expectations. By combining native OS accessibility with speculative transcription, Handless completely eliminates friction<span style="display: inline-block; width: 2px; height: 16px; background: #9b6cf8; vertical-align: middle; margin-left: 2px; animation: pulse 0.8s infinite;"></span>
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

      // Update UI elements
      if (simTitle) simTitle.textContent = cmd.title;
      if (simTierBadge) simTierBadge.textContent = cmd.tier;
      if (simActionState) simActionState.textContent = cmd.state;
      if (simTranscript) simTranscript.textContent = cmd.transcript;

      // Update Action Logs
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

      // Update Canvas Stage
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

      // Close all other items
      faqItems.forEach(other => other.classList.remove("active"));

      // Toggle clicked item
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
      copyBtn.style.background = "#10b981";
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

// Expose copyCode globally for onclick handler in HTML
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
        // Intercept download and show friendly guidance modal
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
      const url = "https://github.com/vyomagroupofficial-lab/handless/releases";
      navigator.clipboard.writeText(url).then(() => {
        const originalText = btnCopyDesktop.innerText;
        btnCopyDesktop.innerText = "✓ Link Copied to Clipboard!";
        btnCopyDesktop.style.background = "#10b981";

        setTimeout(() => {
          btnCopyDesktop.innerText = originalText;
          btnCopyDesktop.style.background = "";
        }, 2500);
      }).catch(err => {
        console.error("Failed to copy link:", err);
      });
    });
  }
}


