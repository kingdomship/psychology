// ═══════════════════════════════════════════
// 分析报告面板
// ═══════════════════════════════════════════

var _reportPeriod = 0; // 0 = latest, >0 = specific report id
var _reportData = null;   // current report data for download

async function loadReportContent() {
  auxContent.innerHTML = '<div class="report-loading">加载报告数据...</div>';
  try {
    if (_reportPeriod === 0) {
      var resp = await fetch('/api/report/latest');
      var json = await resp.json();
      if (!json.ok || !json.data) {
        auxContent.innerHTML = renderReportEmpty(json.message || '暂无报告数据');
        return;
      }
      _reportPeriod = json.data.id;
      renderReport(json.data);
      loadReportList();
    } else {
      var resp2 = await fetch('/api/report/' + _reportPeriod);
      var json2 = await resp2.json();
      if (!json2.ok || !json2.data) {
        auxContent.innerHTML = renderReportEmpty('报告不存在');
        return;
      }
      renderReport(json2.data);
      loadReportList();
    }
  } catch (e) {
    auxContent.innerHTML = '<div class="report-loading" style="color:#f44336;">加载失败: ' + escapeHtml(e.message) + '</div>';
  }
}

function renderReportEmpty(msg) {
  return '<div class="report-empty">'
    + '<div class="report-empty-icon">&#x1F4CB;</div>'
    + '<div class="report-empty-text">' + escapeHtml(msg || '数据收集中...') + '</div>'
    + '<div class="report-empty-hint">活跃天数达到7天后将自动生成第一份报告</div>'
    + '<div class="report-empty-actions">'
    + '<button class="report-gen-btn" onclick="generateReport(7)">生成7天报告</button>'
    + '<button class="report-gen-btn" onclick="generateReport(14)">生成14天报告</button>'
    + '</div></div>';
}

// ── 主渲染 ──

function renderReport(report) {
  _reportData = report;
  var d = report.dashboard || {};
  var ai = report.ai_insight || {};
  var isMilestone = report.report_type === 'milestone';

  var html = '';

  // 标题栏
  html += '<div class="report-header">';
  html += '<div class="report-title-row">';
  html += '<span class="report-title">&#x1F4CA; 分析报告</span>';
  if (isMilestone && report.milestone_label) {
    html += '<span class="report-badge milestone">&#x1F389; ' + escapeHtml(report.milestone_label) + '里程碑</span>';
  } else {
    html += '<span class="report-badge manual">&#x1F4DD; ' + report.period_days + '天报告</span>';
  }
  html += '<button class="report-download-btn" onclick="downloadReport()" title="下载 Markdown">&#x1F4E5; 下载</button>';
  html += '</div>';
  html += '<div class="report-subtitle">' + (d.date_from || '?') + ' ~ ' + (d.date_to || '?') + '  |  ' + (d.active_days || 0) + ' 个活跃天</div>';
  html += '</div>';

  // 手动生成 + 导出按钮
  html += '<div class="report-actions">';
  html += '<span class="report-actions-label">手动生成:</span>';
  [7, 14, 30].forEach(function(days) {
    html += '<button class="report-gen-btn sm" onclick="generateReport(' + days + ')">' + days + '天</button>';
  });
  html += '<span class="report-actions-sep">|</span>';
  html += '<button class="report-gen-btn sm export" onclick="exportTranscript()">&#x1F4E4; 导出逐字稿</button>';
  html += '</div>';

  // 6卡片网格
  html += '<div class="report-grid">';
  html += renderAffectCard(d.affect_trend || {});
  html += renderActivityCard(d.activity || {}, d.valence_summary || {});
  html += renderBehaviorCard(d.behavior || null);
  html += renderInterventionCard(d.interventions || []);
  html += renderCrisisCard(d.crisis || {});
  html += renderMoodCard(d.mood_distribution || {}, d.diary_count || 0);
  html += '</div>';

  // AI 洞察
  html += '<div class="report-insight">';
  html += '<div class="report-insight-title">&#x1F9E0; AI 综合洞察</div>';
  html += '<div class="report-insight-text">' + escapeHtml(ai.insight || '暂无洞察').replace(/\n/g, '<br>') + '</div>';
  if (ai.key_findings && ai.key_findings.length) {
    html += '<div class="report-findings">';
    ai.key_findings.forEach(function(f) {
      html += '<span class="report-finding-tag">' + escapeHtml(f) + '</span>';
    });
    html += '</div>';
  }
  if (ai.suggestions && ai.suggestions.length) {
    html += '<div class="report-suggestions">';
    html += '<div class="report-suggestions-title">&#x1F4AC; 关怀建议</div>';
    ai.suggestions.forEach(function(s) {
      html += '<div class="report-suggestion-item">&#x1F338; ' + escapeHtml(s) + '</div>';
    });
    html += '</div>';
  }
  html += '</div>';

  // 跨会话洞察
  html += '<div id="crossSessionCard"></div>';

  // 历史报告列表容器
  html += '<div class="report-history" id="reportHistory"></div>';

  auxContent.innerHTML = html;
  loadCrossSession();
}

// ── 卡片渲染 ──

function renderAffectCard(affect) {
  var dims = [
    { key: 'seeking', label: '探索', color: '#4fc3f7' },
    { key: 'play', label: '玩耍', color: '#ffb74d' },
    { key: 'care', label: '关怀', color: '#ef5350' },
    { key: 'fear', label: '恐惧', color: '#7e57c2' },
    { key: 'rage', label: '愤怒', color: '#f44336' },
    { key: 'panic', label: '恐慌', color: '#5c6bc0' }
  ];
  var empty = !affect || Object.keys(affect).length === 0;
  var bars = dims.map(function(d) {
    var v = Number(empty ? 0 : (affect[d.key] || 0));
    var pct = Math.round(v * 100);
    return '<div class="report-bar-row">'
      + '<span class="report-bar-label">' + d.label + '</span>'
      + '<div class="report-bar-track"><div class="report-bar-fill" style="width:' + pct + '%;background:' + d.color + '"></div></div>'
      + '<span class="report-bar-val">' + v.toFixed(2) + '</span>'
      + '</div>';
  }).join('');
  return '<div class="report-card"><div class="report-card-title">&#x1F9EC; 情绪六维</div>'
    + (empty ? '<div class="report-card-empty">暂无数据</div>' : bars)
    + '</div>';
}

function renderActivityCard(activity, valence) {
  var msgs = activity.total_messages || 0;
  var days = activity.active_days || 0;
  var vAvg = Number(valence.avg_valence !== undefined ? valence.avg_valence : 0.5);
  var vTrend = valence.trend_direction || 'stable';
  var trendIcon = { improving: '&#x2197;', declining: '&#x2198;', stable: '&#x2192;' }[vTrend] || '&#x2192;';
  var trendLabel = { improving: '上升中', declining: '下降中', stable: '平稳' }[vTrend] || '平稳';
  var trendColor = { improving: '#4caf50', declining: '#f44336', stable: '#ffb74d' }[vTrend] || '#888';

  return '<div class="report-card"><div class="report-card-title">&#x1F4AC; 对话活跃度</div>'
    + '<div class="report-stat-row"><span class="report-stat-num">' + msgs + '</span><span class="report-stat-label">消息总数</span></div>'
    + '<div class="report-stat-row"><span class="report-stat-num">' + days + '</span><span class="report-stat-label">活跃天数</span></div>'
    + '<div class="report-stat-row"><span class="report-stat-num" style="color:' + trendColor + '">' + trendIcon + ' ' + trendLabel + '</span><span class="report-stat-label">效价趋势 (' + vAvg.toFixed(2) + ')</span></div>'
    + '</div>';
}

function renderBehaviorCard(behavior) {
  if (!behavior) {
    return '<div class="report-card"><div class="report-card-title">&#x1F3AF; 行为模式</div><div class="report-card-empty">暂无数据</div></div>';
  }
  var items = [];
  var lt = behavior.latency_trend_direction || 'stable';
  items.push('<div class="report-metric"><span class="report-metric-label">回复延迟趋势</span><span class="report-metric-val">' + lt + '</span></div>');
  var lst = behavior.length_trend_direction || 'stable';
  items.push('<div class="report-metric"><span class="report-metric-label">消息长度趋势</span><span class="report-metric-val">' + lst + '</span></div>');
  var ln = Number(behavior.late_night_ratio || 0);
  items.push('<div class="report-metric"><span class="report-metric-label">深夜活跃度</span><span class="report-metric-val">' + (ln * 100).toFixed(0) + '%</span></div>');
  var rhythm = Number(behavior.rhythm_stability || 0);
  items.push('<div class="report-metric"><span class="report-metric-label">节律稳定性</span><span class="report-metric-val">' + (rhythm * 100).toFixed(0) + '%</span></div>');
  return '<div class="report-card"><div class="report-card-title">&#x1F3AF; 行为模式</div>' + items.join('') + '</div>';
}

function renderInterventionCard(interventions) {
  if (!interventions || !interventions.length) {
    return '<div class="report-card"><div class="report-card-title">&#x1F3AF; 干预效果</div><div class="report-card-empty">暂无数据</div></div>';
  }
  var items = interventions.slice(0, 4).map(function(iv) {
    var label = { cbt: 'CBT认知重评', mindfulness: '正念引导', venting: '情绪宣泄', crisis: '危机干预' }[iv.intervention_type] || escapeHtml(iv.intervention_type);
    return '<div class="report-metric">'
      + '<span class="report-metric-label">' + label + '</span>'
      + '<span class="report-metric-val">' + (Number(iv.avg_distress_reduction) >= 0 ? '+' : '') + (Number(iv.avg_distress_reduction || 0)).toFixed(2) + '</span>'
      + '<span class="report-metric-sub">' + iv.sample_count + '次</span>'
      + '</div>';
  }).join('');
  return '<div class="report-card"><div class="report-card-title">&#x1F3AF; 干预效果</div>' + items + '</div>';
}

function renderCrisisCard(crisis) {
  var total = crisis.total || 0;
  var verified = crisis.verified || 0;
  var maxSev = Number(crisis.max_severity || 0);
  var sevColor = maxSev > 3 ? '#f44336' : maxSev > 1.5 ? '#ff9800' : '#4caf50';
  return '<div class="report-card"><div class="report-card-title">&#x1F6E1; 风险概览</div>'
    + (total === 0
      ? '<div class="report-card-empty">&#x2705; 期间无危机信号</div>'
      : '<div class="report-stat-row"><span class="report-stat-num">' + total + '</span><span class="report-stat-label">危机信号</span></div>'
        + '<div class="report-stat-row"><span class="report-stat-num">' + verified + '</span><span class="report-stat-label">LLM确认</span></div>'
        + '<div class="report-stat-row"><span class="report-stat-num" style="color:' + sevColor + '">' + maxSev.toFixed(1) + '</span><span class="report-stat-label">最高严重度</span></div>')
    + '</div>';
}

function renderMoodCard(moodDist, diaryCount) {
  var items = '';
  if (moodDist && Object.keys(moodDist).length > 0) {
    var entries = Object.entries(moodDist).sort(function(a, b) { return b[1] - a[1]; }).slice(0, 5);
    items = entries.map(function(e) {
      return '<div class="report-metric"><span class="report-metric-label">' + escapeHtml(e[0]) + '</span><span class="report-metric-val">' + e[1] + '次</span></div>';
    }).join('');
  } else {
    items = '<div class="report-card-empty">暂无自检记录</div>';
  }
  return '<div class="report-card"><div class="report-card-title">&#x1F3AD; 情绪分布</div>'
    + items
    + '<div class="report-metric" style="margin-top:8px;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;"><span class="report-metric-label">日记篇数</span><span class="report-metric-val">' + diaryCount + '篇</span></div>'
    + '</div>';
}

// ── 历史列表 ──

async function loadReportList() {
  try {
    var resp = await fetch('/api/report/list?limit=10');
    var json = await resp.json();
    var el = document.getElementById('reportHistory');
    if (!el) return;
    if (!json.ok || !json.data || !json.data.length) {
      el.innerHTML = '';
      return;
    }
    var items = json.data.map(function(r) {
      var active = r.id === _reportPeriod ? ' active' : '';
      var badge = r.report_type === 'milestone'
        ? '<span class="report-badge milestone sm">' + escapeHtml(r.milestone_label || '') + '</span>'
        : '<span class="report-badge manual sm">' + r.period_days + '天</span>';
      return '<div class="report-history-item' + active + '" onclick="switchReport(' + r.id + ')">'
        + '<span class="report-history-date">' + (r.date_from || '').slice(0, 10) + ' ~ ' + (r.date_to || '').slice(0, 10) + '</span>'
        + badge
        + '<span class="report-history-days">' + r.active_days + '活跃天</span>'
        + '</div>';
    }).join('');
    el.innerHTML = '<div class="report-history-title">&#x1F4C1; 历史报告</div>' + items;
  } catch (e) {
    // Silently fail - history is auxiliary
  }
}

// ── 交互 ──

function switchReport(id) {
  _reportPeriod = id;
  loadReportContent();
}

async function generateReport(days) {
  var btn = event && event.target;
  if (btn) { btn.disabled = true; btn.textContent = '生成中...'; }
  try {
    var resp = await fetch('/api/report/generate?days=' + days, { method: 'POST' });
    var json = await resp.json();
    if (json.ok && json.data) {
      _reportPeriod = json.data.id;
      loadReportContent();
    } else {
      alert('生成失败: ' + (json.message || '未知错误'));
    }
  } catch (e) {
    alert('生成失败: ' + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = days + '天'; }
  }
}

// ── 下载报告 ──

function downloadReport() {
  if (!_reportData) return;
  var r = _reportData;
  var d = r.dashboard || {};
  var ai = r.ai_insight || {};

  var lines = [];
  lines.push('# 心理健康分析报告');
  lines.push('');
  lines.push('**期间**: ' + (d.date_from || '?') + ' ~ ' + (d.date_to || '?'));
  lines.push('**活跃天数**: ' + (d.active_days || 0));
  lines.push('**报告类型**: ' + (r.report_type === 'milestone' ? '里程碑 ' + (r.milestone_label || '') : r.period_days + '天总结'));
  lines.push('');

  // 情绪六维
  var affect = d.affect_trend || {};
  if (Object.keys(affect).length) {
    lines.push('## 情绪六维');
    var labels = { seeking: '探索', play: '玩耍', care: '关怀', fear: '恐惧', rage: '愤怒', panic: '恐慌' };
    Object.keys(labels).forEach(function(k) {
      lines.push('- **' + labels[k] + '**: ' + (Number(affect[k] || 0)).toFixed(2));
    });
    lines.push('');
  }

  // 活跃度
  var activity = d.activity || {};
  lines.push('## 对话活跃度');
  lines.push('- 消息总数: ' + (activity.total_messages || 0));
  lines.push('- 活跃天数: ' + (activity.active_days || 0));
  var valence = d.valence_summary || {};
  lines.push('- 情绪效价: ' + Number(valence.avg_valence || 0.5).toFixed(2) + ' (' + (valence.trend_direction || 'stable') + ')');
  lines.push('');

  // 行为模式
  var behavior = d.behavior;
  if (behavior) {
    lines.push('## 行为模式');
    lines.push('- 回复延迟趋势: ' + (behavior.latency_trend_direction || 'stable'));
    lines.push('- 消息长度趋势: ' + (behavior.length_trend_direction || 'stable'));
    lines.push('- 深夜活跃度: ' + (Number(behavior.late_night_ratio || 0) * 100).toFixed(0) + '%');
    lines.push('- 节律稳定性: ' + (Number(behavior.rhythm_stability || 0) * 100).toFixed(0) + '%');
    lines.push('');
  }

  // 干预效果
  var interventions = d.interventions || [];
  if (interventions.length) {
    lines.push('## 干预效果');
    interventions.forEach(function(iv) {
      var label = { cbt: 'CBT认知重评', mindfulness: '正念引导', venting: '情绪宣泄', crisis: '危机干预' }[iv.intervention_type] || escapeHtml(iv.intervention_type);
      lines.push('- **' + label + '**: 痛苦缓解 ' + Number(iv.avg_distress_reduction || 0).toFixed(2) + ' (' + iv.sample_count + '次)');
    });
    lines.push('');
  }

  // 风险概览
  var crisis = d.crisis || {};
  lines.push('## 风险概览');
  lines.push('- 危机信号: ' + (crisis.total || 0));
  lines.push('- LLM确认: ' + (crisis.verified || 0));
  lines.push('- 最高严重度: ' + Number(crisis.max_severity || 0).toFixed(1));
  lines.push('');

  // 情绪分布
  var moodDist = d.mood_distribution || {};
  if (Object.keys(moodDist).length) {
    lines.push('## 情绪分布');
    Object.entries(moodDist).sort(function(a, b) { return b[1] - a[1]; }).forEach(function(e) {
      lines.push('- ' + escapeHtml(e[0]) + ': ' + e[1] + '次');
    });
    lines.push('');
  }

  // AI 洞察
  lines.push('## AI 综合洞察');
  lines.push('');
  lines.push(ai.insight || '暂无洞察');
  lines.push('');

  if (ai.key_findings && ai.key_findings.length) {
    lines.push('**关键发现**:');
    ai.key_findings.forEach(function(f) { lines.push('- ' + escapeHtml(f)); });
    lines.push('');
  }

  if (ai.suggestions && ai.suggestions.length) {
    lines.push('**关怀建议**:');
    ai.suggestions.forEach(function(s) { lines.push('- ' + escapeHtml(s)); });
    lines.push('');
  }

  lines.push('---');
  lines.push('*报告由 Psychology 自动生成*');

  var blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'report-' + (d.date_from || 'unknown') + '.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// ── 导出逐字稿 ──

function exportTranscript() {
  var d = _reportData ? (_reportData.dashboard || {}) : {};
  var df = d.date_from || '';
  var dt = d.date_to || '';
  var url = '/api/export/transcript?fmt=md';
  if (df) url += '&date_from=' + encodeURIComponent(df);
  if (dt) url += '&date_to=' + encodeURIComponent(dt);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'transcript-' + (df || 'recent') + '.md';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// ── 跨会话洞察 ──

async function loadCrossSession() {
  var el = document.getElementById('crossSessionCard');
  if (!el) return;
  el.innerHTML = '<div style="text-align:center;padding:20px;color:#6a6a8a;">加载跨会话分析...</div>';
  try {
    var resp = await fetch('/api/report/cross-session?weeks=4');
    var json = await resp.json();
    if (!json.ok) { el.innerHTML = ''; return; }
    renderCrossSession(json, el);
  } catch (e) {
    el.innerHTML = '<div class="report-card-empty">跨会话分析暂不可用</div>';
  }
}

function renderCrossSession(result, el) {
  var analysis = result.analysis;
  var data = result.data || {};
  var html = '';

  if (!analysis) {
    html += '<div class="report-card"><div class="report-card-title">🔄 跨会话洞察</div>';
    html += '<div class="report-card-empty">' + escapeHtml(result.message || '需要至少2周活跃数据') + '</div>';
    html += '<div class="report-card-meta" style="margin-top:8px;">当前: ' + (data.active_weeks || 0) + ' 活跃周, ' + (data.total_messages || 0) + ' 条消息</div>';
    html += '</div>';
    el.innerHTML = html;
    return;
  }

  html += '<div class="report-card" style="grid-column:1/-1;">';
  html += '<div class="report-card-title">🔄 跨会话洞察 (' + (data.weeks || 4) + '周)</div>';

  // Narrative
  if (analysis.narrative) {
    html += '<div class="report-insight-text" style="margin-bottom:14px;">' + escapeHtml(analysis.narrative) + '</div>';
  }

  // Themes
  if (analysis.themes && analysis.themes.length) {
    html += '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">';
    analysis.themes.forEach(function(t) {
      var trendIcon = { '上升': '↑', '下降': '↓', '稳定': '→' }[t.trend] || '';
      html += '<span class="report-finding-tag">' + escapeHtml(t.topic) + ' ' + trendIcon + ' (' + t.weeks_seen + '周)</span>';
    });
    html += '</div>';
  }

  // Emotion trend
  if (analysis.emotion_trend) {
    html += '<div class="report-metric">';
    html += '<span class="report-metric-label">📈 情绪趋势</span>';
    html += '<span class="report-metric-sub">' + escapeHtml(analysis.emotion_trend) + '</span>';
    html += '</div>';
  }

  // Behavior shift
  if (analysis.behavior_shift) {
    html += '<div class="report-metric">';
    html += '<span class="report-metric-label">🔄 行为变化</span>';
    html += '<span class="report-metric-sub">' + escapeHtml(analysis.behavior_shift) + '</span>';
    html += '</div>';
  }

  // Suggestions
  if (analysis.suggestions && analysis.suggestions.length) {
    html += '<div class="report-suggestions" style="margin-top:12px;">';
    html += '<div class="report-suggestions-title">💡 纵向建议</div>';
    analysis.suggestions.forEach(function(s) {
      html += '<div class="report-suggestion-item">🌱 ' + escapeHtml(s) + '</div>';
    });
    html += '</div>';
  }

  // Source summary
  html += '<div class="report-card-meta" style="margin-top:10px;border-top:1px solid rgba(255,255,255,0.05);padding-top:8px;">';
  html += '基于 ' + (data.active_weeks || 0) + ' 周 ' + (data.total_messages || 0) + ' 条对话 + ';
  var diaryTotal = 0;
  (data.weekly_diary || []).forEach(function(w) { diaryTotal += w.diary_count || 0; });
  html += diaryTotal + ' 篇日记</div>';

  html += '</div>';
  el.innerHTML = html;
}
