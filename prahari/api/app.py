"""
FastAPI Application for the Munzir (منذر) Early-Warning Platform.
Serves role-based REST APIs and responsive Single Page Application UI.
Enforces Entra ID app roles, differential privacy, and occupational privacy boundaries.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Depends, Query, Request, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from prahari.api.rbac import (
    EntraRole,
    AuthenticatedUser,
    get_current_user,
    RequireRoles,
    enforce_employer_privacy_boundary,
)
from prahari.api.models import (
    RolesListResponse,
    RoleInfo,
    MapLayersResponse,
    AlertInboxResponse,
    AcknowledgeRequest,
    AcknowledgeResponse,
    WorkplaceRateView,
    DataHealthResponse,
    DemoToggleRequest,
    DemoToggleResponse,
    AuditLogsResponse,
)
from prahari.api.map_service import MapLayerService
from prahari.api.alert_service import AlertInboxService
from prahari.api.employer_service import EmployerSafetyService
from prahari.api.health_service import get_health_service
from prahari.api.demo_service import get_demo_service
from prahari.api.audit import get_audit_service
from prahari.impact.models import (
    ImpactCalculatorRequest,
    ImpactEstimate,
    SensitivityMatrix,
    DistrictPolicyEvidence,
    PolicyReportSummary,
    AssumptionParameter,
)
from prahari.impact.calculator import HealthResilienceImpactCalculator
from prahari.impact.policy_report import DistrictPolicyEvidenceGenerator
from prahari.interop.fhir_adapter import FHIRSurveillanceAdapter
from prahari.interop.sftp_csv import SFTPCSVAdapter
from prahari.interop.drift_monitor import ModelDriftMonitor, DriftReport
from prahari.models.canonical import (
    SentinelUpload,
    SentinelUploadResponse,
    SentinelCommission,
    SentinelNodeStatus,
)
from prahari.ingestion.sentinel_ingest import SentinelIngestionEngine
from prahari.ingestion.openfda import ClinicalVulnerabilityEngine
import numpy as np

# Directories
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Munzir (منذر) Health Early-Warning Platform",
    description="Role-based, privacy-preserving population and occupational health surveillance engine.",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Services
map_service = MapLayerService()
alert_service = AlertInboxService()
employer_service = EmployerSafetyService()
health_service = get_health_service()
demo_service = get_demo_service()
audit_service = get_audit_service()
impact_calculator = HealthResilienceImpactCalculator()
policy_generator = DistrictPolicyEvidenceGenerator(random_seed=42)
sentinel_engine = SentinelIngestionEngine()


# Middleware for View Audit Logging
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/v1/"):
        role = request.headers.get("X-Role", "anonymous")
        user_id = request.headers.get("X-User-ID", "demo-client")
        purpose = request.headers.get("X-Purpose", "standard_query")
        client_ip = request.client.host if request.client else "127.0.0.1"

        geo_level = "district"
        if "workplace" in path or "site" in str(request.query_params):
            geo_level = "site"

        try:
            audit_service.log_view(
                role=role,
                user_id=user_id,
                endpoint=path,
                geo_level=geo_level,
                geo_id=request.query_params.get("site_id", request.query_params.get("geo_id", "ALL")),
                purpose=purpose,
                status_code=response.status_code,
                client_ip=client_ip,
            )
        except Exception:
            pass  # Do not block response if logging encounters an issue
    return response


# --- 1. Authentication & Role Switcher ---

@app.get("/api/v1/auth/roles", response_model=RolesListResponse)
def get_roles_info(user: AuthenticatedUser = Depends(get_current_user)) -> RolesListResponse:
    """Returns available Entra ID roles and the current session's permissions."""
    roles_info = [
        RoleInfo(
            role=EntraRole.SURVEILLANCE_OFFICER.value,
            display_name="District Surveillance Officer",
            description="Full public health authority: clinical syndromic data, cluster boundaries, GLM baselines, and public health triage.",
            permitted_geo_levels=["state", "district", "h3_res7", "site"],
            permitted_signals=["clinical_resp", "clinical_gi", "clinical_fever", "lab_pos", "otc_pharmacy", "wbgt", "air_quality", "workplace_absence"],
            can_view_audit_logs=True,
            can_acknowledge_alerts=True,
        ),
        RoleInfo(
            role=EntraRole.OCCUPATIONAL_HEALTH.value,
            display_name="Occupational Health Officer (MOHRE)",
            description="Workplace inspection and safety: thermal stress, site absence rates (N >= 50), sector aggregate heat hazard.",
            permitted_geo_levels=["state", "district", "site"],
            permitted_signals=["wbgt", "air_quality", "workplace_absence", "workplace_incident"],
            can_view_audit_logs=True,
            can_acknowledge_alerts=True,
        ),
        RoleInfo(
            role=EntraRole.EMPLOYER_SAFETY.value,
            display_name="Employer Site Safety Officer",
            description="Restricted strictly to authorized registered worksite. Rates per 1,000 workers only. Zero clinical data access.",
            permitted_geo_levels=["site"],
            permitted_signals=["wbgt", "workplace_absence", "workplace_incident"],
            can_view_audit_logs=False,
            can_acknowledge_alerts=True,
        ),
        RoleInfo(
            role=EntraRole.REGULATOR.value,
            display_name="Public Health & Safety Regulator",
            description="Policy, statutory oversight, and compliance auditing across all industrial and municipal sectors.",
            permitted_geo_levels=["state", "district"],
            permitted_signals=["wbgt", "air_quality", "clinical_resp", "workplace_absence"],
            can_view_audit_logs=True,
            can_acknowledge_alerts=False,
        ),
        RoleInfo(
            role=EntraRole.PUBLIC.value,
            display_name="Public Open Data Portal",
            description="Differential privacy protected releases (OpenDP epsilon=1.0). Small cells suppressed, no workplace or clinical identifiers.",
            permitted_geo_levels=["state", "district"],
            permitted_signals=["weather", "air_quality", "public_advisory"],
            can_view_audit_logs=False,
            can_acknowledge_alerts=False,
        ),
        RoleInfo(
            role=EntraRole.AUDITOR.value,
            display_name="Inspector General / Auditor",
            description="Full access to non-repudiation audit logs, system access history, human triage decisions, and model performance metrics.",
            permitted_geo_levels=["all"],
            permitted_signals=["all"],
            can_view_audit_logs=True,
            can_acknowledge_alerts=False,
        ),
    ]

    return RolesListResponse(
        current_role=user.role.value,
        user_id=user.user_id,
        organization=user.organization,
        available_roles=roles_info,
    )


# --- 2. Situation Map ---

@app.get("/api/v1/map/layers", response_model=MapLayersResponse)
def get_map_layers(
    date: str = Query("2025-08-20", description="Target surveillance date YYYY-MM-DD"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> MapLayersResponse:
    """Returns geospatial feature overlays, risk tiers, and prospective clusters filtered by role."""
    return map_service.get_map_layers(target_date=date, user=user)


# --- 3. Alert Inbox & Decision Support ---

@app.get("/api/v1/alerts", response_model=AlertInboxResponse)
def get_alert_inbox(
    date: str = Query("2025-08-20", description="Date YYYY-MM-DD"),
    severity: Optional[str] = Query(None, description="Filter by severity: watch, warning, alert"),
    status: Optional[str] = Query(None, description="Filter by review status: pending, acknowledged, acted, dismissed"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> AlertInboxResponse:
    """Returns filtered decision-ready alert inbox."""
    return alert_service.get_inbox(
        target_date=date,
        user=user,
        severity_filter=severity,
        status_filter=status,
    )


@app.get("/api/v1/alerts/{alert_id}/evidence")
def get_evidence_card(
    alert_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns structured Evidence Card in under 2 seconds SLA.
    Enforces strict role checks (employer_safety cannot access cards for other sites).
    """
    return alert_service.get_evidence_card(alert_id=alert_id, user=user)


@app.post("/api/v1/alerts/{alert_id}/acknowledge", response_model=AcknowledgeResponse)
def acknowledge_alert(
    alert_id: str,
    request: AcknowledgeRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> AcknowledgeResponse:
    """Human-in-the-loop acknowledgement workflow with mandatory dismissal reasons."""
    return alert_service.acknowledge_alert(alert_id=alert_id, request=request, user=user)


# --- 4. Employer Safety View (Privacy-Preserving) ---

@app.get("/api/v1/workplace/site-rates", response_model=WorkplaceRateView)
def get_workplace_site_rates(
    request: Request,
    site_id: str = Query("SITE-JA-01", description="Worksite identifier"),
    date: str = Query("2025-08-20", description="Date YYYY-MM-DD"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> WorkplaceRateView:
    """
    Employer Safety View:
    - Enforces rate-only views per 1,000 workers.
    - Enforces minimum group size (N >= 50); cohorts < 50 are suppressed.
    - Prohibits sub-site or worker identification breakdowns (HTTP 403).
    - Injects mandatory statutory non-disciplinary banner.
    """
    return employer_service.get_site_rates(
        site_id=site_id,
        target_date=date,
        user=user,
        query_params=dict(request.query_params),
    )


# --- 5. Clinical Syndromic Micro-Surveillance (Strictly Restricted) ---

@app.get("/api/v1/clinical/syndromic")
def get_clinical_syndromic(
    geo_id: str = Query("DXB-JA", description="District identifier"),
    date: str = Query("2025-08-20", description="Date YYYY-MM-DD"),
    signal_type: str = Query("clinical_resp", description="Syndromic signal"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Public Health Clinical Syndromic Feed:
    Accessible ONLY to surveillance_officer, regulator, and auditor.
    STRICT PRIVACY RULE: employer_safety is completely FORBIDDEN from accessing this endpoint (HTTP 403).
    """
    # Enforce employer privacy boundary
    enforce_employer_privacy_boundary(
        user=user,
        target_geo_id=geo_id,
        signal_type=signal_type,
    )

    if user.role not in [EntraRole.SURVEILLANCE_OFFICER, EntraRole.REGULATOR, EntraRole.AUDITOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Role '{user.role.value}' is not permitted to access clinical syndromic data."
        )

    return {
        "geo_id": geo_id,
        "date": date,
        "signal_type": signal_type,
        "observed_cases": 48.0,
        "expected_cases": 32.5,
        "ears_c2_stat": 2.45,
        "access_granted_to": user.role.value,
    }


# --- 6. Data Health Panel ---

@app.get("/api/v1/health/feeds", response_model=DataHealthResponse)
def get_data_health() -> DataHealthResponse:
    """Monitors ingestion feed freshness, completeness, and latency per source."""
    return health_service.get_health_status()


# --- 7. Missing-Data Demo Simulation Control ---

@app.post("/api/v1/demo/toggle-feed", response_model=DemoToggleResponse)
def toggle_feed_dropout(request: DemoToggleRequest) -> DemoToggleResponse:
    """Simulates feed outages live and proves anti-fatigue policy and confidence widening."""
    return demo_service.toggle_feed(request)


# --- 8. Audit Log Explorer ---

@app.get("/api/v1/audit/logs", response_model=AuditLogsResponse)
def get_audit_logs(
    role_filter: Optional[str] = Query(None, description="Filter logs by role"),
    limit: int = Query(50, ge=1, le=500),
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuditLogsResponse:
    """
    Audit log inspector:
    Accessible only to auditor, surveillance_officer, and regulator.
    Forbidden to employer_safety and public (HTTP 403).
    """
    if user.role in [EntraRole.EMPLOYER_SAFETY, EntraRole.PUBLIC]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access Denied: Role '{user.role.value}' is not permitted to inspect security audit logs."
        )

    logs = audit_service.get_logs(role_filter=role_filter, limit=limit)
    return AuditLogsResponse(total_records=len(logs), records=logs)


# --- 9. Health & Resilience Impact Model & Policy Evidence ---

@app.get("/api/v1/impact/assumptions", response_model=Dict[str, AssumptionParameter])
def get_impact_assumptions(
    user: AuthenticatedUser = Depends(get_current_user),
) -> Dict[str, AssumptionParameter]:
    """Returns the traceable registry of all operational, clinical, and economic assumptions with citations."""
    return impact_calculator.get_assumptions_audit()


@app.post("/api/v1/impact/calculate", response_model=ImpactEstimate)
def calculate_resilience_impact(
    request: Optional[ImpactCalculatorRequest] = None,
    user: AuthenticatedUser = Depends(get_current_user),
) -> ImpactEstimate:
    """
    Computes expected lost workdays averted, severe incidents prevented,
    false alarm response costs, and net economic benefits across Low/Central/High scenarios.
    All results are explicitly marked as modelled estimates.
    """
    return impact_calculator.calculate(request=request)


@app.get("/api/v1/impact/sensitivity", response_model=SensitivityMatrix)
def get_impact_sensitivity_matrix(
    user: AuthenticatedUser = Depends(get_current_user),
) -> SensitivityMatrix:
    """Returns 2D sensitivity matrix varying lead time (1-5 days) and preventability (30-85%)."""
    return impact_calculator.compute_sensitivity_matrix()


@app.get("/api/v1/impact/policy-report", response_model=DistrictPolicyEvidence)
def get_district_policy_evidence(
    month: str = Query("July 2024", description="Reporting month"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> DistrictPolicyEvidence:
    """
    Generates privacy-preserving, aggregate exposure burden reports for municipal regulators.
    Protected via small-cell suppression (k<=10) and Laplace Differential Privacy (epsilon=1.0).
    """
    return policy_generator.generate_policy_evidence_report(month_name=month)


@app.get("/api/v1/impact/policy-report/summary", response_model=PolicyReportSummary)
def get_policy_report_summary(
    month: str = Query("July 2024", description="Reporting month"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> PolicyReportSummary:
    """Returns executive policy summary of extreme exposure hours and recommended inspections."""
    evidence = policy_generator.generate_policy_evidence_report(month_name=month)
    return policy_generator.generate_summary(evidence=evidence)


@app.get("/api/v1/impact/policy-report/markdown", response_class=HTMLResponse)
def get_policy_report_markdown(
    month: str = Query("July 2024", description="Reporting month"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> str:
    """Returns downloadable / printable Markdown policy brief."""
    evidence = policy_generator.generate_policy_evidence_report(month_name=month)
    return policy_generator.export_markdown_brief(evidence)


# --- 9.5 Interoperability & Drift Endpoints ---

@app.get("/api/v1/interop/fhir/export", response_class=JSONResponse)
def export_fhir_surveillance_bundle(
    district_id: str = Query("UAE-DXB", description="District identifier"),
    user: AuthenticatedUser = Depends(RequireRoles([EntraRole.SURVEILLANCE_OFFICER, EntraRole.OCCUPATIONAL_HEALTH, EntraRole.AUDITOR])),
) -> JSONResponse:
    """
    Exports active surveillance alerts and metrics formatted as standard HL7 FHIR R4 Bundle
    (comprising RiskAssessment and MeasureReport resources) for external integration.
    """
    raw_alerts = alert_service._ensure_alerts_for_date("2025-08-20")
    bundle = FHIRSurveillanceAdapter.create_surveillance_bundle(
        alerts=raw_alerts,
        district_id=district_id,
        period_start="2026-06-01",
        period_end="2026-06-07"
    )
    return JSONResponse(content=bundle)


@app.get("/api/v1/interop/drift/report", response_class=JSONResponse)
def get_model_drift_report(
    user: AuthenticatedUser = Depends(get_current_user),
) -> JSONResponse:
    """
    Returns Population Stability Index (PSI) feature drift metrics, Brier score calibration,
    and telemetry latency health status for production surveillance monitoring.
    """
    rng = np.random.default_rng(42)
    # Synthetic baseline vs production distributions for operational reporting
    baseline_feats = {
        "wbgt_max": rng.normal(32.0, 3.5, 1000),
        "pm25": rng.exponential(35.0, 1000),
        "respiratory_ratio": rng.beta(2, 5, 1000),
        "absence_rate": rng.beta(2, 20, 1000),
    }
    current_feats = {
        "wbgt_max": rng.normal(32.8, 3.6, 1000),
        "pm25": rng.exponential(37.0, 1000),
        "respiratory_ratio": rng.beta(2.2, 5, 1000),
        "absence_rate": rng.beta(2.1, 20, 1000),
    }
    report = ModelDriftMonitor.evaluate_model_drift(
        baseline_features=baseline_feats,
        current_features=current_feats,
        recent_probabilities=[0.1, 0.2, 0.8, 0.9, 0.3],
        recent_ground_truth=[0, 0, 1, 1, 0],
    )
    return JSONResponse(content={
        "timestamp": report.timestamp,
        "overall_status": report.overall_status,
        "max_psi": report.max_psi,
        "psi_scores": report.psi_scores,
        "psi_status": report.psi_status,
        "calibration_brier": report.calibration_brier,
        "calibration_status": report.calibration_status,
        "data_freshness_hrs": report.data_freshness_hrs,
        "stale_feeds": report.stale_feeds,
        "action_recommendation": report.action_recommendation
    })


@app.post("/api/v1/interop/sftp/ingest", response_class=JSONResponse)
async def ingest_sftp_workplace_drop(
    request: Request,
    user: AuthenticatedUser = Depends(RequireRoles([EntraRole.EMPLOYER_SAFETY, EntraRole.OCCUPATIONAL_HEALTH])),
) -> JSONResponse:
    """
    Ingests inbound CSV workplace batch drops with strict PII rejection under UAE PDPL.
    """
    body_bytes = await request.body()
    csv_text = body_bytes.decode("utf-8", errors="ignore")
    try:
        obs, warnings = SFTPCSVAdapter.ingest_workplace_batch(csv_text)
        return JSONResponse(content={
            "status": "success",
            "ingested_observations": len(obs),
            "warnings": warnings,
            "sample_first_obs": obs[0].model_dump() if obs else None
        })
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# --- 9.6 Munzir Sentinel Hardware Integration Endpoints ---

@app.post("/api/v1/sentinel/upload", response_model=SentinelUploadResponse)
async def sentinel_upload(
    upload: SentinelUpload,
    x_sentinel_key: Optional[str] = Header(None, alias="X-Sentinel-Key"),
) -> SentinelUploadResponse:
    """
    Ingests 1-minute telemetry payload from shade-mounted ESP32 Sentinel node.
    Re-derives WBGT, stores Bronze observations, and returns real-time alert level to drive on-board LED.
    """
    try:
        return sentinel_engine.process_upload(upload)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/v1/sentinel/commission", response_model=SentinelNodeStatus)
def commission_sentinel_node(
    commission: SentinelCommission,
    user: AuthenticatedUser = Depends(RequireRoles([
        EntraRole.SURVEILLANCE_OFFICER,
        EntraRole.OCCUPATIONAL_HEALTH,
        EntraRole.EMPLOYER_SAFETY,
    ])),
) -> SentinelNodeStatus:
    """
    Commissions an on-site Sentinel node: binds node ID to physical site and browser geolocation.
    Derives H3 Res-7 index and sets location confidence flag.
    """
    try:
        return sentinel_engine.commission_node(commission)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/v1/sentinel/nodes", response_model=List[SentinelNodeStatus])
def get_sentinel_nodes(
    site_id: Optional[str] = Query(None, description="Optional site filter"),
    user: AuthenticatedUser = Depends(get_current_user),
) -> List[SentinelNodeStatus]:
    """
    Returns live fleet health of all commissioned Sentinel nodes,
    including online/offline status, last observed WBGT, and sensor health flags.
    """
    nodes = sentinel_engine.get_all_nodes()
    if site_id:
        nodes = [n for n in nodes if n.site_id == site_id]
    return nodes


@app.post("/api/v1/sentinel/ack", response_class=JSONResponse)
def acknowledge_sentinel_button(
    payload: Dict[str, Any],
) -> JSONResponse:
    """
    Logs physical BOOT button press from an ESP32 Sentinel node.
    Logged in the non-repudiation audit trail as an on-site operator acknowledgement.
    """
    node_id = payload.get("node_id")
    if not node_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required 'node_id' field.")
    try:
        record = sentinel_engine.log_node_ack(node_id=node_id, ts=payload.get("ts"))
        return JSONResponse(content={"status": "acknowledged", "record": record})
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.post("/api/v1/sentinel/test-buzzer/{node_id}", response_class=JSONResponse)
def trigger_sentinel_test_buzzer(node_id: str) -> JSONResponse:
    """Manually forces Alert level on node to sound the buzzer for demo testing."""
    res = sentinel_engine.set_test_alert_level(node_id, level="Alert", duration_seconds=120)
    return JSONResponse(content={"status": "buzzer_triggered", **res})


@app.post("/api/v1/sentinel/silence-buzzer/{node_id}", response_class=JSONResponse)
def silence_sentinel_test_buzzer(node_id: str) -> JSONResponse:
    """Silences the test buzzer on node."""
    res = sentinel_engine.clear_test_alert_level(node_id)
    return JSONResponse(content={"status": "buzzer_silenced", **res})


clinical_engine = ClinicalVulnerabilityEngine()


@app.get("/api/v1/clinical/vulnerability-profile", response_class=JSONResponse)
def get_clinical_vulnerability_profile(
    hazard: str = "heat",
    severity: str = "warning",
    wbgt: Optional[float] = None,
    pm25: Optional[float] = None,
) -> JSONResponse:
    """
    Returns clinical pharmacological vulnerability evaluation derived from
    openFDA Drug Label warnings and DailyMed thermoregulatory risk classes.
    """
    env_metrics = {}
    if wbgt is not None:
        env_metrics["wbgt_max"] = wbgt
    if pm25 is not None:
        env_metrics["pm25"] = pm25

    profile = clinical_engine.evaluate_vulnerability_profile(
        alert_type=f"{hazard}_cluster",
        severity=severity,
        environmental_metrics=env_metrics,
    )
    return JSONResponse(content=profile)


# --- 10. Web Single Page Application (Static UI) ---

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def serve_index() -> HTMLResponse:
    """Serves the Munzir Front-End Single Page Application."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Munzir Health Early-Warning Platform</h1><p>UI loading...</p>")
