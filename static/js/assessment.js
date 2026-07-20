// ═══════════════════════════════════════════
// 临床评估面板 — PHQ-9 / GAD-7
// ═══════════════════════════════════════════

var _asSessionId = null;

async function loadAssessmentContent() {
  // 检查是否有进行中的评估
  auxContent.innerHTML = '<div class="report-loading">加载评估...</div>';
  try {
    var scalesResp = await fetch('/api/assessment/scales');
    var scalesData = await scalesResp.json();

    var html = '<div class="report-header">';
    html += '<div class="report-title-row"><span class="report-title">&#x1F3AF; 临床评估</span></div>';
    html += '<div class="report-subtitle">PHQ-9 抑郁筛查 · GAD-7 焦虑筛查</div>';
    html += '</div>';

    if (!_asSessionId) {
      // 量表选择
      html += '<div style="display:flex;gap:12px;margin-bottom:16px;">';
      html += '<button class="consent-btn primary" onclick="startAssessment(\'phq9\')" style="flex:1;">&#x1F4CB; PHQ-9 抑郁筛查<br><span style="font-size:0.65rem;opacity:0.7;">9题 · 约3分钟</span></button>';
      html += '<button class="consent-btn primary" onclick="startAssessment(\'gad7\')" style="flex:1;">&#x1F4CB; GAD-7 焦虑筛查<br><span style="font-size:0.65rem;opacity:0.7;">7题 · 约2分钟</span></button>';
      html += '</div>';
      html += '<div class="report-insight"><div class="report-insight-title">&#x26A0; 重要提示</div><div class="report-insight-text">本评估仅为筛查工具，结果不作为临床诊断依据。如有严重困扰，请咨询精神科医生或拨打 400-161-9995。</div></div>';
      html += '<div id="asQuestion"></div>';
    }
    html += '<div id="asHistory"></div>';
    auxContent.innerHTML = html;
    loadAssessmentHistory();
  } catch(e) {
    auxContent.innerHTML = '<div class="report-loading" style="color:#f44336;">加载失败</div>';
  }
}

async function startAssessment(scaleId) {
  try {
    var resp = await fetch('/api/assessment/start?scale_id=' + scaleId, { method: 'POST' });
    var json = await resp.json();
    if (!json.ok) { alert(json.message); return; }
    _asSessionId = json.session_id;
    renderQuestion(json);
  } catch(e) { alert('启动失败: ' + e.message); }
}

function renderQuestion(data) {
  var html = '<div class="report-card" style="margin-top:12px;">';
  html += '<div class="report-card-title">' + (data.completed ? '评估完成' : ('问题 ' + data.question_index + '/' + data.total_questions)) + '</div>';
  html += '<div style="font-size:0.9rem;color:#d0d0e0;margin-bottom:12px;">' + escapeHtml(data.question) + '</div>';

  if (data.completed) {
    html += '<div style="text-align:center;margin:16px 0;">';
    html += '<div style="font-size:2rem;font-weight:700;color:' + (data.total_score > data.max_score*0.5 ? '#f44336' : '#4caf50') + ';">' + data.total_score + ' / ' + data.max_score + '</div>';
    html += '<div style="font-size:0.85rem;color:#b0b0d0;margin:8px 0;">' + escapeHtml(data.level) + '</div>';
    html += '<div style="font-size:0.75rem;color:#8a8aaa;line-height:1.6;">' + escapeHtml(data.suggestion) + '</div>';
    html += '</div>';
    html += '<button class="consent-btn primary" onclick="_asSessionId=null;loadAssessmentContent();" style="width:100%;margin-top:12px;">&#x1F504; 重新评估</button>';
    _asSessionId = null;
  } else {
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">';
    data.options.forEach(function(opt) {
      html += '<button class="report-gen-btn" onclick="answerQuestion(' + opt.score + ')" style="text-align:center;">' + escapeHtml(opt.label) + '<br><span style="font-size:0.55rem;opacity:0.5;">(' + opt.score + '分)</span></button>';
    });
    html += '</div>';
  }
  html += '</div>';
  document.getElementById('asQuestion').innerHTML = html;
}

async function answerQuestion(score) {
  try {
    var resp = await fetch('/api/assessment/answer?session_id=' + _asSessionId + '&score=' + score, { method: 'POST' });
    var json = await resp.json();
    if (!json.ok) { alert(json.message); return; }
    renderQuestion(json);
  } catch(e) { alert('提交失败: ' + e.message); }
}

async function loadAssessmentHistory() {
  try {
    var resp = await fetch('/api/assessment/history?limit=5');
    var json = await resp.json();
    var el = document.getElementById('asHistory');
    if (!el || !json.data || !json.data.length) return;
    var items = json.data.map(function(r) {
      var scoreColor = r.total_score > (r.scale_id === 'phq9' ? 27 : 21) * 0.5 ? '#f44336' : '#ffb74d';
      return '<div class="report-metric">'
        + '<span class="report-metric-label">' + escapeHtml(r.scale_name || '') + '</span>'
        + '<span class="report-metric-val" style="color:' + scoreColor + '">' + r.total_score + '分</span>'
        + '<span class="report-metric-sub">' + (r.completed_at || '').slice(0, 10) + '</span>'
        + '</div>';
    }).join('');
    el.innerHTML = '<div class="report-card" style="margin-top:12px;"><div class="report-card-title">&#x1F4C1; 历史评估</div>' + items + '</div>';
  } catch(e) {}
}
