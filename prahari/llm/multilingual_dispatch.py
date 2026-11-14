"""
Munzir Multilingual Frontline Dispatch Engine (Phase 17).
Generates localized supervisory and worker WhatsApp cards and spoken voice scripts
in Arabic (العربية), English, Urdu (اردو), and Hindi (हिन्दी).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from prahari.llm.jais_runner import JaisInferenceRunner


@dataclass
class MultilingualDispatchCard:
    """Complete 5-language frontline safety dispatch package."""
    alert_id: str
    site_id: str
    site_name: str
    tier: str
    arabic_text: str
    english_text: str
    urdu_text: str
    hindi_text: str
    audio_tts_scripts: Dict[str, str]  # language_code -> phonetic text
    whatsapp_preview_markdown: str
    malayalam_text: str = ""


def generate_multilingual_dispatch(
    alert_dict: Dict[str, Any],
    jais_runner: Optional[JaisInferenceRunner] = None,
) -> MultilingualDispatchCard:
    """
    Generates a localized multi-language dispatch card powered by Inception 42 Jais conventions.
    Produces formatted text for mobile messaging and audio playback scripts for site foremen.
    """
    if jais_runner is None:
        jais_runner = JaisInferenceRunner()

    site_name = alert_dict.get("site_name", "Jebel Ali Industrial Yard")
    site_id = alert_dict.get("site_id", "SITE-JA-01")
    tier = alert_dict.get("tier", "Warning")
    wbgt = round(alert_dict.get("wbgt", 33.4), 1)
    prob_pct = round(alert_dict.get("calibrated_p", 0.833) * 100.0, 1)

    # 1. Arabic Text (Official sovereign supervisor advisory)
    arabic = (
        f"منصة مُنذِر للإنذار المبكر | تنبيه وقائي ({tier})\n"
        f"الموقع: {site_name}\n"
        f"درجة الحرارة الرطبة المقاسة: {wbgt} درجة مئوية (احتمالية الخطر: {prob_pct}٪)\n"
        f"الإجراء المطلوب: تنفيذاً للقرار الوزاري رقم ٤٤ لسنة ٢٠٢٢، يجب بدء فترات راحة مظللة وتوفير محطات ماء مبرد مع أملاح تعويضية فوراً."
    )

    # 2. English Text (Executive and international contractor standard)
    english = (
        f"MUNZIR EARLY WARNING | Tier: {tier}\n"
        f"Site: {site_name} ({site_id})\n"
        f"Peak WBGT: {wbgt}°C | Outbreak Risk Probability: {prob_pct}%\n"
        f"Mandatory Action: MOHRE Resolution No. 44 of 2022. Deploy 15-minute shaded rest per hour and electrolyte hydration stations."
    )

    # 3. Urdu Text (South Asian labor supervisors, foremen, and safety captains)
    urdu = (
        f"منذر پیشگی وارننگ الرٹ ({tier})\n"
        f"مقام: {site_name}\n"
        f"گرمی اور حبس کی شدت (WBGT): {wbgt}°C (خطرہ: {prob_pct}٪)\n"
        f"ضروری ہدایات: یو اے ای حکومتی فیصلے کے مطابق تمام ورکرز کو ہر گھنٹے بعد ۱۵ منٹ سائے میں آرام اور او آر ایس ملا ٹھنڈا پانی فراہم کریں۔"
    )

    # 4. Hindi Text (Frontline construction and logistics team leads)
    hindi = (
        f"मुन्ज़िर अर्ली वार्निंग अलर्ट ({tier})\n"
        f"स्थान: {site_name}\n"
        f"वेट-बल्ब तापमान (WBGT): {wbgt}°C (जोखिम: {prob_pct}%)\n"
        f"अनिवार्य निर्देश: यूएई श्रम मंत्रालय के नियम अनुसार हर घंटे 15 मिनट छाया में विश्राम दें और ठंडा ओआरएस युक्त पानी तुरंत उपलब्ध कराएं।"
    )

    # 5. Malayalam Text (Kerala workforce supervisors and logistics coordinators)
    malayalam = (
        f"മുൻസിർ മുൻകരുതൽ മുന്നറിയിപ്പ് ({tier})\n"
        f"സ്ഥലം: {site_name}\n"
        f"താപ സൂചിക (WBGT): {wbgt}°C (അപകട സാധ്യത: {prob_pct}%)\n"
        f"നിർദ്ദേശം: യുഎഇ സർക്കാർ ഉത്തരവ് അനുസരിച്ച് തൊഴിലാളികൾക്ക് തണലിൽ വിശ്രമവും ഒ.ആർ.എസ് അടങ്ങിയ തണുത്ത വെള്ളവും ഉടൻ നൽകുക."
    )

    # Audio TTS Phonetic Scripts (Optimized for Web Speech Synthesis API)
    audio_scripts = {
        "ar": f"تنبيه وقائي منذر في {site_name}. يرجى تطبيق فترات الراحة المظللة والترطيب فوراً.",
        "en": f"Munzir preventive warning for {site_name}. Please enforce shaded rest and hydration stations immediately.",
        "ur": f"منذر الرٹ برائے {site_name}۔ برائے مہربانی ورکرز کو سائے میں آرام اور پانی دیں۔",
        "hi": f"मुन्ज़िर सुरक्षा अलर्ट: {site_name} में तुरंत छायादार आराम और ओआरएस पानी उपलब्ध कराएं।",
        "ml": f"മുൻസിർ സുരക്ഷാ മുന്നറിയിപ്പ്: {site_name} ൽ തൊഴിലാളികൾക്ക് തണലിൽ വിശ്രമവും വെള്ളവും നൽകുക.",
    }

    # WhatsApp Styled Preview Markdown
    wa_preview = (
        f"```\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  MUNZIR DISPATCH | {tier.upper()} ALERT  \n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{english}\n\n"
        f"────────────────────────────────────────\n"
        f"{arabic}\n\n"
        f"────────────────────────────────────────\n"
        f"{urdu}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"[ 1-CLICK ACTIONS ]\n"
        f"[ACKNOWLEDGE & START 15M BREAK]  [CONFIRM HYDRATION]\n"
        f"```"
    )

    return MultilingualDispatchCard(
        alert_id=alert_dict.get("alert_id", "ALT-001"),
        site_id=site_id,
        site_name=site_name,
        tier=tier,
        arabic_text=arabic,
        english_text=english,
        urdu_text=urdu,
        hindi_text=hindi,
        audio_tts_scripts=audio_scripts,
        whatsapp_preview_markdown=wa_preview,
        malayalam_text=malayalam,
    )

