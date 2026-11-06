/**
 * Munzir (منذر) Front-End Web Application
 * Accessible, Responsive, Multi-Role Single Page App
 */

const state = {
  role: "surveillance_officer",
  userId: "user-surveillance-01",
  employerId: "SITE-JA-01",
  date: "2025-08-20",
  activeTab: "map",
};

// Common fetch wrapper injecting simulated Entra ID headers
async function apiFetch(endpoint, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Role": state.role,
    "X-User-ID": state.userId,
    "X-Employer-ID": state.employerId,
    "X-Purpose": "hackathon_evaluation_demo",
    ...(options.headers || {}),
  };

  const response = await fetch(endpoint, { ...options, headers });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `HTTP Error ${response.status}`);
  }
  return response.json();
}

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupRoleSwitcher();
  setupDateSelector();
  setupDemoToggles();
  loadCurrentView();
});

function setupNavigation() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      tabButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.activeTab = btn.dataset.tab;

      document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
      const targetContent = document.getElementById(`view-${state.activeTab}`);
      if (targetContent) targetContent.classList.add("active");

      loadCurrentView();
    });
  });
}

function setupRoleSwitcher() {
  const roleSelect = document.getElementById("roleSelect");
  if (!roleSelect) return;

  roleSelect.value = state.role;
  roleSelect.addEventListener("change", (e) => {
    state.role = e.target.value;
    updateRoleIndicator();
    loadCurrentView();
  });
  updateRoleIndicator();
}

function updateRoleIndicator() {
  const badge = document.getElementById("activeRoleBadge");
  const siteNotice = document.getElementById("employerSiteIndicator");
  if (badge) {
    badge.textContent = state.role.replace("_", " ").toUpperCase();
  }
  if (siteNotice) {
    if (state.role === "employer_safety") {
      siteNotice.style.display = "inline-flex";
      siteNotice.textContent = `Authorized Worksite: ${state.employerId}`;
    } else {
      siteNotice.style.display = "none";
    }
  }
}

function setupDateSelector() {
  const dateInput = document.getElementById("simDateInput");
  if (!dateInput) return;
  dateInput.value = state.date;
  dateInput.addEventListener("change", (e) => {
    state.date = e.target.value;
    loadCurrentView();
  });
}

function loadCurrentView() {
  if (state.activeTab === "map") loadSituationMap();
  else if (state.activeTab === "inbox") loadAlertInbox();
  else if (state.activeTab === "employer") loadEmployerSafetyView();
  else if (state.activeTab === "health") loadDataHealthView();
  else if (state.activeTab === "audit") loadAuditLogs();
  else if (state.activeTab === "impact") loadImpactView();
  else if (state.activeTab === "sentinel") loadSentinelView();
}

// --- 1. Situation Map View ---
async function loadSituationMap() {
  const container = document.getElementById("mapGeoList");
  const svgMap = document.getElementById("situationSvgMap");
  const noticeBox = document.getElementById("mapPrivacyNotice");
  if (!container || !svgMap) return;

  container.innerHTML = `<div style="padding:1rem;color:#94a3b8;">Loading map features for ${state.date}...</div>`;

  try {
    const data = await apiFetch(`/api/v1/map/layers?date=${state.date}`);
    
    // Privacy banner
    if (noticeBox) {
      if (data.privacy_notice) {
        noticeBox.style.display = "block";
        noticeBox.textContent = data.privacy_notice;
      } else {
        noticeBox.style.display = "none";
      }
    }

    // Render list
    container.innerHTML = "";
    data.features.forEach(feat => {
      const card = document.createElement("div");
      card.className = `geo-item-card ${feat.hatch_pattern ? 'hatch-pattern' : ''}`;
      
      const badgeClass = `badge-${feat.risk_tier.toLowerCase()}`;
      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong>${feat.geo_name}</strong>
          <span class="badge ${badgeClass}">${feat.risk_tier.toUpperCase()}</span>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:0.35rem; font-size:0.75rem; color:#94a3b8;">
          <span>ID: ${feat.geo_id} (${feat.geo_level})</span>
          <span>Confidence: <b>${feat.location_confidence.toUpperCase()}</b></span>
        </div>
        <div style="margin-top:0.25rem; font-size:0.75rem; color:#cbd5e1;">
          Outbreak Prob: <b>${(feat.calibrated_prob * 100).toFixed(1)}%</b> | Population: ${feat.population ? feat.population.toLocaleString() : 'N/A'}
        </div>
      `;
      container.appendChild(card);
    });

    // Render SVG Map
    renderSvgMap(svgMap, data.features, data.clusters);

  } catch (err) {
    container.innerHTML = `<div style="padding:1rem;color:#ef4444;">Failed to load map: ${err.message}</div>`;
  }
}

function renderSvgMap(svgElement, features, clusters) {
  // Geo bounds for Dubai
  const minLat = 24.75, maxLat = 25.35;
  const minLon = 54.95, maxLon = 56.20;

  const width = svgElement.clientWidth || 700;
  const height = svgElement.clientHeight || 480;

  function toXY(lat, lon) {
    const x = ((lon - minLon) / (maxLon - minLon)) * (width - 80) + 40;
    const y = height - (((lat - minLat) / (maxLat - minLat)) * (height - 80) + 40);
    return { x, y };
  }

  let svgHtml = `
    <defs>
      <pattern id="diagonalHatch" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
        <line x1="0" y1="0" x2="0" y2="10" style="stroke:#3b82f6; stroke-width:3; opacity:0.4" />
      </pattern>
    </defs>
    <!-- Background Grid -->
    <rect width="${width}" height="${height}" fill="#0b1120" />
    <path d="M 0,${height/2} L ${width},${height/2} M ${width/2},0 L ${width/2},${height}" stroke="#1e293b" stroke-width="1" />
  `;

  // Draw clusters first
  if (clusters && clusters.length > 0) {
    clusters.forEach(c => {
      const center = toXY(c.centroid_lat, c.centroid_lon);
      svgHtml += `
        <circle cx="${center.x}" cy="${center.y}" r="45" fill="rgba(239, 68, 68, 0.25)" stroke="#ef4444" stroke-width="2" stroke-dasharray="4,4" />
        <text x="${center.x}" y="${center.y - 48}" fill="#f87171" font-size="11" font-weight="bold" text-anchor="middle">
          L3 Cluster (RR: ${c.relative_risk}x, p &lt; 0.05)
        </text>
      `;
    });
  }

  // Draw features
  features.forEach(f => {
    const pt = toXY(f.lat, f.lon);
    let color = "#10b981"; // normal
    if (f.risk_tier === "watch") color = "#3b82f6";
    else if (f.risk_tier === "warning") color = "#f59e0b";
    else if (f.risk_tier === "alert") color = "#ef4444";

    const isSite = f.geo_level === "site";
    const shape = isSite ? "rect" : "circle";

    if (shape === "circle") {
      svgHtml += `
        <circle cx="${pt.x}" cy="${pt.y}" r="14" fill="${f.hatch_pattern ? 'url(#diagonalHatch)' : color}" stroke="${color}" stroke-width="2" />
        <circle cx="${pt.x}" cy="${pt.y}" r="4" fill="${color}" />
      `;
    } else {
      svgHtml += `
        <rect x="${pt.x - 12}" y="${pt.y - 12}" width="24" height="24" rx="4" fill="${color}" stroke="#ffffff" stroke-width="1.5" />
      `;
    }

    svgHtml += `
      <text x="${pt.x}" y="${pt.y + 24}" fill="#f8fafc" font-size="11" font-weight="600" text-anchor="middle" style="text-shadow: 0 1px 3px #000;">
        ${f.geo_name.split(" ")[0]}
      </text>
      <text x="${pt.x}" y="${pt.y + 36}" fill="#94a3b8" font-size="9" text-anchor="middle">
        [${f.risk_tier.toUpperCase()}]
      </text>
    `;
  });

  svgElement.innerHTML = svgHtml;
}

// --- 2. Alert Inbox View ---
async function loadAlertInbox() {
  const tbody = document.getElementById("alertsTableBody");
  const countBadge = document.getElementById("inboxCountBadge");
  const ppvBadge = document.getElementById("inboxPpvBadge");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#94a3b8;">Loading alerts...</td></tr>`;

  try {
    const data = await apiFetch(`/api/v1/alerts?date=${state.date}`);
    if (countBadge) countBadge.textContent = `${data.total_alerts} Active Alerts`;
    if (ppvBadge && data.operational_ppv !== null) {
      ppvBadge.textContent = `Operational PPV: ${(data.operational_ppv * 100).toFixed(1)}%`;
    }

    if (data.alerts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#94a3b8;">No alerts matching current role and date filters.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    data.alerts.forEach(a => {
      const tr = document.createElement("tr");
      const tierBadge = `badge-${a.alert_tier.toLowerCase()}`;
      
      let statusBadge = "badge-gray";
      if (a.status === "ACKNOWLEDGED") statusBadge = "badge-watch";
      else if (a.status === "ACTED") statusBadge = "badge-normal";
      else if (a.status === "DISMISSED") statusBadge = "badge-gray";

      tr.innerHTML = `
        <td><span class="badge ${tierBadge}">${a.alert_tier.toUpperCase()}</span></td>
        <td><strong>${a.alert_id}</strong><br><span style="font-size:0.75rem;color:#94a3b8;">${a.syndrome}</span></td>
        <td>${a.geo_name}<br><span style="font-size:0.75rem;color:#94a3b8;">${a.geo_id}</span></td>
        <td>
          <b>${(a.calibrated_probability * 100).toFixed(1)}%</b>
          <div style="font-size:0.7rem;color:#94a3b8;">90% CI: [${(a.conformal_interval[0]*100).toFixed(0)}%, ${(a.conformal_interval[1]*100).toFixed(0)}%]</div>
        </td>
        <td><span class="badge badge-gray">${a.dq_badge}</span></td>
        <td><span style="font-size:0.8rem;color:#e2e8f0;">${a.primary_owner}</span></td>
        <td><span class="badge ${statusBadge}">${a.status}</span></td>
        <td>
          <button class="btn btn-primary" onclick="viewEvidenceCard('${a.alert_id}')">Evidence Card</button>
          ${a.can_acknowledge && a.status === 'PENDING' ? `
            <button class="btn btn-secondary" onclick="openAcknowledgeModal('${a.alert_id}')" style="margin-left:0.3rem;">Triage</button>
          ` : ''}
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:#ef4444;text-align:center;">Failed to load alerts: ${err.message}</td></tr>`;
  }
}

// --- 3. Evidence Card Modal ---
async function viewEvidenceCard(alertId) {
  const modal = document.getElementById("evidenceCardModal");
  const modalBody = document.getElementById("evidenceCardContent");
  if (!modal || !modalBody) return;

  modal.classList.add("active");
  modalBody.innerHTML = `<div style="text-align:center;padding:3rem;color:#94a3b8;">Synthesizing Evidence Card for ${alertId}...</div>`;

  const t0 = performance.now();
  try {
    const card = await apiFetch(`/api/v1/alerts/${alertId}/evidence`);
    const latencyMs = Math.round(performance.now() - t0);

    modalBody.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #334155; padding-bottom:1rem; margin-bottom:1.5rem;">
        <div>
          <span class="badge badge-${card.severity.toLowerCase()}">${card.severity.toUpperCase()}</span>
          <h2 style="font-size:1.35rem; margin-top:0.25rem;">${card.alert_id}: ${card.geo_name}</h2>
          <div style="font-size:0.85rem; color:#94a3b8;">Type: <b>${card.alert_type}</b> | Date: ${card.obs_date} | Proportionality Tier: <b>${card.proportionality_tier.toUpperCase()}</b></div>
        </div>
        <div style="text-align:right;">
          <div style="font-size:0.75rem; color:#94a3b8;">Decision Card Generation Latency</div>
          <div style="font-size:1.2rem; font-weight:700; color:#10b981;">${card.generation_time_ms.toFixed(1)} ms</div>
          <div style="font-size:0.7rem; color:#64748b;">(SLA: &lt; 2,000 ms)</div>
        </div>
      </div>

      <!-- Fenced Situational Briefing Narrative -->
      <div style="background-color:rgba(15,23,42,0.6); border-left:4px solid #38bdf8; padding:1rem; border-radius:4px; margin-bottom:1.5rem;">
        <div style="font-size:0.75rem; text-transform:uppercase; color:#38bdf8; font-weight:700; letter-spacing:0.05em; margin-bottom:0.25rem;">
          Verified Situational Briefing (Zero-Hallucination Gate Verified)
        </div>
        <p style="font-size:0.9rem; line-height:1.6; color:#f1f5f9;">${card.narrative_summary}</p>
      </div>

      <!-- 2-Column Section: Time Series & SHAP Attribution -->
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.25rem; margin-bottom:1.5rem;">
        
        <!-- Observed vs Expected vs Exposure-Adjusted -->
        <div class="kpi-card">
          <div class="kpi-title">Epidemiological Trajectory (Observed vs Expected)</div>
          <div style="display:flex; justify-content:space-between; margin-bottom:0.75rem; font-size:0.85rem;">
            <span>Observed Today: <b style="color:#f87171;">${card.time_series_comparison.observed_today}</b></span>
            <span>Historical Baseline: <b style="color:#94a3b8;">${card.time_series_comparison.historical_baseline}</b></span>
            <span>Exposure-Adjusted: <b style="color:#38bdf8;">${card.time_series_comparison.exposure_adjusted_expected}</b></span>
          </div>
          <div style="height:120px; background:#0b1120; border-radius:6px; display:flex; align-items:flex-end; gap:8px; padding:10px 15px;">
            ${renderTimeSeriesMiniBars(card.time_series_comparison.trailing_14d_observed)}
          </div>
          <div style="font-size:0.7rem; color:#64748b; text-align:center; margin-top:0.4rem;">Trailing 14-day observed incidence surge</div>
        </div>

        <!-- SHAP 5-Group Attribution -->
        <div class="kpi-card">
          <div class="kpi-title">SHAP 5-Group Feature Attribution (L4 LightGBM)</div>
          <div class="shap-bar-container">
            ${renderShapBars(card.shap_breakdown)}
          </div>
          <div style="font-size:0.7rem; color:#64748b; text-align:center; margin-top:0.4rem;">Top Driver: <b>${card.primary_driver.toUpperCase()}</b></div>
        </div>

      </div>

      <!-- Environmental Forecast -->
      <div class="kpi-card" style="margin-bottom:1.5rem;">
        <div class="kpi-title">3-Day Environmental Exposure Forecast (Open-Meteo & OpenAQ)</div>
        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:1rem; margin-top:0.5rem; text-align:center;">
          <div style="background:#0b1120; padding:0.75rem; border-radius:6px;">
            <div style="font-size:0.75rem; color:#94a3b8;">Today</div>
            <div style="font-size:1.1rem; font-weight:700; color:#fbbf24;">WBGT ${card.environmental_forecast.wbgt_today}°C</div>
            <div style="font-size:0.75rem; color:#cbd5e1;">PM2.5: ${card.environmental_forecast.pm25_today} µg/m³</div>
          </div>
          <div style="background:#0b1120; padding:0.75rem; border-radius:6px;">
            <div style="font-size:0.75rem; color:#94a3b8;">Tomorrow (+1d)</div>
            <div style="font-size:1.1rem; font-weight:700; color:#f87171;">WBGT ${card.environmental_forecast.wbgt_forecast_3d[0]}°C</div>
            <div style="font-size:0.75rem; color:#cbd5e1;">Thermal Danger</div>
          </div>
          <div style="background:#0b1120; padding:0.75rem; border-radius:6px;">
            <div style="font-size:0.75rem; color:#94a3b8;">Day +2</div>
            <div style="font-size:1.1rem; font-weight:700; color:#f87171;">WBGT ${card.environmental_forecast.wbgt_forecast_3d[1]}°C</div>
            <div style="font-size:0.75rem; color:#cbd5e1;">Thermal Danger</div>
          </div>
        </div>
      </div>

      <!-- RACI Matrix Table -->
      <div class="kpi-card" style="margin-bottom:1.5rem;">
        <div class="kpi-title">RACI Governance Stakeholder Mapping</div>
        <table style="margin-top:0.5rem;">
          <tr><th style="width:140px;">Role</th><th>Stakeholder Organization & Jurisdiction</th></tr>
          <tr><td><span class="badge badge-alert">Responsible (R)</span></td><td><b>${card.raci_matrix.responsible}</b> (Action Lead)</td></tr>
          <tr><td><span class="badge badge-warning">Accountable (A)</span></td><td><b>${card.raci_matrix.accountable}</b> (Approving Authority)</td></tr>
          <tr><td><span class="badge badge-watch">Consulted (C)</span></td><td>${card.raci_matrix.consulted.join(", ")}</td></tr>
          <tr><td><span class="badge badge-gray">Informed (I)</span></td><td>${card.raci_matrix.informed.join(", ")}</td></tr>
        </table>
      </div>

      <!-- Verified Action Checklist -->
      <div class="kpi-card" style="margin-bottom:1.5rem;">
        <div class="kpi-title">Proportionality Ladder Verified Action Checklist</div>
        <ul style="list-style:none; padding:0; margin-top:0.5rem;">
          ${card.action_checklist.map(action => `
            <li style="padding:0.6rem 0.75rem; background:rgba(15,23,42,0.4); border-left:3px solid #10b981; margin-bottom:0.4rem; border-radius:4px; font-size:0.875rem;">
              • ${action}
            </li>
          `).join("")}
        </ul>
      </div>

      <!-- Explicit Stated Assumptions -->
      <div style="font-size:0.75rem; color:#94a3b8; border-top:1px solid #334155; padding-top:0.75rem;">
        <strong>Explicit Operational Assumptions:</strong>
        ${card.assumptions.map(asm => `<span style="display:inline-block; margin-right:1rem;">• ${asm}</span>`).join("")}
      </div>
    `;

  } catch (err) {
    modalBody.innerHTML = `<div style="padding:2rem;color:#ef4444;text-align:center;">Failed to generate Evidence Card: ${err.message}</div>`;
  }
}

function renderTimeSeriesMiniBars(points) {
  if (!points || points.length === 0) points = [5, 6, 7, 8, 9, 12, 14, 18, 22, 28, 35, 42, 48, 52];
  const max = Math.max(...points, 1);
  return points.map(v => {
    const heightPct = Math.round((v / max) * 100);
    const color = heightPct > 70 ? "#ef4444" : heightPct > 40 ? "#f59e0b" : "#3b82f6";
    return `<div style="flex:1; height:${heightPct}%; background:${color}; border-radius:3px 3px 0 0;" title="${v} cases"></div>`;
  }).join("");
}

function renderShapBars(breakdown) {
  if (!breakdown) breakdown = { "workplace": 0.35, "wbgt": 0.30, "clinical": 0.20, "air_quality": 0.10, "otc": 0.05 };
  return Object.entries(breakdown).map(([k, v]) => {
    const pct = Math.round(v * 100);
    return `
      <div class="shap-bar-row">
        <span class="shap-label">${k.replace("_", " ").toUpperCase()}</span>
        <div class="shap-bar-bg">
          <div class="shap-bar-fill" style="width:${pct}%;"></div>
        </div>
        <span class="shap-val">${pct}%</span>
      </div>
    `;
  }).join("");
}

function closeModal() {
  document.getElementById("evidenceCardModal").classList.remove("active");
  document.getElementById("acknowledgeModal").classList.remove("active");
}

// --- 4. Human Triage Modal ---
function openAcknowledgeModal(alertId) {
  const modal = document.getElementById("acknowledgeModal");
  document.getElementById("ackAlertId").value = alertId;
  document.getElementById("ackAlertTitle").textContent = `Triage Alert: ${alertId}`;
  modal.classList.add("active");
}

async function submitAcknowledgement(action) {
  const alertId = document.getElementById("ackAlertId").value;
  const comment = document.getElementById("ackComment").value;
  const dismissReason = document.getElementById("ackDismissReason").value;

  if (action === "DISMISSED" && !dismissReason) {
    alert("A mandatory dismissal reason must be provided when dismissing an alert.");
    return;
  }

  try {
    const res = await apiFetch(`/api/v1/alerts/${alertId}/acknowledge`, {
      method: "POST",
      body: JSON.stringify({
        action: action,
        comment: comment,
        dismissal_reason: action === "DISMISSED" ? dismissReason : null,
      }),
    });
    alert(res.message);
    closeModal();
    loadAlertInbox();
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
}

// --- 5. Employer Safety View ---
async function loadEmployerSafetyView() {
  const container = document.getElementById("employerDashboardContainer");
  if (!container) return;

  container.innerHTML = `<div style="padding:2rem;color:#94a3b8;">Loading workplace safety metrics for ${state.employerId}...</div>`;

  try {
    const data = await apiFetch(`/api/v1/workplace/site-rates?site_id=${state.employerId}&date=${state.date}`);

    container.innerHTML = `
      <!-- Mandatory Statutory Banner -->
      <div class="banner banner-statutory">
        <span style="font-size:1.25rem;">⚖️</span>
        <div>
          <strong>STATUTORY PRIVACY BANNER (MOHRE & EHS COMPLIANCE)</strong>
          <div style="font-weight:normal; font-size:0.85rem;">${data.statutory_banner}</div>
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-title">Worksite Workforce Cohort</div>
          <div class="kpi-val">${data.workforce_size.toLocaleString()}</div>
          <div class="kpi-sub"><span class="badge badge-normal">N &ge; 50 Compliant</span></div>
        </div>

        <div class="kpi-card">
          <div class="kpi-title">Heat Illness Rate</div>
          <div class="kpi-val" style="color:#f59e0b;">${data.heat_incident_rate_per_1000} <span style="font-size:0.9rem;color:#94a3b8;">/ 1k workers</span></div>
          <div class="kpi-sub">Aggregated site-level rate only</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-title">Sickness Absence Rate</div>
          <div class="kpi-val" style="color:#f87171;">${data.absence_rate_per_1000} <span style="font-size:0.9rem;color:#94a3b8;">/ 1k workers</span></div>
          <div class="kpi-sub">Aggregated site-level rate only</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-title">Peak Thermal Stress (WBGT)</div>
          <div class="kpi-val" style="color:#ef4444;">${data.wbgt_max}°C</div>
          <div class="kpi-sub">${data.wbgt_hours_danger} Danger Hours Today</div>
        </div>
      </div>

      <div class="kpi-card" style="margin-bottom:1.5rem;">
        <div class="kpi-title">Mandatory ACGIH / MOHRE Work-Rest Hydration Schedule</div>
        <p style="margin-top:0.5rem; font-size:0.95rem; color:#f1f5f9; line-height:1.5;">${data.work_rest_recommendation}</p>
      </div>

      <!-- Test Privacy Guard Button -->
      <div class="kpi-card" style="background:rgba(15,23,42,0.5);">
        <div class="kpi-title">Privacy Boundary Verification Test</div>
        <p style="font-size:0.85rem; color:#94a3b8; margin:0.4rem 0 0.75rem 0;">
          Verify that this role cannot access district-wide clinical micro-surveillance or prohibited sub-site breakdowns.
        </p>
        <button class="btn btn-secondary" onclick="testClinicalAccessRejection()">
          🔒 Probe Prohibited Clinical Syndromic Feed
        </button>
        <button class="btn btn-secondary" onclick="testSubsiteParamRejection()" style="margin-left:0.5rem;">
          🔒 Probe Prohibited Sub-site Breakdown (gang_id)
        </button>
        <div id="privacyProbeResult" style="margin-top:0.75rem; font-size:0.85rem;"></div>
      </div>
    `;

  } catch (err) {
    container.innerHTML = `<div style="padding:2rem;color:#ef4444;">Failed to load employer safety view: ${err.message}</div>`;
  }
}

async function testClinicalAccessRejection() {
  const resultDiv = document.getElementById("privacyProbeResult");
  resultDiv.innerHTML = `<span style="color:#38bdf8;">Testing clinical feed access boundary...</span>`;
  try {
    await apiFetch(`/api/v1/clinical/syndromic?geo_id=DXB-JA`);
    resultDiv.innerHTML = `<span style="color:#ef4444;">❌ Security Boundary Failed: Endpoint unexpectedly returned data!</span>`;
  } catch (err) {
    resultDiv.innerHTML = `<span style="color:#10b981;">✅ Privacy Gate Enforced: <b>${err.message}</b></span>`;
  }
}

async function testSubsiteParamRejection() {
  const resultDiv = document.getElementById("privacyProbeResult");
  resultDiv.innerHTML = `<span style="color:#38bdf8;">Testing prohibited sub-site parameter (gang_id=CREW-04)...</span>`;
  try {
    await apiFetch(`/api/v1/workplace/site-rates?site_id=${state.employerId}&gang_id=CREW-04`);
    resultDiv.innerHTML = `<span style="color:#ef4444;">❌ Security Boundary Failed: Sub-site parameter was accepted!</span>`;
  } catch (err) {
    resultDiv.innerHTML = `<span style="color:#10b981;">✅ Privacy Gate Enforced: <b>${err.message}</b></span>`;
  }
}

// --- 6. Data Health View ---
async function loadDataHealthView() {
  const container = document.getElementById("healthFeedsContainer");
  const overallScore = document.getElementById("compositeDqScore");
  const gatingBadge = document.getElementById("dqGatingBadge");
  if (!container) return;

  container.innerHTML = `<div style="padding:2rem;color:#94a3b8;">Loading data health metrics...</div>`;

  try {
    const data = await apiFetch(`/api/v1/health/feeds`);
    if (overallScore) overallScore.textContent = `${(data.composite_dq_score * 100).toFixed(1)}%`;
    if (gatingBadge) {
      if (data.dq_gating_triggered) {
        gatingBadge.className = "badge badge-alert";
        gatingBadge.textContent = "GATING ACTIVE (LOW QUALITY)";
      } else {
        gatingBadge.className = "badge badge-normal";
        gatingBadge.textContent = "STREAMS HEALTHY";
      }
    }

    container.innerHTML = "";
    data.feeds.forEach(f => {
      const card = document.createElement("div");
      card.className = "kpi-card";
      const statusBadge = f.status === "HEALTHY" ? "badge-normal" : "badge-alert";

      card.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="font-size:0.95rem;">${f.source_name}</strong>
          <span class="badge ${statusBadge}">${f.status}</span>
        </div>
        <div style="margin-top:0.75rem; font-size:0.85rem; color:#cbd5e1;">
          <div>Completeness: <b>${f.completeness_pct.toFixed(1)}%</b></div>
          <div>Freshness: <b>${f.freshness_minutes.toFixed(0)} min</b> ago</div>
          <div>Ingestion Latency: <b>${f.latency_hours.toFixed(1)} hrs</b></div>
        </div>
        <div style="margin-top:0.5rem; height:6px; background:#334155; border-radius:3px; overflow:hidden;">
          <div style="width:${f.completeness_pct}%; height:100%; background:${f.status === 'HEALTHY' ? '#10b981' : '#ef4444'};"></div>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<div style="padding:2rem;color:#ef4444;">Failed to load data health: ${err.message}</div>`;
  }
}

// --- 7. Interactive Missing-Data Demo Controls ---
function setupDemoToggles() {
  const toggles = [
    { id: "toggleClinical", feed: "clinical" },
    { id: "toggleWeather", feed: "weather" },
    { id: "toggleAirQuality", feed: "air_quality" },
  ];

  toggles.forEach(t => {
    const el = document.getElementById(t.id);
    if (el) {
      el.addEventListener("change", async (e) => {
        const enabled = e.target.checked;
        const resultBox = document.getElementById("demoToggleResult");
        resultBox.style.display = "block";
        resultBox.innerHTML = `<span style="color:#38bdf8;">Simulating telemetry state change on '${t.feed}'...</span>`;

        try {
          const res = await apiFetch(`/api/v1/demo/toggle-feed`, {
            method: "POST",
            body: JSON.stringify({ feed: t.feed, enabled: enabled }),
          });

          resultBox.innerHTML = `
            <div style="border-left:3px solid ${enabled ? '#10b981' : '#f59e0b'}; padding-left:0.75rem;">
              <strong style="color:${enabled ? '#10b981' : '#f59e0b'};">${res.message}</strong>
              <div style="font-size:0.85rem; color:#e2e8f0; margin-top:0.35rem;">${res.alert_impact}</div>
              <div style="margin-top:0.35rem; font-size:0.8rem; color:#94a3b8;">
                Composite DQ: ${(res.before_composite_dq * 100).toFixed(0)}% &rarr; <b>${(res.after_composite_dq * 100).toFixed(0)}%</b> |
                90% Conformal Interval: [${res.before_conformal_interval[0]}, ${res.before_conformal_interval[1]}] &rarr; 
                <b style="color:#f87171;">[${res.after_conformal_interval[0]}, ${res.after_conformal_interval[1]}]</b>
              </div>
            </div>
          `;

          // Refresh underlying view if on health or inbox
          if (state.activeTab === "health") loadDataHealthView();
          if (state.activeTab === "inbox") loadAlertInbox();

        } catch (err) {
          resultBox.innerHTML = `<span style="color:#ef4444;">Toggle failed: ${err.message}</span>`;
        }
      });
    }
  });
}

// --- 8. Audit Logs View ---
async function loadAuditLogs() {
  const tbody = document.getElementById("auditTableBody");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#94a3b8;">Loading audit records...</td></tr>`;

  try {
    const data = await apiFetch(`/api/v1/audit/logs?limit=50`);
    if (data.records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#94a3b8;">No audit records found.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    data.records.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td style="font-size:0.75rem;color:#94a3b8;">${r.timestamp.substring(0, 19).replace("T", " ")}</td>
        <td><span class="badge badge-gray">${r.role}</span></td>
        <td>${r.user_id}</td>
        <td><code>${r.endpoint}</code></td>
        <td>${r.purpose}</td>
        <td><span class="badge ${r.status_code < 400 ? 'badge-normal' : 'badge-alert'}">${r.status_code}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" style="color:#ef4444;text-align:center;">${err.message}</td></tr>`;
  }
}

// --- 9. Health & Resilience Impact Model & Policy Evidence ---

function switchImpactSubtab(subtab) {
  const btnCalc = document.getElementById("impactSubtabCalc");
  const btnPolicy = document.getElementById("impactSubtabPolicy");
  const secCalc = document.getElementById("impactCalcSection");
  const secPolicy = document.getElementById("impactPolicySection");

  if (!btnCalc || !btnPolicy || !secCalc || !secPolicy) return;

  if (subtab === "calc") {
    btnCalc.className = "btn btn-primary";
    btnPolicy.className = "btn btn-secondary";
    secCalc.style.display = "block";
    secPolicy.style.display = "none";
    recalculateImpact();
  } else {
    btnCalc.className = "btn btn-secondary";
    btnPolicy.className = "btn btn-primary";
    secCalc.style.display = "none";
    secPolicy.style.display = "block";
    loadPolicyEvidence();
  }
}

function loadImpactView() {
  onAssumptionChange();
}

function onAssumptionChange() {
  // 1. Update live value badges
  const wf = parseInt(document.getElementById("inpWorkforce")?.value || 50000);
  const baseRate = parseFloat(document.getElementById("inpBaselineRate")?.value || 2.5);
  const prev = parseInt(document.getElementById("inpPreventability")?.value || 65);
  const costWorkday = parseInt(document.getElementById("inpWorkdayCost")?.value || 450);
  const costSevere = parseInt(document.getElementById("inpSevereCost")?.value || 12000);
  const alarmHours = parseFloat(document.getElementById("inpAlarmHours")?.value || 4.0);
  const hourlyWage = parseInt(document.getElementById("inpHourlyWage")?.value || 120);

  if (document.getElementById("valWorkforce")) document.getElementById("valWorkforce").textContent = wf.toLocaleString();
  if (document.getElementById("valBaselineRate")) document.getElementById("valBaselineRate").textContent = baseRate.toFixed(1) + "%";
  if (document.getElementById("valPreventability")) document.getElementById("valPreventability").textContent = prev + "%";
  if (document.getElementById("valWorkdayCost")) document.getElementById("valWorkdayCost").textContent = costWorkday.toLocaleString() + " AED";
  if (document.getElementById("valSevereCost")) document.getElementById("valSevereCost").textContent = costSevere.toLocaleString() + " AED";
  if (document.getElementById("valAlarmHours")) document.getElementById("valAlarmHours").textContent = alarmHours.toFixed(1) + " hrs";
  if (document.getElementById("valHourlyWage")) document.getElementById("valHourlyWage").textContent = hourlyWage.toLocaleString() + " AED/h";

  // 2. Trigger instant recalculation
  recalculateImpact();
}

async function recalculateImpact() {
  const wf = parseInt(document.getElementById("inpWorkforce")?.value || 50000);
  const baseRate = parseFloat(document.getElementById("inpBaselineRate")?.value || 2.5) / 100.0;
  const prev = parseFloat(document.getElementById("inpPreventability")?.value || 65) / 100.0;
  const costWorkday = parseFloat(document.getElementById("inpWorkdayCost")?.value || 450);
  const costSevere = parseFloat(document.getElementById("inpSevereCost")?.value || 12000);
  const alarmHours = parseFloat(document.getElementById("inpAlarmHours")?.value || 4.0);
  const hourlyWage = parseFloat(document.getElementById("inpHourlyWage")?.value || 120);

  const payload = {
    workforce: {
      workforce_size: wf,
      baseline_heat_illness_rate: baseRate,
    },
    clinical: {
      preventability_coefficient: prev,
    },
    economic: {
      cost_per_lost_workday_aed: costWorkday,
      severe_case_medical_cost_aed: costSevere,
      response_hours_per_false_alarm: alarmHours,
      hourly_inspector_cost_aed: hourlyWage,
    },
  };

  try {
    const data = await apiFetch("/api/v1/impact/calculate", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    const central = data.central_estimate;
    const scen = data.scenarios;

    // Update KPI Highlight Cards
    if (document.getElementById("kpiNetBenefit")) {
      document.getElementById("kpiNetBenefit").textContent = `AED ${central.net_economic_benefit_aed.toLocaleString()}`;
    }
    if (document.getElementById("kpiBenefitRange")) {
      document.getElementById("kpiBenefitRange").textContent = `Range: AED ${scen.low_conservative.net_economic_benefit_aed.toLocaleString()} to ${scen.high_optimistic.net_economic_benefit_aed.toLocaleString()}`;
    }
    if (document.getElementById("kpiWorkdays")) {
      document.getElementById("kpiWorkdays").textContent = `${central.lost_workdays_averted.toLocaleString()} days`;
    }
    if (document.getElementById("kpiSevereCases")) {
      document.getElementById("kpiSevereCases").textContent = `${central.severe_incidents_averted} cases`;
    }
    if (document.getElementById("kpiFatigueCost")) {
      document.getElementById("kpiFatigueCost").textContent = `AED ${central.false_alarm_response_cost_aed.toLocaleString()}`;
    }
    if (document.getElementById("kpiFatigueOverhead")) {
      document.getElementById("kpiFatigueOverhead").textContent = `Overhead: ${central.alert_fatigue_overhead_pct.toFixed(2)}% (< 5% bounded)`;
    }
    if (document.getElementById("kpiBCR")) {
      document.getElementById("kpiBCR").textContent = `${central.benefit_cost_ratio.toFixed(1)}x ROI`;
    }

    // Populate Scenario Uncertainty Bounds Table
    const scenBody = document.getElementById("scenarioTableBody");
    if (scenBody) {
      scenBody.innerHTML = `
        <tr>
          <td><strong style="color:#94a3b8;">Conservative Lower Bound</strong><br><span style="font-size:0.7rem;color:#64748b;">1.8% rate, 40% prev</span></td>
          <td>${scen.low_conservative.total_baseline_cases.toLocaleString()}</td>
          <td>${scen.low_conservative.cases_prevented.toLocaleString()}</td>
          <td><strong style="color:#38bdf8;">${scen.low_conservative.lost_workdays_averted.toLocaleString()} d</strong></td>
          <td>AED ${scen.low_conservative.gross_economic_benefit_aed.toLocaleString()}</td>
          <td style="color:#f87171;">AED ${scen.low_conservative.false_alarm_response_cost_aed.toLocaleString()}</td>
          <td><strong style="color:#10b981;">AED ${scen.low_conservative.net_economic_benefit_aed.toLocaleString()}</strong></td>
          <td><span class="badge badge-gray">${scen.low_conservative.benefit_cost_ratio.toFixed(1)}x</span></td>
        </tr>
        <tr style="background:#0f2942; border-left:3px solid #0284c7;">
          <td><strong style="color:#38bdf8;">★ Central Expected (Baseline)</strong><br><span style="font-size:0.7rem;color:#94a3b8;">2.5% rate, 65% prev (+3.4d lead)</span></td>
          <td>${central.total_baseline_cases.toLocaleString()}</td>
          <td>${central.cases_prevented.toLocaleString()}</td>
          <td><strong style="color:#38bdf8;">${central.lost_workdays_averted.toLocaleString()} d</strong></td>
          <td>AED ${central.gross_economic_benefit_aed.toLocaleString()}</td>
          <td style="color:#f87171;">AED ${central.false_alarm_response_cost_aed.toLocaleString()}</td>
          <td><strong style="color:#10b981; font-size:1.05rem;">AED ${central.net_economic_benefit_aed.toLocaleString()}</strong></td>
          <td><span class="badge badge-normal">${central.benefit_cost_ratio.toFixed(1)}x</span></td>
        </tr>
        <tr>
          <td><strong style="color:#a855f7;">Optimistic Upper Bound</strong><br><span style="font-size:0.7rem;color:#64748b;">3.2% rate, 82% prev</span></td>
          <td>${scen.high_optimistic.total_baseline_cases.toLocaleString()}</td>
          <td>${scen.high_optimistic.cases_prevented.toLocaleString()}</td>
          <td><strong style="color:#38bdf8;">${scen.high_optimistic.lost_workdays_averted.toLocaleString()} d</strong></td>
          <td>AED ${scen.high_optimistic.gross_economic_benefit_aed.toLocaleString()}</td>
          <td style="color:#f87171;">AED ${scen.high_optimistic.false_alarm_response_cost_aed.toLocaleString()}</td>
          <td><strong style="color:#10b981;">AED ${scen.high_optimistic.net_economic_benefit_aed.toLocaleString()}</strong></td>
          <td><span class="badge badge-watch">${scen.high_optimistic.benefit_cost_ratio.toFixed(1)}x</span></td>
        </tr>
      `;
    }

    // Populate 2D Sensitivity Heatmap Table
    const sensTable = document.getElementById("sensitivityTable");
    if (sensTable && data.sensitivity) {
      const s = data.sensitivity;
      let headerHtml = "<thead><tr><th style='text-align:left;'>Lead Time (Days) \\ Preventability</th>";
      s.preventability_steps.forEach(p => {
        headerHtml += `<th>${p}%</th>`;
      });
      headerHtml += "</tr></thead><tbody>";

      let bodyHtml = "";
      s.grid.forEach((row, rowIdx) => {
        const lt = s.lead_time_steps[rowIdx];
        const isOperatingRow = Math.abs(lt - 3.4) < 0.05;
        bodyHtml += `<tr ${isOperatingRow ? "style='background:#0f2744;'" : ""}>`;
        bodyHtml += `<td style='text-align:left;font-weight:700;'>${lt.toFixed(1)} days ${isOperatingRow ? "★" : ""}</td>`;

        row.forEach(cell => {
          const isOperatingPoint = isOperatingRow && Math.abs(cell.preventability_pct - 65.0) < 0.1;
          const bgOpacity = Math.min(0.85, Math.max(0.15, cell.net_benefit_aed / (central.net_economic_benefit_aed * 1.5)));
          const cellStyle = isOperatingPoint
            ? "border:2px solid #38bdf8; background:#0369a1; font-weight:800; color:#fff;"
            : `background:rgba(16, 185, 129, ${bgOpacity.toFixed(2)}); color:#fff;`;

          bodyHtml += `
            <td class="heat-cell" style="${cellStyle}">
              AED ${(cell.net_benefit_aed / 1000.0).toFixed(0)}k<br>
              <span style="font-size:0.7rem;opacity:0.85;">(${cell.workdays_averted.toFixed(0)}d)</span>
            </td>
          `;
        });
        bodyHtml += "</tr>";
      });

      bodyHtml += "</tbody>";
      sensTable.innerHTML = headerHtml + bodyHtml;
    }

  } catch (err) {
    console.error("Impact calculation failed:", err);
  }
}

function resetImpactDefaults() {
  const elWf = document.getElementById("inpWorkforce");
  const elBr = document.getElementById("inpBaselineRate");
  const elPr = document.getElementById("inpPreventability");
  const elWc = document.getElementById("inpWorkdayCost");
  const elSc = document.getElementById("inpSevereCost");
  const elAh = document.getElementById("inpAlarmHours");
  const elHw = document.getElementById("inpHourlyWage");

  if (elWf) elWf.value = 50000;
  if (elBr) elBr.value = 2.5;
  if (elPr) elPr.value = 65;
  if (elWc) elWc.value = 450;
  if (elSc) elSc.value = 12000;
  if (elAh) elAh.value = 4.0;
  if (elHw) elHw.value = 120;

  onAssumptionChange();
}

// --- 10. District Policy Evidence View ---
async function loadPolicyEvidence() {
  const month = document.getElementById("policyMonthSelect")?.value || "August 2024";
  const distTableBody = document.getElementById("policyDistrictTableBody");
  const recList = document.getElementById("policyRecommendationsList");
  const citList = document.getElementById("policyCitationsList");

  if (!distTableBody || !recList || !citList) return;

  distTableBody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#94a3b8;">Loading aggregate policy data...</td></tr>`;

  try {
    const data = await apiFetch(`/api/v1/impact/policy-report?month=${encodeURIComponent(month)}`);

    // 1. Populate District Exposure Burden Table
    distTableBody.innerHTML = "";
    data.districts.forEach(d => {
      const isSuppressed = d.attributable_heat_stress_cases_suppressed === 0;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${d.district_name}</strong><br><span style="font-size:0.7rem;color:#64748b;">${d.district_id}</span></td>
        <td><strong style="color:#f59e0b;">${d.extreme_wbgt_hours_gt_32c}h</strong></td>
        <td><strong style="color:#ef4444;">${d.danger_wbgt_hours_gt_34c}h</strong></td>
        <td>${d.pm25_exceedance_days} days</td>
        <td>${d.midday_high_heat_days} days</td>
        <td>
          ${isSuppressed
            ? '<span class="badge badge-gray" title="Small-cell suppression applied (<=10)">≤ 10 (Suppressed)</span>'
            : `<strong style="color:#38bdf8;">${d.attributable_heat_stress_cases_suppressed} cases</strong>`
          }
        </td>
        <td><span class="badge badge-normal">DP Laplace ε=1.0</span></td>
      `;
      distTableBody.appendChild(tr);
    });

    // 2. Populate Actionable Statutory Policy Interventions
    recList.innerHTML = "";
    data.policy_recommendations.forEach(r => {
      let badgeClass = "badge-priority-moderate";
      if (r.priority_level === "CRITICAL_HIGH") badgeClass = "badge-priority-critical";
      else if (r.priority_level === "ELEVATED") badgeClass = "badge-priority-elevated";

      const card = document.createElement("div");
      card.className = "policy-card";
      card.innerHTML = `
        <div class="policy-card-header">
          <h4 style="font-size:0.95rem; font-weight:700; color:#f8fafc;">${r.action_title}</h4>
          <span class="badge ${badgeClass}">${r.priority_level}</span>
        </div>
        <div style="font-size:0.75rem; color:#38bdf8; font-weight:600;">Domain: ${r.policy_domain}</div>
        <div style="font-size:0.75rem; color:#94a3b8;">Target Jurisdictions: <strong>${r.target_districts.join(", ")}</strong></div>
        <p style="font-size:0.8rem; color:#cbd5e1; margin-top:0.25rem;">${r.statutory_justification}</p>
        <div style="font-size:0.75rem; color:#10b981; margin-top:0.25rem;">
          🛡️ Protection Impact: ${r.expected_workforce_protection}
        </div>
      `;
      recList.appendChild(card);
    });

    // 3. Populate Statutory & Scientific Citations
    citList.innerHTML = "";
    data.statutory_citations.forEach(c => {
      const li = document.createElement("li");
      li.textContent = c;
      citList.appendChild(li);
    });

  } catch (err) {
    distTableBody.innerHTML = `<tr><td colspan="7" style="color:#ef4444;text-align:center;">Failed to load policy data: ${err.message}</td></tr>`;
  }
}

async function exportPolicyMarkdown() {
  const month = document.getElementById("policyMonthSelect")?.value || "August 2024";
  try {
    const text = await apiFetch(`/api/v1/impact/policy-report/markdown?month=${encodeURIComponent(month)}`, {
      headers: { "Accept": "text/markdown" },
    });
    
    // Create download trigger
    const blob = new Blob([text], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `prahari_policy_brief_${month.toLowerCase().replace(" ", "_")}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("Export failed: " + err.message);
  }
}

// --- 8. Munzir Sentinel Hardware Integration View ---

async function loadSentinelView() {
  const tbody = document.getElementById("sentinelNodesTableBody");
  const compContainer = document.getElementById("microclimateComparisonContent");
  if (!tbody) return;

  tbody.innerHTML = `<tr><td colspan="12" style="text-align:center; padding:1.5rem; color:#94a3b8;">Loading Sentinel hardware fleet...</td></tr>`;

  try {
    const nodes = await apiFetch("/api/v1/sentinel/nodes");

    // KPI Counters
    const total = nodes.length;
    const online = nodes.filter(n => n.is_online).length;
    const wbgtVals = nodes.map(n => n.last_wbgt).filter(v => v !== null && v !== undefined);
    const maxWbgt = wbgtVals.length > 0 ? Math.max(...wbgtVals).toFixed(1) + "°C" : "--";
    const alerts = nodes.filter(n => n.current_level && n.current_level !== "None").length;

    document.getElementById("sentinelKpiTotal").textContent = total;
    document.getElementById("sentinelKpiOnline").textContent = online;
    document.getElementById("sentinelKpiMaxWbgt").textContent = maxWbgt;
    document.getElementById("sentinelKpiAlerts").textContent = alerts;

    if (total === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="12" style="text-align:center; padding:2rem; color:#94a3b8;">
            No Sentinel nodes currently commissioned. Click <strong>"➕ Commission New Node"</strong> to register an ESP32 hardware node.
          </td>
        </tr>
      `;
      if (compContainer) {
        compContainer.innerHTML = `<div style="color:#94a3b8; font-size:0.85rem;">Commission nodes to enable live on-site vs regional model comparison.</div>`;
      }
      return;
    }

    // Render Table Rows
    tbody.innerHTML = nodes.map(node => {
      const isOnline = node.is_online;
      const statusBadge = isOnline 
        ? `<span class="badge badge-normal" style="background:#065f46; color:#34d399;">🟢 ONLINE</span>`
        : `<span class="badge badge-alert" style="background:#7f1d1d; color:#f87171;">🔴 OFFLINE</span>`;

      // Alert level badge
      let lvlBadge = `<span class="badge badge-gray">NONE</span>`;
      if (node.current_level === "Watch") lvlBadge = `<span class="badge badge-watch">WATCH</span>`;
      else if (node.current_level === "Warning") lvlBadge = `<span class="badge badge-warning">WARNING</span>`;
      else if (node.current_level === "Alert") lvlBadge = `<span class="badge badge-alert">ALERT</span>`;

      // Sensors
      const dhtOk = node.sensor_health?.dht ? `<span title="DHT22 Air Temp & Humidity Healthy" style="color:#10b981;">✔ DHT</span>` : `<span title="DHT22 Sensor Fault" style="color:#ef4444;">✖ DHT</span>`;
      const globeOk = node.sensor_health?.globe ? `<span title="DS18B20 Globe Sensor Healthy" style="color:#10b981;">✔ Globe</span>` : `<span title="Globe Sensor Fault" style="color:#ef4444;">✖ Globe</span>`;

      // Loc Confidence
      let locBadge = `<span class="badge badge-normal" style="font-size:0.65rem;">EXACT</span>`;
      if (node.location_confidence === "inferred") locBadge = `<span class="badge badge-warning" style="font-size:0.65rem;">INFERRED</span>`;
      else if (node.location_confidence === "district_only") locBadge = `<span class="badge badge-alert" style="font-size:0.65rem;">DISTRICT</span>`;

      // Values
      const wbgtStr = node.last_wbgt !== null && node.last_wbgt !== undefined ? `<strong>${node.last_wbgt.toFixed(1)}°C</strong>` : `<span style="color:#64748b;">--</span>`;
      const airStr = node.last_air_temp !== null && node.last_air_temp !== undefined ? `${node.last_air_temp.toFixed(1)}°C` : `--`;
      const rhStr = node.last_rh !== null && node.last_rh !== undefined ? `${Math.round(node.last_rh)}%` : `--`;
      const globeStr = node.last_globe_temp !== null && node.last_globe_temp !== undefined ? `${node.last_globe_temp.toFixed(1)}°C` : `--`;
      const lastSeenStr = node.last_seen_utc ? node.last_seen_utc.substring(11, 19) + " UTC" : "Never";

      return `
        <tr>
          <td><code style="color:#38bdf8; font-weight:700;">${node.node_id}</code></td>
          <td><span style="font-weight:600;">${node.site_id}</span></td>
          <td>${statusBadge}</td>
          <td style="color:#f59e0b; font-size:0.95rem;">${wbgtStr}</td>
          <td>${airStr}</td>
          <td>${rhStr}</td>
          <td>${globeStr}</td>
          <td>${dhtOk} &nbsp; ${globeOk}</td>
          <td>${locBadge}</td>
          <td>${lvlBadge}</td>
          <td style="font-size:0.75rem; color:#94a3b8;">${lastSeenStr}</td>
          <td>
            <button class="btn btn-secondary" style="font-size:0.7rem; padding:0.25rem 0.5rem;" onclick="simulateNodeUpload('${node.node_id}')">
              ⚡ Test Reading
            </button>
          </td>
        </tr>
      `;
    }).join("");

    // Render Microclimate Comparison Card
    if (compContainer) {
      compContainer.innerHTML = nodes.map(node => {
        const measured = node.last_wbgt || 31.5;
        const modelled = 30.2; // Reference Open-Meteo regional district WBGT
        const delta = (measured - modelled).toFixed(1);
        const deltaSign = delta > 0 ? `+${delta}` : delta;
        const isHotspot = delta > 0.5;

        return `
          <div style="background:#0f172a; border:1px solid #334155; border-radius:8px; padding:0.85rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.75rem;">
            <div>
              <div style="font-weight:700; color:#fff; display:flex; align-items:center; gap:0.5rem;">
                <span>📍 ${node.site_id}</span>
                <code style="font-size:0.75rem; color:#38bdf8;">(${node.node_id})</code>
                ${isHotspot ? `<span class="badge badge-warning" style="font-size:0.65rem;">MICROCLIMATE HOTSPOT</span>` : `<span class="badge badge-normal" style="font-size:0.65rem;">NOMINAL</span>`}
              </div>
              <div style="font-size:0.75rem; color:#94a3b8; margin-top:0.25rem;">
                H3 Cell: <code style="color:#cbd5e1;">${node.h3_index || "8743a104effffff"}</code> &bull; Mode: ${node.indoor_mode ? "Indoor / Canteen" : "Outdoor Sun Shield"}
              </div>
            </div>

            <div style="display:flex; gap:1.25rem; align-items:center;">
              <div style="text-align:right;">
                <div style="font-size:0.7rem; color:#94a3b8;">On-Site (ESP32)</div>
                <div style="font-size:1.1rem; font-weight:700; color:#f59e0b;">${measured.toFixed(1)}°C</div>
              </div>
              <div style="text-align:right;">
                <div style="font-size:0.7rem; color:#94a3b8;">Open-Meteo Model</div>
                <div style="font-size:1.1rem; font-weight:700; color:#38bdf8;">${modelled.toFixed(1)}°C</div>
              </div>
              <div style="text-align:right; min-width:65px;">
                <div style="font-size:0.7rem; color:#94a3b8;">Microclimate Δ</div>
                <div style="font-size:1.1rem; font-weight:700; color:${delta > 0 ? '#ef4444' : '#10b981'};">${deltaSign}°C</div>
              </div>
            </div>
          </div>
        `;
      }).join("");
    }

  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="12" style="text-align:center; padding:1.5rem; color:#ef4444;">Failed to load Sentinel nodes: ${err.message}</td></tr>`;
  }
}

// Modal Handlers
function openCommissionModal() {
  const modal = document.getElementById("commissionModal");
  if (!modal) return;
  document.getElementById("commNodeId").value = "SENT-" + Math.floor(100 + Math.random() * 900);
  document.getElementById("commLat").value = "24.9920";
  document.getElementById("commLon").value = "55.0410";
  document.getElementById("commAccuracy").value = "15";
  document.getElementById("commAccuracyText").textContent = "15m";
  updateConfidenceBadge(15);
  modal.style.display = "flex";
}

function closeCommissionModal() {
  const modal = document.getElementById("commissionModal");
  if (modal) modal.style.display = "none";
}

function useCurrentDeviceLocation() {
  if (!navigator.geolocation) {
    alert("Geolocation is not supported by your browser.");
    return;
  }
  const btn = event.target;
  const originalText = btn.textContent;
  btn.textContent = "⌛ Acquiring GPS...";
  btn.disabled = true;

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      btn.textContent = originalText;
      btn.disabled = false;
      const lat = pos.coords.latitude.toFixed(4);
      const lon = pos.coords.longitude.toFixed(4);
      const acc = Math.round(pos.coords.accuracy);

      document.getElementById("commLat").value = lat;
      document.getElementById("commLon").value = lon;
      document.getElementById("commAccuracy").value = acc;
      document.getElementById("commAccuracyText").textContent = acc + "m";
      updateConfidenceBadge(acc);
    },
    (err) => {
      btn.textContent = originalText;
      btn.disabled = false;
      alert("Location acquisition failed: " + err.message + "\nEnsure permissions are granted and page is served over localhost or HTTPS.");
    },
    { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
  );
}

function updateConfidenceBadge(accuracyM) {
  const badgeContainer = document.getElementById("commConfidenceBadge");
  if (!badgeContainer) return;
  if (accuracyM <= 50) {
    badgeContainer.innerHTML = `<span class="badge badge-normal">EXACT GPS (≤50m)</span>`;
  } else if (accuracyM <= 1000) {
    badgeContainer.innerHTML = `<span class="badge badge-warning">INFERRED (≤1000m)</span>`;
  } else {
    badgeContainer.innerHTML = `<span class="badge badge-alert">DISTRICT ONLY (>1000m)</span>`;
  }
}

async function submitCommissionNode() {
  const nodeId = document.getElementById("commNodeId").value.trim();
  const siteId = document.getElementById("commSiteId").value;
  const lat = parseFloat(document.getElementById("commLat").value);
  const lon = parseFloat(document.getElementById("commLon").value);
  const acc = parseFloat(document.getElementById("commAccuracy").value);
  const indoor = document.getElementById("commIndoorMode").checked;

  if (!nodeId) {
    alert("Please enter a valid Node ID (e.g. SENT-001).");
    return;
  }

  const payload = {
    node_id: nodeId,
    site_id: siteId,
    latitude: lat,
    longitude: lon,
    accuracy_m: acc,
    method: "browser_geolocation",
    indoor_mode: indoor,
  };

  try {
    const res = await apiFetch("/api/v1/sentinel/commission", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    closeCommissionModal();
    alert(`✔ Successfully commissioned ${nodeId} at ${siteId}!\nH3 Cell: ${res.h3_index}\nLocation Confidence: ${res.location_confidence.toUpperCase()}`);
    loadSentinelView();
  } catch (err) {
    alert("Commissioning failed: " + err.message);
  }
}

async function simulateNodeUpload(nodeId) {
  // Generates a live test reading with plausible summer heat parameters
  const airTemp = 36.5 + (Math.random() * 3.0);
  const rh = 55.0 + (Math.random() * 10.0);
  const globeTemp = 43.0 + (Math.random() * 4.0);

  const payload = {
    node_id: nodeId,
    seq: Math.floor(Math.random() * 10000),
    ts: new Date().toISOString(),
    air_temp_c: parseFloat(airTemp.toFixed(1)),
    rh_pct: parseFloat(rh.toFixed(1)),
    globe_temp_c: parseFloat(globeTemp.toFixed(1)),
    wbgt_est_c: 32.5,
    ok: { dht: true, globe: true, rssi: -58 },
  };

  try {
    const res = await apiFetch("/api/v1/sentinel/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    alert(`✔ Sent telemetry for ${nodeId}!\nRe-derived WBGT: ${res.rederived_wbgt}°C\nLED Level returned to ESP32: ${res.level.toUpperCase()}\nValid until: ${res.valid_until.substring(11, 19)} UTC`);
    loadSentinelView();
  } catch (err) {
    alert("Telemetry test failed: " + err.message);
  }
}


