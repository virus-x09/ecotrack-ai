const hostname = window.location.hostname;
const isLocal = !hostname || hostname === 'localhost' || hostname === '127.0.0.1' || hostname.startsWith('192.168.') || hostname.startsWith('10.');
// In Vercel, the API is available at the same domain under /api
const API_URL = isLocal ? `http://${hostname || 'localhost'}:8000` : "/api";
let reports = [];
let accessToken = localStorage.getItem("ecotrack_token");
let currentUser = null;
let map;
let campusScene;
const GIDA_CENTER = [26.7430558, 83.2733427];
const CAMPUS_SCALE = 90000;
let currentLocation;

const byId = (id) => document.getElementById(id);
const authHeaders = () =>
  accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
const isGuest = () => Boolean(currentUser?.isGuest);

function updateSidebarProfile(name) {
  const avatarEl = document.getElementById("sidebar-avatar");
  const nameEl = document.getElementById("sidebar-name");
  
  if (nameEl) nameEl.textContent = name;
  if (avatarEl) {
    const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    avatarEl.textContent = initials || 'G';
  }
}

function enterGuestMode() {
  accessToken = null;
  currentUser = { name: "Guest", role: "citizen", isGuest: true };
  updateSidebarProfile("Guest");
  byId("session-label").textContent = "Guest mode";
  byId("login").hidden = false;
  byId("logout").hidden = true;
  byId("login-screen").hidden = true;
  byId("app-wrapper").hidden = false;
  const colDash = byId("collector-dashboard-wrapper");
  if (colDash) colDash.hidden = true;
  document.body.classList.remove("collector-mode");
  if (byId("reports-panel")) byId("reports-panel").hidden = false;
}

function openSignIn() {
  byId("login-screen").hidden = false;
  byId("login-screen").classList.add("active");
  byId("app-wrapper").hidden = true;
  setAuthMode("login");
}



function initMap() {
  if (typeof THREE === "undefined") return;
  const container = byId("map");
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xdceee3);
  const camera = new THREE.PerspectiveCamera(
    42,
    container.clientWidth / container.clientHeight,
    0.1,
    1000,
  );
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
  const material = (color) =>
    new THREE.MeshStandardMaterial({ color, roughness: 0.85 });
  const ground = new THREE.Mesh(
    new THREE.BoxGeometry(24, 0.25, 18),
    material(0xb9dfc5),
  );
  ground.position.y = -0.25;
  campus.add(ground);
  const addBlock = (name, x, z, width, depth, height, color) => {
    const block = new THREE.Mesh(
      new THREE.BoxGeometry(width, height, depth),
      material(color),
    );
    block.position.set(x, height / 2, z);
    block.userData.name = name;
    campus.add(block);
  };
  const addGround = (x, z, width, depth, color) => {
    const field = new THREE.Mesh(
      new THREE.BoxGeometry(width, 0.06, depth),
      material(color),
    );
    field.position.set(x, 0.03, z);
    campus.add(field);
  };
  addBlock("Main Building", -4, 1, 5, 3, 2.2, 0xf4f0dc);
  addBlock("Workshops", -8, -3, 3, 4, 1.1, 0xe3c9a9);
  addBlock("Shri Krishna Academy", 5, -2, 4, 3, 1.6, 0xf0dcae);
  addBlock("Admin Block", -1, -3.6, 2.5, 1.4, 1.4, 0xd8e5df);
  addBlock("Gate House", 8, 6, 1.3, 1.2, 0.9, 0xc9d8d0);
  addGround(5, 4, 7, 5, 0x83bd91);
  addGround(-1, 6, 5, 2.5, 0xc9df9b);
  addGround(-3, -6, 5, 2.2, 0x9ed29f);
  addGround(3, -6, 5, 2.2, 0x9ed29f);
  const road = material(0xa8b9b0);
  const path = new THREE.Mesh(new THREE.BoxGeometry(1, 0.08, 16), road);
  path.position.set(1.5, 0.08, 0);
  campus.add(path);
  scene.add(campus);
  const markerGroup = new THREE.Group();
  scene.add(markerGroup);
  campusScene = { scene, camera, renderer, container, markerGroup, campus };
  const animate = () => {
    requestAnimationFrame(animate);
    campus.rotation.y += 0.0008;
    renderer.render(scene, camera);
  };
  animate();
  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });
}

function setLocation(latitude, longitude) {
  currentLocation = [latitude, longitude];
  byId("latitude").value = latitude.toFixed(6);
  byId("longitude").value = longitude.toFixed(6);
  byId("location-status").textContent =
    `GPS locked: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
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

function createMarker(color, size = 0.28) {
  return new THREE.Mesh(
    new THREE.SphereGeometry(size, 16, 16),
    new THREE.MeshStandardMaterial({
      color,
      emissive: color,
      emissiveIntensity: 0.25,
    }),
  );
}

function renderCampusLocation() {
  if (!campusScene || !currentLocation) return;
  if (campusScene.locationMarker)
    campusScene.markerGroup.remove(campusScene.locationMarker);
  const position = toCampusPosition(currentLocation[0], currentLocation[1]);
  const marker = createMarker(0x2478ff, 0.34);
  marker.position.set(position.x, 1.35, position.z);
  campusScene.markerGroup.add(marker);
  campusScene.locationMarker = marker;
}

function getLocation() {
  const locationStatus = byId("location-status");
  if (!navigator.geolocation) {
    locationStatus.textContent = "GPS is not supported by this browser";
    return;
  }
  locationStatus.textContent = "Requesting your location...";
  navigator.geolocation.getCurrentPosition(
    (position) =>
      setLocation(position.coords.latitude, position.coords.longitude),
    () => {
      locationStatus.textContent =
        "GPS unavailable. Trying network location...";
      getNetworkLocation();
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
  );
}

async function getNetworkLocation() {
  const locationStatus = byId("location-status");
  locationStatus.textContent = "Detecting approximate network location...";
  try {
    const response = await fetch(`${API_URL}/location/ip`);
    const result = await response.json();
    if (!response.ok)
      throw new Error(result.detail || "Network location unavailable");
    setLocation(Number(result.latitude), Number(result.longitude));
    locationStatus.textContent =
      `${result.city || "Approximate area"}, ${result.region || ""} (network)`.trim();
  } catch (error) {
    locationStatus.textContent = "Unable to detect network location.";
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
  return value.replaceAll("_", " ");
}

function renderAnalytics(data) {
  byId("total-reports").textContent = data.total_reports;
  byId("pending-reports").textContent = data.pending_reports;
  byId("collected-reports").textContent = data.collected_reports;
  const verified = data.status_counts.verified || 0;
  byId("verified-rate").textContent = data.total_reports
    ? `${Math.round((verified / data.total_reports) * 100)}%`
    : "0%";
}

function renderReports() {
  const search = byId("search").value.trim().toLowerCase();
  const status = byId("status-filter").value;
  const visible = reports.filter((report) => {
    const matchesSearch =
      !search ||
      report.report_id.toLowerCase().includes(search) ||
      (report.category || "").toLowerCase().includes(search);
    return matchesSearch && (!status || report.status === status);
  });
  byId("map-count").textContent = `${visible.length} visible`;
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
  const body = byId("reports-body");
  if (!visible.length) {
    body.innerHTML =
      '<tr><td colspan="6" class="empty">No reports match these filters.</td></tr>';
    return;
  }
  body.innerHTML = visible
    .map(
      (report) => `<tr>
    <td><div class="report-id">${report.report_id}</div><div class="muted">${report.description || "No description"}</div></td>
    <td>${report.category || "Unclassified"}</td>
    <td>${Number(report.latitude).toFixed(4)}, ${Number(report.longitude).toFixed(4)}</td>
    <td>${new Date(report.timestamp).toLocaleDateString()}</td>
    <td><span class="status ${report.status}">${formatStatus(report.status)}</span></td>
    <td>${actionMarkup(report)}</td>
  </tr>`,
    )
    .join("");
  body
    .querySelectorAll("[data-action]")
    .forEach((button) =>
      button.addEventListener("click", () =>
        handleAction(button.dataset.action, button.dataset.id),
      ),
    );
}

function actionMarkup(report) {
  if (!currentUser) return '<span class="muted">Sign in</span>';
  if (currentUser.role === "administrator") {
    if (
      !report.collector_id &&
      !["verified", "rejected"].includes(report.status)
    )
      return `<button class="table-action" data-action="assign" data-id="${report.report_id}">Assign</button>`;
    if (report.evidence_reference)
      return `<button class="table-action" data-action="verify" data-id="${report.report_id}">Verify</button>`;
    return '<span class="muted">Watching</span>';
  }
  if (
    currentUser.role === "collector" &&
    report.collector_id === currentUser.user_id
  ) {
    if (report.status === "assigned")
      return `<button class="table-action" data-action="progress" data-id="${report.report_id}">Start</button>`;
    if (report.status === "in_progress")
      return `<button class="table-action" data-action="collect" data-id="${report.report_id}">Collected</button>`;
    if (report.status === "collected" && !report.evidence_reference)
      return `<button class="table-action" data-action="evidence" data-id="${report.report_id}">Evidence</button>`;
  }
  return '<span class="muted">-</span>';
}

async function handleAction(action, reportId) {
  let endpoint;
  let options = {
    headers: { ...authHeaders(), "Content-Type": "application/json" },
  };
  if (action === "assign") {
    options.method = "POST";
    options.body = JSON.stringify({ collector_id: "collector-demo" });
    endpoint = `/reports/${reportId}/assignment`;
  } else if (action === "progress" || action === "collect") {
    options.method = "PATCH";
    options.body = JSON.stringify({
      status: action === "progress" ? "in_progress" : "collected",
    });
    endpoint = `/reports/${reportId}/status`;
  } else if (action === "evidence") {
    const evidence = prompt("Evidence image reference or filename:");
    if (!evidence) return;
    options.method = "POST";
    options.body = JSON.stringify({ evidence_reference: evidence });
    endpoint = `/reports/${reportId}/evidence`;
  } else if (action === "verify") {
    const approved = confirm("Approve this completion evidence?");
    options.method = "POST";
    endpoint = `/reports/${reportId}/verify?approved=${approved}`;
  }
  const response = await fetch(`${API_URL}${endpoint}`, options);
  if (!response.ok) {
    const error = await response.json();
    alert(error.detail || "Action failed");
    return;
  }
  await loadDashboard();
}

async function loadDashboard() {
  if (isGuest()) {
    reports = [];
    renderAnalytics({
      total_reports: 0,
      pending_reports: 0,
      collected_reports: 0,
      status_counts: {},
    });
    renderReports();
    byId("form-message").textContent =
      "You are browsing as a guest. Sign in to submit or track reports.";
    return;
  }
  try {
    const [reportsResponse, analyticsResponse] = await Promise.all([
      fetch(`${API_URL}/reports`, { headers: authHeaders() }),
      fetch(`${API_URL}/analytics`, { headers: authHeaders() }),
    ]);
    if (!reportsResponse.ok || !analyticsResponse.ok)
      throw new Error("API unavailable");
    reports = await reportsResponse.json();
    renderAnalytics(await analyticsResponse.json());
    renderReports();
    byId("form-message").textContent = "";
  } catch (error) {
    byId("reports-body").innerHTML =
      '<tr><td colspan="6" class="empty">Start the API with uvicorn to load live reports.</td></tr>';
    byId("form-message").textContent = accessToken
      ? "API connection unavailable."
      : "Sign in to load live reports.";
  }
}

async function restoreSession() {
  if (!accessToken) {
    enterGuestMode();
    return;
  }
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: authHeaders(),
  });
  if (!response.ok) {
    accessToken = null;
    localStorage.removeItem("ecotrack_token");
    enterGuestMode();
    return;
  }
  currentUser = await response.json();
  updateSidebarProfile(currentUser.name);
  byId("session-label").textContent =
    `${currentUser.name} · ${currentUser.role}`;
  byId("login").hidden = true;
  byId("logout").hidden = false;
  byId("login-screen").hidden = true;
  
  if (currentUser.role === "administrator") {
    window.location.href = "admin/index.html";
    return;
  }

  if (currentUser.role === "collector") {
    byId("app-wrapper").hidden = true;
    const colDash = document.getElementById("collector-dashboard-wrapper");
    if (colDash) colDash.hidden = false;
    document.body.classList.add("collector-mode");
    
    // Update user info in collector dashboard
    const nameEl = document.getElementById("col-user-name");
    const emailEl = document.getElementById("col-user-email");
    if (nameEl) nameEl.textContent = currentUser.name;
    if (emailEl) emailEl.textContent = currentUser.email || `${currentUser.name.toLowerCase().replace(" ", "")}@ecotrack.local`;
  } else {
    byId("app-wrapper").hidden = false;
    const colDash = document.getElementById("collector-dashboard-wrapper");
    if (colDash) colDash.hidden = true;
    document.body.classList.remove("collector-mode");
  }

  if (currentUser.role === "citizen") {
    if (byId("reports-panel")) byId("reports-panel").hidden = true;
  } else {
    byId("reports-panel").hidden = false;
  }
}

let isOtpStep = false;
function setAuthMode(mode) {
  byId("auth-mode").value = mode;
  const registering = mode === "register";
  const forgot = mode === "forgot";
  const loginOtp = mode === "login_otp";

  const btnTextNode = byId("auth-btn-text");

  if (byId("group-name")) byId("group-name").style.display = registering ? "flex" : "none";
  if (document.querySelector(".form-actions-row")) document.querySelector(".form-actions-row").style.display = (!registering && !forgot) ? "flex" : "none";

  if (forgot || loginOtp) {
    if (byId("group-password")) byId("group-password").hidden = true;
    if (byId("auth-password")) {
      byId("auth-password").required = false;
      if (forgot) byId("auth-password").placeholder = "New Password (5+ characters)";
    }
    if (btnTextNode)
      btnTextNode.textContent = loginOtp ? "Login" : "Send Code";
    if (byId("auth-title")) byId("auth-title").textContent = loginOtp ? "Login with OTP" : "Forgot Password?";
    if (byId("auth-subtitle"))
      byId("auth-subtitle").textContent = loginOtp ? "Please enter your email and OTP to login." : "Enter your email and we'll send a 5-digit verification code instantly.";
  } else {
    if (byId("group-password")) byId("group-password").hidden = false;
    if (byId("auth-password")) {
      byId("auth-password").required = true;
      byId("auth-password").placeholder = "@Sn123hsn#";
    }
    if (btnTextNode)
      btnTextNode.textContent = registering ? "Register" : "Sign in";
    if (byId("auth-title"))
      byId("auth-title").textContent = registering
        ? "Create Your Account?"
        : "Welcome Back!";
    if (byId("auth-subtitle"))
      byId("auth-subtitle").textContent = registering
        ? "Create your account to explore exciting travel destinations and adventures."
        : "Sign in to access smart, personalized travel plans made for you.";

    if (byId("bottom-text")) {
      byId("bottom-text").innerHTML = registering
        ? 'Already have an account? <a href="#" id="link-login">Sign In</a>'
        : 'Don\'t have an account? <a href="#" id="link-register">Sign up</a>';
      
      // Re-attach event listeners to dynamic links
      if (byId("link-login")) byId("link-login").addEventListener("click", (e) => { e.preventDefault(); setAuthMode("login"); });
      if (byId("link-register")) byId("link-register").addEventListener("click", (e) => { e.preventDefault(); setAuthMode("register"); });
    }
  }

  if (byId("auth-password"))
    byId("auth-password").autocomplete = registering
      ? "new-password"
      : "current-password";

  if (byId("link-login")) byId("link-login").hidden = !registering;
  if (byId("link-register")) byId("link-register").hidden = registering;
  if (byId("password-rules")) byId("password-rules").hidden = !registering;

  if (byId("link-login-otp")) byId("link-login-otp").hidden = (mode !== "login" && mode !== "register");
  if (byId("link-login-password")) byId("link-login-password").hidden = !loginOtp;

  // Reset OTP step
  if (loginOtp) {
    isOtpStep = true;
    if (byId("group-otp")) byId("group-otp").hidden = false;
    if (byId("auth-otp")) byId("auth-otp").required = true;
  } else {
    isOtpStep = false;
    if (byId("group-otp")) byId("group-otp").hidden = true;
    if (byId("auth-otp")) byId("auth-otp").required = false;
  }

  if (byId("auth-message")) byId("auth-message").textContent = "";
}

if (byId("link-login"))
  byId("link-login").addEventListener("click", (e) => {
    e.preventDefault();
    setAuthMode("login");
  });
if (byId("link-register"))
  byId("link-register").addEventListener("click", (e) => {
    e.preventDefault();
    setAuthMode("register");
  });
if (byId("link-forgot"))
  byId("link-forgot").addEventListener("click", (e) => {
    e.preventDefault();
    setAuthMode("forgot");
  });
if (byId("link-login-otp"))
  byId("link-login-otp").addEventListener("click", (e) => {
    e.preventDefault();
    setAuthMode("login_otp");
  });
if (byId("link-login-password"))
  byId("link-login-password").addEventListener("click", (e) => {
    e.preventDefault();
    setAuthMode("login");
  });

byId("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();

  if (isOtpStep) {
    const mode = byId("auth-mode").value;
    const isForgot = mode === "forgot";

    byId("auth-message").textContent = "Verifying OTP...";
    try {
      const payload = {
        email: byId("auth-email").value,
        otp: byId("auth-otp").value,
      };
      if (isForgot) payload.new_password = byId("auth-password").value;

      const endpoint = isForgot ? "/auth/reset-password" : "/auth/verify-otp";
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      
      let result;
      const textResponse = await response.text();
      try {
        result = JSON.parse(textResponse);
      } catch (e) {
        throw new Error(`Server error: ${response.status} - ${textResponse.slice(0, 30)}...`);
      }
      
      if (!response.ok)
        throw new Error(result.detail || "OTP verification failed");

      accessToken = result.access_token;
      localStorage.setItem("ecotrack_token", accessToken);
      await restoreSession();
      byId("auth-message").textContent = "";
      await loadDashboard();

      // Reset for next time
      setAuthMode("register");
      byId("auth-form").reset();
    } catch (error) {
      byId("auth-message").textContent = error.message;
    }
    return;
  }

  const mode = byId("auth-mode").value;
  const registering = mode === "register";
  const forgot = mode === "forgot";
  const loginOtp = mode === "login_otp";

  const payload = {
    email: byId("auth-email").value,

  };
  
  if (!payload.email.toLowerCase().endsWith("@gmail.com")) {
    byId("auth-message").textContent = "Only @gmail.com addresses are allowed.";
    return;
  }
  
  if (!forgot && !loginOtp) payload.password = byId("auth-password").value;


  let endpoint = "/auth/login";
  if (registering) endpoint = "/auth/register";
  if (forgot) endpoint = "/auth/forgot-password";

  byId("auth-message").textContent = "Connecting...";
  try {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    
    let result;
    const textResponse = await response.text();
    try {
      result = JSON.parse(textResponse);
    } catch (e) {
      throw new Error(`Server error: ${response.status} - ${textResponse.slice(0, 30)}...`);
    }
    
    if (!response.ok) {
      let errorMessage = "Authentication failed";
      if (result.detail) {
        if (Array.isArray(result.detail)) {
          errorMessage = result.detail.map((err) => err.msg || JSON.stringify(err)).join(", ");
        } else {
          errorMessage = result.detail;
        }
      }
      throw new Error(errorMessage);
    }

    if (result.status === "otp_sent") {
      isOtpStep = true;
      byId("auth-message").textContent =
        "OTP sent to your email. Please verify.";

      if (forgot) {
        byId("group-password").hidden = false;
        byId("auth-password").required = true;
        if (byId("password-rules")) byId("password-rules").hidden = false;
      } else {
        byId("group-password").hidden = true;
        byId("auth-password").required = false;
        if (byId("password-rules")) byId("password-rules").hidden = true;
      }

      byId("group-otp").hidden = false;
      byId("auth-otp").required = true;

      let btnText = "Verify OTP";
      if (forgot) btnText = "Reset Password";
      else if (loginOtp) btnText = "Login";
      byId("auth-submit-btn").textContent = btnText;
      return;
    }

    accessToken = result.access_token;
    localStorage.setItem("ecotrack_token", accessToken);
    await restoreSession();
    byId("auth-message").textContent = "";
    await loadDashboard();
  } catch (error) {
    byId("auth-message").textContent = error.message;

  }
});

byId("logout").addEventListener("click", () => {
  localStorage.removeItem("ecotrack_token");
  enterGuestMode();
  loadDashboard();
});

byId("login").addEventListener("click", openSignIn);

const colLogout = document.getElementById("col-logout");
if (colLogout) {
  colLogout.addEventListener("click", () => {
    localStorage.removeItem("ecotrack_token");
    const colDash = document.getElementById("collector-dashboard-wrapper");
    if (colDash) colDash.hidden = true;
    enterGuestMode();
    loadDashboard();
  });
}

byId("report-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const message = byId("form-message");
  if (!currentUser || isGuest()) {
    message.textContent = "Sign in to submit a report.";
    openSignIn();
    return;
  }
  const data = new FormData(form);
  data.append("user_id", currentUser.user_id);
  message.textContent = "Submitting report...";
  try {
    const response = await fetch(`${API_URL}/reports`, {
      method: "POST",
      headers: authHeaders(),
      body: data,
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(result.detail || "Unable to submit report");
    form.reset();
    byId("file-label").textContent = "Choose a photo";
    message.textContent = `Reference No: ${result.report_id} - Record successful and confirmation letter will be sent soon`;
    await loadDashboard();
  } catch (error) {
    message.textContent = error.message;
  }
});

byId("image-compare-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const first = byId("compare-photo-1").files[0];
  const second = byId("compare-photo-2").files[0];
  const message = byId("image-compare-message");
  const resultBox = byId("image-compare-result");
  if (!first || !second) return;
  if (isGuest()) {
    message.textContent = "Sign in to analyze images.";
    openSignIn();
    return;
  }
  message.textContent = "Analyzing image details...";
  resultBox.hidden = true;
  try {
    const data = new FormData();
    data.append("photo1", first);
    data.append("photo2", second);
    const response = await fetch(`${API_URL}/image-compare`, {
      method: "POST",
      headers: authHeaders(),
      body: data,
    });
    const result = await response.json();
    if (!response.ok)
      throw new Error(result.detail || "Image comparison failed");
    resultBox.className = `compare-result${result.match ? "" : " no-match"}`;
    resultBox.textContent = `${result.match ? "TRUE" : "FALSE"} · ${result.similarity}% match (threshold: ${result.threshold}%). Visual appearance: ${result.comparison.visual_appearance}%, colour distribution: ${result.comparison.colour_distribution}%.`;
    resultBox.hidden = false;
    message.textContent = "";
  } catch (error) {
    message.textContent = error.message;
  }
});

byId("image").addEventListener("change", (event) => {
  byId("file-label").textContent =
    event.target.files[0]?.name || "Choose a photo";
});
byId("search").addEventListener("input", renderReports);
byId("status-filter").addEventListener("change", renderReports);
byId("refresh").addEventListener("click", () => {
  if (campusScene) {
    campusScene.camera.position.set(13, 16, 18);
    campusScene.camera.lookAt(0, 0, 0);
  }
  loadDashboard();
});
byId("locate").addEventListener("click", getLocation);
byId("network-locate").addEventListener("click", getNetworkLocation);
byId("focus-report").addEventListener("click", () =>
  byId("report-panel").scrollIntoView({ behavior: "smooth" }),
);

initMap();
getLocation();
setAuthMode("login");

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
  const intro = document.getElementById("intro");
  if (intro) intro.style.display = "none";
}, 6200);

// Password Visibility Toggle Logic
const togglePassword = document.getElementById('toggle-password');
const passwordInput = document.getElementById('auth-password');

if (togglePassword && passwordInput) {
  togglePassword.addEventListener('click', function () {
    const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
    passwordInput.setAttribute('type', type);
    this.classList.toggle('fa-eye');
    this.classList.toggle('fa-eye-slash');
  });
}

// Send OTP Button Logic
if (byId("btn-send-otp")) {
  byId("btn-send-otp").addEventListener("click", async () => {
    const email = byId("auth-email").value;
    if (!email || !email.toLowerCase().endsWith("@gmail.com")) {
      byId("auth-message").textContent = "Please enter a valid @gmail.com address first.";
      return;
    }
    
    byId("auth-message").textContent = "Sending OTP...";
    byId("btn-send-otp").disabled = true;
    try {
      const response = await fetch(`${API_URL}/auth/request-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      
      let result;
      const textResponse = await response.text();
      try {
        result = JSON.parse(textResponse);
      } catch (e) {
        throw new Error(`Server error: ${response.status} - ${textResponse.slice(0, 30)}...`);
      }
      
      if (!response.ok) throw new Error(result.detail || "Failed to send OTP");
      
      byId("auth-message").textContent = "OTP sent to your email. Please verify.";
      
      // Cooldown timer
      let countdown = 60;
      const interval = setInterval(() => {
        countdown--;
        byId("btn-send-otp").textContent = `Resend (${countdown}s)`;
        if (countdown <= 0) {
          clearInterval(interval);
          byId("btn-send-otp").textContent = "Send OTP";
          byId("btn-send-otp").disabled = false;
        }
      }, 1000);
      
    } catch (error) {
      byId("auth-message").textContent = error.message;
      byId("btn-send-otp").disabled = false;
      byId("btn-send-otp").textContent = "Send OTP";
    }
  });
}
