from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover
    PdfReader = None  # type: ignore[assignment]


@dataclass(frozen=True)
class TravelerCandidate:
    id: int
    display_name: str
    english_name: str
    aliases: str


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    confidence: float
    evidence: str


@dataclass(frozen=True)
class TravelerMatch:
    traveler_id: int
    display_name: str
    confidence: float
    evidence: str


@dataclass(frozen=True)
class ExtractedDocument:
    text: str
    page_count: int
    warnings: list[str]


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
    category_confidence: float = 0.0
    detected_travelers: str = ""
    page_count: int = 0


CATEGORY_DEFINITIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "airfare": {
        "strong": ("e-ticket", "eticket", "air ticket", "항공권", "여정안내서", "flight itinerary"),
        "normal": ("flight", "airline", "reservation", "항공", "항공사", "예약번호", "pnr"),
        "filename": ("air", "flight", "ticket", "항공", "비행", "항공권"),
    },
    "boarding_pass": {
        "strong": ("boarding pass", "탑승권", "mobile boarding", "boarding time"),
        "normal": ("gate", "seat", "boarding", "zone", "탑승", "좌석", "게이트"),
        "filename": ("boarding", "boardingpass", "탑승권", "보딩"),
    },
    "lodging": {
        "strong": ("hotel", "accommodation", "lodging", "숙박", "호텔", "guest folio"),
        "normal": ("check-in", "check out", "check-out", "room", "guest", "숙소", "객실", "folio"),
        "filename": ("hotel", "lodging", "accommodation", "숙박", "호텔", "숙소"),
    },
    "conference_registration": {
        "strong": ("conference registration", "registration fee", "학회 등록", "등록비", "symposium registration"),
        "normal": ("conference", "symposium", "workshop", "abstract", "participant", "학회", "초록", "참가"),
        "filename": ("registration", "conference", "symposium", "학회", "등록"),
    },
    "badge": {
        "strong": ("name badge", "name tag", "conference badge", "명찰"),
        "normal": ("badge", "delegate", "participant", "소속", "affiliation"),
        "filename": ("badge", "nametag", "name_tag", "명찰"),
    },
    "meal": {
        "strong": ("restaurant", "cafe", "meal", "식비", "음식점", "영수증"),
        "normal": ("coffee", "카페", "커피", "dining", "receipt", "total", "합계", "결제"),
        "filename": ("meal", "food", "restaurant", "cafe", "식비", "영수증"),
    },
    "transport": {
        "strong": ("taxi", "train", "rail", "bus", "교통", "택시", "철도", "ktx"),
        "normal": ("metro", "subway", "uber", "transport", "transit", "지하철", "버스", "기차"),
        "filename": ("taxi", "train", "bus", "transport", "교통", "택시", "기차"),
    },
}

DATE_PATTERNS = (
    re.compile(r"\b20\d{2}[./-]\d{1,2}[./-]\d{1,2}\b"),
    re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]20\d{2}\b"),
    re.compile(r"20\d{2}\s*년\s*\d{1,2}\s*월\s*\d{1,2}\s*일"),
    re.compile(
        r"\b\d{1,2}\s*(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s*20\d{2}\b",
        re.IGNORECASE,
    ),
)
MONEY_RE = re.compile(
    r"(?:(?:KRW|USD|EUR|JPY|GBP)\s*)?(?:[$€¥₩]\s*)?\d{1,3}(?:,\d{3})+(?:\.\d+)?\s*(?:원|KRW|USD|EUR|JPY|GBP)?|"
    r"(?:KRW|USD|EUR|JPY|GBP)\s*\d+(?:\.\d{2})?",
    re.IGNORECASE,
)


def extract_text(path: Path) -> str:
    return extract_document(path).text


def extract_document(path: Path) -> ExtractedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_document(path)
    if suffix in {".txt", ".csv"}:
        return ExtractedDocument(read_text_file(path).strip(), 1, [])
    if suffix in {".jpg", ".jpeg", ".png", ".heic", ".webp", ".tif", ".tiff"}:
        return ExtractedDocument("", 1, ["image OCR is not enabled; filename and uploader were used only"])
    return ExtractedDocument("", 0, [f"unsupported file extension: {suffix or '(none)'}"])


def extract_pdf_document(path: Path) -> ExtractedDocument:
    if PdfReader is None:
        return ExtractedDocument("", 0, ["pypdf is unavailable"])
    try:
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n".join(pages).strip()
        warnings = [] if text else ["PDF has no extractable text; OCR may be needed"]
        return ExtractedDocument(text, len(reader.pages), warnings)
    except Exception as exc:
        return ExtractedDocument("", 0, [f"PDF text extraction failed: {exc}"])


def read_text_file(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return ""


def classify_document(text: str, filename: str = "") -> str:
    return classify_document_detailed(text, filename).category


def classify_document_detailed(text: str, filename: str = "") -> ClassificationResult:
    haystack = normalize_words(f"{filename}\n{text}")
    file_haystack = normalize_words(filename)
    scores: dict[str, float] = {}
    evidence: dict[str, list[str]] = {}

    for category, groups in CATEGORY_DEFINITIONS.items():
        score = 0.0
        hits: list[str] = []
        for keyword in groups["strong"]:
            if normalize_words(keyword) in haystack:
                score += 3.0
                hits.append(keyword)
        for keyword in groups["normal"]:
            if normalize_words(keyword) in haystack:
                score += 1.4
                hits.append(keyword)
        for keyword in groups["filename"]:
            if normalize_words(keyword) in file_haystack:
                score += 1.8
                hits.append(f"filename:{keyword}")
        if score:
            scores[category] = score
            evidence[category] = hits

    if not scores:
        return ClassificationResult("misc", 0.0, "no category keyword matched")

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    category, score = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    confidence = min(0.99, 0.35 + score / 10.0)
    if runner_up and score - runner_up < 1.0:
        confidence = min(confidence, 0.62)
    hit_text = ", ".join(evidence[category][:5])
    return ClassificationResult(category, round(confidence, 2), f"matched {hit_text}" if hit_text else "matched")


def normalize_words(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = re.sub(r"[_\-./:;,#()[\]{}]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z가-힣]+", "", value, flags=re.UNICODE)


def latin_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z]+", normalize_words(value))


def split_aliases(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,/|]", value or "") if item.strip()]


def raw_name_variants(traveler: TravelerCandidate) -> list[str]:
    raw_names = [traveler.display_name, traveler.english_name, *split_aliases(traveler.aliases)]
    variants: list[str] = []
    for raw in raw_names:
        raw = raw.strip()
        if not raw:
            continue
        variants.append(raw)
        parts = [part for part in re.split(r"\s+", raw) if part]
        if len(parts) >= 2:
            variants.append(" ".join(reversed(parts)))
            initials = "".join(part[0] for part in parts if part)
            variants.append(f"{parts[-1]} {initials}")
            variants.append(f"{initials} {parts[-1]}")
    seen: set[str] = set()
    deduped = []
    for variant in variants:
        key = normalize(variant)
        if key and key not in seen:
            deduped.append(variant)
            seen.add(key)
    return deduped


def name_variants(traveler: TravelerCandidate) -> set[str]:
    return {normalize(item) for item in raw_name_variants(traveler) if normalize(item)}


def score_traveler(text: str, traveler: TravelerCandidate) -> TravelerMatch | None:
    compact_text = normalize(text)
    word_text = normalize_words(text)
    text_tokens = set(latin_tokens(text))
    best_score = 0.0
    best_evidence = ""

    for raw in raw_name_variants(traveler):
        compact_variant = normalize(raw)
        if len(compact_variant) >= 2 and compact_variant in compact_text:
            score = 0.98 if len(compact_variant) >= 5 else 0.92
            if score > best_score:
                best_score = score
                best_evidence = f"exact name: {raw}"

        tokens = latin_tokens(raw)
        meaningful_tokens = [token for token in tokens if len(token) >= 2]
        if len(meaningful_tokens) >= 2 and set(meaningful_tokens).issubset(text_tokens):
            token_span = " ".join(meaningful_tokens)
            contiguous = normalize_words(token_span) in word_text or normalize_words(" ".join(reversed(meaningful_tokens))) in word_text
            score = 0.94 if contiguous else 0.87
            if score > best_score:
                best_score = score
                best_evidence = f"english tokens: {' '.join(meaningful_tokens)}"

        if len(compact_variant) >= 6:
            for window in sliding_windows(compact_text, len(compact_variant)):
                ratio = SequenceMatcher(None, compact_variant, window).ratio()
                if ratio >= 0.92 and 0.82 > best_score:
                    best_score = 0.82
                    best_evidence = f"near match: {raw}"
                    break

    if best_score <= 0:
        return None
    return TravelerMatch(traveler.id, traveler.display_name, round(best_score, 2), best_evidence)


def sliding_windows(value: str, size: int) -> list[str]:
    if size <= 0 or len(value) < size:
        return []
    if len(value) > 3000:
        value = value[:3000]
    return [value[idx : idx + size] for idx in range(0, len(value) - size + 1)]


def detect_travelers(text: str, travelers: list[TravelerCandidate]) -> list[TravelerMatch]:
    matches = [match for traveler in travelers if (match := score_traveler(text, traveler))]
    return sorted(matches, key=lambda item: item.confidence, reverse=True)


def match_traveler(
    text: str,
    travelers: list[TravelerCandidate],
    uploaded_by: str = "",
) -> tuple[int | None, float, str]:
    matches = detect_travelers(text, travelers)
    strong = [match for match in matches if match.confidence >= 0.9]
    if len(strong) == 1:
        match = strong[0]
        return match.traveler_id, match.confidence, match.evidence
    if len(strong) > 1:
        names = ", ".join(match.display_name for match in strong[:5])
        return None, strong[0].confidence, f"multiple travelers detected: {names}"
    if matches:
        match = matches[0]
        return match.traveler_id, match.confidence, match.evidence

    uploaded_by_norm = normalize(uploaded_by)
    if uploaded_by_norm:
        for traveler in travelers:
            if uploaded_by_norm in name_variants(traveler):
                return traveler.id, 0.58, "candidate matched by uploader name"
    return None, 0.0, "no traveler match"


def first_date(text: str) -> str:
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(0).strip()
    return ""


def money_value(raw: str) -> float:
    number = re.search(r"\d[\d,]*(?:\.\d+)?", raw)
    if not number:
        return 0.0
    try:
        return float(number.group(0).replace(",", ""))
    except ValueError:
        return 0.0


def best_amount(text: str) -> str:
    matches = [match.group(0).strip() for match in MONEY_RE.finditer(text)]
    if not matches:
        return ""
    total_nearby = []
    lowered = text.casefold()
    for item in matches:
        idx = lowered.find(item.casefold())
        context = lowered[max(0, idx - 30) : idx + len(item) + 30] if idx >= 0 else ""
        priority = 1 if any(word in context for word in ("total", "합계", "총액", "결제", "amount")) else 0
        total_nearby.append((priority, money_value(item), item))
    return max(total_nearby, key=lambda row: (row[0], row[1]))[2]


def build_status(
    traveler_id: int | None,
    traveler_confidence: float,
    category_confidence: float,
    detected_matches: list[TravelerMatch],
    extraction: ExtractedDocument,
) -> str:
    strong_matches = [match for match in detected_matches if match.confidence >= 0.9]
    if len(strong_matches) > 1:
        return "needs_review"
    if traveler_id is None:
        return "needs_review"
    if traveler_confidence < 0.9:
        return "needs_review"
    if category_confidence < 0.45:
        return "needs_review"
    if extraction.warnings:
        return "needs_review"
    return "auto_matched"


def analyze_document(
    path: Path,
    travelers: list[TravelerCandidate],
    uploaded_by: str = "",
) -> AnalysisResult:
    extraction = extract_document(path)
    combined = f"{path.name}\n{extraction.text}"
    classification = classify_document_detailed(combined, path.name)
    detected_matches = detect_travelers(combined, travelers)
    traveler_id, confidence, traveler_reason = match_traveler(combined, travelers, uploaded_by)
    status = build_status(traveler_id, confidence, classification.confidence, detected_matches, extraction)
    detected_text = "; ".join(
        f"{match.display_name}:{match.confidence:.2f}" for match in detected_matches[:8]
    )
    notes_parts = [
        f"category {classification.confidence:.2f}: {classification.evidence}",
        f"traveler {confidence:.2f}: {traveler_reason}",
    ]
    notes_parts.extend(extraction.warnings)
    return AnalysisResult(
        extracted_text=extraction.text[:20000],
        category=classification.category,
        matched_traveler_id=traveler_id,
        match_confidence=confidence,
        status=status,
        date_hint=first_date(combined),
        amount_hint=best_amount(combined),
        notes="; ".join(part for part in notes_parts if part),
        category_confidence=classification.confidence,
        detected_travelers=detected_text,
        page_count=extraction.page_count,
    )
