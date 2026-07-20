// ═══════════════════════════════════════════
// Long press detection
// ═══════════════════════════════════════════
let pressTimer = null, pressStartX = 0, pressStartY = 0;
const LONG_PRESS_DURATION = 1000;
const MOVE_THRESHOLD = 10;

canvas.addEventListener('pointerdown', e => {
  pressStartX = e.clientX;
  pressStartY = e.clientY;
  pressTimer = setTimeout(() => {
    if (state === STATE.STARFIELD || state === STATE.CHAT) {
      openAuxiliary('diary');
    }
  }, LONG_PRESS_DURATION);
});

canvas.addEventListener('pointermove', e => {
  if (!pressTimer) return;
  const dx = e.clientX - pressStartX;
  const dy = e.clientY - pressStartY;
  if (Math.abs(dx) > MOVE_THRESHOLD || Math.abs(dy) > MOVE_THRESHOLD) {
    clearTimeout(pressTimer);
    pressTimer = null;
  }
});

canvas.addEventListener('pointerup', () => {
  clearTimeout(pressTimer);
  pressTimer = null;
});

// Cursor tracking for constellation interaction
canvas.addEventListener('pointermove', e => {
  const r = canvas.getBoundingClientRect();
  cursorX = e.clientX - r.left;
  cursorY = e.clientY - r.top;
});

canvas.addEventListener('pointerleave', () => {
  clearTimeout(pressTimer);
  pressTimer = null;
  cursorX = null; cursorY = null;
});

// ═══════════════════════════════════════════
// Click to interact
// ═══════════════════════════════════════════
let clickCount = 0, clickTimer = null;

canvas.addEventListener('click', e => {
  if (state === STATE.AUXILIARY) return;
  const rect = canvas.getBoundingClientRect();
  const cx = e.clientX - rect.left, cy = e.clientY - rect.top;

  if (pressTimer === null && Math.abs(e.clientX - pressStartX) < MOVE_THRESHOLD) {
    // Check face click (poke interaction)
    if (state === STATE.CHAT) {
      const faceCX = canvas.width / 2;
      const faceCY = canvas.height / 2 + 5 * faceCS + faceBob;
      const faceR = 14 * faceCS;
      const dfx = cx - faceCX, dfy = cy - faceCY;
      if (Math.sqrt(dfx*dfx + dfy*dfy) < faceR) {
        triggerPokeReaction(cx, cy);
        return;
      }
    }

    // Check memory star click
    if ((state === STATE.STARFIELD || state === STATE.CHAT) && checkMemoryStarClick(cx, cy)) return;

    // Check if clicked a functional point in starfield
    if (state === STATE.STARFIELD) {
      for (const fp of functionalPoints) {
        const s = fp.star;
        const dx = cx - s.x, dy = cy - s.y;
        if (Math.sqrt(dx*dx + dy*dy) < s.size * 3) {
          openAuxiliary(fp.type === 'diary' ? 'diary' : 'mood');
          return;
        }
      }
    }

    // Count clicks for convergence trigger
    clickCount++;
    clearTimeout(clickTimer);
    clickTimer = setTimeout(() => { clickCount = 0; }, 600);
    if (clickCount >= 3 && state === STATE.STARFIELD) {
      clickCount = 0;
      startConvergence();
    }
  }
});

// ═══════════════════════════════════════════
// Input / Chat
// ═══════════════════════════════════════════
let pending = false;
let abortController = null;
let storyPaused = false;
let storyBuffer = [];
let batchMode = false;

function autoGrow() {
  textarea.style.height = 'auto';
  var h = Math.min(textarea.scrollHeight, 200);
  textarea.style.height = h + 'px';
  // Toggle expanded class for border-radius transition
  if (h > 50) inputRow.classList.add('expanded');
  else inputRow.classList.remove('expanded');
  // Character count
  var len = textarea.value.length;
  if (len > 350) {
    charCount.textContent = len + '/500';
    charCount.classList.add('visible');
    charCount.classList.toggle('warning', len > 460);
  } else {
    charCount.classList.remove('visible', 'warning');
  }
}

function resetTextarea() {
  textarea.value = '';
  textarea.style.height = 'auto';
  inputRow.classList.remove('expanded');
  charCount.classList.remove('visible', 'warning');
}

textarea.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
  if (state === STATE.STARFIELD) startConvergence();
});

textarea.addEventListener('input', autoGrow);

textarea.addEventListener('focus', () => {
  if (state === STATE.STARFIELD) startConvergence();
});

// ── Kaomoji picker ──

function renderKaomojiGrid(catId) {
  var cat = KAOMOJI_DATA[catId];
  if (!cat) return;
  activeKaomojiCat = catId;
  // Update category buttons
  var cats = kaomojiCats.querySelectorAll('.kaomoji-cat');
  cats.forEach(function(c) { c.classList.toggle('active', c.dataset.cat === catId); });
  // Render grid
  kaomojiGrid.innerHTML = cat.items.map(function(k) {
    return '<button class="kaomoji-item" data-kaomoji="' + escapeHtml(k) + '">' + escapeHtml(k) + '</button>';
  }).join('');
}

function toggleKaomojiPanel() {
  var open = kaomojiPanel.classList.contains('visible');
  if (open) { closeKaomojiPanel(); return; }
  // Render categories
  kaomojiCats.innerHTML = KAOMOJI_CATEGORIES.map(function(c) {
    return '<button class="kaomoji-cat' + (c.id === activeKaomojiCat ? ' active' : '') + '" data-cat="' + c.id + '">' + c.label + '</button>';
  }).join('');
  renderKaomojiGrid(activeKaomojiCat);
  kaomojiPanel.classList.add('visible');
  kaomojiBtn.classList.add('active');
}

function closeKaomojiPanel() {
  kaomojiPanel.classList.remove('visible');
  kaomojiBtn.classList.remove('active');
}

kaomojiBtn.addEventListener('click', e => {
  e.stopPropagation();
  toggleKaomojiPanel();
});

kaomojiCats.addEventListener('click', e => {
  var catBtn = e.target.closest('.kaomoji-cat');
  if (!catBtn) return;
  renderKaomojiGrid(catBtn.dataset.cat);
});

kaomojiGrid.addEventListener('click', e => {
  var item = e.target.closest('.kaomoji-item');
  if (!item) return;
  insertKaomoji(item.dataset.kaomoji);
  textarea.focus();
});

function insertKaomoji(k) {
  var start = textarea.selectionStart, end = textarea.selectionEnd;
  var before = textarea.value.substring(0, start);
  var after = textarea.value.substring(end);
  textarea.value = before + k + after;
  // Place cursor after the inserted kaomoji
  var pos = start + k.length;
  textarea.setSelectionRange(pos, pos);
  // Trigger auto-grow
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
  // Update char count
  autoGrow();
}

// Close panel on outside click
document.addEventListener('click', e => {
  if (kaomojiPanel.classList.contains('visible') &&
      !kaomojiPanel.contains(e.target) &&
      e.target !== kaomojiBtn && !kaomojiBtn.contains(e.target)) {
    closeKaomojiPanel();
  }
});

// Esc to close
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && kaomojiPanel.classList.contains('visible')) {
    closeKaomojiPanel();
    textarea.focus();
  }
});

function _applySceneStart(evt) {
  clearInterval(thinkingTimer);
  if (evt.emotions) setSequence(evt.emotions, '');
  if (evt.affect) updateMoodFromAffect(evt.affect);
  else if (evt.label) updateMoodFromEmotion(evt.label);
  if (evt.color_fields && Array.isArray(evt.color_fields)) {
    colorFieldsTarget = evt.color_fields.map(function(f) {
      return {
        color: f.color,
        cx: f.cx || 0.5, cy: f.cy || 0.5,
        radius: f.radius || 0.5,
        blend: f.blend || 'soft-light',
        opacity: f.opacity != null ? f.opacity : 0.9,
        blur: f.blur || 0,
        pulse: f.pulse || null,
        drift: f.drift || null
      };
    });
  }
  bgColorTarget = (evt.background && typeof evt.background === 'string') ? evt.background : null;
  if (evt.whiteboard && typeof parseWhiteboardCommands === 'function') {
    parseWhiteboardCommands(evt.whiteboard);
  }
}

function showStoryContinueBtn() {
  var existing = document.getElementById('story-continue-btn');
  if (existing) existing.remove();
  var btn = document.createElement('button');
  btn.id = 'story-continue-btn';
  btn.className = 'story-continue-btn';
  if (batchMode) {
    btn.classList.add('icon-only');
    btn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>';
  } else {
    btn.textContent = '▶ 下一段';
  }
  btn.addEventListener('click', function() {
    storyPaused = false;
    btn.remove();
    var text = dlgText || '';
    var buf = storyBuffer;
    storyBuffer = [];
    for (var i = 0; i < buf.length; i++) {
      var item = buf[i];
      if (item.type === 'scene_start') {
        _applySceneStart(item.evt);
      } else if (item.type === 'text') {
        text += item.evt.text;
        playTypingSound();
      } else if (item.type === 'scene_done') {
        text += '\n\n—— ✦ ——\n\n';
        dlgText = text;
        dlgBody.innerHTML = escapeHtml(text);
        if (item.evt.index != null && item.evt.total != null && item.evt.index < item.evt.total - 1) {
          storyPaused = true;
          showStoryContinueBtn();
          storyBuffer = buf.slice(i + 1);
          return;
        }
      } else if (item.type === 'done') {
        clearInterval(thinkingTimer);
        dlgText = text;
        dlgBody.innerHTML = escapeHtml(text);
        checkChoices(text);
        pending = false; sendBtn.disabled = false; textarea.focus();
        return;
      }
    }
    dlgText = text;
    dlgBody.innerHTML = escapeHtml(text) + '<span class="cursor-blink"></span>';
    // Fallback: if no "done" event in buffer (e.g. stream aborted), reset pending
    pending = false; sendBtn.disabled = false;
  });
  dialog.appendChild(btn);
}

async function sendMessage() {
  const text = textarea.value.trim();
  if (!text || pending) return;
  if (state !== STATE.CHAT) return;

  initAudio(); // warm up AudioContext inside user gesture
  topicBubbles.classList.remove('visible');
  closeKaomojiPanel();
  resetTextarea(); pending = true; sendBtn.disabled = true;
  // Clear any lingering sprites and whiteboard from previous reply
  if (typeof pixelSprites !== 'undefined') pixelSprites.length = 0;
  if (typeof whiteboardCommands !== 'undefined') whiteboardCommands.length = 0;

  // Position dialog (responsive)
  const faceCenterX = canvas.width / 2;
  const faceCenterY = canvas.height / 2;
  const faceRadius = 29 * faceCS;
  const isNarrow = window.innerWidth < 600;
  const dlgW = isNarrow ? 260 : 340;
  let dx = faceCenterX + faceRadius + 20;
  let dy = faceCenterY - 60;
  if (dx + dlgW > window.innerWidth - 20) dx = Math.max(10, faceCenterX - faceRadius - dlgW);
  if (isNarrow && dx < 10) { dx = (window.innerWidth - dlgW) / 2; dy = faceCenterY + faceRadius + 30; }
  if (dy < 60) dy = faceCenterY + faceRadius + 20;
  if (dy + 120 > window.innerHeight - 20) dy = faceCenterY - 120;
  dialog.style.left = dx + 'px';
  dialog.style.top = dy + 'px';
  dialog.classList.add('visible');
  dlgBody.innerHTML = '<span class="cursor-blink"></span>';
  let streamedReply = '';

  try {
    abortController = new AbortController();
    resetSilenceCheck(); // user is engaging, cancel any pending crisis follow-up
    const resp = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, therapy_mode: therapyMode, scenario_session_id: scenarioSessionId }),
      signal: abortController.signal,
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Parse SSE events from buffer
      const lines = buffer.split('\n');
      buffer = '';
      for (let li = 0; li < lines.length; li++) {
        var line = lines[li];
        if (!line.startsWith('data: ')) {
          // Only keep the LAST non-data line as a potential partial
          if (li === lines.length - 1 && line !== '') buffer = line;
          continue;
        }
        try {
          const evt = JSON.parse(line.slice(6));
          if (evt.type === 'emotions') {
            clearInterval(thinkingTimer);
            setSequence(evt.emotions, '');
            if (evt.affect) updateMoodFromAffect(evt.affect);
            else updateMoodFromEmotion(evt.label || '');
            if (evt.color_fields && Array.isArray(evt.color_fields)) {
              colorFieldsTarget = evt.color_fields.map(function(f) {
                return {
                  color: f.color,
                  cx: f.cx || 0.5, cy: f.cy || 0.5,
                  radius: f.radius || 0.5,
                  blend: f.blend || 'soft-light',
                  opacity: f.opacity != null ? f.opacity : 0.9,
                  blur: f.blur || 0,
                  pulse: f.pulse || null,
                  drift: f.drift || null
                };
              });
            }
            bgColorTarget = (evt.background && typeof evt.background === 'string') ? evt.background : null;
            if (evt.whiteboard && typeof parseWhiteboardCommands === 'function') {
              parseWhiteboardCommands(evt.whiteboard);
            }
          } else if (evt.type === 'pixel_sprites') {
            if (evt.sprites && Array.isArray(evt.sprites) && typeof spawnPixelSprites === 'function') {
              spawnPixelSprites(evt.sprites);
            }
          } else if (evt.type === 'scene_done') {
            if (storyPaused) {
              storyBuffer.push({ type: 'scene_done', evt: evt });
            } else {
              streamedReply += '\n\n—— ✦ ——\n\n';
              dlgBody.innerHTML = escapeHtml(streamedReply);
              if (evt.index != null && evt.total != null && evt.index < evt.total - 1) {
                storyPaused = true;
                dlgText = streamedReply;
                if (evt.batch_mode) batchMode = true;
                showStoryContinueBtn();
              }
            }
          } else if (evt.type === 'scene_start') {
            if (storyPaused) {
              storyBuffer.push({ type: 'scene_start', evt: evt });
            } else {
              if (evt.batch_mode) batchMode = true;
              _applySceneStart(evt);
            }
          } else if (evt.type === 'thinking') {
            dlgBody.innerHTML = '<span class="thinking-indicator">思考中<span class="thinking-dots">...</span></span>';
            var dotsEl = dlgBody.querySelector('.thinking-dots');
            var dotFrames = ['', '.', '..', '...'];
            var dotIdx = 0;
            clearInterval(thinkingTimer);
            thinkingTimer = setInterval(function() {
              dotIdx = (dotIdx + 1) % 4;
              if (dotsEl) dotsEl.textContent = dotFrames[dotIdx];
            }, 400);
          } else if (evt.type === 'text') {
            if (storyPaused) {
              storyBuffer.push({ type: 'text', evt: evt });
            } else {
              clearInterval(thinkingTimer);
              streamedReply += evt.text;
              playTypingSound();
              dlgBody.innerHTML = escapeHtml(streamedReply) + '<span class="cursor-blink"></span>';
            }
          } else if (evt.type === 'error') {
            clearInterval(thinkingTimer);
            streamedReply = evt.text;
            dlgBody.innerHTML = escapeHtml(streamedReply);
            addDebugLog('error', 'LLM调用失败', evt.text, 'DeepSeek API 可能超时或返回异常，检查 API Key 和网络连接');
          } else if (evt.type === 'crisis_alert') {
            showCrisisToast(evt);
            startSilenceCheck();
          } else if (evt.type === 'de_escalation') {
            if (typeof showDeescToast === 'function') showDeescToast(evt);
          } else if (evt.type === 'trend_warning') {
            if (typeof showTrendWarning === 'function') showTrendWarning(evt);
          } else if (evt.type === 'breathing_exercise') {
            startBreathingExercise(evt.pattern || 'simple', evt.duration || 120);
          } else if (evt.type === 'cbt_trigger') {
            if (typeof openCbtWizard === 'function') openCbtWizard(evt.thought || '');
          } else if (evt.type === 'done') {
            if (storyPaused) {
              storyBuffer.push({ type: 'done' });
            } else {
              clearInterval(thinkingTimer);
              dlgBody.innerHTML = escapeHtml(streamedReply);
              checkChoices(streamedReply);
              if (typeof refreshSessionProgress === 'function') refreshSessionProgress();
            }
          }
        } catch(e) {
          // If the line has a closing brace, it's complete but malformed — skip.
          // Otherwise it's likely split across chunks (incomplete) — retry.
          if (line.indexOf('}') !== -1) {
            addDebugLog('warn', 'SSE解析错误', e.message, line.slice(0, 100));
          } else {
            buffer = (buffer ? buffer + '\n' : '') + line;
          }
        }
      }
    }
  } catch(err) {
    clearInterval(thinkingTimer);
    dlgText = '嗯...出了点问题 😢';
    dlgBody.innerHTML = dlgText;
    dlgTyping = false;
    addDebugLog('error', '请求失败', err.message, '检查容器是否运行、网络是否正常、DeepSeek API 是否可达');
  } finally {
    clearInterval(thinkingTimer);
    abortController = null;
    if (storyPaused) {
      // Story still in progress — don't clean up, user needs to click through
      pending = true;  // keep input locked until story finishes
    } else {
      storyPaused = false; storyBuffer = []; batchMode = false;
      var btn = document.getElementById('story-continue-btn');
      if (btn) btn.remove();
      pending = false; sendBtn.disabled = false; textarea.focus();
    }
    if (streamedReply) {
      dlgText = streamedReply;
    }
  }
}

// Conversation starters — psychology-themed prompts
var CONVERSATION_STARTERS = [
  "我今天心情不太好",
  "陪我聊聊最近的事",
  "最近总是焦虑",
  "不知道怎么了，就是觉得累",
  "我今天特别开心！",
  "想不通一些事情",
  "陪我一起感受当下",
  "我刚刚做了一个奇怪的梦",
];

function loadTopics() {
  topicBubbles.innerHTML = CONVERSATION_STARTERS.map(function(t) {
    return '<span class="topic-bubble" data-prompt="' + escapeHtml(t) + '">' + escapeHtml(t) + '</span>';
  }).join('');
  topicBubbles.classList.add('visible');
  topicBubbles.querySelectorAll('.topic-bubble').forEach(function(b) {
    b.addEventListener('click', function() {
      var prompt = b.dataset.prompt;
      textarea.value = prompt;
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
      topicBubbles.classList.remove('visible');
      sendMessage();
    });
  });
}

sendBtn.addEventListener('click', sendMessage);

// ═══════════════════════════════════════════
// 场景练习 — 结束 & 反馈
// ═══════════════════════════════════════════

function updateScenarioUI() {
  var indicator = document.getElementById('scenarioIndicator');
  var endBtn = document.getElementById('scenarioEndBtn');
  if (scenarioSessionId) {
    if (indicator) {
      indicator.textContent = '🎯 正在和 ' + (scenarioAiRole || '对方') + ' 练习';
      indicator.style.display = 'flex';
    }
    if (endBtn) endBtn.style.display = 'inline-flex';
    if (textarea) textarea.placeholder = '对 ' + (scenarioAiRole || '对方') + ' 说...';
    // 互斥：场景模式隐藏疗愈开关，避免 UI 重叠
    if (typeof therapyToggleEl !== 'undefined' && therapyToggleEl) {
      therapyToggleEl.style.display = 'none';
    }
  } else {
    if (indicator) indicator.style.display = 'none';
    if (endBtn) endBtn.style.display = 'none';
    if (textarea) textarea.placeholder = '想说点什么...';
    // 恢复疗愈开关
    if (typeof therapyToggleEl !== 'undefined' && therapyToggleEl) {
      therapyToggleEl.style.display = '';
    }
  }
}

async function endScenario() {
  if (!confirm('确认结束练习？系统将生成反馈报告。')) return;

  var endBtn = document.getElementById('scenarioEndBtn');
  if (endBtn) { endBtn.disabled = true; endBtn.textContent = '生成中...'; }

  try {
    var resp = await fetch('/api/training/end?session_id=' + scenarioSessionId, { method: 'POST' });
    var json = await resp.json();
    if (!json.ok) { alert(json.error || '结束失败'); return; }

    var sid = scenarioSessionId;
    scenarioSessionId = '';
    scenarioAiRole = '';
    updateScenarioUI();

    renderScenarioFeedback(json);
  } catch (e) { alert('结束失败: ' + e.message); }
  finally {
    if (endBtn) { endBtn.disabled = false; endBtn.textContent = '结束练习'; }
  }
}

function renderScenarioFeedback(result) {
  var fb = result.feedback || {};
  var scores = fb.scores || {};

  var html = '<div style="padding:16px;margin-top:12px;background:rgba(124,131,255,0.06);border:1px solid rgba(124,131,255,0.15);border-radius:14px;">';
  html += '<div style="font-size:1rem;font-weight:700;color:#e0e0f0;margin-bottom:4px;">📋 练习反馈报告</div>';
  html += '<div style="font-size:0.68rem;color:#6a6a8a;margin-bottom:14px;">场景: ' + escapeHtml(result.scenario_label || '') + ' | 对方: ' + escapeHtml(result.ai_role || '') + ' | 对话轮数: ' + (result.turn_count || 0) + '</div>';

  var dims = [
    { key: 'clarity', label: '表达清晰度' },
    { key: 'awareness', label: '情绪觉察' },
    { key: 'boundary', label: '边界维护' },
    { key: 'assertiveness', label: '自信表达' },
    { key: 'perspective', label: '换位思考' }
  ];
  html += '<div style="margin-bottom:14px;">';
  dims.forEach(function(d) {
    var score = Number(scores[d.key] || 3);
    var stars = '★'.repeat(score) + '☆'.repeat(5 - score);
    html += '<div style="display:flex;align-items:center;gap:10px;padding:4px 0;font-size:0.78rem;">';
    html += '<span style="flex:1;color:#b0b0d0;">' + d.label + '</span>';
    html += '<span style="color:#ffb74d;letter-spacing:2px;">' + stars + '</span>';
    html += '<span style="color:#8080a0;min-width:28px;text-align:right;">' + score + '/5</span>';
    html += '</div>';
  });
  html += '</div>';

  if (fb.highlights && fb.highlights.length) {
    html += '<div style="margin-top:12px;"><div style="font-size:0.8rem;font-weight:600;color:#c0c0e0;margin-bottom:6px;">✅ 亮点</div>';
    fb.highlights.forEach(function(h) {
      html += '<div style="padding:6px 10px;border-radius:8px;margin-bottom:3px;font-size:0.76rem;background:rgba(76,175,80,0.08);color:#a5d6a7;">' + escapeHtml(h) + '</div>';
    });
    html += '</div>';
  }

  if (fb.improvements && fb.improvements.length) {
    html += '<div style="margin-top:12px;"><div style="font-size:0.8rem;font-weight:600;color:#c0c0e0;margin-bottom:6px;">📝 改进建议</div>';
    fb.improvements.forEach(function(h) {
      html += '<div style="padding:6px 10px;border-radius:8px;margin-bottom:3px;font-size:0.76rem;background:rgba(255,183,77,0.08);color:#ffcc80;">' + escapeHtml(h) + '</div>';
    });
    html += '</div>';
  }

  if (fb.overall) {
    html += '<div style="margin-top:12px;padding:10px 14px;background:rgba(124,131,255,0.06);border-radius:10px;font-size:0.8rem;color:#d0d0e0;">💬 ' + escapeHtml(fb.overall) + '</div>';
  }
  html += '</div>';

  // 显示在对话框中
  var dlg = document.getElementById('dlgBody');
  if (dlg) dlg.innerHTML += html;
}
