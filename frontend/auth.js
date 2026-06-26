const API_BASE = 'https://leadstack-backend.onrender.com';


let currentActiveTab = 'signin';
let activeToolUrl = null;
let activeToolName = null;

window.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  updateUserUI();
  setupEventListeners();
});

function setupEventListeners() {
  document.getElementById('navAuthBtn').addEventListener('click', () => openAuthModal('signin'));
  document.getElementById('closeAuthBtn').addEventListener('click', () => closeModal('authOverlay'));
  
  document.getElementById('tabSignIn').addEventListener('click', () => switchAuthTab('signin'));
  document.getElementById('tabSignUp').addEventListener('click', () => switchAuthTab('signup'));
  
  document.getElementById('authSubmitBtn').addEventListener('click', handleAuthSubmit);
  document.getElementById('logoutBtn').addEventListener('click', logout);

  document.getElementById('tool-youtube').addEventListener('click', () => 
    accessTool('YouTube', 'https://leadstack-youtube.onrender.com')
  );
  document.getElementById('tool-telegram').addEventListener('click', () => 
    accessTool('Telegram', 'https://leadstack-telegram.onrender.com')
  );
}

function updateUserUI() {
  const user = JSON.parse(sessionStorage.getItem('memberUser') || 'null');
  const tray = document.getElementById('userTray');
  const badge = document.getElementById('userBadge');
  const navBtn = document.getElementById('navAuthBtn');
  
  if (user) {
    badge.textContent = `Logged in as: ${user.email}`;
    tray.classList.remove('hidden');
    navBtn.classList.add('hidden');
  } else {
    tray.classList.add('hidden');
    navBtn.classList.remove('hidden');
  }
}

function openAuthModal(tabMode) {
  switchAuthTab(tabMode);
  document.getElementById('authOverlay').classList.remove('hidden');
}

function switchAuthTab(mode) {
  currentActiveTab = mode;
  clearMessages();
  
  const tabSignIn = document.getElementById('tabSignIn');
  const tabSignUp = document.getElementById('tabSignUp');
  const nameGroup = document.getElementById('nameGroup');
  const desc = document.getElementById('authCardDescription');
  const submitBtn = document.getElementById('authSubmitBtn');

  if (mode === 'signin') {
    tabSignIn.classList.add('active');
    tabSignUp.classList.remove('active');
    nameGroup.classList.add('hidden');
    desc.textContent = "Log in to your Leadstack account and deploy your active scrapers.";
    submitBtn.textContent = "Sign In Account";
  } else {
    tabSignUp.classList.add('active');
    tabSignIn.classList.remove('active');
    nameGroup.classList.remove('hidden');
    desc.textContent = "Create an account in seconds and get your active scrapers.";
    submitBtn.textContent = "Create Free Account";
  }
}

function handleAuthSubmit() {
  if (currentActiveTab === 'signin') {
    handleLogin();
  } else {
    handleRegister();
  }
}

async function handleLogin() {
  const emailEl = document.getElementById('email');
  const passwordEl = document.getElementById('password');

  const email    = emailEl.value.trim();
  const password = passwordEl.value;

  clearMessages();

  if (!email || !password) {
    showError('Please enter your email and password.');
    return;
  }

  setLoading(true, 'Signing inâ€¦');

  try {
    const res = await fetch(`${API_BASE}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.message || 'Invalid email or password.');
      return;
    }

    sessionStorage.setItem('memberUser', JSON.stringify({
      email:              data.email,
      name:               data.name,
      token:              data.token
    }));

    document.getElementById('authOverlay').classList.add('hidden');
    updateUserUI();
    openPendingTool(data.token);

  } catch (err) {
    showError('Unable to reach the server. Please try again.');
  } finally {
    setLoading(false);
  }
}

async function handleRegister() {
  const nameEl     = document.getElementById('username');
  const emailEl    = document.getElementById('email');
  const passwordEl = document.getElementById('password');

  const name     = nameEl.value.trim();
  const email    = emailEl.value.trim();
  const password = passwordEl.value;

  clearMessages();

  if (!name || !email || !password) {
    showError('Please complete all form fields to sign up.');
    return;
  }

  setLoading(true, 'Creating accountâ€¦');

  try {
    const res = await fetch(`${API_BASE}/api/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name })
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.message || 'Registration failed. Try a different email.');
      return;
    }

    showSuccess('Account created successfully! Switching to login tab...');
    setTimeout(() => {
      switchAuthTab('signin');
    }, 2000);

  } catch (err) {
    showError('Connection to server dropped. Please retry.');
  } finally {
    setLoading(false);
  }
}

function accessTool(name, url) {
  const user = JSON.parse(sessionStorage.getItem('memberUser') || 'null');
  activeToolUrl = url;
  activeToolName = name;

  if (!user) {
    openAuthModal('signup');
    return;
  }

  openToolWithToken(url, user.token);
  activeToolUrl = null;
  activeToolName = null;
}

function openPendingTool(token) {
  if (!activeToolUrl) return;
  openToolWithToken(activeToolUrl, token);
  activeToolUrl = null;
  activeToolName = null;
}

function openToolWithToken(url, token) {
  if (!token) {
    window.open(url, '_blank');
    return;
  }
  const cleanUrl = url.replace(/\/+$/, '');
  const separator = cleanUrl.includes('?') ? '&' : '?';
  const targetUrl = `${cleanUrl}${separator}token=${encodeURIComponent(token)}`;
  window.open(targetUrl, '_blank');
}

function logout() {
  sessionStorage.removeItem('memberUser');
  window.location.reload();
}

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
  if(id === 'authOverlay') clearMessages();
}

function showError(msg) {
  const el = document.getElementById('errorMsg');
  if (!el) return;
  el.innerHTML = msg;
  el.classList.remove('hidden');
}

function showSuccess(msg) {
  const el = document.getElementById('successMsg');
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
}

function clearMessages() {
  ['errorMsg', 'successMsg'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });
}

function setLoading(on, textString) {
  const btn = document.getElementById('authSubmitBtn');
  if (!btn) return;
  btn.disabled = on;
  if(on) {
    btn.textContent = textString;
  } else {
    btn.textContent = currentActiveTab === 'signin' ? 'Sign In Account' : 'Create Free Account';
  }
}