// ═══════════════════════════════════════════
// 治疗目标管理面板
// ═══════════════════════════════════════════

var _goalsData = [];

async function loadGoalsContent() {
  auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#6a6a8a;">加载目标...</div>';
  try {
    var resp = await fetch('/api/goals');
    var json = await resp.json();
    if (!json.ok) throw new Error(json.message || '加载失败');
    _goalsData = json.data || [];
    renderGoals();
  } catch (e) {
    auxContent.innerHTML = '<div style="text-align:center;padding:40px;color:#f44336;">加载失败: ' + escapeHtml(e.message) + '</div>';
  }
}

function renderGoals() {
  var html = '';

  // 标题
  html += '<div class="goals-header">';
  html += '<div class="goals-title-row"><span class="goals-title">🎯 治疗目标</span>';
  html += '<span class="goals-subtitle">SMART 目标追踪</span></div>';
  html += '</div>';

  // 预设目标快速添加
  html += '<div class="goals-section"><div class="goals-section-title">💡 快速预设</div>';
  html += '<div class="goals-presets">';

  var presets = [
    { text: '每天记录3件感恩的事', cat: 'selfcare' },
    { text: '每周运动3次，每次30分钟', cat: 'health' },
    { text: '识别并挑战1个负面自动思维', cat: 'cognition' },
    { text: '练习正念冥想10分钟', cat: 'emotion' },
    { text: '减少自我批评，练习自我关怀', cat: 'cognition' },
    { text: '主动联系1位朋友或家人', cat: 'relationship' },
    { text: '保持规律作息，23点前入睡', cat: 'health' },
    { text: '每天户外活动15分钟', cat: 'behavior' },
  ];
  presets.forEach(function(p) {
    html += '<button class="goals-preset-btn" onclick="addPreset(\'' + escapeHtml(p.text) + '\', \'' + p.cat + '\')" title="点击添加">' + escapeHtml(p.text) + '</button>';
  });
  html += '</div></div>';

  // 新建目标表单
  html += '<div class="goals-create" id="goalsCreate">';
  html += '<input type="text" class="goals-input" id="goalsInput" placeholder="输入自定义目标..." maxlength="500">';
  html += '<select class="goals-category" id="goalsCategory">';
  var cats = ['general:一般', 'emotion:情绪管理', 'behavior:行为改变', 'cognition:认知调整', 'relationship:人际关系', 'selfcare:自我关怀', 'work:工作学习', 'health:身体健康'];
  cats.forEach(function(c) {
    var parts = c.split(':');
    html += '<option value="' + parts[0] + '">' + parts[1] + '</option>';
  });
  html += '</select>';
  html += '<button class="goals-btn primary" onclick="createGoal()">+ 添加</button>';
  html += '</div>';

  // 活跃目标列表
  var activeGoals = _goalsData.filter(function(g) { return g.status === 'active'; });
  var completedGoals = _goalsData.filter(function(g) { return g.status === 'completed'; });

  html += '<div class="goals-section"><div class="goals-section-title">进行中 (' + activeGoals.length + ')</div>';
  if (activeGoals.length === 0) {
    html += '<div class="goals-empty">暂无活跃目标，在上方创建第一个</div>';
  } else {
    html += '<div class="goals-list">';
    activeGoals.forEach(function(g) { html += renderGoalCard(g); });
    html += '</div>';
  }
  html += '</div>';

  // 已完成目标
  if (completedGoals.length > 0) {
    html += '<div class="goals-section" style="margin-top:20px;"><div class="goals-section-title">已完成 (' + completedGoals.length + ')</div>';
    html += '<div class="goals-list">';
    completedGoals.forEach(function(g) { html += renderGoalCard(g); });
    html += '</div></div>';
  }

  auxContent.innerHTML = html;
}

function renderGoalCard(g) {
  var pct = g.progress_pct || 0;
  var isDone = g.status === 'completed';
  var catLabel = { general: '一般', emotion: '情绪管理', behavior: '行为改变', cognition: '认知调整', relationship: '人际关系', selfcare: '自我关怀', work: '工作学习', health: '身体健康' }[g.category] || g.category;

  var html = '<div class="goal-card' + (isDone ? ' completed' : '') + '" id="goal-' + g.id + '">';
  html += '<div class="goal-card-header">';
  html += '<span class="goal-card-cat">' + escapeHtml(catLabel) + '</span>';
  if (!isDone) {
    html += '<div class="goal-card-actions">';
    html += '<button class="goal-action-btn" onclick="showProgressEditor(' + g.id + ')" title="更新进展">✏️</button>';
    html += '<button class="goal-action-btn" onclick="completeGoal(' + g.id + ')" title="标记完成">✅</button>';
    html += '<button class="goal-action-btn danger" onclick="deleteGoal(' + g.id + ')" title="删除">🗑️</button>';
    html += '</div>';
  } else {
    html += '<div class="goal-card-actions">';
    html += '<button class="goal-action-btn" onclick="reactivateGoal(' + g.id + ')" title="重新激活">🔄</button>';
    html += '<button class="goal-action-btn danger" onclick="deleteGoal(' + g.id + ')" title="删除">🗑️</button>';
    html += '</div>';
  }
  html += '</div>';

  html += '<div class="goal-card-text">' + escapeHtml(g.goal_text) + '</div>';

  // 进度条
  html += '<div class="goal-progress">';
  html += '<div class="goal-progress-track">';
  html += '<div class="goal-progress-fill' + (isDone ? ' done' : '') + '" style="width:' + pct + '%"></div>';
  html += '</div>';
  html += '<span class="goal-progress-text">' + pct + '%</span>';
  html += '</div>';

  if (g.evidence) {
    html += '<div class="goal-evidence">📝 ' + escapeHtml(g.evidence) + '</div>';
  }
  if (g.created_at) {
    html += '<div class="goal-meta">创建于 ' + escapeHtml(g.created_at.slice(0, 10)) + '</div>';
  }

  html += '</div>';
  return html;
}

// ── CRUD 操作 ──

async function addPreset(text, cat) {
  try {
    var resp = await fetch('/api/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal_text: text, category: cat })
    });
    var json = await resp.json();
    if (!json.ok) { alert(json.message); return; }
    loadGoalsContent();
  } catch (e) { alert('添加失败: ' + e.message); }
}

async function createGoal() {
  var input = document.getElementById('goalsInput');
  var cat = document.getElementById('goalsCategory');
  var text = (input.value || '').trim();
  if (!text) { alert('请输入目标内容'); return; }

  try {
    var resp = await fetch('/api/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ goal_text: text, category: cat.value })
    });
    var json = await resp.json();
    if (!json.ok) { alert(json.message); return; }
    input.value = '';
    loadGoalsContent();
  } catch (e) { alert('创建失败: ' + e.message); }
}

function showProgressEditor(goalId) {
  var goal = _goalsData.find(function(g) { return g.id === goalId; });
  if (!goal) return;
  var pct = goal.progress_pct || 0;
  var evidence = goal.evidence || '';

  var html = '<div class="goal-editor-overlay" id="progressOverlay" onclick="if(event.target===this)closeProgressEditor()">';
  html += '<div class="goal-editor-dialog">';
  html += '<div class="goal-editor-title">更新进展 — ' + escapeHtml((goal.goal_text || '').slice(0, 30)) + '</div>';
  html += '<label class="goal-editor-label">进度 (' + pct + '%)</label>';
  html += '<input type="range" class="goal-slider" id="progressSlider" min="0" max="100" value="' + pct + '" oninput="document.getElementById(\'progressVal\').textContent=this.value+\'%\'">';
  html += '<span id="progressVal" style="color:#c0c0e0;font-size:0.8rem;">' + pct + '%</span>';
  html += '<label class="goal-editor-label">进展说明</label>';
  html += '<textarea class="goal-editor-textarea" id="progressEvidence" rows="2" maxlength="200" placeholder="简述进展证据...">' + escapeHtml(evidence) + '</textarea>';
  html += '<div class="goal-editor-btns">';
  html += '<button class="goals-btn" onclick="closeProgressEditor()">取消</button>';
  html += '<button class="goals-btn primary" onclick="saveProgress(' + goalId + ')">保存</button>';
  html += '</div></div></div>';
  document.body.insertAdjacentHTML('beforeend', html);
}

function closeProgressEditor() {
  var overlay = document.getElementById('progressOverlay');
  if (overlay) overlay.remove();
}

async function saveProgress(goalId) {
  var slider = document.getElementById('progressSlider');
  var evidence = document.getElementById('progressEvidence');
  var pct = parseInt(slider.value) || 0;
  try {
    var resp = await fetch('/api/goals/' + goalId + '/progress', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ progress: pct, evidence: (evidence.value || '').trim() })
    });
    var json = await resp.json();
    if (!json.ok) { alert(json.message); return; }
    closeProgressEditor();
    loadGoalsContent();
  } catch (e) { alert('更新失败: ' + e.message); }
}

async function completeGoal(goalId) {
  if (!confirm('确认将此目标标记为已完成？')) return;
  try {
    var resp = await fetch('/api/goals/' + goalId + '/complete', { method: 'PUT' });
    var json = await resp.json();
    if (!json.ok) { alert(json.message); return; }
    loadGoalsContent();
  } catch (e) { alert('操作失败: ' + e.message); }
}

async function reactivateGoal(goalId) {
  try {
    var resp = await fetch('/api/goals/' + goalId + '/reactivate', { method: 'PUT' });
    var json = await resp.json();
    if (!json.ok) { alert(json.message); return; }
    loadGoalsContent();
  } catch (e) { alert('操作失败: ' + e.message); }
}

async function deleteGoal(goalId) {
  if (!confirm('确认删除此目标？此操作不可撤销。')) return;
  try {
    var resp = await fetch('/api/goals/' + goalId, { method: 'DELETE' });
    var json = await resp.json();
    if (!json.ok) { alert(json.message); return; }
    loadGoalsContent();
  } catch (e) { alert('删除失败: ' + e.message); }
}

// Enter 提交
document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && auxTab === 'goals' && document.activeElement === document.getElementById('goalsInput')) {
    e.preventDefault();
    createGoal();
  }
});
