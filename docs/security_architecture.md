# Munzir Enterprise Security & Cloud Reference Architecture

**Document Version:** 1.0  
**Last Updated:** November 2026  
**Target Environment:** Microsoft Azure Commercial & GCC Cloud Regions (e.g. `uaenorth` - Dubai)  
**Security Benchmark:** Microsoft Cloud Security Benchmark (MCSB) v1, CIS Azure Foundations Benchmark

---

## 1. Cloud Architecture Overview

Munzir is deployed on Microsoft Azure using a cloud-native, serverless, and containerized architecture designed for high availability, zero-trust network boundaries, and automatic scale-to-zero when idle.

```
                           [External Traffic (HTTPS TLS 1.3)]
                                          │
                                          ▼
                         [Azure Front Door / API Management]
                           (WAF, DDoS Protection, Rate Limiting)
                                          │
                                          ▼
                      [Microsoft Entra ID (Azure AD)]
                      (JWT App Role Authentication: RBAC)
                                          │
                                          ▼
                         [Azure Container Apps / App Service]
                             (FastAPI + Web Application)
                                          │
            ┌─────────────────────────────┼─────────────────────────────┐
            ▼                             ▼                             ▼
   [Managed Identity]            [Managed Identity]            [Managed Identity]
            │                             │                             │
            ▼                             ▼                             ▼
  [Azure Key Vault]            [Azure Database for PostgreSQL]  [Azure Blob Storage]
(API Keys & App Secrets)        (PostGIS Flexible Server)       (Bronze/Silver/Gold Lakehouse)
(Zero Hardcoded Credentials)    (Private Endpoint & TLS)        (Parquet Encrypted at Rest)
```

---

## 2. Zero-Trust Security Controls

### 1. Azure Key Vault & Secret Management
- **Zero Hardcoded Secrets:** Application configurations contain no passwords, database connection strings, or third-party API tokens.
- **Key Vault References:** Sensitive credentials (OpenAQ API key, database administrative passwords) are stored exclusively in **Azure Key Vault** and resolved dynamically via managed service identities at application startup.
- **Automated Rotation:** Secrets are version-controlled with automated 90-day rotation policies.

---

### 2. Passwordless Managed Identity
- **System-Assigned Managed Identity:** The Azure Container App and Azure Functions communicate with downstream cloud resources (PostgreSQL Flexible Server, Azure Storage Lakehouse, Key Vault) using Azure AD Managed Identities.
- **No Database Passwords in Transit:** Authentication between the application container and PostgreSQL uses Azure AD access tokens generated on-the-fly (`prahari-app@tenant`).

---

### 3. Network Isolation & Private Endpoints
- **Virtual Network (VNet) Integration:** Application containers and database servers are bound within an isolated Azure Virtual Network (`10.0.0.0/16`).
- **Private Endpoints (Azure Private Link):** PostgreSQL and Azure Blob Storage communicate over private IP addresses within subnet `10.0.2.0/24`. Public network access is disabled (`publicNetworkAccess = Disabled`).
- **Transport Encryption:** All ingress and egress traffic requires **TLS 1.3** with modern cipher suites. Insecure HTTP (Port 80) is permanently redirected to HTTPS.

---

### 4. Least-Privilege Entra ID Role-Based Access Control (RBAC)

Munzir maps user identity tokens directly to discrete Entra ID Application Roles:

| Entra ID App Role | Permitted Operational Scope | Prohibited Actions (Enforced at API Gateway) |
|---|---|---|
| `surveillance_officer` | Full district syndromic telemetry, cluster scans, evidence cards, playbook execution. | Raw individual PII queries (non-existent). |
| `occupational_health` | Labor inspectorate overview, worksite ACGIH compliance, aggregate burden reports. | Individual patient clinical histories. |
| `employer_safety` | Authorized worksite rate views per 1,000 workers ($N \ge 50$), hydration regimens. | **Blocked (HTTP 403):** Clinical syndromic feeds, other employer sites, sub-site gang parameters, audit logs. |
| `regulator` | District policy evidence briefs, midday work ban compliance indices. | Site-level individual worker tracking. |
| `public` | Differentially private ($\epsilon = 1.0$) district trend indicators. | All worksite identifiers, cluster scan coordinates, raw event logs. |
| `auditor` | Full view and action security audit log explorer, non-repudiation verification. | Alert dismissal or operational playbook triggering. |

---

### 5. Storage Security & Encryption at Rest
- **Customer-Managed Keys (CMK):** Data stored in Bronze, Silver, and Gold Parquet lakehouse containers is encrypted at rest using 256-bit AES encryption with keys managed in Azure Key Vault.
- **Immutable Audit Logging:** Gold audit records (`data/gold/audit/view_audit_log.parquet`) are written to append-only storage with Azure Blob Storage **WORM (Write Once, Read Many)** immutability policies enabled, preventing tampering or deletion.

