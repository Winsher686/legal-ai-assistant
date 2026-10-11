/* 企业法务 AI 助手 - 页面逻辑 */

// ---------- 登录 ----------
async function doLogin() {
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value.trim();
  const errEl = document.getElementById('login-error');
  errEl.textContent = '';
  if (!username || !password) {
    errEl.textContent = '请输入用户名和密码';
    return;
  }
  const btn = document.getElementById('login-btn');
  btn.disabled = true;
  try {
    const data = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    Auth.setToken(data.access_token);
    Auth.setUsername(username);
    toast('登录成功', 'success');
    window.location.hash = '#/dashboard';
    showApp();
  } catch (e) {
    errEl.textContent = e.message;
  } finally {
    btn.disabled = false;
  }
}

// ---------- 路由与布局 ----------
function showApp() {
  document.getElementById('login-page').classList.add('hidden');
  document.getElementById('app-layout').classList.remove('hidden');
  document.getElementById('user-name').textContent = Auth.getUsername();
}

function hideAllPages() {
  ['dashboard', 'chat', 'documents', 'graph'].forEach(p => {
    document.getElementById(`page-${p}`).classList.add('hidden');
  });
}

registerRoute('/dashboard', () => { hideAllPages(); document.getElementById('page-dashboard').classList.remove('hidden'); loadDashboard(); });
registerRoute('/chat', () => { hideAllPages(); document.getElementById('page-chat').classList.remove('hidden'); });
registerRoute('/documents', () => { hideAllPages(); document.getElementById('page-documents').classList.remove('hidden'); loadDocuments(); });
registerRoute('/graph', () => { hideAllPages(); document.getElementById('page-graph').classList.remove('hidden'); });

// ---------- 首页 ----------
async function loadDashboard() {
  try {
    const status = await api('/knowledge/status');
    document.getElementById('stat-docs').textContent = status.document_count ?? '-';
    document.getElementById('stat-vectors').textContent = status.vector_count ?? '-';
  } catch (e) {
    console.error(e);
  }
  // 今日问答（简化：从历史记录统计）
  try {
    const history = await api('/chat/history');
    document.getElementById('stat-today').textContent = history.length ?? '-';
  } catch (e) {}
}

// ---------- 智能问答 ----------
function handleChatKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendChat();
  }
}

async function sendChat() {
  const input = document.getElementById('chat-input');
  const question = input.value.trim();
  if (!question) return;
  const messages = document.getElementById('chat-messages');
  const btn = document.getElementById('chat-send-btn');

  // 显示用户消息
  appendMessage('user', question);
  input.value = '';
  btn.disabled = true;

  // 显示加载状态
  const loadingEl = appendMessage('assistant', '正在检索知识库...');

  try {
    const data = await api('/chat/query', {
      method: 'POST',
      body: JSON.stringify({ question }),
    });
    loadingEl.remove();
    appendAnswer(data);
  } catch (e) {
    loadingEl.remove();
    appendMessage('assistant', `❌ 出错了：${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

function appendMessage(role, text) {
  const messages = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `message ${role}`;
  const avatar = role === 'user' ? '👤' : '🤖';
  div.innerHTML = `<div class="avatar">${avatar}</div><div class="bubble">${escapeHtml(text)}</div>`;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function appendAnswer(data) {
  const messages = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = 'message assistant';
  let html = `<div class="avatar">🤖</div><div class="bubble">${escapeHtml(data.answer)}`;

  // 可信度
  const conf = data.confidence ?? 0;
  const confClass = conf >= 0.7 ? 'confidence-high' : (conf >= 0.4 ? 'confidence-mid' : 'confidence-low');
  html += `<div><span class="confidence-bar ${confClass}">可信度 ${(conf * 100).toFixed(0)}%</span></div>`;

  // 引用来源
  if (data.sources && data.sources.length > 0) {
    html += `<div class="sources"><strong style="font-size:13px;">📚 引用来源</strong>`;
    data.sources.forEach(s => {
      html += `<div class="source-item">
        <div class="src-name">${escapeHtml(s.document_name || '未知文档')}</div>
        <div class="src-loc">${escapeHtml(s.chapter || '')} ${escapeHtml(s.article || '')} ${s.page ? '第' + s.page + '页' : ''}</div>
        ${s.text ? `<div class="src-text">${escapeHtml(s.text)}</div>` : ''}
      </div>`;
    });
    html += `</div>`;
  }
  html += `</div>`;
  div.innerHTML = html;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

// ---------- 文档管理 ----------
async function uploadDocument() {
  const fileInput = document.getElementById('doc-file');
  const file = fileInput.files[0];
  if (!file) {
    toast('请选择要上传的文件', 'error');
    return;
  }
  const docType = document.getElementById('doc-type').value;
  const version = document.getElementById('doc-version').value.trim() || 'V1.0';

  const formData = new FormData();
  formData.append('file', file);
  formData.append('document_type', docType);
  formData.append('version', version);

  const token = Auth.getToken();
  try {
    const resp = await fetch(`${API_BASE}/document/upload`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData,
    });
    if (!resp.ok) {
      const data = await resp.json();
      throw new Error(data.detail || '上传失败');
    }
    const data = await resp.json();
    toast(`上传成功，文档 ID: ${data.document_id}`, 'success');
    fileInput.value = '';
    loadDocuments();
  } catch (e) {
    toast(e.message, 'error');
  }
}

async function loadDocuments() {
  try {
    const data = await api('/document/list');
    const tbody = document.getElementById('doc-table-body');
    if (!data.documents || data.documents.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#5a6b85;">暂无文档，请上传</td></tr>`;
      return;
    }
    const typeMap = {
      company_policy: '企业制度', contract_template: '合同模板', regulation: '法律法规',
      case_file: '历史案例', process_document: '流程文档',
    };
    tbody.innerHTML = data.documents.map(d => {
      const statusBadge = {
        completed: '<span class="badge badge-success">已完成</span>',
        pending: '<span class="badge badge-pending">待处理</span>',
        processing: '<span class="badge badge-processing">处理中</span>',
        failed: '<span class="badge badge-failed">失败</span>',
      }[d.status] || d.status;
      return `<tr>
        <td>${escapeHtml(d.name)}</td>
        <td>${typeMap[d.type] || d.type}</td>
        <td>${escapeHtml(d.version)}</td>
        <td>${statusBadge}</td>
        <td><a href="javascript:deleteDocument('${d.id}')" style="color:#dc2626;">删除</a></td>
      </tr>`;
    }).join('');
  } catch (e) {
    console.error(e);
  }
}

async function deleteDocument(id) {
  if (!confirm('确认删除该文档？将同时清理向量与图谱数据。')) return;
  try {
    await api(`/document/${id}`, { method: 'DELETE' });
    toast('删除成功', 'success');
    loadDocuments();
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ---------- 知识图谱 ----------
async function queryGraph() {
  const entity = document.getElementById('graph-entity').value.trim();
  if (!entity) return;
  try {
    const data = await api(`/knowledge/graph?entity=${encodeURIComponent(entity)}`);
    renderGraph(entity, data);
  } catch (e) {
    toast(e.message, 'error');
  }
}

function renderGraph(center, data) {
  const canvas = document.getElementById('graph-canvas');
  const relContainer = document.getElementById('graph-relations');
  const related = data.related || data.paths || [];

  if (related.length === 0) {
    canvas.innerHTML = `<div style="padding:40px;text-align:center;color:#5a6b85;">未找到相关实体关系</div>`;
    relContainer.innerHTML = '';
    return;
  }

  // 构建节点和边
  const nodes = new Map();
  nodes.set(center, { name: center, x: 300, y: 250 });
  const edges = [];
  let angle = 0;
  related.forEach((r, i) => {
    const toName = r.to || r.node?.name || '';
    const rel = r.relation || r.rel || '相关';
    if (!toName) return;
    if (!nodes.has(toName)) {
      angle = (i / Math.max(related.length, 1)) * Math.PI * 2;
      nodes.set(toName, { name: toName, x: 300 + Math.cos(angle) * 180, y: 250 + Math.sin(angle) * 150 });
    }
    edges.push({ from: center, to: toName, rel });
  });

  // 绘制 SVG
  let svg = `<svg width="100%" height="500" viewBox="0 0 600 500" style="background:#fff;border-radius:12px;">`;
  // 边
  edges.forEach(e => {
    const a = nodes.get(e.from), b = nodes.get(e.to);
    if (a && b) {
      svg += `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="#cbd5e1" stroke-width="1.5" marker-end="url(#arrow)" />`;
    }
  });
  svg += `<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="#94a3b8"/></marker></defs>`;
  // 关系标签
  edges.forEach(e => {
    const a = nodes.get(e.from), b = nodes.get(e.to);
    if (a && b) {
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      svg += `<text x="${mx}" y="${my - 6}" font-size="10" fill="#5a6b85" text-anchor="middle">${e.rel}</text>`;
    }
  });
  // 节点
  nodes.forEach(n => {
    const isCenter = n.name === center;
    svg += `<circle cx="${n.x}" cy="${n.y}" r="${isCenter ? 30 : 24}" fill="${isCenter ? '#2b5cff' : '#e8efff'}" stroke="${isCenter ? '#1e45c9' : '#2b5cff'}" stroke-width="2" />`;
    svg += `<text x="${n.x}" y="${n.y + 4}" font-size="${isCenter ? 11 : 10}" fill="${isCenter ? '#fff' : '#1a2233'}" text-anchor="middle" font-weight="600">${n.name.length > 6 ? n.name.slice(0, 6) + '…' : n.name}</text>`;
  });
  svg += `</svg>`;
  canvas.innerHTML = svg;

  // 关系列表
  relContainer.innerHTML = `<div class="card-title">关系明细</div>` + related.map(r => {
    const rel = r.relation || r.rel || '相关';
    const from = r.from || center;
    const to = r.to || '';
    return `<div class="source-item"><span style="color:#2b5cff;font-weight:600;">${escapeHtml(from)}</span> --${escapeHtml(rel)}--> <span style="font-weight:600;">${escapeHtml(to)}</span></div>`;
  }).join('');
}

// ---------- 工具 ----------
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ---------- 初始化 ----------
(function init() {
  if (Auth.isAuthed()) {
    showApp();
    handleRoute();
  } else {
    document.getElementById('login-page').classList.remove('hidden');
    document.getElementById('app-layout').classList.add('hidden');
    window.location.hash = '#/login';
  }
})();
