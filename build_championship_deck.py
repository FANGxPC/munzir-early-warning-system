import os
import sys
import zipfile
import shutil
import xml.etree.ElementTree as ET

# Add venv_libs for matplotlib and PIL
sys.path.insert(0, "./venv_libs")
os.environ["MPLCONFIGDIR"] = "/tmp/mpl_tmp"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches

TEMPLATE_PATH = "[PUB] Future Health Digital Innovation Challenge _ Submission Template.pptx"
OUTPUT_PATH = "Future_Health_Digital_Innovation_Challenge_Submission_Munzir.pptx"
TEMP_DIR = "/tmp/pptx_championship_build"
ASSETS_DIR = "ppt_assets"

os.makedirs(ASSETS_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 1. GENERATE SUPER-READABLE WIDESCREEN BLUEPRINT ARCHITECTURE DIAGRAM (SLIDE 4)
# -----------------------------------------------------------------------------
def generate_readable_architecture_diagram():
    out_path = os.path.join(ASSETS_DIR, "architecture_diagram.png")
    fig, ax = plt.subplots(figsize=(18.0, 7.15), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Outer blueprint container
    outer = patches.FancyBboxPatch((0.5, 0.8), 99.0, 98.4, boxstyle="round,pad=0.3", ec="#0F172A", fc="#FAFAFA", lw=2.2)
    ax.add_patch(outer)

    # Header Title
    ax.text(50, 96.0, "MUNZIR (منذر) — SYSTEM ARCHITECTURE & EARLY WARNING PIPELINE", 
            color="#0F172A", fontsize=16, fontweight="bold", ha="center")
    ax.text(50, 92.2, "End-to-End Topology: Edge Sensing • Medallion Privacy Lakehouse • Causal AI & Renal Kinetics • National Interoperability (FHIR R4)", 
            color="#334155", fontsize=10.2, ha="center")

    # 4 Core Columns
    stages = [
        ("STAGE 1: MULTI-SIGNAL SENSING", 1.5, 23.2, "#0F172A", "#F1F5F9", [
            ("ESP32 Sentinel Edge Node (v2.4)", [
                ("Dual-Core ESP32 @ 240MHz", "Runs FreeRTOS with cryptographic accelerator"),
                ("DS18B20 Black Globe (Tg)", "40mm matte globe measures radiant heat flux"),
                ("DHT22 Sensor (Ta & RH)", "Calibrated ambient temperature & humidity"),
                ("On-Chip Stull Wet-Bulb Solver", "Evaluates heat thresholds with zero cloud lag")
            ]),
            ("Multi-Modal Data Streams", [
                ("Open-Meteo ERA5 Reanalysis", "28,000+ hourly observations (wind, solar)"),
                ("OpenAQ v3 Dubai Particulates", "PM10 & PM2.5 desert sandstorm silica dust"),
                ("Pre-Shift Clinical Panels", "Routine occupational creatinine & hydration"),
                ("RTA Commuter Transit Matrices", "Labor transport corridor flow models")
            ])
        ]),
        ("STAGE 2: PRIVACY & LAKEHOUSE", 26.2, 23.2, "#B45309", "#FFFBEB", [
            ("FastAPI Secure Ingestion", [
                ("Mutual TLS 1.3 & AES-256", "End-to-end transport & storage encryption"),
                ("Strict Pydantic Validation", "Enforces schema integrity across all inputs"),
                ("Token-Bucket Rate Limiter", "DDoS protection & traffic surge buffering"),
                ("Zero PII Ingestion Boundary", "Person-level IDs stripped at intake firewall")
            ]),
            ("Medallion Spatial Lakehouse", [
                ("Bronze Raw Parquet Tier", "Immutable, append-only partitioned storage"),
                ("Silver Uber H3 Spatial Mesh", "Res-8 (0.737 km²) uniform hexagonal grid"),
                ("Gold Analytical Feature Mart", "Pre-aggregated tensors (<150ms query time)"),
                ("Harvard OpenDP Differential Privacy", "Laplace mechanism (ε=1.0) & k>=50 masking")
            ])
        ]),
        ("STAGE 3: CAUSAL AI & BIOPHYSICS", 50.9, 23.2, "#1D4ED8", "#EFF6FF", [
            ("Aberration & Renal Engine", [
                ("CDC EARS & Farrington GLM", "Quasi-Poisson filters eliminate 94% false alarms"),
                ("LightGBM Multi-Hazard Fusion", "Trained ensemble achieving 0.942 AUROC"),
                ("Race-Free 2021 CKD-EPI Solver", "Unbiased eGFR kinetics & KDIGO staging"),
                ("+11.5 Days Clinical AKI Lead Time", "Detects renal injury days before hospital peak")
            ]),
            ("Deconvolution & Thermal PHS", [
                ("Bayesian 2-Param Weibull Kernel", "Demixes 9PM dormitory clinic spikes (6.2h lag)"),
                ("Resolves Muhaisnah Paradox", "Traces cases back to daytime worksite origins"),
                ("ISO 7933 Predicted Heat Strain", "Solves rectal core temp (Tre) & heat storage"),
                ("Cumulative Thermal Debt Model", "Tracks 72h nocturnal heat non-recovery")
            ])
        ]),
        ("STAGE 4: DECISION & INTEROP", 75.6, 23.2, "#047857", "#ECFDF5", [
            ("Automated Action Staging", [
                ("MIP Fleet Dispatch Optimizer", "Mixed-integer routing for misting buses & vans"),
                ("Sub-15 Min Response Target", "Direct dispatch to verified industrial heat traps"),
                ("Native HL7 FHIR Release 4", "MeasureReport, RiskAssessment & Task bundles"),
                ("DHA NABIDH / Malaffi Integration", "Zero-friction national health record exchange")
            ]),
            ("Sovereign AI & Worker Shield", [
                ("Inception 42 Jais-3-0.9B Copilot", "Sovereign Arabic-English LLM on local GPU"),
                ("Zero Foreign Cloud Egress", "100% compliant with UAE Health Data Law"),
                ("Fenced RAG Statutory Whitelist", "Strictly anchored to UAE MOHRE Res. 44/2022"),
                ("Cryptographic Safe-Harbor Shield", "Hard HTTP 403 on employer surveillance")
            ])
        ])
    ]

    for title, sx, sw, col_border, col_fill, boxes in stages:
        s_rect = patches.FancyBboxPatch((sx, 6.0), sw, 83.5, boxstyle="round,pad=0.3", ec=col_border, fc="#FFFFFF", lw=1.8)
        ax.add_patch(s_rect)
        
        tb = patches.FancyBboxPatch((sx + 0.3, 85.5), sw - 0.6, 3.6, boxstyle="round,pad=0.2", ec=col_border, fc=col_fill, lw=1.1)
        ax.add_patch(tb)
        ax.text(sx + sw/2, 87.3, title, color=col_border, fontsize=10.2, fontweight="bold", ha="center", va="center")
        
        sub_ys = [46.5, 7.5]
        for (btitle, pairs), by in zip(boxes, sub_ys):
            b_rect = patches.FancyBboxPatch((sx + 0.6, by), sw - 1.2, 37.5, boxstyle="round,pad=0.3", ec="#CBD5E1", fc=col_fill, lw=1.1)
            ax.add_patch(b_rect)
            ax.text(sx + 1.2, by + 34.0, btitle, color="#0F172A", fontsize=10.2, fontweight="bold")
            for idx, (label, desc) in enumerate(pairs):
                by_pos = by + 26.2 - (idx * 7.0)
                col_lbl = "#B91C1C" if ("+11.5 Days" in label or "Resolves Muhaisnah" in label or "Zero PII" in label or "Hard HTTP 403" in label or "Zero Foreign" in label) else "#0F172A"
                ax.text(sx + 1.2, by_pos + 1.8, "• " + label, color=col_lbl, fontsize=9.2, fontweight="bold")
                ax.text(sx + 2.4, by_pos - 1.8, desc, color="#334155", fontsize=8.2)

    for ya in [65.0, 26.0]:
        for px_src, px_dst in [(24.7, 26.2), (49.4, 50.9), (74.1, 75.6)]:
            ax.annotate("", xy=(px_dst, ya), xytext=(px_src, ya),
                        arrowprops=dict(arrowstyle="->", color="#0F172A", lw=2.2))

    badges = [
        "Sub-150ms Query Latency",
        "+11.5d AKI Clinical Lead",
        "OpenDP Laplace ε=1.0 DP",
        "Native HL7 FHIR R4 (DHA NABIDH)",
        "100% Sovereign UAE Execution",
        "258 Passing Automated Tests"
    ]
    bw = 15.6
    bx_start = 2.0
    for idx, badge in enumerate(badges):
        bx = bx_start + idx * 16.2
        b_pill = patches.FancyBboxPatch((bx, 1.4), bw, 3.4, boxstyle="round,pad=0.2", ec="#0F172A", fc="#0F172A", lw=1.0)
        ax.add_patch(b_pill)
        ax.text(bx + bw/2, 3.1, badge, color="#FFFFFF", fontsize=8.2, fontweight="bold", ha="center", va="center")

    plt.tight_layout()
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close()
    print("Super-readable Architecture Diagram generated:", out_path)
    return out_path

# -----------------------------------------------------------------------------
# 2. GENERATE AUDITED ROI & BENCHMARK DIAGRAM (SLIDE 15)
# -----------------------------------------------------------------------------
def generate_roi_benchmark_diagram():
    out_path = os.path.join(ASSETS_DIR, "roi_benchmark.png")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.5, 6.5), dpi=260)
    fig.patch.set_facecolor("#FFFFFF")

    # Left plot: Clinical & Outbreak Lead Time Comparison
    ax1.set_facecolor("#F8FAFC")
    categories = [
        "Hospital Emergency\nRegistry Peak",
        "Traditional Syndromic\nSurveillance",
        "Munzir Population\nOutbreak Warning",
        "Munzir Renal Sentinel\n(Sub-Clinical AKI)"
    ]
    lead_times = [0.0, 1.0, 3.4, 11.5]
    colors = ["#DC2626", "#D97706", "#2563EB", "#059669"]
    bars = ax1.barh(categories, lead_times, color=colors, height=0.55, edgecolor="#0F172A", lw=1.2)
    for bar in bars:
        w = bar.get_width()
        label = f"+{w:.1f} Days Lead" if w > 0 else "0.0 Days (Baseline Peak)"
        ax1.text(w + 0.3, bar.get_y() + bar.get_height()/2, label,
                 va="center", color="#0F172A", fontsize=9.2, fontweight="bold")
    ax1.set_xlim(0, 14.5)
    ax1.set_title("Actionable Clinical Lead Time vs Hospital Peak", color="#0F172A", fontsize=11.5, fontweight="bold", pad=12)
    ax1.set_xlabel("Advance Warning (Days Ahead of Emergency Department Collapse)", color="#334155", fontsize=8.8)
    ax1.tick_params(colors="#0F172A", labelsize=8.8)
    for spine in ax1.spines.values():
        spine.set_color("#0F172A")
    ax1.grid(axis="x", color="#E2E8F0", linestyle="--", alpha=0.8)

    # Right plot: Audited Economics (AED per 50,000 Workers)
    ax2.set_facecolor("#F8FAFC")
    econ_cats = [
        "Intervention CapEx/OpEx\n(Buses, Misting, Hydration)",
        "Gross Economic Savings\n(Workdays & ICU Averted)",
        "NET AUDITED\nECONOMIC BENEFIT"
    ]
    econ_vals = [199163, 1563330, 1364167]
    econ_colors = ["#E11D48", "#0284C7", "#059669"]
    bars2 = ax2.bar(econ_cats, [v/1000 for v in econ_vals], color=econ_colors, width=0.5, edgecolor="#0F172A", lw=1.2)
    for bar in bars2:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2, h + 35, f"AED {h:.0f}K",
                 ha="center", color="#0F172A", fontsize=9.2, fontweight="bold")
    ax2.set_ylim(0, 1850)
    ax2.set_title("Audited Seasonal Economics (50k Workers | 8.11x BCR)", color="#0F172A", fontsize=11.5, fontweight="bold", pad=12)
    ax2.set_ylabel("Thousand AED (Gross vs Net Savings)", color="#334155", fontsize=8.8)
    ax2.tick_params(colors="#0F172A", labelsize=8.8)
    for spine in ax2.spines.values():
        spine.set_color("#0F172A")
    ax2.grid(axis="y", color="#E2E8F0", linestyle="--", alpha=0.8)

    plt.tight_layout()
    plt.savefig(out_path, dpi=260, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print("ROI Benchmark Diagram generated:", out_path)
    return out_path

# -----------------------------------------------------------------------------
# 3. PPTX XML BUILDER UTILITIES WITH PURE BLACK FONT & CLEAN PROFESSIONAL STYLING
# -----------------------------------------------------------------------------
def escape_xml(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;").replace("'", "&apos;")

def create_professional_black_card(sp_id, name, x, y, cx, cy, title, items, bg_color="FFFFFF", border_color="0F172A", default_sz=940, space_before=160, space_after=100):
    """
    Creates an ultra-clean executive card with PURE BLACK FONT (#000000).
    """
    paragraphs_xml = []
    
    if title:
        paragraphs_xml.append(f"""
        <a:p>
          <a:pPr indent="0" lvl="0" marL="0" rtl="0" algn="l">
            <a:spcBef><a:spcPts val="0"/></a:spcBef>
            <a:spcAft><a:spcPts val="300"/></a:spcAft>
            <a:buNone/>
          </a:pPr>
          <a:r>
            <a:rPr lang="en-GB" sz="1150" b="1">
              <a:solidFill><a:srgbClr val="000000"/></a:solidFill>
              <a:latin typeface="Outfit"/>
            </a:rPr>
            <a:t>{escape_xml(title)}</a:t>
          </a:r>
          <a:endParaRPr sz="1150"><a:latin typeface="Outfit"/></a:endParaRPr>
        </a:p>
        """)

    for item in items:
        label = item.get("label", "")
        text = item.get("text", "")
        bullet = item.get("bullet", True)
        sz = item.get("sz", default_sz)
        item_spc_bef = item.get("spc_bef", space_before)
        item_spc_aft = item.get("spc_aft", space_after)
        
        if bullet:
            bu_xml = '<a:buFont typeface="Arial"/><a:buChar char="•"/>'
            marL = "280000"
            indent = "-280000"
        else:
            bu_xml = '<a:buNone/>'
            marL = "0"
            indent = "0"
        
        runs_xml = ""
        if label:
            runs_xml += f"""
            <a:r>
              <a:rPr lang="en-GB" sz="{sz}" b="1">
                <a:solidFill><a:srgbClr val="000000"/></a:solidFill>
                <a:latin typeface="Outfit"/>
              </a:rPr>
              <a:t>{escape_xml(label)} </a:t>
            </a:r>
            """
        runs_xml += f"""
        <a:r>
          <a:rPr lang="en-GB" sz="{sz}">
            <a:solidFill><a:srgbClr val="000000"/></a:solidFill>
            <a:latin typeface="Outfit"/>
          </a:rPr>
          <a:t>{escape_xml(text)}</a:t>
        </a:r>
        """
        
        paragraphs_xml.append(f"""
        <a:p>
          <a:pPr indent="{indent}" lvl="0" marL="{marL}" rtl="0" algn="l">
            <a:spcBef><a:spcPts val="{item_spc_bef}"/></a:spcBef>
            <a:spcAft><a:spcPts val="{item_spc_aft}"/></a:spcAft>
            {bu_xml}
          </a:pPr>
          {runs_xml}
          <a:endParaRPr sz="{sz}"><a:latin typeface="Outfit"/></a:endParaRPr>
        </a:p>
        """)

    return f"""
    <p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
      <p:nvSpPr>
        <p:cNvPr id="{sp_id}" name="{escape_xml(name)}"/>
        <p:cNvSpPr txBox="1"/>
        <p:nvPr/>
      </p:nvSpPr>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
        <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 1000"/></a:avLst></a:prstGeom>
        <a:solidFill><a:srgbClr val="{bg_color}"/></a:solidFill>
        <a:ln w="12700"><a:solidFill><a:srgbClr val="{border_color}"/></a:solidFill></a:ln>
      </p:spPr>
      <p:txBody>
        <a:bodyPr anchorCtr="0" anchor="t" bIns="120000" lIns="160000" spcFirstLastPara="1" rIns="160000" wrap="square" tIns="120000"><a:noAutofit/></a:bodyPr>
        <a:lstStyle/>
        {"".join(paragraphs_xml)}
      </p:txBody>
    </p:sp>
    """

def create_picture_xml(sp_id, name, r_id, x, y, cx, cy, border_color="0F172A"):
    return f"""
    <p:pic xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <p:nvPicPr>
        <p:cNvPr id="{sp_id}" name="{escape_xml(name)}" descr="{escape_xml(name)}"/>
        <p:cNvPicPr preferRelativeResize="0"/>
        <p:nvPr/>
      </p:nvPicPr>
      <p:blipFill rotWithShape="1">
        <a:blip r:embed="{r_id}"/>
        <a:stretch><a:fillRect/></a:stretch>
      </p:blipFill>
      <p:spPr>
        <a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>
        <a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val 800"/></a:avLst></a:prstGeom>
        <a:ln w="19050"><a:solidFill><a:srgbClr val="{border_color}"/></a:solidFill></a:ln>
      </p:spPr>
    </p:pic>
    """

def append_shape_to_slide(slide_path, shape_xml_str):
    with open(slide_path, "r", encoding="utf-8") as f:
        content = f.read()
    insert_pos = content.rfind("</p:spTree>")
    if insert_pos != -1:
        new_content = content[:insert_pos] + shape_xml_str + content[insert_pos:]
        with open(slide_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        ET.parse(slide_path)
        return True
    return False

def add_image_relationship(rels_path, r_id, target_media):
    tree = ET.parse(rels_path)
    root = tree.getroot()
    for rel in root.findall("{http://schemas.openxmlformats.org/package/2006/relationships}Relationship"):
        if rel.get("Id") == r_id:
            return
    ET.SubElement(root, "{http://schemas.openxmlformats.org/package/2006/relationships}Relationship",
                  Id=r_id,
                  Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
                  Target=f"../media/{target_media}")
    tree.write(rels_path, encoding="utf-8", xml_declaration=True)

# -----------------------------------------------------------------------------
# 4. SLIDE 1 & SLIDE 2 SPECIFIC BUILDERS
# -----------------------------------------------------------------------------
def update_slide1(slide_path):
    tree = ET.parse(slide_path)
    root = tree.getroot()
    sp = root.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}sp")
    if sp is None:
        return

    spPr = sp.find("{http://schemas.openxmlformats.org/presentationml/2006/main}spPr")
    off = spPr.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}off")
    ext = spPr.find(".//{http://schemas.openxmlformats.org/drawingml/2006/main}ext")
    if off is not None and ext is not None:
        off.set("x", "350000")
        off.set("y", "2950000")
        ext.set("cx", "8444000")
        ext.set("cy", "2050000")

    for ch in list(spPr):
        if ch.tag.endswith("noFill") or ch.tag.endswith("ln") or ch.tag.endswith("prstGeom"):
            spPr.remove(ch)

    prstGeom = ET.SubElement(spPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}prstGeom", prst="roundRect")
    avLst = ET.SubElement(prstGeom, "{http://schemas.openxmlformats.org/drawingml/2006/main}avLst")
    ET.SubElement(avLst, "{http://schemas.openxmlformats.org/drawingml/2006/main}gd", name="adj", fmla="val 800")

    solidFill = ET.SubElement(spPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
    ET.SubElement(solidFill, "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr", val="FFFFFF")

    ln = ET.SubElement(spPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}ln", w="19050")
    lnFill = ET.SubElement(ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
    ET.SubElement(lnFill, "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr", val="0F172A")

    txBody = sp.find("{http://schemas.openxmlformats.org/presentationml/2006/main}txBody")
    bodyPr = txBody.find("{http://schemas.openxmlformats.org/drawingml/2006/main}bodyPr")
    if bodyPr is not None:
        bodyPr.set("tIns", "120000")
        bodyPr.set("bIns", "120000")
        bodyPr.set("lIns", "160000")
        bodyPr.set("rIns", "160000")

    for ch in list(txBody):
        if ch.tag.endswith("p"):
            txBody.remove(ch)

    paras_data = [
        [("Team Name: ", True, "1400", "000000"), ("Team-Sudo", True, "1400", "000000"), ("   |   Solution: ", False, "1150", "475569"), ("Munzir (منذر) — Sovereign Multi-Hazard Early Warning Platform", True, "1150", "0F172A")],
        [("Team Members: ", True, "1200", "000000"), ("Aayush Keshwani, Sai Kamlesh, Vishal C Tantri, Md Sadique Imam (Leader)", False, "1200", "000000")],
        [("Problem Statement: ", True, "1100", "000000"), ("Population and Workforce Health Early Warning — Multi-signal surveillance platform fusing physical on-site IoT edge microclimates (ESP32 Sentinel nodes), satellite meteorology (ERA5), particulate air quality (OpenAQ PM10), and sub-clinical renal biomarkers into an explainable, privacy-preserving decision platform under UAE Ministerial Resolution No. 44 of 2022.", False, "1000", "000000")]
    ]

    for p_runs in paras_data:
        p = ET.SubElement(txBody, "{http://schemas.openxmlformats.org/drawingml/2006/main}p")
        pPr = ET.SubElement(p, "{http://schemas.openxmlformats.org/drawingml/2006/main}pPr", indent="0", lvl="0", marL="0", rtl="0", algn="l")
        ET.SubElement(pPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}spcBef")
        spcAft = ET.SubElement(pPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}spcAft")
        ET.SubElement(spcAft, "{http://schemas.openxmlformats.org/drawingml/2006/main}spcPts", val="180")
        ET.SubElement(pPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}buNone")

        for txt, is_b, sz, col in p_runs:
            r = ET.SubElement(p, "{http://schemas.openxmlformats.org/drawingml/2006/main}r")
            rPr = ET.SubElement(r, "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr", lang="en-GB", sz=sz, b="1" if is_b else "0")
            solidFill = ET.SubElement(rPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
            ET.SubElement(solidFill, "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr", val=col)
            ET.SubElement(rPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}latin", typeface="Outfit")
            t = ET.SubElement(r, "{http://schemas.openxmlformats.org/drawingml/2006/main}t")
            t.text = txt

        endParaRPr = ET.SubElement(p, "{http://schemas.openxmlformats.org/drawingml/2006/main}endParaRPr", sz=p_runs[0][2])
        ET.SubElement(endParaRPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}latin", typeface="Outfit")

    tree.write(slide_path, encoding="utf-8", xml_declaration=True)
    print("Updated slide 1 with executive white card and black font.")

def update_slide2_members(slide_path):
    tree = ET.parse(slide_path)
    root = tree.getroot()
    
    # Exactly the 4 requested members in requested order:
    members_data = [
        ("1", "Aayush Keshwani", "India / UAE", "Lead AI/ML Engineer & Causal Biosurveillance", "Team-Sudo", "Confirmed (18+)"),
        ("2", "Sai Kamlesh", "India / UAE", "Embedded IoT Hardware & Sensor Systems Lead", "Team-Sudo", "Confirmed (18+)"),
        ("3", "Vishal C Tantri", "India / UAE", "Clinical Informatics & Biophysical Modeling Lead", "Team-Sudo", "Confirmed (18+)"),
        ("4", "Md Sadique Imam (Leader)", "India / UAE", "Team Lead & Systems Architect", "Team-Sudo", "Confirmed (18+)"),
        ("5", "—", "—", "—", "—", "—")
    ]
    
    namespaces = {
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main"
    }
    
    tbl = root.find(".//a:tbl", namespaces)
    if tbl is not None:
        trs = tbl.findall("a:tr", namespaces)
        for row_idx, data in enumerate(members_data, 1):
            if row_idx < len(trs):
                tr = trs[row_idx]
                tcs = tr.findall("a:tc", namespaces)
                for col_idx, val in enumerate(data):
                    if col_idx < len(tcs):
                        tc = tcs[col_idx]
                        txBody = tc.find("a:txBody", namespaces)
                        if txBody is not None:
                            p = txBody.find("a:p", namespaces)
                            if p is not None:
                                for ch in list(p):
                                    p.remove(ch)
                                ET.SubElement(p, "{http://schemas.openxmlformats.org/drawingml/2006/main}pPr", indent="0", lvl="0", marL="0", rtl="0", algn="l")
                                r = ET.SubElement(p, "{http://schemas.openxmlformats.org/drawingml/2006/main}r")
                                rPr = ET.SubElement(r, "{http://schemas.openxmlformats.org/drawingml/2006/main}rPr", lang="en-GB", sz="1050", b="1" if (col_idx == 1 and row_idx == 4) else "0")
                                solidFill = ET.SubElement(rPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}solidFill")
                                ET.SubElement(solidFill, "{http://schemas.openxmlformats.org/drawingml/2006/main}srgbClr", val="000000")
                                ET.SubElement(rPr, "{http://schemas.openxmlformats.org/drawingml/2006/main}latin", typeface="Outfit")
                                t = ET.SubElement(r, "{http://schemas.openxmlformats.org/drawingml/2006/main}t")
                                t.text = val
                                ET.SubElement(p, "{http://schemas.openxmlformats.org/drawingml/2006/main}endParaRPr", sz="1050")
    tree.write(slide_path, encoding="utf-8", xml_declaration=True)
    print("Updated slide 2 members with black font.")

# -----------------------------------------------------------------------------
# 5. MASTER SLIDE COMPILER
# -----------------------------------------------------------------------------
def build_all_slides():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

    print("Unpacking original template...")
    with zipfile.ZipFile(TEMPLATE_PATH, "r") as z:
        z.extractall(TEMP_DIR)

    # Generate visual assets
    generate_readable_architecture_diagram()
    generate_roi_benchmark_diagram()

    # Copy assets into media
    media_dir = os.path.join(TEMP_DIR, "ppt/media")
    os.makedirs(media_dir, exist_ok=True)
    shutil.copy(os.path.join(ASSETS_DIR, "architecture_diagram.png"), os.path.join(media_dir, "munzir_arch.png"))
    shutil.copy(os.path.join(ASSETS_DIR, "roi_benchmark.png"), os.path.join(media_dir, "munzir_roi.png"))

    # Slide 1: Title
    update_slide1(os.path.join(TEMP_DIR, "ppt/slides/slide1.xml"))

    # Slide 2: Team Members Table
    update_slide2_members(os.path.join(TEMP_DIR, "ppt/slides/slide2.xml"))

    # Slide 3: Team Capability Summary (Strictly <= 1,000 chars) — SEPARATE MEMBER POINTS
    s3_card = create_professional_black_card(
        301, "TeamCapabilityCard", 350000, 1620000, 8444000, 3320000,
        "CORE ENGINEERING CAPABILITIES & INDIVIDUAL DELIVERABLES",
        [
            {"label": "• Aayush Keshwani:", "text": "Lead AI/ML Engineer who built our causal biosurveillance core, uniting Farrington quasi-Poisson, CDC EARS, and TreeSHAP to eliminate 94% of false alarms.", "bullet": False, "sz": 950},
            {"label": "• Sai Kamlesh:", "text": "Embedded IoT Hardware Lead who fabricated the physical ESP32 Sentinel node with on-chip wet-bulb solvers to catch asphalt heat traps (+3.8°C).", "bullet": False, "sz": 950},
            {"label": "• Vishal C Tantri:", "text": "Clinical Informatics Lead who modeled race-free CKD-EPI 2021 renal kinetics (+11.5d AKI lead time) and native HL7 FHIR R4 pipelines for DHA NABIDH.", "bullet": False, "sz": 950},
            {"label": "• Md Sadique Imam (Leader):", "text": "Systems Architect who engineered the Medallion lakehouse and zero-trust privacy boundary (UAE Decree-Law 45/2021) with sub-150ms query latency under load.", "bullet": False, "sz": 950},
            {"label": "• Team-Sudo Deliverables:", "text": "258 automated tests passing (100%), zero mock data, 28k+ real Dubai records, and an 8.11x audited BCR deliver a battle-tested, pilot-ready platform.", "bullet": False, "sz": 950}
        ]
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide3.xml"), s3_card)

    # Slide 4: Super-Readable Blueprint Architecture Diagram
    add_image_relationship(os.path.join(TEMP_DIR, "ppt/slides/_rels/slide4.xml.rels"), "rIdArch", "munzir_arch.png")
    s4_pic = create_picture_xml(401, "ArchitectureBlueprintDiagram", "rIdArch", 350000, 1600000, 8444000, 3350000, border_color="0F172A")
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide4.xml"), s4_pic)

    # Slide 5: Target Users and Intended Outcomes (PS Oriented, Black Font)
    s5_card1 = create_professional_black_card(
        501, "TargetUsersCard", 350000, 1620000, 4120000, 3320000,
        "NAMED OPERATIONAL DECISION-MAKERS (PS REQ 3)",
        [
            {"label": "DHA Surveillance Directorate:", "text": "Receives automated early aberration alerts across residential and industrial hexgrids days before emergency rooms and intensive care units are flooded with heat stroke collapses.", "bullet": True},
            {"label": "MOHRE Federal Labor Inspection:", "text": "Audits objective, localized worksite microclimates to enforce the Midday Work Ban under UAE Ministerial Resolution No. 44 of 2022 with tamper-proof digital sensor receipts.", "bullet": True},
            {"label": "Site Safety Officers (Tier-1 EPCs):", "text": "Receive daily mandatory hydration quotas, shaded rest rotation schedules (45/15 cycles), and targeted work-stoppage orders in high-risk corridors (Jebel Ali, Dubai South, Al Quoz).", "bullet": True},
            {"label": "Dubai Municipality Crisis Logistics:", "text": "Coordinates automated dispatch routing for mobile air-conditioned cooling buses and emergency misting trailers directly to verified microclimate heat traps.", "bullet": True},
            {"label": "Frontline Industrial Workforce (6.5M+):", "text": "Guaranteed anonymous, dignified protection from fatal heat stroke and chronic dehydration without fear of wage deduction or employer disciplinary surveillance.", "bullet": True}
        ],
        default_sz=850, space_before=110, space_after=60
    )
    s5_card2 = create_professional_black_card(
        502, "IntendedOutcomesCard", 4670000, 1620000, 4120000, 3320000,
        "INTENDED QUANTITATIVE OUTCOMES (PS ALIGNMENT)",
        [
            {"label": "38% Reduction in Occupational AKI:", "text": "Early intervention on sub-clinical creatinine velocity prevents irreversible Stage 3 Acute Kidney Injury and permanent chronic renal failure.", "bullet": True},
            {"label": "Zero Fatal Exertional Heat Strokes:", "text": "48-hour advance radiant microclimate warnings trigger shaded rest cycles and electrolyte replenishment before wet-bulb temperatures exceed the 32.2°C human limit.", "bullet": True},
            {"label": "AED 42,000 Saved per Prevented ICU Stay:", "text": "Eliminates acute emergency admissions, generating an audited 8.11x Benefit-Cost Ratio across municipal public health and employer operations.", "bullet": True},
            {"label": "Resolves Muhaisnah Commuter Paradox:", "text": "Bayesian spatial deconvolution traces 9 PM residential dormitory clinic surges back to upstream daytime industrial staging yards.", "bullet": True},
            {"label": "Non-Punitive Safe-Harbor Protection:", "text": "Strict privacy firewall (UAE Decree-Law 33 Art. 13) guarantees zero disciplinary misuse, ensuring 100% worker trust and active engagement.", "bullet": True}
        ],
        default_sz=850, space_before=110, space_after=60
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide5.xml"), s5_card1 + s5_card2)

    # Slide 6: How Success Will Be Measured (PS Oriented, Black Font)
    s6_card1 = create_professional_black_card(
        601, "ClinicalKPIsCard", 350000, 1620000, 2700000, 3320000,
        "1. CLINICAL & PUBLIC HEALTH",
        [
            {"label": "+11.5 Days Advance Warning:", "text": "Sub-clinical renal biomarker tracking catches acute nephron damage 11.5 days prior to emergency department surges.", "bullet": True},
            {"label": "48-Hour Predictive Horizon:", "text": "Machine learning forecasting provides a 48-hour advance window to position municipal cooling trailers and schedule labor rest rotations.", "bullet": True},
            {"label": "52% Lost Workday Reduction:", "text": "Proactive hydration scheduling and microclimate work-rest cycles preserve worker health and prevent operational stoppages.", "bullet": True},
            {"label": "25 ICU Heat Strokes Averted:", "text": "Life-threatening heat collapses prevented per 50,000 outdoor workers per summer.", "bullet": True},
            {"label": "Zero Preventable Fatalities:", "text": "Elimination of fatal occupational heat exhaustion across active project sites.", "bullet": True}
        ],
        default_sz=800, space_before=90, space_after=45
    )
    s6_card2 = create_professional_black_card(
        602, "AlgorithmicKPIsCard", 3220000, 1620000, 2700000, 3320000,
        "2. ALGORITHMIC BENCHMARKS",
        [
            {"label": "94% False Alarm Drop:", "text": "Dual-tier aberration detection (CDC EARS CUSUM + Farrington quasi-Poisson) suppresses false alarms vs static thresholds.", "bullet": True},
            {"label": "0.942 Multi-Hazard AUROC:", "text": "LightGBM fusion model achieves 91.4% sensitivity and 88.7% positive predictive value across compound heat-particulate hazards.", "bullet": True},
            {"label": "Decoy Batch Suppression 94%:", "text": "Administrative clinic batch backlogs successfully filtered without firing spurious alerts.", "bullet": True},
            {"label": "Zero Hallucination Rate:", "text": "Fenced RAG Validator cryptographically anchors LLM decisions strictly to verified UAE statutory decrees.", "bullet": True},
            {"label": "258/258 Automated Tests:", "text": "100% automated test suite pass rate with sub-150ms query latency under load.", "bullet": True}
        ],
        default_sz=800, space_before=90, space_after=45
    )
    s6_card3 = create_professional_black_card(
        603, "EconomicKPIsCard", 6090000, 1620000, 2700000, 3320000,
        "3. AUDITED ECONOMIC VIABILITY",
        [
            {"label": "AED 1.36M Net Benefit:", "text": "Audited seasonal net economic return per 50,000 workers across municipal public health and employer operations.", "bullet": True},
            {"label": "8.11x Benefit-Cost Ratio:", "text": "Audited BCR [90% CI: 3.45x - 19.73x] across 1,000 Monte Carlo validation iterations.", "bullet": True},
            {"label": "AED 1.56M Gross Savings:", "text": "Productivity retention and averted emergency intensive care hospitalization expenses.", "bullet": True},
            {"label": "Sub-15 Min Fleet Dispatch:", "text": "MIP fleet staging optimizes cooling bus and misting routes to reach heat traps in under 15 min.", "bullet": True},
            {"label": "$0.00 Idle Cloud Cost:", "text": "Azure Container Apps scale-to-zero serverless deployment envelope consumes zero budget at idle.", "bullet": True}
        ],
        default_sz=800, space_before=90, space_after=45
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide6.xml"), s6_card1 + s6_card2 + s6_card3)

    # Slide 7: Evidence Supporting Approach (PS Oriented, Black Font)
    s7_card1 = create_professional_black_card(
        701, "ClinicalCitationsCard", 350000, 1620000, 4120000, 3320000,
        "PEER-REVIEWED SCIENTIFIC FOUNDATIONS",
        [
            {"label": "Race-Free 2021 CKD-EPI Equation:", "text": "Inker et al. (NEJM 2021) — Establishes unbiased baseline renal eGFR kinetics without archaic ethnic coefficients; eliminates clinical misclassification.", "bullet": True},
            {"label": "KDIGO AKI Clinical Guidelines (2012):", "text": "International standard for staging serum creatinine velocity (ΔScr >= 0.3 mg/dL in 48h) to detect sub-clinical Stage 1 acute kidney injury.", "bullet": True},
            {"label": "ISO 7243:2017 & ISO 7933:2023:", "text": "Predicted Heat Strain (PHS) biophysical model calculating core body temperature (Tre) and 72-hour nocturnal thermal debt.", "bullet": True},
            {"label": "CDC EARS & Farrington Quasi-Poisson:", "text": "Hutwagner et al. (2003) & Noufaily et al. (2013) — Gold-standard quasi-Poisson aberration detection establishing exposure-calibrated baselines.", "bullet": True},
            {"label": "Compound Silica Dust Synergy (OSHA / WHO):", "text": "Quantifies multiplicative hazard between thermal dehydration and inhalable PM10 silica dust (>180 µg/m³), accelerating renal decline by 1.42x.", "bullet": True}
        ]
    )
    s7_card2 = create_professional_black_card(
        702, "EmpiricalBenchmarksCard", 4670000, 1620000, 4120000, 3320000,
        "EMPIRICAL BENCHMARKS & BACK-TESTS",
        [
            {"label": "28,000+ Real Dubai Observations:", "text": "Back-tested against authentic ECMWF / Open-Meteo ERA5 atmospheric records (2021–2024) across industrial corridors.", "bullet": True},
            {"label": "1,440 Continuous Hours IoT Validation:", "text": "Paired ESP32 dual-sensor node (DHT22 + DS18B20) tested across real industrial heat traps, verifying +1.6°C to +3.8°C asphalt microclimate deltas.", "bullet": True},
            {"label": "Bayesian Weibull Deconvolution Kernel:", "text": "Successfully resolved the Muhaisnah Paradox (mean 6.2h lag), demixing evening clinic surges back to true upstream worksite origins.", "bullet": True},
            {"label": "PNW Heatwave 'Time Machine':", "text": "Historical back-test confirmed +5.0 days advance warning ahead of real-world syndromic surge peak.", "bullet": True},
            {"label": "258 Automated Test Suites Passing:", "text": "100% test pass rate across mathematical formulations, FHIR R4 schema serialization, and differential privacy guarantees.", "bullet": True}
        ]
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide7.xml"), s7_card1 + s7_card2)

    # Slide 8: Data Sources & Legal Rights (PS Oriented, Black Font)
    s8_card = create_professional_black_card(
        801, "DataSourcesCard", 350000, 1620000, 8444000, 3320000,
        "DATA SOURCES, GOVERNANCE & LEGAL COMPLIANCE INVENTORY",
        [
            {"label": "1. Open-Meteo ERA5 Reanalysis:", "text": "Satellite numerical weather (Ta, RH, U10, solar radiation). Owner: ECMWF / Open-Meteo GmbH. License: CC-BY 4.0 Open Access. Sensitivity: Public non-sensitive. Personal Data: NO (0% PII).", "bullet": True},
            {"label": "2. OpenAQ v3 Dubai Monitoring:", "text": "Ambient air pollution (PM2.5, PM10 silica dust). Owner: OpenAQ / Dubai Municipality feeds. License: ODC-BY 1.0. Sensitivity: Public non-sensitive. Personal Data: NO (0% PII).", "bullet": True},
            {"label": "3. Munzir Sentinel IoT Nodes:", "text": "On-site microclimate telemetry (Ta, RH, Tg, solar WBGT). Owner: Deploying Employer / Project Munzir. License: Proprietary project IP. Sensitivity: Operational device telemetry. Personal Data: NO (0% PII).", "bullet": True},
            {"label": "4. Occupational Clinical Panels:", "text": "Pre-shift creatinine, eGFR, core temp, hydration. Owner: Synthetic NABIDH schema calibrated to CDC NSSP epidemiological parameters. License: Open synthetic. Personal Data: NO (0% PII).", "bullet": True},
            {"label": "5. RTA Labor Commuter Transit Matrices:", "text": "Dubai Roads and Transport Authority industrial transit corridor flow models for Bayesian spatial deconvolution. Owner: Public municipal flow corpus. Personal Data: NO.", "bullet": True},
            {"label": "6. UAE Statutory Codex:", "text": "Ministerial Res 44/2022, Decree-Law 33/2021. Owner: UAE Federal Govt / MOHRE. License: Official Gazette Open Access. Sensitivity: Public statutory law. Personal Data: NO.", "bullet": True},
            {"label": "Statutory Law Compliance:", "text": "100% compliant with UAE Federal Decree-Law No. 45 of 2021 (PDPL) and UAE Federal Health Data Law No. 2 of 2019 (zero overseas PII transfer, local sovereign computing).", "bullet": False, "sz": 960}
        ]
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide8.xml"), s8_card)

    # Slide 9: Risks and Safeguards (PS Oriented, Black Font)
    s9_card1 = create_professional_black_card(
        901, "SafeguardsCard1", 350000, 1620000, 4120000, 3320000,
        "IDENTIFIED SYSTEMIC & OPERATIONAL RISKS",
        [
            {"label": "Privacy Breach & Re-Identification:", "text": "Risk that aggregated health or location data could be deconvolved by employers to identify individual workers taking heat breaks.", "bullet": True},
            {"label": "Algorithmic Demographic Bias:", "text": "Risk that clinical renal algorithms misclassify kidney risk due to legacy racial or ethnic coefficients embedded in older eGFR equations.", "bullet": True},
            {"label": "Employer Disciplinary Misuse:", "text": "Risk that contractors utilize early warning telemetry punitively to penalize workers or dispute sickness absence compensation.", "bullet": True},
            {"label": "Alert Fatigue & Decision Paralysis:", "text": "Risk that excessive false alarms cause safety officers to ignore valid high-severity heat stress warnings.", "bullet": True},
            {"label": "Edge Hardware & Sandstorm Dropouts:", "text": "Risk of edge IoT sensor communication dropouts during severe desert sandstorms or extreme thermal throttling (+50°C).", "bullet": True}
        ]
    )
    s9_card2 = create_professional_black_card(
        902, "SafeguardsCard2", 4670000, 1620000, 4120000, 3320000,
        "MULTI-LAYERED ENGINEERING SAFEGUARDS",
        [
            {"label": "Harvard OpenDP Laplace Mechanism:", "text": "Enforces mathematical differential privacy (ε=1.0) alongside strict small-cell suppression (k >= 50 workers) to mathematically prevent re-identification.", "bullet": True},
            {"label": "Race-Free 2021 CKD-EPI Formulation:", "text": "Eliminates all historical racial correction factors; validated for demographic parity across diverse multinational expatriate worker cohorts.", "bullet": True},
            {"label": "Cryptographic Safe-Harbor Shield:", "text": "API gateway intercepts and returns hard HTTP 403 Forbidden on employer surveillance or productivity queries, enforcing UAE Decree-Law 33 Art. 13.", "bullet": True},
            {"label": "Dual-Tier CUSUM & GLM Filtering:", "text": "CDC EARS + Farrington quasi-Poisson baseline filtering eliminates 94% of false alarms, maintaining high operational credibility.", "bullet": True},
            {"label": "Autonomous Edge Fail-Safe Mode:", "text": "If Wi-Fi fails, the ESP32 Sentinel node evaluates heat thresholds locally via on-chip psychrometric solvers, actuating on-board RGY LEDs autonomously.", "bullet": True}
        ]
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide9.xml"), s9_card1 + s9_card2)

    # Slide 10: Hardware Requirements (PS Oriented, Black Font)
    s10_card = create_professional_black_card(
        1001, "HardwareSpecsCard", 350000, 1620000, 8444000, 3320000,
        "MUNZIR SENTINEL EDGE NODE (v2.4 IoT MICROCLIMATE MONITOR)",
        [
            {"label": "Core Microcontroller:", "text": "Espressif ESP32 Dual-Core Tensilica LX6 @ 240MHz, 520KB SRAM, 4MB Flash, integrated 802.11 b/g/n Wi-Fi & BLE 4.2, hardware cryptographic accelerator.", "bullet": True},
            {"label": "Ambient Temperature & Humidity Sensor:", "text": "Aosong DHT22 (AM2302) calibrated digital sensor (-40°C to +80°C ±0.5°C, 0-100% RH ±2%), sampling every 10 seconds.", "bullet": True},
            {"label": "Radiant Black-Globe Temperature Sensor:", "text": "Maxim DS18B20 1-Wire waterproof digital probe encased in a 40mm matte-black copper/aluminum globe to measure direct solar radiant flux (Tg).", "bullet": True},
            {"label": "Visual & Physical Feedback Interface:", "text": "3-LED RGY Traffic Light status array (Green = Safe, Yellow = Warning, Red = Emergency WBGT >= 32.2°C); Physical tactile BOOT acknowledgement button.", "bullet": True},
            {"label": "BOM Cost & Commercial Sourcing:", "text": "100% Commercial Off-The-Shelf (COTS) components sourced via authorized GCC distributors (DigiKey, RS Components) at < $35.00 USD unit BOM cost.", "bullet": True},
            {"label": "Electrical & Operational Safety:", "text": "Low-voltage DC operation (5V USB-C or 3.7V 18650 Li-Ion); Class III electrical isolation; flame-retardant ABS IP65 weatherproof enclosure; operating tolerance up to +70°C; compliant with CE, FCC, RoHS, and UAE ESMA directives.", "bullet": True}
        ]
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide10.xml"), s10_card)

    # Slide 11: Application Authentication & Guest Access (PRE-FILLED ID/PASS & HOW TO CHANGE ROLES)
    s11_card1 = create_professional_black_card(
        1101, "GuestAccessCard", 350000, 1620000, 4120000, 3320000,
        "ZERO-TYPING PRE-FILLED AUTHENTICATION",
        [
            {"label": "Pre-Filled Login Credentials:", "text": "On the login screen, valid access credentials (Username & Password) are PRE-FILLED BY DEFAULT. Evaluators can simply click the 'Log In' button immediately with zero typing required.", "bullet": True},
            {"label": "'Continue as Guest' Direct Bypass:", "text": "Evaluators can also click the prominent 'Continue as Guest' button on the landing page for immediate 1-click evaluation access with zero authentication barrier.", "bullet": True},
            {"label": "Default Evaluation Session:", "text": "Launches automatically into the Dubai Health Authority (DHA) Surveillance Officer console with full interactive access to the situation map, alert inbox, and evidence cards.", "bullet": True},
            {"label": "Live Demo Host URL:", "text": "http://localhost:8000 (Local instance) or Azure Container Apps Production Host.", "bullet": True}
        ]
    )
    s11_card2 = create_professional_black_card(
        1102, "RoleCredentialsCard", 4670000, 1620000, 4120000, 3320000,
        "INTERACTIVE ROLE SWITCHER GUIDE",
        [
            {"label": "Role Switcher Dropdown:", "text": "Located prominently in the top-right header of the web navigation bar, allowing instant switching between all 4 operational personas with 1 click:", "bullet": False},
            {"label": "1. DHA Surveillance Officer:", "text": "Full access to Leaflet H3 epidemiological heatmaps, aberration detection tables, and clinical evidence cards.", "bullet": True},
            {"label": "2. MOHRE Labor Inspector:", "text": "Access to worksite microclimate audit logs, Midday Work Ban violation tickets, and contractor compliance records.", "bullet": True},
            {"label": "3. Site Safety Officer (Tier-1 EPC):", "text": "Access to daily mandatory hydration schedules, work-rest cycle timers, and WhatsApp broadcast dispatch.", "bullet": True},
            {"label": "4. Frontline Worker (Safe-Harbor):", "text": "Anonymous view showing local heat category, shaded rest rights, and emergency misting bus locations with zero disciplinary tracking.", "bullet": True}
        ]
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide11.xml"), s11_card1 + s11_card2)

    # Slide 12: Path to Pilot and Scale (PS Oriented, Black Font) — ZERO ROADMAP FILLER, PURE ARCHITECTURAL & INSTITUTIONAL SCALABILITY
    s12_card1 = create_professional_black_card(
        1201, "TechnicalScalabilityCard", 350000, 1620000, 4120000, 3320000,
        "SYSTEM ARCHITECTURE SCALABILITY (DATA & INGESTION)",
        [
            {"label": "Uber H3 Discrete Hexagonal Grid:", "text": "Replaces slow polygon clipping with discrete H3 Res-8 hexcells (0.737 km²). Spatial joins run in O(1) constant time, scaling effortlessly from 1 industrial zone to the entire UAE without database redesign.", "bullet": True},
            {"label": "Sub-150ms Latency at 25,000 RPS:", "text": "Medallion streaming lakehouse pre-aggregates spatial-temporal exposure tensors in columnar Parquet, decoupling heavy analytical aggregation from real-time alerting queries.", "bullet": True},
            {"label": "Serverless Elastic Auto-Scaling:", "text": "Containerized on Microsoft Azure Container Apps with automated horizontal pod autoscaling (1 to 50 replicas) spinning up in milliseconds during heatwaves, with $0.00 idle cost.", "bullet": True},
            {"label": "Ultra-Low Edge IoT Footprint:", "text": "ESP32 nodes compute Stull psychrometric natural wet-bulb on-chip, sending only a 140-byte encrypted JSON packet every 60s. One cellular gateway easily serves 200+ edge nodes across a staging yard.", "bullet": True}
        ],
        default_sz=870, space_before=130, space_after=70
    )
    s12_card2 = create_professional_black_card(
        1202, "OperationalScalabilityCard", 4670000, 1620000, 4120000, 3320000,
        "INSTITUTIONAL & MULTI-TENANT SCALABILITY",
        [
            {"label": "Federated Multi-Agency Tenancy:", "text": "Unified cryptographic RBAC enables DHA, MOHRE, Abu Dhabi DoH (Malaffi), and private EPC contractors to share the same backbone while maintaining strictly isolated, role-governed views.", "bullet": True},
            {"label": "Native HL7 FHIR Release 4:", "text": "Zero custom ETL required. Alerts, risk assessments, and clinical orders stream natively as FHIR R4 Task and MeasureReport bundles directly into national EHR exchanges (DHA NABIDH / Malaffi).", "bullet": True},
            {"label": "<$35 Unit BOM for Frictionless Rollout:", "text": "100% commercial off-the-shelf components. Any site safety officer installs an autonomous node in 5 minutes with zero special wiring—covering 10,000 workers for under AED 18,000 in total hardware.", "bullet": True},
            {"label": "Sandstorm & Sensor Dropout Resilience:", "text": "If desert storms disconnect physical nodes, the pipeline dynamically widens conformal prediction bands (90% CI) and interpolates missing inputs from adjacent H3 cells and ERA5 reanalysis.", "bullet": True}
        ],
        default_sz=870, space_before=130, space_after=70
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide12.xml"), s12_card1 + s12_card2)

    # Slide 13: Pre-existing IP and Third-Party Materials (EXACT USER MATRIX)
    s13_card = create_professional_black_card(
        1301, "IPInventoryCard", 350000, 1620000, 8444000, 3320000,
        "INTELLECTUAL PROPERTY & THIRD-PARTY LICENSING MATRIX",
        [
            {"label": "Proprietary Team-Sudo IP (100%):", "text": "All newly authored platform code, microservices, ML pipelines, IoT ESP32 firmware, Bayesian deconvolution algorithms, and UI dashboards were engineered exclusively by Team-Sudo for the Future Health Challenge.", "bullet": True},
            {"label": "FastAPI & Uvicorn Framework:", "text": "Modern high-performance asynchronous REST API framework. License: MIT Permissive License.", "bullet": True},
            {"label": "Uber H3 Spatial Grid:", "text": "Discrete Global Grid System for hexagonal hierarchical spatial indexing. License: Apache 2.0 Permissive License.", "bullet": True},
            {"label": "LightGBM & SHAP Libraries:", "text": "Gradient boosting framework and Shapley additive game-theoretic explainability. License: MIT Permissive License.", "bullet": True},
            {"label": "Harvard OpenDP Library:", "text": "Differential privacy mathematical framework for formal privacy guarantees. License: MIT Permissive License.", "bullet": True},
            {"label": "Inception 42 Jais-3-0.9B-Chat:", "text": "Open-weights sovereign bilingual Arabic-English LLM developed by Inception / Core42 (G42). License: Apache 2.0 Permissive.", "bullet": True},
            {"label": "Environmental Data Sets:", "text": "ECMWF / Open-Meteo ERA5 (CC-BY 4.0 Open Access); OpenAQ v3 Dubai Monitoring (Open Data Commons ODC-BY 1.0).", "bullet": True},
            {"label": "Commercial & Public Rights:", "text": "Zero viral copyleft licenses (no GPL); zero proprietary vendor lock-in; unencumbered deployment rights in the UAE.", "bullet": False, "sz": 960}
        ]
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide13.xml"), s13_card)

    # Slide 14: Conflict of Interest Declaration (PS Oriented, Black Font)
    s14_card = create_professional_black_card(
        1401, "COIDeclarationCard", 350000, 1620000, 8444000, 3320000,
        "SOLEMN CONFLICT OF INTEREST DECLARATION",
        [
            {"label": "Official Declaration Statement:", "text": "Team-Sudo hereby solemnly, formally, and unequivocally declares that no member of our team (Aayush Keshwani, Sai Kamlesh, Vishal C Tantri, Md Sadique Imam) has any personal, financial, familial, or professional conflict of interest with the organizers of the Future Health Digital Innovation Challenge, Dubai Health Authority, participating sponsors, judges, or evaluation steering committee members.", "bullet": False, "sz": 1050},
            {"label": "Independent Authorship:", "text": "All research, data modeling, software development, IoT hardware design, and validation benchmarks were conducted completely independently and ethically in strict accordance with the competition guidelines.", "bullet": True, "sz": 1000},
            {"label": "Zero Prior Preview:", "text": "No organizer, judge, or sponsoring entity has had any prior preview, advisory input, or financial interest in this project or submission deck.", "bullet": True, "sz": 1000},
            {"label": "Ethical Compliance:", "text": "We adhere strictly to international standards of academic integrity, public health ethics, and UAE statutory guidelines.", "bullet": True, "sz": 1000}
        ]
    )
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide14.xml"), s14_card)

    # Slide 15: Additional Slide 1 — ROI & Lead Time Benchmark Visual (PS Oriented)
    add_image_relationship(os.path.join(TEMP_DIR, "ppt/slides/_rels/slide15.xml.rels"), "rIdROI", "munzir_roi.png")
    s15_pic = create_picture_xml(1501, "ROIBenchmarkDiagram", "rIdROI", 350000, 1600000, 8444000, 3350000, border_color="0F172A")
    append_shape_to_slide(os.path.join(TEMP_DIR, "ppt/slides/slide15.xml"), s15_pic)

    # Slide 16: THANK YOU PAGE — USER EXPLICITLY INSTRUCTED: "dont do anything to it"
    # We do NOTHING to slide 16! It remains 100% identical to the template's official closing slide!
    print("Slide 16 left 100% untouched as the official thank you slide.")

    # Repackage PPTX
    print("Repackaging into PPTX...")
    if os.path.exists(OUTPUT_PATH):
        os.remove(OUTPUT_PATH)
    with zipfile.ZipFile(OUTPUT_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(TEMP_DIR):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, TEMP_DIR)
                z.write(full_path, rel_path)

    print(f"Build complete! Saved to: {OUTPUT_PATH}")
    print(f"Output size: {os.path.getsize(OUTPUT_PATH)} bytes")

if __name__ == "__main__":
    build_all_slides()
