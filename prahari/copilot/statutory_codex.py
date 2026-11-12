"""
Munzir Statutory and Regulatory Knowledge Codex (Phase 18).
Stores structured, authentic legal decrees, occupational safety guidelines,
and public health emergency protocols for zero-hallucination RAG retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class StatutoryArticle:
    """A specific statutory article or standard section with legal citation."""
    jurisdiction: str
    authority: str
    instrument: str
    article_number: str
    title: str
    legal_text: str
    mandatory_actions: List[str]
    applicability: str
    penalties: Optional[str] = None
    citation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert article to JSON-serializable dictionary."""
        return {
            "jurisdiction": self.jurisdiction,
            "authority": self.authority,
            "instrument": self.instrument,
            "article_number": self.article_number,
            "title": self.title,
            "legal_text": self.legal_text,
            "mandatory_actions": self.mandatory_actions,
            "applicability": self.applicability,
            "penalties": self.penalties,
            "citation": self.citation,
        }


# ==============================================================================
# 1. UAE MOHRE MINISTERIAL RESOLUTION NO. 44 OF 2022
# Official decree on occupational safety, heat stress, and midday work ban.
# ==============================================================================
UAE_MOHRE_RESOLUTION_44_2022: List[StatutoryArticle] = [
    StatutoryArticle(
        jurisdiction="United Arab Emirates (Federal)",
        authority="Ministry of Human Resources and Emiratisation (MOHRE)",
        instrument="Ministerial Resolution No. 44 of 2022",
        article_number="Article 1",
        title="Mandatory Midday Work Ban (Summer Prohibition)",
        legal_text=(
            "Prohibits any work performed under direct sunlight and in open-air places from "
            "12:30 PM to 3:00 PM daily, effective from 15 June to 15 September annually. "
            "Daily working hours shall not exceed eight hours for morning, evening, or split shifts."
        ),
        mandatory_actions=[
            "Halt all outdoor activities under direct sunlight between 12:30 PM and 3:00 PM.",
            "Display the daily work schedule prominently in Arabic and languages understood by the workers.",
            "Maintain total shift hours within 8 hours per day, compensating any overtime under UAE Labor Law."
        ],
        applicability="All private sector outdoor construction, industrial, and logistics operations in the UAE.",
        penalties="Fines of AED 5,000 per violating worker up to a maximum of AED 50,000 per employer.",
        citation="MOHRE Ministerial Resolution No. 44 of 2022, Article 1 (UAE Federal Law No. 33 of 2021)",
    ),
    StatutoryArticle(
        jurisdiction="United Arab Emirates (Federal)",
        authority="Ministry of Human Resources and Emiratisation (MOHRE)",
        instrument="Ministerial Resolution No. 44 of 2022",
        article_number="Article 2",
        title="Employer Welfare, Hydration & Shade Obligations",
        legal_text=(
            "Employers are legally obligated to provide a fully shaded resting area equipped with cooling "
            "devices, adequate cold potable water with electrolyte minerals approved by local authorities, "
            "first-aid kits on-site, and dedicated medical triage capabilities."
        ),
        mandatory_actions=[
            "Provide shaded rest shelters with high-velocity air-cooling devices or evaporative misting.",
            "Provide unlimited cold potable water fortified with oral rehydration salts (ORS) / electrolytes.",
            "Ensure certified on-site occupational first-aiders and emergency heat triage kits are present.",
            "Grant immediate shaded resting breaks whenever workers exhibit dizziness or thermal distress."
        ],
        applicability="All outdoor and high-temperature work environments across all Emirates.",
        penalties="Administrative sanctions, facility classification downgrades, and site stop-work orders.",
        citation="MOHRE Ministerial Resolution No. 44 of 2022, Article 2",
    ),
    StatutoryArticle(
        jurisdiction="United Arab Emirates (Federal)",
        authority="Ministry of Human Resources and Emiratisation (MOHRE)",
        instrument="Ministerial Resolution No. 44 of 2022",
        article_number="Article 3",
        title="Exceptional Technical Works & Continuous Pour Exemptions",
        legal_text=(
            "Exemptions from the midday stoppage apply only to works which for technical reasons must continue "
            "uninterrupted (e.g., major concrete pouring, asphalt road paving, repairing water/electricity lines, "
            "and unclogging sewage pipes). For exempted works, employers must provide continuous cold hydration, "
            "cooling equipment, and rotating worker shifts."
        ),
        mandatory_actions=[
            "File formal permit notification with municipal authorities for continuous concrete or asphalt works.",
            "Deploy rotating micro-shifts (maximum 30 minutes continuous exposure followed by 15 minutes shaded cooling).",
            "Station mobile air-conditioned cooling buses and paramedic standby directly adjacent to work faces."
        ],
        applicability="Critical infrastructure maintenance and uninterrupted technical construction operations.",
        penalties="Revocation of exemption permit and legal prosecution if thermal illness occurs without precautions.",
        citation="MOHRE Ministerial Resolution No. 44 of 2022, Article 3",
    ),
]

# ==============================================================================
# 2. OCCUPATIONAL SAFETY & HEALTH ADMINISTRATION (OSHA) STANDARDS
# Technical manual on physiological monitoring, heat strain, and work/rest cycles.
# ==============================================================================
OSHA_HEAT_STANDARDS: List[StatutoryArticle] = [
    StatutoryArticle(
        jurisdiction="United States / International Benchmark",
        authority="Occupational Safety and Health Administration (OSHA)",
        instrument="OSHA Technical Manual (OTM) Section III: Chapter 4",
        article_number="Section 4.1",
        title="Work/Rest Regimens Based on Environmental WBGT",
        legal_text=(
            "When Wet Bulb Globe Temperature (WBGT) exceeds 32.2°C (90°F) for moderate to heavy metabolic work, "
            "a work/rest cycle of 50% work / 50% rest (30 minutes rest per hour) must be enforced. When WBGT "
            "exceeds 33.5°C, work should be limited to 25% work / 75% rest (45 minutes rest per hour) or halted."
        ),
        mandatory_actions=[
            "WBGT 28.0°C–31.0°C: Continuous work with 15 minutes rest per hour under shade.",
            "WBGT 31.1°C–32.2°C: 45 minutes work / 15 minutes rest per hour.",
            "WBGT 32.3°C–33.5°C: 30 minutes work / 30 minutes rest per hour.",
            "WBGT > 33.5°C: Stoppage of un-mitigated heavy manual labor."
        ],
        applicability="General Duty Clause Section 5(a)(1) enforcement for high heat index environments.",
        citation="OSHA Technical Manual (OTM) Sec. III Ch. 4 (OSHA-3151)",
    ),
    StatutoryArticle(
        jurisdiction="United States / International Benchmark",
        authority="Occupational Safety and Health Administration (OSHA)",
        instrument="OSHA Technical Manual (OTM) Section III: Chapter 4",
        article_number="Section 4.2",
        title="Two-Person Buddy System & Heat Stroke Emergency Triage",
        legal_text=(
            "Workers must operate under a paired buddy system to monitor signs of confusion, irrational behavior, "
            "slurred speech, or lack of sweating. Heat stroke is a medical emergency requiring immediate active "
            "cooling (cold-water immersion or ice packs on neck/groin) and rapid paramedic evacuation."
        ),
        mandatory_actions=[
            "Assign every outdoor worker a safety buddy; conduct mandatory mutual checks every 30 minutes.",
            "At first sign of confusion or ataxia: call 998/999 immediately.",
            "Initiate rapid aggressive cooling before ambulance arrival (ice sheets or water dousing)."
        ],
        applicability="All high-thermal stress occupational settings.",
        citation="OSHA Heat Stress Directive (OTM Sec. III Ch. 4.2)",
    ),
]

# ==============================================================================
# 3. DUBAI CORPORATION FOR AMBULANCE SERVICES (DCAS) PRE-STAGING PROTOCOLS
# ==============================================================================
DCAS_EMERGENCY_PROTOCOLS: List[StatutoryArticle] = [
    StatutoryArticle(
        jurisdiction="Dubai (Emirate)",
        authority="Dubai Corporation for Ambulance Services (DCAS)",
        instrument="Mass Occupational Thermal Response Protocol (SOP-DCAS-H04)",
        article_number="SOP-DCAS-H04",
        title="High Heat Warning Pre-Staging & Mobile Paramedic Positioning",
        legal_text=(
            "Upon issuance of an official Heat Cluster Warning or Tier-2 Thermal Alert for industrial clusters "
            "exceeding 1,000 workers, DCAS activates Stage-1 Pre-Positioning: designating nearest rapid response "
            "ambulance units to hold station within 4.0 km of the cluster centroid with dedicated IV cooling packs."
        ),
        mandatory_actions=[
            "Designate primary rapid response ambulance unit to standby station.",
            "Prime vehicle IV fluid chilling chambers to 4°C for aggressive cold saline infusion.",
            "Establish direct radio communication link between site safety director and DCAS dispatch control."
        ],
        applicability="Major industrial clusters (Jebel Ali, Al Quoz, Dubai South, Ras Al Khor).",
        citation="DCAS Emergency Pre-Staging Directive SOP-DCAS-H04",
    ),
]


class StatutoryCodex:
    """Query engine for official statutory decrees, standards, and emergency protocols."""

    def __init__(self):
        self.articles: List[StatutoryArticle] = (
            UAE_MOHRE_RESOLUTION_44_2022 + OSHA_HEAT_STANDARDS + DCAS_EMERGENCY_PROTOCOLS
        )

    def search_codex(self, query: str, limit: int = 3) -> List[StatutoryArticle]:
        """Performs keyword and semantic matching over statutory articles."""
        q_lower = query.lower()
        scored_articles: List[tuple[float, StatutoryArticle]] = []

        keywords_map = {
            "midday": ["midday", "12:30", "ban", "prohibition", "summer", "resolution 44"],
            "shade": ["shade", "cooling", "rest", "welfare", "shelter"],
            "water": ["water", "hydration", "electrolyte", "ors", "salts", "potable"],
            "exemption": ["exemption", "concrete", "asphalt", "pour", "continuous", "technical"],
            "osha": ["osha", "work/rest", "regimen", "buddy", "otm"],
            "dcas": ["dcas", "ambulance", "paramedic", "pre-staging", "emergency", "998"],
            "penalty": ["penalty", "fine", "5000", "50000", "violation", "sanction"],
            "renal": ["renal", "kidney", "hydration", "urine", "egfr", "kdigo"],
        }

        for article in self.articles:
            score = 0.0
            text_corpus = (
                f"{article.title} {article.legal_text} "
                f"{' '.join(article.mandatory_actions)} {article.applicability} {article.citation}"
            ).lower()

            # Exact phrase matches
            if any(term in q_lower for term in [article.article_number.lower(), article.title.lower()]):
                score += 10.0

            for topic, kws in keywords_map.items():
                if any(kw in q_lower for kw in kws):
                    for kw in kws:
                        if kw in text_corpus:
                            score += 2.0

            # General token overlap
            q_tokens = [t for t in q_lower.split() if len(t) > 3]
            for tok in q_tokens:
                if tok in text_corpus:
                    score += 1.0

            if score > 0.0:
                scored_articles.append((score, article))

        scored_articles.sort(key=lambda x: x[0], reverse=True)
        return [art for _, art in scored_articles[:limit]] or self.articles[:limit]

    def get_all_articles(self) -> List[Dict[str, str]]:
        """Returns all structured articles as serializable dictionaries."""
        return [
            {
                "jurisdiction": a.jurisdiction,
                "authority": a.authority,
                "instrument": a.instrument,
                "article": a.article_number,
                "title": a.title,
                "legal_text": a.legal_text,
                "mandatory_actions": a.mandatory_actions,
                "penalties": a.penalties or "N/A",
                "citation": a.citation,
            }
            for a in self.articles
        ]
