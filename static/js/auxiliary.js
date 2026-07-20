// ═══════════════════════════════════════════
// Auxiliary panel
// ═══════════════════════════════════════════
let auxTab = 'diary';

function openAuxiliary(tab = 'diary') {
  state = STATE.AUXILIARY;
  auxPanel.classList.add('open');
  auxTab = tab;
  topicBubbles.classList.remove('visible');
  document.querySelectorAll('.aux-tab').forEach(/** @param {HTMLElement} t */ t => t.classList.toggle('active', t.dataset.tab === tab));
  loadAuxContent();
}

function closeAuxiliary() {
  auxPanel.classList.remove('open');
  state = STATE.STARFIELD;
  chatFadeIn = 0;
  topicBubbles.classList.remove('visible');
  // Clean up constellation overlay if present
  var overlay = document.querySelector('.constellation-overlay');
  if (overlay) {
    if (typeof Constellation !== 'undefined') Constellation.detach();
    overlay.remove();
    auxContent.innerHTML = '';
  }
  initStarfield();
  inputRow.classList.remove('visible');
}

auxBack.addEventListener('click', closeAuxiliary);
document.querySelectorAll('.aux-tab').forEach(/** @param {HTMLElement} tab */ tab => {
  tab.addEventListener('click', () => {
    auxTab = tab.dataset.tab;
    document.querySelectorAll('.aux-tab').forEach(/** @param {HTMLElement} t */ t => t.classList.toggle('active', t.dataset.tab === auxTab));
    if (auxTab === 'settings') {
      openSettings();
    } else if (auxTab === 'personality') {
      openPersonalityModal();
    } else if (auxTab === 'distill') {
      openDistillModal();
    } else {
      loadAuxContent();
    }
  });
});

function loadAuxContent() {
  // Detach constellation canvas and remove overlay when switching away
  if (auxTab !== 'constellation' && typeof Constellation !== 'undefined') {
    Constellation.detach();
  }
  if (auxTab !== 'constellation') {
    var overlay = document.querySelector('.constellation-overlay');
    if (overlay) overlay.remove();
    auxContent.innerHTML = '';
  }
  if (auxTab === 'diary') loadDiaryContent(true);
  else if (auxTab === 'mood') loadMoodContent();
  else if (auxTab === 'memory') loadMemoryContent();
  else if (auxTab === 'constellation') loadConstellationContent();
  else if (auxTab === 'safety') loadSafetyContent();
  else if (auxTab === 'report') loadReportContent();
  else if (auxTab === 'assessment') loadAssessmentContent();
  else if (auxTab === 'goals') loadGoalsContent();
  else if (auxTab === 'training') loadTrainingContent();
}

async function loadSafetyContent() {
  auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#6a6a8a;">加载安全数据...</div>';
  try {
    var logResp = await fetch('/api/therapy/crisis-log?days=30');
    var logData = await logResp.json();
    var dashResp = await fetch('/api/therapy/dashboard');
    var dashData = await dashResp.json();

    var html = '<div class="safety-panel">';
    // Dashboard summary
    html += '<div class="safety-section"><div class="safety-section-title">30日概览</div>';
    html += '<div class="safety-stats">';
    html += '<div class="safety-stat"><span class="safety-stat-num">' + (dashData.total_events || 0) + '</span><span class="safety-stat-label">危机事件</span></div>';
    html += '<div class="safety-stat"><span class="safety-stat-num">' + (dashData.llm_verified_count || 0) + '</span><span class="safety-stat-label">LLM确认</span></div>';
    html += '<div class="safety-stat"><span class="safety-stat-num">' + (dashData.unacknowledged_count || 0) + '</span><span class="safety-stat-label">未确认</span></div>';
    html += '</div></div>';

    // Crisis events list
    html += '<div class="safety-section"><div class="safety-section-title">危机事件记录</div>';
    var events = logData || [];
    if (!events.length) {
      html += '<div style="padding:20px;text-align:center;color:#6a6a9a;font-size:0.78rem;">无危机事件记录 ✅</div>';
    } else {
      events.forEach(function(evt) {
        var sevColor = {high: '#f44336', medium: '#ff9800', low: '#ffeb3b', none: '#4caf50'}[evt.level] || '#888';
        html += '<div class="safety-event" style="border-left:3px solid ' + sevColor + '">';
        html += '<div class="safety-event-header"><span class="safety-event-severity" style="color:' + sevColor + '">' + (evt.level || '?') + '</span>';
        html += '<span class="safety-event-type">' + (evt.crisis_type || '') + '</span>';
        html += '<span class="safety-event-date">' + (evt.created_at || '').slice(0, 10) + '</span></div>';
        html += '<div class="safety-event-msg">' + escapeHtml((evt.user_msg || '').slice(0, 120)) + '</div>';
        html += '</div>';
      });
    }
    html += '</div></div>';
    auxContent.innerHTML = html;
  } catch(e) {
    auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#f44336;">加载失败</div>';
  }
}

async function loadMemoryContent() {
  auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#6a6a8a;">加载记忆中...</div>';
  try {
    const [personaR, profileR] = await Promise.all([
      fetch('/api/memory/persona'),
      fetch('/api/memory/profile')
    ]);
    const persona = await personaR.json();
    const profile = await profileR.json();

    auxContent.innerHTML = `
      <div class="memory-section">
        <div class="memory-label"><svg class="svg-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg> AI 人设</div>
        <div class="memory-card">${escapeHtml(persona.content || '未设定').replace(/\n/g, '<br>')}</div>
      </div>
      <div class="memory-section" style="margin-top:24px;">
        <div class="memory-label"><svg class="svg-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11.5 15H7a4 4 0 0 0-4 4v2"/><path d="M21.378 16.626a1 1 0 0 0-3.004-3.004l-4.01 4.012a2 2 0 0 0-.506.854l-.837 2.87a.5.5 0 0 0 .62.62l2.87-.837a2 2 0 0 0 .854-.506z"/><circle cx="10" cy="7" r="4"/></svg> 用户画像</div>
        <div class="memory-card">${escapeHtml(profile.content || '未设定').replace(/\n/g, '<br>')}</div>
      </div>
      <div style="text-align:center;margin-top:24px;font-size:0.6rem;color:#4a4a6a;letter-spacing:0.04em;">
        仅通过对话逐渐拟合，不可手动编辑
      </div>
    `;
  } catch(e) {
    auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#f44336;">加载失败</div>';
  }
}

// ── Constellation star map (full-screen overlay) ──
async function loadConstellationContent() {
  auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#6a6a8a;">绘制星图中...</div>';
  try {
    const resp = await fetch('/api/constellation');
    const data = await resp.json();

    // Build full-screen overlay
    const overlay = document.createElement("div");
    overlay.className = "constellation-overlay";
    overlay.innerHTML = `
      <button class="constellation-overlay-close" title="关闭 (Esc)">✕</button>
      <div class="constellation-overlay-legend">
        ${(data.galaxies || []).map(g =>
          `<span class="constellation-legend-item">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${g.color};"></span>
            ${g.label}(${g.star_count})
          </span>`
        ).join('')}
        <span style="margin-left:12px;opacity:0.4;font-size:0.65rem;">滚轮缩放 · 拖拽平移 · 拖动节点 · 双击复位</span>
      </div>
      <div class="constellation-overlay-canvas" id="constellationCanvas"></div>
      <div class="constellation-bubble" id="constellationBubble" style="display:none;">
        <div class="constellation-bubble-galaxy" id="bubbleGalaxy"></div>
        <div class="constellation-bubble-tag" id="bubbleTag"></div>
        <div class="constellation-bubble-body" id="bubbleBody"></div>
        <div class="constellation-bubble-meta">
          <span class="bubble-importance" id="bubbleImportance"></span>
        </div>
        <button class="constellation-bubble-close" id="bubbleClose">✕</button>
      </div>
    `;
    document.body.appendChild(overlay);

    // Close helpers
    function closeOverlay() {
      if (typeof Constellation !== 'undefined') Constellation.detach();
      if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
      document.removeEventListener("keydown", onKey);
      auxContent.innerHTML = '';
    }
    function onKey(e) { if (e.key === "Escape") closeOverlay(); }
    document.addEventListener("keydown", onKey);

    /** @type {HTMLElement} */ (overlay.querySelector(".constellation-overlay-close")).onclick = closeOverlay;
    // Click background (not canvas) to close
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeOverlay();
    });

    // Star detail handlers — chat bubble style popup
    window._closeBubbleHandler = null;
    window._onConstellationStarClick = function(star) {
      const bubble = document.getElementById('constellationBubble');
      // Clean up previous close handler
      if (window._closeBubbleHandler) {
        document.removeEventListener('click', window._closeBubbleHandler);
        window._closeBubbleHandler = null;
      }
      if (!star) {
        // Click on blank — close bubble
        bubble.style.display = 'none';
        return;
      }
      document.getElementById('bubbleGalaxy').textContent = '🌌 ' + (star.galaxyName || star.galaxy || '记忆');
      document.getElementById('bubbleGalaxy').style.color = star.color || '#a78bfa';
      document.getElementById('bubbleTag').textContent = star.tag;
      document.getElementById('bubbleBody').textContent = star.summary || '(暂无详情)';
      const imp = star.importance || 0;
      const pct = Math.round(imp * 100);
      document.getElementById('bubbleImportance').innerHTML =
        '⭐ 重要性 <b style="color:' + (star.color || '#a78bfa') + '">' + pct + '%</b>';
      bubble.style.display = 'block';
      // Click outside bubble to close (debounced to avoid immediate close on same click)
      setTimeout(function() {
        window._closeBubbleHandler = function _closeBubble(/** @type {MouseEvent} */ e) {
          var tgt = /** @type {Element} */ (e.target);
          if (!bubble.contains(tgt) && tgt.tagName !== 'CANVAS') {
            bubble.style.display = 'none';
            document.removeEventListener('click', _closeBubble);
            window._closeBubbleHandler = null;
            if (typeof Constellation !== 'undefined') Constellation.clearSelection();
          }
        };
        document.addEventListener('click', window._closeBubbleHandler);
      }, 100);
    };
    document.getElementById('bubbleClose').onclick = function() {
      document.getElementById('constellationBubble').style.display = 'none';
      if (typeof Constellation !== 'undefined') Constellation.clearSelection();
    };

    // Attach canvas renderer
    const container = document.getElementById('constellationCanvas');
    if (container && typeof Constellation !== 'undefined') {
      Constellation.init(data);
      Constellation.attach(container);
    }

    // Restore sidebar neutral state
    auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#6a6a8a;">🌌 星图已打开<br><small>关闭全屏窗口即可返回</small></div>';
  } catch(e) {
    console.error('[Constellation] load failed:', e);
    auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#f44336;">星图加载失败: ' + escapeHtml(e.message) + '</div>';
  }
}
