"""Integration tests for PRAHARI CLI interface."""

import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        [sys.executable, "-m", "prahari", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "backfill" in result.stdout
    assert "run-daily" in result.stdout
    assert "train-nlp" in result.stdout
    assert "inspect" in result.stdout


def test_cli_inspect():
    result = subprocess.run(
        [sys.executable, "-m", "prahari", "inspect"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Bronze Lakehouse Inspection" in result.stdout


def test_cli_playbooks():
    result = subprocess.run(
        [sys.executable, "-m", "prahari", "playbooks"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Munzir Operational Action Playbook Library" in result.stdout
    assert "HEAT_WORKSITE_ALERT" in result.stdout


def test_cli_evidence_card():
    result = subprocess.run(
        [sys.executable, "-m", "prahari", "evidence-card", "--geo", "SITE-JA-01"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "EVIDENCE CARD" in result.stdout
    assert "SHAP Attribution" in result.stdout


def test_cli_safe_harbor_blocked():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "prahari",
            "safe-harbor",
            "--test-query",
            "Show individual worker break logs",
            "--role",
            "employer_safety",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Safe-Harbor Worker Protection Shield" in result.stdout
    assert "BLOCKED: Status 403" in result.stdout
    assert "UAE Federal Decree-Law No. 33" in result.stdout


def test_cli_safe_harbor_allowed():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "prahari",
            "safe-harbor",
            "--test-query",
            "Show aggregate district heat burden",
            "--role",
            "surveillance_officer",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ALLOWED: Status 200" in result.stdout


def test_cli_compound_hazard():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "prahari",
            "compound-hazard",
            "--site",
            "SITE-JA-01",
            "--date",
            "2024-08-18",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Compound Multi-Hazard Climate-Health Engine" in result.stdout
    assert "Synergistic Interaction" in result.stdout
    assert "CONTRAINDICATION" in result.stdout


def test_cli_phs():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "prahari",
            "phs",
            "--ambient-temp",
            "42.0",
            "--humidity",
            "65.0",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "ISO 7933:2004 Predicted Heat Strain" in result.stdout
    assert "Rational Heat Balance Fluxes" in result.stdout
    assert "Physiological Strain Status" in result.stdout


def test_cli_thermal_debt():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "prahari",
            "thermal-debt",
            "--site",
            "SITE-JA-01",
            "--date",
            "2024-08-18",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "72-Hour Cumulative Nocturnal Thermal Debt" in result.stdout
    assert "RECOVERY_FAILURE" in result.stdout
    assert "Projected Day 3 Starting Core T" in result.stdout


def test_cli_policy_studio():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "prahari",
            "policy-studio",
            "--cohort",
            "50000",
            "--draws",
            "100",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "MOHRE Ministerial Policy Studio" in result.stdout
    assert "Hospital Admissions Avoided" in result.stdout
    assert "NET PUBLIC ECONOMIC DIVIDEND" in result.stdout
    assert "Benefit-to-Cost Ratio (BCR)" in result.stdout


def test_cli_nabidh_bundle():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "prahari",
            "nabidh-bundle",
            "--site",
            "SITE-JA-01",
            "--cohort",
            "250",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "DHA NABIDH & Malaffi HL7 FHIR R4 Clinical Decision Gateway" in result.stdout
    assert "RiskAssessment" in result.stdout
    assert "CarePlan" in result.stdout
    assert "Provenance" in result.stdout


def test_cli_causal_demix():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "prahari",
            "causal-demix",
            "--site",
            "SITE-JA-01",
            "--cluster",
            "20",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "BAYESIAN CAUSAL DE-MIXING & OUTBREAK ATTRIBUTION ENGINE" in result.stdout
    assert "DOMINANT ETIOLOGY" in result.stdout
    assert "TRI-AGENCY IMMEDIATE ACTION ORDERS" in result.stdout



