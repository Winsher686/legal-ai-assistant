/* 企业法务 AI 助手 - 公共 JS（API 封装 + 认证 + 路由） */

// API 基地址（Nginx 反向代理到后端 /api）
const API_BASE = '/api';

// 认证状态
const Auth = {
  getToken() {
    return localStorage.getItem('legal_ai_token');
  },
  setToken(token) {
    localStorage.setItem('legal_ai_token', token);
  },
  getUsername() {
    return localStorage.getItem('legal_ai_username');
  },
  setUsername(name) {
    localStorage.setItem('legal_ai_username', name);
  },
  clear() {
    localStorage.removeItem('legal_ai_token');
    localStorage.removeItem('legal_ai_username');
  },
  isAuthed() {
    return !!this.getToken();
  },
};

// API 请求封装
async function api(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  const token = Auth.getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const resp = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (resp.status === 401) {
    Auth.clear();
    window.location.hash = '#/login';
    throw new Error('未认证，请重新登录');
  }
  if (!resp.ok) {
    let detail = '请求失败';
    try {
      const data = await resp.json();
      detail = data.detail || detail;
    } catch (e) {}
    throw new Error(detail);
  }
  return resp.json();
}

// Toast 提示
function toast(message, type = 'success') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// 登出
function logout() {
  Auth.clear();
  window.location.hash = '#/login';
}

// 简单路由
const routes = {};

function registerRoute(path, handler) {
  routes[path] = handler;
}

function handleRoute() {
  const hash = window.location.hash || '#/dashboard';
  const path = hash.replace('#', '') || '/dashboard';
  const handler = routes[path] || routes['/dashboard'];
  if (handler) handler();
}

window.addEventListener('hashchange', handleRoute);
