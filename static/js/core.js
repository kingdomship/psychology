// @ts-check
// ═══════════════════════════════════════════
// core.js — 工具函数 + DOM引用 + 状态机 + Canvas
// ═══════════════════════════════════════════

function escapeHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

// ── Toast 通知 (替代 alert) ──
var _toastTimer = null;
function showToast(msg, type) {
  type = type || 'info';
  var icons = { error: '✕', success: '✓', warning: '!', info: 'i' };
  var container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  var el = document.createElement('div');
  el.className = 'toast ' + type;
  el.innerHTML = '<span class="toast-icon">' + (icons[type] || 'i') + '</span><span class="toast-msg">' + escapeHtml(msg) + '</span>';
  container.appendChild(el);
  // 自动移除
  setTimeout(function() {
    if (el.parentNode) el.parentNode.removeChild(el);
  }, 3200);
  // 点击立即关闭
  el.addEventListener('click', function() {
    if (el.parentNode) el.parentNode.removeChild(el);
  });
}

// Emoji regex for choice-button detection
var EMOJI_RE = /[☀-➿🇦-🇿🌀-🗿😀-🙏🚀-🛿🤀-🧿‍️]/gu;
var EMOJI_SPLIT_RE = /(?=[☀-➿🇦-🇿🌀-🗿😀-🙏🚀-🛿🤀-🧿])/u;

// ═══════════════════════════════════════════
// DOM refs
// ═══════════════════════════════════════════
var canvas = /** @type {HTMLCanvasElement} */ (document.getElementById('c'));
var ctx = canvas.getContext('2d');
var inputRow = document.getElementById('input-row');
var textarea = /** @type {HTMLTextAreaElement} */ (document.getElementById('input'));
var sendBtn = /** @type {HTMLButtonElement} */ (document.getElementById('sendBtn'));
var kaomojiBtn = document.getElementById('kaomojiBtn');
var kaomojiPanel = document.getElementById('kaomoji-panel');
var charCount = document.getElementById('charCount');
var dialog = document.getElementById('dialog');
var dlgBody = document.getElementById('dlgBody');
var dlgClose = document.getElementById('dlgClose');
var topicBubbles = document.getElementById('topic-bubbles');
var auxPanel = document.getElementById('aux-panel');
var auxContent = document.getElementById('auxContent');

// Settings
var settingsModal = document.getElementById('settings-modal');
var settingsOverlay = document.getElementById('settingsOverlay');
var settingsClose = document.getElementById('settingsClose');
var settingsSave = document.getElementById('settingsSave');
var settingsClear = document.getElementById('settingsClear');
var providerSelect = /** @type {HTMLSelectElement} */ (document.getElementById('providerSelect'));
var baseUrlInput = /** @type {HTMLInputElement} */ (document.getElementById('baseUrlInput'));
var modelInput = /** @type {HTMLInputElement} */ (document.getElementById('modelInput'));
var modelHint = /** @type {HTMLElement} */ (document.getElementById('modelHint'));
var apiKeyInput = /** @type {HTMLInputElement} */ (document.getElementById('apiKeyInput'));
var settingsStatus = /** @type {HTMLElement} */ (document.getElementById('settingsStatus'));

var auxBack = document.getElementById('auxBack');
var soundToggle = document.getElementById('sound-toggle');

// ═══════════════════════════════════════════
// 场景练习全局状态
// ═══════════════════════════════════════════
var scenarioSessionId = '';
var scenarioAiRole = '';

// ═══════════════════════════════════════════
// State machine
// ═══════════════════════════════════════════
var STATE = { STARFIELD:'starfield', CONVERGING:'converging', CHAT:'chat', AUXILIARY:'auxiliary', CONSTELLATION:'constellation', BREATHING:'breathing' };
var state = STATE.STARFIELD;

// Breathing exercise state
var breathingPhase = 'inhale';
var breathingTimer = 0;
var breathingStartTime = 0;
var breathingPattern = { inhale: 4, hold: 4, exhale: 4, pause: 2 };
var breathingDuration = 120;

// ═══════════════════════════════════════════
// Sound toggle
// ═══════════════════════════════════════════
var soundOn = true;

soundToggle.addEventListener('click', function() {
  soundOn = !soundOn;
  soundToggle.textContent = soundOn ? '🔊' : '🔇';
  soundToggle.classList.toggle('muted', !soundOn);
});

// ═══════════════════════════════════════════
// Canvas sizing
// ═══════════════════════════════════════════
function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  if (state === STATE.CHAT && typeof updateFacePixelTargets === 'function') updateFacePixelTargets();
}
window.addEventListener('resize', resize);
resize();
