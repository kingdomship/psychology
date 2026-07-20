// ═══════════════════════════════════════════
// 场景练习面板 — 社交情境模拟
// ═══════════════════════════════════════════

var _trainingSessionId = null;
var _trainingAiRole = '';

async function loadTrainingContent() {
  auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#6a6a8a;">加载场景练习...</div>';
  try {
    // 并行加载场景类型和AI建议
    var [clientsResp, suggestResp] = await Promise.all([
      fetch('/api/training/clients'),
      fetch('/api/training/suggest', { method: 'POST' })
    ]);

    if (!clientsResp.ok) {
      auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#f44336;">加载失败: HTTP ' + clientsResp.status + '</div>';
      return;
    }

    var clientsJson = await clientsResp.json();
    if (!clientsJson.ok) throw new Error(clientsJson.error || '加载失败');
    var scenarios = clientsJson.data || [];

    var suggestions = [];
    if (suggestResp.ok) {
      var suggestJson = await suggestResp.json();
      if (suggestJson.ok) suggestions = suggestJson.data || [];
    }

    var html = '';

    // 标题
    html += '<div class="goals-header">';
    html += '<div class="goals-title-row"><span class="goals-title">🎓 场景练习</span>';
    html += '<span class="goals-subtitle">在安全环境中练习真实人际对话，提升沟通能力</span></div>';
    html += '</div>';

    // ── AI 推荐区域 ──
    if (suggestions.length > 0) {
      html += '<div class="training-section">';
      html += '<div class="training-section-title">💡 AI 推荐（基于你的对话模式）</div>';
      html += '<div class="training-suggestions">';
      suggestions.forEach(function(s) {
        html += '<div class="training-suggestion-card">';
        html += '<div class="training-suggestion-header">';
        html += '<span class="training-suggestion-icon">' + escapeHtml(s.icon) + '</span>';
        html += '<span class="training-suggestion-label">' + escapeHtml(s.label) + '</span>';
        html += '<span class="training-suggestion-domain">' + escapeHtml(s.domain_label) + '</span>';
        html += '</div>';
        html += '<div class="training-suggestion-reason">' + escapeHtml(s.reason) + '</div>';
        html += '<button class="goals-btn primary training-suggestion-btn" onclick="startTraining(' +
          JSON.stringify(s.scenario_type) + ', ' + JSON.stringify('') + ', ' + JSON.stringify('') + ')">开始练习</button>';
        html += '</div>';
      });
      html += '</div>';
      html += '</div>';

      html += '<div class="training-divider"><span>—— 或自定义场景 ——</span></div>';
    }

    // ── 自定义场景区域 ──
    html += '<div class="training-section">';
    html += '<div class="training-section-title">✏️ 自定义场景</div>';

    // 场景类型选择
    html += '<div class="training-type-label">场景类型</div>';
    html += '<div class="training-types" id="trainingTypes">';
    scenarios.forEach(function(s, i) {
      html += '<button class="training-type-btn' + (i === 0 ? ' active' : '') + '" data-type="' + escapeHtml(s.id) + '" ';
      html += 'onclick="selectTrainingType(this, ' + JSON.stringify(s.id) + ')">';
      html += '<span class="training-type-icon">' + escapeHtml(s.icon) + '</span>';
      html += '<span class="training-type-name">' + escapeHtml(s.label) + '</span>';
      html += '<span class="training-type-example">' + escapeHtml(s.example) + '</span>';
      html += '</button>';
    });
    html += '</div>';

    // 对方角色
    html += '<div class="training-custom-form">';
    html += '<label class="training-field-label">对方是谁？</label>';
    html += '<input class="training-field-input" id="trainingAiRole" type="text" placeholder="例如：男朋友、妈妈、同事、朋友..." maxlength="30">';

    // 场景描述
    html += '<label class="training-field-label">场景描述（可选）</label>';
    html += '<textarea class="training-field-textarea" id="trainingSituation" rows="2" placeholder="例如：他最近总是忽略我，我想告诉他我的感受..." maxlength="200"></textarea>';

    html += '<div class="training-form-actions">';
    html += '<button class="goals-btn secondary" onclick="startRandomTraining()">🎲 随机场景</button>';
    html += '<button class="goals-btn primary" onclick="startCustomTraining()">🚀 开始练习</button>';
    html += '</div>';
    html += '</div>';
    html += '</div>';

    html += '<div class="report-insight" style="margin-top:16px;">';
    html += '<div class="report-insight-title">💡 提示</div>';
    html += '<div class="report-insight-text">AI 将扮演你指定的角色，帮助你在安全环境中练习沟通。' +
      '练习结束后会自动生成反馈报告，帮助你看到自己的进步。</div>';
    html += '</div>';

    html += '<div id="trainingArea"></div>';
    auxContent.innerHTML = html;
  } catch (e) {
    auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#f44336;">加载失败: ' + escapeHtml(e.message) + '</div>';
  }
}

// ── 场景类型选择 ──

var _selectedScenarioType = 'express_feelings';

function selectTrainingType(btn, typeId) {
  _selectedScenarioType = typeId;
  var buttons = document.querySelectorAll('.training-type-btn');
  buttons.forEach(function(b) { b.classList.remove('active'); });
  btn.classList.add('active');
}

// ── 启动练习 ──

async function startRandomTraining() {
  var btn = document.querySelector('.training-form-actions .goals-btn.secondary');
  if (btn) { btn.disabled = true; btn.textContent = '生成中...'; }

  try {
    var resp = await fetch('/api/training/random', { method: 'POST' });
    var json = await resp.json();
    if (!json.ok) { showToast(json.error || '生成失败', 'error'); return; }

    // 选中对应的场景类型
    _selectedScenarioType = json.scenario_type;
    var buttons = document.querySelectorAll('.training-type-btn');
    buttons.forEach(function(b) { b.classList.remove('active'); });
    var target = document.querySelector('.training-type-btn[data-type="' + json.scenario_type + '"]');
    if (target) target.classList.add('active');

    // 填充表单
    document.getElementById('trainingAiRole').value = json.ai_role || '';
    document.getElementById('trainingSituation').value = json.situation || '';

    // 直接开始
    startTraining(json.scenario_type, json.situation || '', json.ai_role || '');
  } catch (e) { showToast('生成失败: ' + e.message, 'error'); }
  finally {
    if (btn) { btn.disabled = false; btn.textContent = '🎲 随机场景'; }
  }
}

function startCustomTraining() {
  var aiRole = (document.getElementById('trainingAiRole').value || '').trim();
  if (!aiRole) {
    showToast('请输入"对方是谁？"，例如：男朋友、妈妈、同事...', 'warning');
    document.getElementById('trainingAiRole').focus();
    return;
  }
  var situation = (document.getElementById('trainingSituation').value || '').trim();
  startTraining(_selectedScenarioType, situation, aiRole);
}

async function startTraining(scenarioType, situation, aiRole) {
  var params = 'scenario_type=' + encodeURIComponent(scenarioType || 'express_feelings');
  if (situation) params += '&situation=' + encodeURIComponent(situation);
  if (aiRole) params += '&ai_role=' + encodeURIComponent(aiRole);

  try {
    var resp = await fetch('/api/training/start?' + params, { method: 'POST' });
    if (!resp.ok) {
      var text = await resp.text();
      console.error('[Training] start failed: HTTP ' + resp.status, text);
      showToast('启动失败: HTTP ' + resp.status, 'error');
      return;
    }
    var json = await resp.json();
    if (!json.ok) { showToast(json.error || '启动失败', 'error'); return; }

    // 设置全局状态 — 主聊天页面接管对话
    scenarioSessionId = json.session_id;
    scenarioAiRole = json.ai_role || '对方';

    // 关闭侧边栏，切换到主聊天（像素脸）页面
    // 互斥：场景模式关闭疗愈模式
    therapyMode = false;
    applyTherapyMode();
    closeAuxiliary();
    state = STATE.CHAT;
    inputRow.classList.add('visible');
    updateScenarioUI();

    // 清空旧对话框，显示场景提示
    if (typeof dlgBody !== 'undefined' && dlgBody) {
      dlgBody.innerHTML = '<div style="text-align:center;font-size:0.78rem;color:#6a6a8a;padding:20px;">🎯 场景练习开始 — 你现在在和 <b>' + escapeHtml(scenarioAiRole) + '</b> 对话<br><span style="font-size:0.68rem;">' + escapeHtml(json.situation || '') + '</span></div>';
    }
  } catch (e) { showToast('启动失败: ' + e.message, 'error'); }
}

// ── 旧函数已移除: 对话由主聊天 + chat.js 接管 ──

// Typing dots animation
if (!document.getElementById('training-typing-style')) {
  var style = document.createElement('style');
  style.id = 'training-typing-style';
  style.textContent = '.typing-dots span { animation: typingBounce 1.4s infinite ease-in-out both; display: inline-block; }' +
    '.typing-dots span:nth-child(1) { animation-delay: 0s; }' +
    '.typing-dots span:nth-child(2) { animation-delay: 0.2s; }' +
    '.typing-dots span:nth-child(3) { animation-delay: 0.4s; }' +
    '@keyframes typingBounce { 0%,80%,100% { opacity: 0.3; } 40% { opacity: 1; } }';
  document.head.appendChild(style);
}
