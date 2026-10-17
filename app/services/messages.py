"""Fixed UI strings in English, Hindi (Devanagari) and Roman Hindi."""
from __future__ import annotations

from decimal import Decimal

from app.schemas import Language, Period
from app.services.earnings import Summary

MSG: dict[str, dict[str, str]] = {
    "en": {
        "out_of_scope": "I can help with earnings tracking, safety, your rights and welfare schemes, documents, and writing complaints. Please ask about one of these.",
        "no_grounded": "I do not have verified information on this. Please check with your state Labour Department or call the e-Shram helpline 14434.",
        "need_entries": "I could not find an amount. Try: 'Today I earned 850 and spent 200 on petrol'.",
        "saved": "Saved {n} entries.",
        "no_data": "No entries yet for {period}.",
        "grievance_note": "This is a draft to help you write. It is not legal advice. Check every detail before sending.",
        "income": "Income", "expense": "Expenses", "net": "Net", "trips": "Trips",
        "hours": "Hours", "per_hour": "Income per hour",
        "today": "today", "week": "last 7 days", "month": "this month", "all": "all time",
    },
    "hi": {
        "out_of_scope": "मैं कमाई का हिसाब, सुरक्षा, आपके अधिकार और सरकारी योजनाएँ, दस्तावेज़ और शिकायत लिखने में मदद कर सकता हूँ। कृपया इनमें से किसी बारे में पूछें।",
        "no_grounded": "इस बारे में मेरे पास पक्की जानकारी नहीं है। कृपया अपने राज्य के श्रम विभाग से पूछें या ई-श्रम हेल्पलाइन 14434 पर कॉल करें।",
        "need_entries": "मुझे रकम समझ नहीं आई। ऐसे लिखें: 'आज 850 कमाए और 200 का पेट्रोल डाला'।",
        "saved": "{n} एंट्री सेव हो गई।",
        "no_data": "{period} की कोई एंट्री नहीं है।",
        "grievance_note": "यह सिर्फ़ लिखने में मदद के लिए ड्राफ्ट है। यह क़ानूनी सलाह नहीं है। भेजने से पहले हर बात जाँच लें।",
        "income": "कमाई", "expense": "खर्च", "net": "बचत", "trips": "ट्रिप",
        "hours": "घंटे", "per_hour": "प्रति घंटा कमाई",
        "today": "आज", "week": "पिछले 7 दिन", "month": "इस महीने", "all": "अब तक",
    },
    "hinglish": {
        "out_of_scope": "Main kamai ka hisaab, suraksha, aapke adhikar aur sarkari yojana, documents aur shikayat likhne mein madad kar sakta hoon. Inmein se kisi baare mein poochiye.",
        "no_grounded": "Iske baare mein mere paas pakki jaankari nahi hai. Apne rajya ke Shram Vibhag se poochiye ya e-Shram helpline 14434 par call kijiye.",
        "need_entries": "Mujhe rakam samajh nahi aayi. Aise likhiye: 'Aaj 850 kamaye aur 200 ka petrol dala'.",
        "saved": "{n} entry save ho gayi.",
        "no_data": "{period} ki koi entry nahi hai.",
        "grievance_note": "Yeh sirf likhne mein madad ke liye draft hai. Yeh kanooni salah nahi hai. Bhejne se pehle har baat jaanch lijiye.",
        "income": "Kamai", "expense": "Kharcha", "net": "Bachat", "trips": "Trips",
        "hours": "Ghante", "per_hour": "Kamai per ghanta",
        "today": "aaj", "week": "pichhle 7 din", "month": "is mahine", "all": "ab tak",
    },
}


def msg(lang: Language, key: str, **kw: object) -> str:
    return MSG[lang][key].format(**kw)


def money(value: Decimal) -> str:
    return f"₹{value:,.0f}" if value == value.to_integral_value() else f"₹{value:,.2f}"


def format_summary(lang: Language, period: Period, s: Summary) -> str:
    m = MSG[lang]
    lines = [
        f"{m[period]}:",
        f"{m['income']}: {money(s.income)}",
        f"{m['expense']}: {money(s.expense)}",
        f"{m['net']}: {money(s.net)}",
    ]
    if s.trips:
        lines.append(f"{m['trips']}: {s.trips}")
    if s.hours:
        lines.append(f"{m['hours']}: {s.hours.normalize():f}")
    if s.income_per_hour is not None:
        lines.append(f"{m['per_hour']}: {money(s.income_per_hour)}")
    return "\n".join(lines)
