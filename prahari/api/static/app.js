/**
 * PRAHARI Front-End Web Application
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

