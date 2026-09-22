const API_URL = 'http://127.0.0.1:8000';
let reports = [];
let accessToken = localStorage.getItem('ecotrack_token');
let currentUser = null;
let map;
let campusScene;
const GIDA_CENTER = [26.7430558, 83.2733427];
const CAMPUS_SCALE = 90000;
let currentLocation;

const byId = (id) => document.getElementById(id);
const authHeaders = () => accessToken ? { Authorization: `Bearer ${accessToken}` } : {};

function initMap() {
  if (typeof THREE === 'undefined') return;
  const container = byId('map');
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xdceee3);
  const camera = new THREE.PerspectiveCamera(42, container.clientWidth / container.clientHeight, 0.1, 1000);
  camera.position.set(13, 16, 18);
  camera.lookAt(0, 0, 0);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  container.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x668879, 2));
  const sun = new THREE.DirectionalLight(0xffffff, 2.5);
  sun.position.set(8, 18, 10);
  scene.add(sun);
  const campus = new THREE.Group();
  const material = (color) => new THREE.MeshStandardMaterial({ color, roughness: .85 });
  const ground = new THREE.Mesh(new THREE.BoxGeometry(24, .25, 18), material(0xb9dfc5));
  ground.position.y = -.25;
  campus.add(ground);
  const addBlock = (name, x, z, width, depth, height, color) => {
    const block = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), material(color));
    block.position.set(x, height / 2, z);
    block.userData.name = name;
    campus.add(block);
  };
  const addGround = (x, z, width, depth, color) => {
    const field = new THREE.Mesh(new THREE.BoxGeometry(width, .06, depth), material(color));
    field.position.set(x, .03, z);
    campus.add(field);
  };
  addBlock('Main Building', -4, 1, 5, 3, 2.2, 0xf4f0dc);
  addBlock('Workshops', -8, -3, 3, 4, 1.1, 0xe3c9a9);
  addBlock('Shri Krishna Academy', 5, -2, 4, 3, 1.6, 0xf0dcae);
  addBlock('Admin Block', -1, -3.6, 2.5, 1.4, 1.4, 0xd8e5df);
  addBlock('Gate House', 8, 6, 1.3, 1.2, .9, 0xc9d8d0);
  addGround(5, 4, 7, 5, 0x83bd91);
  addGround(-1, 6, 5, 2.5, 0xc9df9b);
  addGround(-3, -6, 5, 2.2, 0x9ed29f);
  addGround(3, -6, 5, 2.2, 0x9ed29f);
  const road = material(0xa8b9b0);
  const path = new THREE.Mesh(new THREE.BoxGeometry(1, .08, 16), road);
  path.position.set(1.5, .08, 0);
  campus.add(path);
  scene.add(campus);
  const markerGroup = new THREE.Group();
  scene.add(markerGroup);
  campusScene = { scene, camera, renderer, container, markerGroup, campus };
  const animate = () => { requestAnimationFrame(animate); campus.rotation.y += .0008; renderer.render(scene, camera); };
  animate();
  window.addEventListener('resize', () => { camera.aspect = container.clientWidth / container.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(container.clientWidth, container.clientHeight); });
}

function setLocation(latitude, longitude) {
  currentLocation = [latitude, longitude];
  byId('latitude').value = latitude.toFixed(6);
  byId('longitude').value = longitude.toFixed(6);
  byId('location-latitude').textContent = latitude.toFixed(6);
  byId('location-longitude').textContent = longitude.toFixed(6);
  byId('location-status').textContent = `GPS locked: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
  if (campusScene) {
    campusScene.camera.position.set(10, 13, 15);
    renderCampusLocation();
  }
}

function toCampusPosition(latitude, longitude) {
  return {
    x: Math.max(-11, Math.min(11, (longitude - GIDA_CENTER[1]) * CAMPUS_SCALE)),
    z: Math.max(-8, Math.min(8, -(latitude - GIDA_CENTER[0]) * CAMPUS_SCALE)),
  };
}

function createMarker(color, size = .28) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(size, 16, 16),
    new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: .25 }),
  );
}

function renderCampusLocation() {
  if (!campusScene || !currentLocation) return;
  if (campusScene.locationMarker) campusScene.markerGroup.remove(campusScene.locationMarker);
  const position = toCampusPosition(currentLocation[0], currentLocation[1]);
  const marker = createMarker(0x2478ff, .34);
  marker.position.set(position.x, 1.35, position.z);
  campusScene.markerGroup.add(marker);
  campusScene.locationMarker = marker;
}

function getLocation() {
  const locationStatus = byId('location-status');
  if (!navigator.geolocation) {
    locationStatus.textContent = 'GPS is not supported by this browser';
    return;
  }
  locationStatus.textContent = 'Requesting your location...';
  navigator.geolocation.getCurrentPosition(
    (position) => setLocation(position.coords.latitude, position.coords.longitude),
    () => { locationStatus.textContent = 'GPS unavailable. Trying network location...'; getNetworkLocation(); },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
  );
}

async function getNetworkLocation() {
  const locationStatus = byId('location-status');
  locationStatus.textContent = 'Detecting approximate network location...';
  try {
    const response = await fetch(`${API_URL}/location/ip`);
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Network location unavailable');
    setLocation(Number(result.latitude), Number(result.longitude));
    locationStatus.textContent = `${result.city || 'Approximate area'}, ${result.region || ''} (network)`.trim();
  } catch (error) {
    locationStatus.textContent = 'Unable to detect network location.';
  }
}

function renderMapMarkers() {
  renderCampusMarkers();
}

function renderCampusMarkers() {
  if (!campusScene) return;
  campusScene.markerGroup.clear();
  reports.forEach((report) => {
    const marker = createMarker(0xf07b61);
    const position = toCampusPosition(report.latitude, report.longitude);
    marker.position.set(position.x, 1.1, position.z);
    marker.userData.reportId = report.report_id;
    campusScene.markerGroup.add(marker);
  });
  renderCampusLocation();
}

function formatStatus(value) {
  return value.replaceAll('_', ' ');
}

function renderAnalytics(data) {
  byId('total-reports').textContent = data.total_reports;
  byId('pending-reports').textContent = data.pending_reports;
  byId('collected-reports').textContent = data.collected_reports;
  const verified = data.status_counts.verified || 0;
  byId('verified-rate').textContent = data.total_reports ? `${Math.round((verified / data.total_reports) * 100)}%` : '0%';
}

function renderReports() {
  const search = byId('search').value.trim().toLowerCase();
  const status = byId('status-filter').value;
  const visible = reports.filter((report) => {
    const matchesSearch = !search || report.report_id.toLowerCase().includes(search) || (report.category || '').toLowerCase().includes(search);
    return matchesSearch && (!status || report.status === status);
  });
  byId('map-count').textContent = `${visible.length} visible`;
  if (campusScene) {
    campusScene.markerGroup.clear();
    visible.forEach((report) => {
      const marker = createMarker(0xf07b61);
      const position = toCampusPosition(report.latitude, report.longitude);
      marker.position.set(position.x, 1.1, position.z);
      campusScene.markerGroup.add(marker);
    });
    renderCampusLocation();
  }
  const body = byId('reports-body');
  if (!visible.length) {
    body.innerHTML = '<tr><td colspan="6" class="empty">No reports match these filters.</td></tr>';
    return;
  }
  body.innerHTML = visible.map((report) => `<tr>
    <td><div class="report-id">${report.report_id}</div><div class="muted">${report.description || 'No description'}</div></td>
    <td>${report.category || 'Unclassified'}</td>
    <td>${Number(report.latitude).toFixed(4)}, ${Number(report.longitude).toFixed(4)}</td>
    <td>${new Date(report.timestamp).toLocaleDateString()}</td>
    <td><span class="status ${report.status}">${formatStatus(report.status)}</span></td>
    <td>${actionMarkup(report)}</td>
  </tr>`).join('');
  body.querySelectorAll('[data-action]').forEach((button) => button.addEventListener('click', () => handleAction(button.dataset.action, button.dataset.id)));
}

function actionMarkup(report) {
  if (!currentUser) return '<span class="muted">Sign in</span>';
  if (currentUser.role === 'administrator') {
    if (!report.collector_id && !['verified', 'rejected'].includes(report.status)) return `<button class="table-action" data-action="assign" data-id="${report.report_id}">Assign</button>`;
    if (report.evidence_reference) return `<button class="table-action" data-action="verify" data-id="${report.report_id}">Verify</button>`;
    return '<span class="muted">Watching</span>';
  }
  if (currentUser.role === 'collector' && report.collector_id === currentUser.user_id) {
    if (report.status === 'assigned') return `<button class="table-action" data-action="progress" data-id="${report.report_id}">Start</button>`;
    if (report.status === 'in_progress') return `<button class="table-action" data-action="collect" data-id="${report.report_id}">Collected</button>`;
    if (report.status === 'collected' && !report.evidence_reference) return `<button class="table-action" data-action="evidence" data-id="${report.report_id}">Evidence</button>`;
  }
  return '<span class="muted">-</span>';
}

async function handleAction(action, reportId) {
  let endpoint;
  let options = { headers: { ...authHeaders(), 'Content-Type': 'application/json' } };
  if (action === 'assign') {
    options.method = 'POST';
    options.body = JSON.stringify({ collector_id: 'collector-demo' });
    endpoint = `/reports/${reportId}/assignment`;
  } else if (action === 'progress' || action === 'collect') {
    options.method = 'PATCH';
    options.body = JSON.stringify({ status: action === 'progress' ? 'in_progress' : 'collected' });
    endpoint = `/reports/${reportId}/status`;
  } else if (action === 'evidence') {
    const evidence = prompt('Evidence image reference or filename:');
    if (!evidence) return;
    options.method = 'POST';
    options.body = JSON.stringify({ evidence_reference: evidence });
    endpoint = `/reports/${reportId}/evidence`;
  } else if (action === 'verify') {
    const approved = confirm('Approve this completion evidence?');
    options.method = 'POST';
    endpoint = `/reports/${reportId}/verify?approved=${approved}`;
  }
  const response = await fetch(`${API_URL}${endpoint}`, options);
  if (!response.ok) {
    const error = await response.json();
    alert(error.detail || 'Action failed');
    return;
  }
  await loadDashboard();
}

async function loadDashboard() {
  try {
    const [reportsResponse, analyticsResponse] = await Promise.all([
      fetch(`${API_URL}/reports`, { headers: authHeaders() }),
      fetch(`${API_URL}/analytics`, { headers: authHeaders() }),
    ]);
    if (!reportsResponse.ok || !analyticsResponse.ok) throw new Error('API unavailable');
    reports = await reportsResponse.json();
    renderAnalytics(await analyticsResponse.json());
    renderReports();
    byId('form-message').textContent = '';
  } catch (error) {
    byId('reports-body').innerHTML = '<tr><td colspan="6" class="empty">Start the API with uvicorn to load live reports.</td></tr>';
    byId('form-message').textContent = accessToken ? 'API connection unavailable.' : 'Sign in to load live reports.';
  }
}

async function restoreSession() {
  if (!accessToken) return;
  const response = await fetch(`${API_URL}/auth/me`, { headers: authHeaders() });
  if (!response.ok) {
    accessToken = null;
    localStorage.removeItem('ecotrack_token');
    return;
  }
  currentUser = await response.json();
  byId('session-label').textContent = `${currentUser.name} · ${currentUser.role}`;
  byId('logout').hidden = false;
  byId('login-screen').hidden = true;
  byId('app-wrapper').hidden = false;

  if (currentUser.role === 'citizen') {
    byId('report-panel').hidden = false;
    byId('reports-panel').hidden = true;
  } else {
    byId('report-panel').hidden = true;
    byId('reports-panel').hidden = false;
  }
}

let isOtpStep = false;
function setAuthMode(mode) {
  byId('auth-mode').value = mode;
  const registering = mode === 'register';
  const forgot = mode === 'forgot';

  byId('group-name').hidden = !registering;
  byId('auth-name').required = registering;

  if (forgot) {
    byId('group-password').hidden = true;
    byId('auth-password').required = false;
    byId('auth-password').placeholder = 'New Password (5+ characters)';
    byId('auth-submit-btn').textContent = 'Send Reset OTP';
    byId('auth-title').textContent = 'Reset Password';
    byId('auth-subtitle').textContent = 'Get back into EcoTrack AI';
  } else {
    byId('group-password').hidden = false;
    byId('auth-password').required = true;
    byId('auth-password').placeholder = 'Password (5+ characters)';
    byId('auth-submit-btn').textContent = registering ? 'Next' : 'Send OTP';
    byId('auth-title').textContent = registering ? 'Register now' : 'Welcome back';
    byId('auth-subtitle').textContent = registering ? 'Secure your spot in EcoTrack AI' : 'Sign in to continue';
  }

  byId('auth-password').autocomplete = registering ? 'new-password' : 'current-password';

  byId('link-login').hidden = !registering;
  byId('link-register').hidden = registering;
  if (byId('password-rules')) byId('password-rules').hidden = !registering;

  // Reset OTP step
  isOtpStep = false;
  byId('group-otp').hidden = true;
  byId('auth-otp').required = false;
  byId('auth-message').textContent = '';
}

byId('link-login').addEventListener('click', (e) => { e.preventDefault(); setAuthMode('login'); });
byId('link-register').addEventListener('click', (e) => { e.preventDefault(); setAuthMode('register'); });
byId('link-forgot').addEventListener('click', (e) => { e.preventDefault(); setAuthMode('forgot'); });

byId('auth-form').addEventListener('submit', async (event) => {
  event.preventDefault();

  if (isOtpStep) {
    const mode = byId('auth-mode').value;
    const isForgot = mode === 'forgot';

    byId('auth-message').textContent = 'Verifying OTP...';
    try {
      const payload = {
        email: byId('auth-email').value,
        otp: byId('auth-otp').value
      };
      if (isForgot) payload.new_password = byId('auth-password').value;

      const endpoint = isForgot ? '/auth/reset-password' : '/auth/verify-otp';
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'OTP verification failed');

      accessToken = result.access_token;
      localStorage.setItem('ecotrack_token', accessToken);
      await restoreSession();
      byId('auth-message').textContent = '';
      await loadDashboard();

      // Reset for next time
      setAuthMode('register');
      byId('auth-form').reset();
    } catch (error) {
      byId('auth-message').textContent = error.message;
    }
    return;
  }

  const mode = byId('auth-mode').value;
  const registering = mode === 'register';
  const forgot = mode === 'forgot';

  const payload = {
    email: byId('auth-email').value
  };
  if (!forgot) payload.password = byId('auth-password').value;
  if (registering) payload.name = byId('auth-name').value;

  let endpoint = '/auth/login';
  if (registering) endpoint = '/auth/register';
  if (forgot) endpoint = '/auth/forgot-password';

  byId('auth-message').textContent = 'Connecting...';
  try {
    const response = await fetch(`${API_URL}${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Authentication failed');

    if (result.status === 'otp_sent') {
      isOtpStep = true;
      byId('auth-message').textContent = result.otp
        ? `Development OTP: ${result.otp}`
        : 'OTP sent to your email. Please verify.';

      if (forgot) {
        byId('group-password').hidden = false;
        byId('auth-password').required = true;
        if (byId('password-rules')) byId('password-rules').hidden = false;
      } else {
        byId('group-password').hidden = true;
        byId('auth-password').required = false;
        if (byId('password-rules')) byId('password-rules').hidden = true;
      }

      byId('group-otp').hidden = false;
      byId('auth-otp').required = true;
      byId('auth-submit-btn').textContent = forgot ? 'Reset Password' : 'Verify OTP';
      return;
    }

    accessToken = result.access_token;
    localStorage.setItem('ecotrack_token', accessToken);
    await restoreSession();
    byId('auth-message').textContent = '';
    await loadDashboard();
  } catch (error) {
    byId('auth-message').textContent = error.message;
  }
});

byId('logout').addEventListener('click', () => {
  accessToken = null;
  currentUser = null;
  localStorage.removeItem('ecotrack_token');
  byId('session-label').textContent = 'Not signed in';
  byId('logout').hidden = true;
  byId('login-screen').hidden = false;
  byId('app-wrapper').hidden = true;
});

byId('report-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = byId('form-message');
  if (!currentUser) {
    message.textContent = 'Sign in before submitting a report.';
    byId('login-screen').hidden = false;
    byId('app-wrapper').hidden = true;
    return;
  }
  const data = new FormData(form);
  data.append('user_id', currentUser.user_id);
  message.textContent = 'Submitting report...';
  try {
    const response = await fetch(`${API_URL}/reports`, {
      method: 'POST',
      headers: authHeaders(),
      body: data,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Unable to submit report');
    form.reset();
    byId('file-label').textContent = 'Choose a photo';
    message.textContent = `Reference No: ${result.report_id} - Record successful and confirmation letter will be sent soon`;
    await loadDashboard();
  } catch (error) {
    message.textContent = error.message;
  }
});

byId('image').addEventListener('change', (event) => {
  byId('file-label').textContent = event.target.files[0]?.name || 'Choose a photo';
});
byId('search').addEventListener('input', renderReports);
byId('status-filter').addEventListener('change', renderReports);
byId('refresh').addEventListener('click', () => {
  if (campusScene) { campusScene.camera.position.set(13, 16, 18); campusScene.camera.lookAt(0, 0, 0); }
  loadDashboard();
});
byId('locate').addEventListener('click', getLocation);
byId('network-locate').addEventListener('click', getNetworkLocation);
byId('focus-report').addEventListener('click', () => byId('report-panel').scrollIntoView({ behavior: 'smooth' }));
initMap();
getLocation();
setAuthMode('login');
restoreSession().finally(loadDashboard);

// Intro Animation Logic
setTimeout(() => {
  const box = document.getElementById("box");
  const place = document.getElementById("boxPlace");
  if (box && place) {
    box.style.transition = "1.2s ease";
    box.style.position = "fixed";
    box.style.left = "70%";
    box.style.top = "auto";
    box.style.bottom = "82px";
    box.style.transform = "scale(.8)";
    place.classList.add("show");
  }
}, 4200);

setTimeout(() => {
  const intro = document.getElementById("intro");
  if (intro) intro.style.opacity = "0";
}, 5400);

setTimeout(() => {
  const loginScreen = document.getElementById("login-screen");
  if (loginScreen) loginScreen.classList.add("active");
  const intro = document.getElementById("intro");
  if (intro) intro.style.display = "none";
}, 6200);
