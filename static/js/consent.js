// ═══════════════════════════════════════════
// 知情同意弹窗
// ═══════════════════════════════════════════

(function() {
  var CONSENT_KEY = 'psychology_consent_v1';

  if (localStorage.getItem(CONSENT_KEY) === '1') return;

  var overlay = document.createElement('div');
  overlay.id = 'consent-overlay';
  overlay.innerHTML =
    '<div class="consent-modal">' +
    '<div class="consent-icon">&#x1F9E0;</div>' +
    '<div class="consent-title">欢迎使用 Psychology</div>' +
    '<div class="consent-subtitle">心理健康辅助AI · 专业边界声明</div>' +
    '<div class="consent-body">' +
    '<p>我是一个<strong>心理健康辅助AI</strong>，不是持证心理治疗师或精神科医生。在使用前，请了解以下重要信息：</p>' +
    '<ul>' +
    '<li>我不做<strong>临床诊断</strong>，不推荐药物</li>' +
    '<li>如果你有<strong>自杀或自伤</strong>的想法，请立即拨打全国心理援助热线 <strong>400-161-9995</strong></li>' +
    '<li>对话记录不构成医疗档案，建议定期咨询<strong>持证专业人士</strong></li>' +
    '<li>我不会主动索要你的真实姓名、住址、联系方式等<strong>可识别个人信息</strong></li>' +
    '<li>我会努力倾听和支持你，但我<strong>不能替代</strong>真人治疗师</li>' +
    '</ul>' +
    '<p style="margin-top:12px;color:#9090b0;">点击"同意并继续"即表示你已阅读并理解以上声明。</p>' +
    '</div>' +
    '<div class="consent-actions">' +
    '<button class="consent-btn primary" id="consentAgree">同意并继续</button>' +
    '</div>' +
    '</div>';

  document.body.appendChild(overlay);

  document.getElementById('consentAgree').addEventListener('click', function() {
    localStorage.setItem(CONSENT_KEY, '1');
    // 异步通知后端
    try { fetch('/api/consent', { method: 'POST' }); } catch(e) {}
    overlay.classList.add('consent-fadeout');
    setTimeout(function() { overlay.remove(); }, 400);
  });
})();
