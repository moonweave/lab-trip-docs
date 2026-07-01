from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "airfare": ("e-ticket", "eticket", "air ticket", "itinerary", "항공권", "항공", "flight"),
    "boarding_pass": ("boarding pass", "탑승권", "gate", "seat", "boarding"),
    "lodging": ("hotel", "accommodation", "lodging", "숙박", "호텔", "guesthouse"),
    "conference_registration": (
        "registration",
        "conference",
        "symposium",
        "학회",
        "등록비",
        "초록",
    ),
    "badge": ("badge", "name tag", "nametag", "명찰", "name badge"),
    "meal": ("restaurant", "cafe", "meal", "식비", "음식", "카페", "커피"),
    "transport": ("taxi", "train", "rail", "bus", "교통", "택시", "철도", "ktx"),
}

DATE_RE = re.compile(r"\b(20\d{2}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]20\d{2})\b")
MONEY_RE = re.compile(
    r"(?:(?:KRW|USD|EUR|JPY)\s*)?(?:[$€¥₩]\s*)?\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*(?:원|KRW|USD|EUR|JPY)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TravelerCandidate:
    id: int
    display_name: str
    english_name: str
    aliases: str


@dataclass(frozen=True)
class AnalysisResult:
    extracted_text: str
    category: str
    matched_traveler_id: int | None
    match_confidence: float
    status: str
    date_hint: str
    amount_hint: str
    notes: str


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_text(path)
    if suffix in {".txt", ".csv"}:
        return read_text_file(path)
    return ""


def extract_pdf_text(path: Path) -> str:
    if PdfReader is None:
        return ""
    try:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages).strip()
    except Exception:
        return ""


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return ""


def classify_document(text: str, filename: str = "") -> str:
    haystack = f"{filename}\n{text}".lower()
    scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword.lower() in haystack)
        if score:
            scores[category] = score
    if not scores:
        return "misc"
    return max(scores.items(), key=lambda item: item[1])[0]


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    return re.sub(r"[\s\W_]+", "", value, flags=re.UNICODE)


def name_variants(traveler: TravelerCandidate) -> set[str]:
    raw_names = [traveler.display_name, traveler.english_name]
    raw_names.extend(re.split(r"[;,/|]", traveler.aliases or ""))
    variants: set[str] = set()
    for raw in raw_names:
        raw = raw.strip()
        if not raw:
            continue
        variants.add(normalize(raw))
        parts = [part for part in re.split(r"\s+", raw) if part]
        if len(parts) >= 2:
            variants.add(normalize(" ".join(reversed(parts))))
    return {item for item in variants if item}


def match_traveler(
    text: str,
    travelers: list[TravelerCandidate],
    uploaded_by: str = "",
) -> tuple[int | None, float, str]:
    normalized_text = normalize(text)
    for traveler in travelers:
        for variant in sorted(name_variants(traveler), key=len, reverse=True):
            if variant and variant in normalized_text:
                return traveler.id, 0.95, "matched by document text"

    normalized_uploader = normalize(uploaded_by)
    if normalized_uploader:
        for traveler in travelers:
            if normalized_uploader in name_variants(traveler):
                return traveler.id, 0.55, "candidate matched by uploader name"

    return None, 0.0, "no traveler match"


def first_match(pattern: re.Pattern[str], text: str) -> str:
    match = pattern.search(text)
    return match.group(0).strip() if match else ""


def analyze_document(
    path: Path,
    travelers: list[TravelerCandidate],
    uploaded_by: str = "",
) -> AnalysisResult:
    text = extract_text(path)
    combined = f"{path.name}\n{text}"
    category = classify_document(combined, path.name)
    traveler_id, confidence, reason = match_traveler(combined, travelers, uploaded_by)
    status = "auto_matched" if confidence >= 0.9 else "needs_review"
    if not text:
        reason = f"{reason}; no extractable text or OCR not enabled"
        status = "needs_review"
    return AnalysisResult(
        extracted_text=text[:20000],
        category=category,
        matched_traveler_id=traveler_id,
        match_confidence=confidence,
        status=status,
        date_hint=first_match(DATE_RE, combined),
        amount_hint=first_match(MONEY_RE, combined),
        notes=reason,
    )

