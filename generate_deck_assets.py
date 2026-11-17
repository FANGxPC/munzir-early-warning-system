import os
import sys
import zipfile
import xml.etree.ElementTree as ET

# Add venv_libs to path
sys.path.insert(0, "./venv_libs")
os.environ["MPLCONFIGDIR"] = "/tmp/mpl_tmp"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

os.makedirs("ppt_assets", exist_ok=True)

# -------------------------------------------------------------
# 1. Generate Architecture Diagram for Slide 4
# -------------------------------------------------------------
def generate_architecture_image():
    out_path = "ppt_assets/architecture_diagram.png"
    fig, ax = plt.subplots(figsize=(13, 6.2), dpi=220)
    fig.patch.set_facecolor("#090d16")
    ax.set_facecolor("#090d16")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Header Title
    ax.text(50, 96, "MUNZIR (منذر) — END-TO-END SYSTEM ARCHITECTURE", 
            color="#38bdf8", fontsize=14, fontweight="bold", ha="center")
    ax.text(50, 91.5, "Physical Edge Telemetry  •  Privacy Lakehouse  •  Causal Reasoning Core  •  Sovereign Bilingual Action", 
            color="#94a3b8", fontsize=8.5, ha="center")

    # Section 1: Ingestion & Edge (Top)
    r1 = patches.FancyBboxPatch((2, 63), 96, 25, boxstyle="round,pad=0.5", ec="#0284c7", fc="#0f172a", lw=1.5)
    ax.add_patch(r1)
    ax.text(4, 84, "1. MULTI-MODAL SENSING & ZERO-PII PRIVACY LAKEHOUSE", color="#38bdf8", fontsize=8.5, fontweight="bold")
    
    b1_items = [
        ("ESP32 Sentinel IoT Node\n(DHT22 + DS18B20 Globe)\nStull WBGT Solver | RGY LED", 3.5, 65, 22.5),
        ("Satellite Numerical Weather\n(Open-Meteo ERA5 28k+ Obs)\n45°C+ Ambient | Solar Flux", 27.5, 65, 22.5),
        ("Air Quality & Silica Dust\n(OpenAQ v3 Dubai Monitoring)\nPM2.5 / PM10 Particulates", 51.5, 65, 22),
        ("Medallion Privacy Lakehouse\nBronze -> Silver H3 Hexgrid\nOpenDP Laplace ε=1.0 | k>=50", 75, 65, 22)
    ]
    for text, x, y, w in b1_items:
        b = patches.FancyBboxPatch((x, y), w, 16.5, boxstyle="round,pad=0.3", ec="#334155", fc="#1e293b", lw=1)
        ax.add_patch(b)
        ax.text(x + w/2, y + 8.25, text, color="#f8fafc", fontsize=6.8, ha="center", va="center")

    # Section 2: Reasoning Core (Middle)
    r2 = patches.FancyBboxPatch((2, 33), 96, 26, boxstyle="round,pad=0.5", ec="#6366f1", fc="#0f172a", lw=1.5)
    ax.add_patch(r2)
    ax.text(4, 55.5, "2. CLINICAL EPIDEMIOLOGICAL & CAUSAL REASONING ENGINES", color="#818cf8", fontsize=8.5, fontweight="bold")

    b2_items = [
        ("CDC EARS C2 & Farrington GLM\nQuasi-Poisson Outbreak Core\nExposure-Calibrated Baselines", 3.5, 35, 22.5),
        ("Renal Sentinel (+11.5d Lead)\nCKD-EPI 2021 Race-Free eGFR\nKDIGO Sub-Clinical AKI Staging", 27.5, 35, 22.5),
        ("Bayesian Spatial Deconvolution\n2-Param Weibull Lag + Transit\nSolves 9PM Muhaisnah Paradox", 51.5, 35, 22),
        ("ISO 7933 Predicted Heat Strain\nCore Rectal Temp (Tre) Solver\n72h Nocturnal Thermal Debt", 75, 35, 22)
    ]
    for text, x, y, w in b2_items:
        b = patches.FancyBboxPatch((x, y), w, 17.5, boxstyle="round,pad=0.3", ec="#334155", fc="#1e293b", lw=1)
        ax.add_patch(b)
        ax.text(x + w/2, y + 8.75, text, color="#f8fafc", fontsize=6.8, ha="center", va="center")

    # Section 3: Decision & Sovereign Action (Bottom)
    r3 = patches.FancyBboxPatch((2, 3), 96, 26, boxstyle="round,pad=0.5", ec="#10b981", fc="#0f172a", lw=1.5)
    ax.add_patch(r3)
    ax.text(4, 25.5, "3. DECISION SUPPORT, INTERVENTION & SOVEREIGN COPILOT", color="#34d399", fontsize=8.5, fontweight="bold")

    b3_items = [
        ("Counterfactual What-If Studio\n1,000 Monte Carlo Simulations\nResolution 44/2022 Midday Ban", 3.5, 5, 22.5),
        ("Municipal Cooling Fleet\nDijkstra Bus & Misting Dispatch\nEmergency Hydration Logistics", 27.5, 5, 22.5),
        ("DHA NABIDH HL7 FHIR R4\nNative Task & RiskAssessment\nZero-Lockin Health Exchange", 51.5, 5, 22),
        ("Sovereign Bilingual Copilot\nInception 42 Jais-3-0.9B on GPU\nCryptographic Safe-Harbor Shield", 75, 5, 22)
    ]
    for text, x, y, w in b3_items:
        b = patches.FancyBboxPatch((x, y), w, 17.5, boxstyle="round,pad=0.3", ec="#334155", fc="#1e293b", lw=1)
        ax.add_patch(b)
        ax.text(x + w/2, y + 8.75, text, color="#f8fafc", fontsize=6.8, ha="center", va="center")

    # Connecting arrows
    for xc in [15, 38.5, 62.5, 86]:
        ax.annotate("", xy=(xc, 61), xytext=(xc, 64),
                    arrowprops=dict(arrowstyle="->", color="#38bdf8", lw=1.5))
        ax.annotate("", xy=(xc, 31), xytext=(xc, 34),
                    arrowprops=dict(arrowstyle="->", color="#818cf8", lw=1.5))

    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print("Generated architecture diagram:", out_path)
    return out_path

# -------------------------------------------------------------
# 2. Generate ROI & Benchmark Visual for Slide 15
# -------------------------------------------------------------
def generate_roi_benchmark_image():
    out_path = "ppt_assets/roi_benchmark.png"
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.8), dpi=220)
    fig.patch.set_facecolor("#090d16")

    # Left plot: Lead Time Comparison
    ax1.set_facecolor("#0f172a")
    categories = ["Hospital ED\nSurge Peak", "Standard\nSyndromic", "Munzir\nPopulation Lead", "Munzir Renal\nSentinel (AKI)"]
    lead_times = [0.0, 1.0, 3.4, 11.5]
    colors = ["#ef4444", "#f59e0b", "#38bdf8", "#10b981"]
    bars = ax1.barh(categories, lead_times, color=colors, height=0.55, edgecolor="#334155", lw=1.2)
    for bar in bars:
        w = bar.get_width()
        ax1.text(w + 0.3, bar.get_y() + bar.get_height()/2, f"+{w:.1f} Days" if w > 0 else "0.0 Days (Baseline)",
                 va="center", color="#f8fafc", fontsize=8.5, fontweight="bold")
    ax1.set_xlim(0, 14)
    ax1.set_title("Intervention Lead Time vs Hospital Peak", color="#38bdf8", fontsize=11, fontweight="bold", pad=12)
    ax1.set_xlabel("Days of Actionable Advance Warning", color="#94a3b8", fontsize=9)
    ax1.tick_params(colors="#cbd5e1", labelsize=8.5)
    for spine in ax1.spines.values():
        spine.set_color("#334155")
    ax1.grid(axis="x", color="#1e293b", linestyle="--", alpha=0.7)

    # Right plot: Audited Economics (AED per 50,000 Workers)
    ax2.set_facecolor("#0f172a")
    econ_cats = ["Intervention\nCapEx (Buses/Shade)", "Gross Savings\n(Workdays & ICU)", "NET ECONOMIC\nBENEFIT"]
    econ_vals = [199163, 1563330, 1364167]
    econ_colors = ["#f43f5e", "#0284c7", "#10b981"]
    bars2 = ax2.bar(econ_cats, [v/1000 for v in econ_vals], color=econ_colors, width=0.5, edgecolor="#334155", lw=1.2)
    for bar in bars2:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 30, f"AED {h:.0f}K",
                 ha="center", color="#f8fafc", fontsize=8.5, fontweight="bold")
    ax2.set_ylim(0, 1850)
    ax2.set_title("Audited Seasonal Economics (50k Workers | 8.11x BCR)", color="#34d399", fontsize=11, fontweight="bold", pad=12)
    ax2.set_ylabel("Thousand AED (Thousands)", color="#94a3b8", fontsize=9)
    ax2.tick_params(colors="#cbd5e1", labelsize=8.5)
    for spine in ax2.spines.values():
        spine.set_color("#334155")
    ax2.grid(axis="y", color="#1e293b", linestyle="--", alpha=0.7)

    plt.tight_layout()
    plt.savefig(out_path, dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print("Generated ROI benchmark image:", out_path)
    return out_path

if __name__ == "__main__":
    generate_architecture_image()
    generate_roi_benchmark_image()

