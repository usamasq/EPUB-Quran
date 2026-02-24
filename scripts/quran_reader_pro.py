import argparse
import io
import json
import os
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from ebooklib import epub

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

INPUT_JSON = os.path.join(PROJECT_ROOT, "data", "indopak.json")
RUKU_MAP_JSON = os.path.join(PROJECT_ROOT, "data", "ruku_starts.json")
FONT_PATH = os.path.join(PROJECT_ROOT, "assets", "fonts", "AlQalam-Quran-IndoPak.ttf")
COVER_PATH = os.path.join(PROJECT_ROOT, "assets", "cover.png")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "releases")

# =========================
# EPUB METADATA CONFIGURATION
# =========================
BOOK_TITLE = "القرآن الكريم"
BOOK_LANGUAGE = "ar"
BOOK_IDENTIFIER = "holy-quran"
BOOK_AUTHOR = "Usama Bin Shahid (Compiler), Tarteel QUL (Text)"
BOOK_PUBLISHER = "Usama Bin Shahid"

ARABIC_END_MARK = "\u06DD"
SAJDAH_SYMBOL = "\u06E9"
RUB_EL_HIZB_SYMBOL = "\u06DE"
HAIR_SPACE = "\u200A"
QURANIC_MARK_PAIR_RE = re.compile(r"([\u06D6-\u06ED])([\u06D6-\u06ED])")
TRAILING_AYAH_DIGITS_RE = re.compile(r"\s*[\u0660-\u0669\u06F0-\u06F90-9]+\s*$")
PUA_RE = re.compile(r"[\uE000-\uF8FF]")


@dataclass(frozen=True)
class BuildTarget:
    key: str
    label: str
    output_name: str
    profile: str  # enhanced | compat
    variant: str  # full | lite
    split_threshold: int
    show_juz: bool = True
    show_ruku: bool = True
    show_sajdah: bool = True


BUILD_TARGETS = {
    "full": BuildTarget(
        key="full",
        label="Full Edition (Enhanced)",
        output_name="Holy_Quran_full.epub",
        profile="enhanced",
        variant="full",
        split_threshold=0,
    ),
    "full_compat": BuildTarget(
        key="full_compat",
        label="Full Edition (Compatibility)",
        output_name="Holy_Quran_full_compat.epub",
        profile="compat",
        variant="full",
        split_threshold=110,
    ),
    "lite": BuildTarget(
        key="lite",
        label="Lite Edition (Enhanced)",
        output_name="Holy_Quran_lite.epub",
        profile="enhanced",
        variant="lite",
        split_threshold=90,
    ),
    "lite_compat": BuildTarget(
        key="lite_compat",
        label="Lite Edition (Compatibility)",
        output_name="Holy_Quran_lite_compat.epub",
        profile="compat",
        variant="lite",
        split_threshold=70,
    ),
}
DEFAULT_TARGET_KEYS = ["full", "full_compat", "lite", "lite_compat"]


# =========================
# HELPERS
# =========================
def to_arabic_number(n):
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    return "".join(arabic_digits[int(d)] for d in str(n))


def load_json_map(filename):
    try:
        with open(filename, encoding="utf-8") as f:
            raw = json.load(f)
        return {int(k): tuple(v) for k, v in raw.items()}
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Related markers will be skipped.")
        return {}


def normalize_ayah_text(text):
    strip_chars = [
        ARABIC_END_MARK,
        "\ufeff",
        "\u200f",
        "\u200b",
        "\u2002",
        "\u2003",
        "\u200c",
        "\u200d",
    ]
    for char_to_strip in strip_chars:
        text = text.replace(char_to_strip, "")

    text = TRAILING_AYAH_DIGITS_RE.sub("", text)
    text = PUA_RE.sub("", text)

    # Keep all consecutive Quranic marks visible by separating each pair.
    while True:
        updated = QURANIC_MARK_PAIR_RE.sub(rf"\1{HAIR_SPACE}\2", text)
        if updated == text:
            break
        text = updated

    return text


def collect_font_charset(structured):
    chars = set()

    for surah in structured.values():
        for ayah_words in surah.values():
            chars.update(normalize_ayah_text(" ".join(ayah_words)))

    chars.update(BOOK_TITLE)
    chars.update("بِسۡمِ اللهِ الرَّحۡمٰنِ الرَّحِيۡمِ")
    chars.update("الجزءع")
    chars.update("۩۞")
    chars.update("٠١٢٣٤٥٦٧٨٩")

    for name in SURAH_NAMES.values():
        chars.update(name)

    return "".join(sorted(chars))


def prepare_font_content(structured, subset_font):
    if not os.path.exists(FONT_PATH):
        return None

    with open(FONT_PATH, "rb") as f:
        full_content = f.read()

    if not subset_font:
        print("[FONT] Using full embedded font.")
        return full_content

    try:
        from fontTools import subset
    except ImportError:
        print("[FONT] fontTools not installed; using full embedded font.")
        return full_content

    try:
        options = subset.Options()
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.name_languages = ["*"]
        options.notdef_outline = True
        options.recommended_glyphs = True
        options.glyph_names = True
        options.hinting = True

        font = subset.load_font(FONT_PATH, options)
        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text=collect_font_charset(structured))
        subsetter.subset(font)

        buffer = io.BytesIO()
        subset.save_font(font, buffer, options)
        data = buffer.getvalue()
        print(f"[FONT] Embedded subset font generated ({len(data)} bytes).")
        return data
    except Exception as exc:
        print(f"[FONT] Failed to subset font ({exc}); using full embedded font.")
        return full_content


def stylize_special_symbols(text, target):
    has_sajdah_symbol = SAJDAH_SYMBOL in text
    text = text.replace(RUB_EL_HIZB_SYMBOL, '<span class="rub-el-hizb">۞</span>')
    if target.show_sajdah:
        text = text.replace(SAJDAH_SYMBOL, '<span class="sajdah">۩</span>')
    return text, has_sajdah_symbol


def load_data():
    with open(INPUT_JSON, encoding="utf-8") as f:
        raw = json.load(f)

    structured = defaultdict(lambda: defaultdict(list))
    for key in sorted(raw.keys(), key=lambda x: tuple(map(int, x.split(":")))):
        item = raw[key]
        s = int(item["surah"])
        a = int(item["ayah"])
        structured[s][a].append(item["text"])

    return structured


# =========================
# QURAN MAPS
# =========================
from quran_maps import SURAH_NAMES, JUZ_LOOKUP, SAJDAH_VERSES

RUKU_MAP = load_json_map(RUKU_MAP_JSON)


def build_ruku_metadata(surah_last_ayah):
    ruku_ends = {}
    surah_ruku_totals = defaultdict(int)
    surah_ruku_index = defaultdict(int)
    ruku_starts_list = sorted(RUKU_MAP.items())  # [(global_ruku_num, (surah, ayah)), ...]

    for _, (surah, _) in ruku_starts_list:
        surah_ruku_totals[surah] += 1

    for idx, (_, (surah, _)) in enumerate(ruku_starts_list):
        surah_ruku_index[surah] += 1

        if idx + 1 < len(ruku_starts_list):
            _, (next_surah, next_ayah) = ruku_starts_list[idx + 1]
            if next_surah == surah:
                ending_ayah = next_ayah - 1
            else:
                ending_ayah = surah_last_ayah.get(surah)
        else:
            ending_ayah = surah_last_ayah.get(surah)

        if ending_ayah is not None:
            ruku_ends[(surah, ending_ayah)] = surah_ruku_index[surah]

    single_ruku_surahs = {s for s, total in surah_ruku_totals.items() if total <= 1}
    return ruku_ends, single_ruku_surahs


def plan_surah_sections(structured, split_threshold):
    """
    Returns:
      - section_plan: {surah: [section_dict, ...]}
      - ayah_to_file: {(surah, ayah): file_name}
      - surah_first_file: {surah: file_name}
    """
    section_plan = {}
    ayah_to_file = {}
    surah_first_file = {}

    for surah in sorted(structured.keys()):
        ayah_numbers = sorted(structured[surah].keys())
        if split_threshold > 0 and len(ayah_numbers) > split_threshold:
            chunks = [ayah_numbers[i : i + split_threshold] for i in range(0, len(ayah_numbers), split_threshold)]
        else:
            chunks = [ayah_numbers]

        sections = []
        total_parts = len(chunks)
        for idx, chunk in enumerate(chunks, 1):
            if total_parts == 1:
                file_name = f"surah_{surah}.xhtml"
            else:
                file_name = f"surah_{surah}_p{idx}.xhtml"

            section = {
                "file_name": file_name,
                "ayah_numbers": chunk,
                "part_index": idx,
                "total_parts": total_parts,
                "is_first": idx == 1,
            }
            sections.append(section)
            for ayah in chunk:
                ayah_to_file[(surah, ayah)] = file_name

        section_plan[surah] = sections
        surah_first_file[surah] = sections[0]["file_name"]

    return section_plan, ayah_to_file, surah_first_file


# =========================
# RENDERING
# =========================
def build_css(target):
    quran_font_size = "1.56em" if target.variant == "full" else "1.48em"
    quran_line_height = "3.0" if target.variant == "full" else "2.8"
    body_margin = "3% 5%" if target.variant == "full" else "2.8% 4.2%"
    body_text = "#111111"
    bg_color = "#fdfcf8"
    card_bg = "#ffffff"
    accent = "#174d35"
    accent_soft = "#2a7d5e"

    if target.profile == "compat":
        advanced_typography = ""
    else:
        advanced_typography = """
    font-feature-settings: "liga" 1, "ccmp" 1, "kern" 1;
    text-rendering: optimizeLegibility;
"""

    return f"""
@font-face {{
    font-family: 'AlQalamIndoPak';
    src: local('AlQalam Quran IndoPak'),
         local('AlQalam-Quran-IndoPak'),
         url('fonts/AlQalam-Quran-IndoPak.ttf') format('truetype');
    font-display: swap;
    font-weight: normal;
    font-style: normal;
}}

html, body {{
    direction: rtl;
    margin: 0;
    padding: 0;
}}

body {{
    font-family: 'AlQalamIndoPak', 'Amiri', 'Scheherazade New', serif;
    margin: {body_margin};
    color: {body_text};
    background-color: {bg_color};
    -webkit-hyphens: none;
    hyphens: none;
}}

.main-wrapper {{
    direction: rtl;
    text-align: right;
}}

h1 {{
    text-align: center;
    color: {accent};
    margin: 1.2em 0 0.9em;
    font-size: 2.12em;
    letter-spacing: 0.02em;
}}

.bismillah {{
    text-align: center;
    font-size: 1.75em;
    margin-bottom: 1.3em;
    color: #0f3425;
    line-height: 2;
}}

.juz-marker {{
    display: block;
    text-align: center;
    font-size: 1.06em;
    margin: 1em 0;
    color: {accent_soft};
    font-weight: bold;
    border-bottom: 1px solid #d3ddd8;
    padding-bottom: 0.32em;
    clear: both;
}}

.ruku-marker {{
    display: inline-block;
    color: {accent};
    margin: 0 0.42em;
    font-size: 0.82em;
    vertical-align: middle;
    font-weight: bold;
    border: 1px solid #b7c9c1;
    border-radius: 50%;
    width: 1.64em;
    height: 1.64em;
    line-height: 1.64em;
    text-align: center;
}}

.sajdah {{
    color: #8a1414;
    font-size: 1.18em;
    margin: 0 0.34em;
    font-weight: bold;
    vertical-align: middle;
}}

.rub-el-hizb {{
    color: #575f17;
    font-size: 1.06em;
    margin: 0 0.15em;
    vertical-align: baseline;
}}

.ayah-end {{
    white-space: nowrap;
    margin-right: 0.2em;
    font-size: 0.98em;
}}

.ayah-anchor {{
    display: inline;
}}

.quran-text {{
    direction: rtl;
    text-align: right;
    text-justify: auto;
    line-height: {quran_line_height};
    font-size: {quran_font_size};
    word-spacing: 0;
    letter-spacing: normal;
    word-break: keep-all;
    overflow-wrap: normal;
{advanced_typography}
}}

.part-title {{
    text-align: center;
    font-size: 1em;
    color: #5f665f;
    margin: 0 0 1.1em;
}}

.surah-separator {{
    text-align: center;
    font-size: 1.2em;
    color: #b5beb9;
    margin: 1.8em 0 1.4em;
    letter-spacing: 0.3em;
    page-break-before: always;
}}

.title-page {{
    text-align: center;
    margin-top: 28%;
}}

.main-title {{
    font-size: 3.2em;
    color: {accent};
    margin-bottom: 0.14em;
}}

.edition-badge {{
    direction: ltr;
    display: inline-block;
    font-family: 'Noto Sans', sans-serif;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border: 1px solid #c6d5ce;
    color: #375447;
    padding: 0.26em 0.8em;
    border-radius: 999px;
    margin-bottom: 1.1em;
    font-size: 0.74em;
}}

.ornament {{
    font-size: 2em;
    color: #8d9b95;
    margin: 0.6em 0;
}}

.credits-page {{
    direction: ltr;
    text-align: left;
    font-family: 'Noto Sans', sans-serif;
    margin: 4% 2%;
    color: #25302d;
    line-height: 1.66;
}}

.credits-header {{
    border-bottom: 1px solid #cfd9d4;
    padding-bottom: 0.8em;
    margin-bottom: 1.6em;
}}

.credits-title {{
    font-size: 1.65em;
    color: #103828;
    margin-bottom: 0.25em;
}}

.credits-sub {{
    color: #50635c;
    font-size: 0.96em;
}}

.signature {{
    background: #eef4f1;
    border: 1px solid #d5e3dc;
    border-left: 4px solid {accent};
    border-radius: 10px;
    padding: 0.85em 0.95em;
    margin: 1em 0 1.5em;
}}

.signature strong {{
    color: #123e2c;
}}

.credit-grid {{
    display: block;
}}

.credit-card {{
    background: {card_bg};
    border: 1px solid #d9e2dd;
    border-radius: 12px;
    padding: 0.95em 1em;
    margin-bottom: 0.8em;
}}

.credit-card h3 {{
    margin: 0 0 0.25em;
    font-size: 1.02em;
    color: #1a4c37;
}}

.build-meta {{
    margin-top: 1.4em;
    color: #61726b;
    font-size: 0.88em;
    border-top: 1px dashed #d7dfdb;
    padding-top: 0.8em;
}}

.index-list {{
    margin: 0.8em 3%;
    line-height: 2;
}}

.index-item {{
    margin-bottom: 0.4em;
    font-size: 1.13em;
    border-bottom: 1px solid #e0e5e3;
    padding-bottom: 0.35em;
}}

.index-link {{
    text-decoration: none;
    color: inherit;
}}

@media (prefers-color-scheme: dark) {{
    body {{
        color: #e8efec;
        background-color: #0f1714;
    }}
    h1, .main-title {{
        color: #90c8ae;
    }}
    .bismillah {{
        color: #c7e8d9;
    }}
    .juz-marker {{
        color: #9ad7b9;
        border-bottom-color: #2d4b3f;
    }}
    .ruku-marker {{
        color: #abdbc5;
        border-color: #3b6251;
    }}
    .credits-page {{
        color: #cfddda;
    }}
    .credits-header {{
        border-bottom-color: #274136;
    }}
    .signature {{
        background: #13201b;
        border-color: #2a4338;
    }}
    .credit-card {{
        background: #131d19;
        border-color: #2a3f36;
    }}
    .build-meta {{
        border-top-color: #264238;
        color: #a6b9b2;
    }}
}}
"""


def build_title_html(target):
    return f"""<html>
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>Title Page</title></head>
<body><div class="main-wrapper">
    <div class="title-page">
        <div class="edition-badge">{target.label}</div>
        <div class="ornament">﴾ ❖ ﴿</div>
        <h1 class="main-title">{BOOK_TITLE}</h1>
        <div class="ornament">﴾ ❖ ﴿</div>
    </div>
</div></body></html>"""


def build_credits_html(target):
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<html>
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>Attribution & Credits</title></head>
<body><div class="main-wrapper" dir="ltr">
    <div class="credits-page">
        <div class="credits-header">
            <div class="credits-title">Attribution & Publication Credits</div>
            <div class="credits-sub">Professional digital publication record for this Quran EPUB edition.</div>
        </div>
        <div class="signature">
            Compiled, engineered, and curated by <strong>Usama Bin Shahid</strong>.<br/>
            This edition is optimized for practical Quran reading across Kindle and Android EPUB engines.
        </div>
        <div class="credit-grid">
            <div class="credit-card">
                <h3>Quran Text Source</h3>
                The authentic Indo-Pak Quranic text used in this publication is sourced from
                <a href="https://qul.tarteel.ai/">Tarteel QUL</a>.
            </div>
            <div class="credit-card">
                <h3>Structural Mapping</h3>
                Juz and Ruku boundary mapping support was prepared using reference data from
                <a href="https://alquran.cloud/">AlQuran.cloud</a>.
            </div>
            <div class="credit-card">
                <h3>Typeface</h3>
                Arabic text is rendered using the embedded AlQalam Quran IndoPak font for
                consistent script behavior on constrained e-reader engines.
            </div>
            <div class="credit-card">
                <h3>Edition Profile</h3>
                {target.label}
            </div>
        </div>
        <div class="build-meta">
            Publisher: {BOOK_PUBLISHER}<br/>
            Build: {built_at}<br/>
            License: MIT
        </div>
    </div>
</div></body></html>"""


def build_surah_section_html(surah_num, ayahs, section, target, ruku_ends, single_ruku_surahs):
    arabic_num = to_arabic_number(surah_num)
    surah_name = SURAH_NAMES.get(surah_num, f"Surah {surah_num}")
    title = f"{arabic_num}. {surah_name}"
    if section["total_parts"] > 1:
        title = f"{title} (Part {section['part_index']}/{section['total_parts']})"

    html = f"""<html>
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>{title}</title></head>
<body><div class="main-wrapper">"""

    if section["is_first"]:
        html += f"<h1>{arabic_num}. {surah_name}</h1>"
        if surah_num > 1:
            html += '<div class="surah-separator">✦ ✦ ✦</div>'
        if surah_num not in [1, 9]:
            html += '<div class="bismillah" dir="rtl">بِسۡمِ اللهِ الرَّحۡمٰنِ الرَّحِيۡمِ</div>'
    else:
        html += (
            f'<div class="part-title">{surah_name} — Part {section["part_index"]} '
            f'of {section["total_parts"]}</div>'
        )

    html += '<div class="quran-text">'

    for ayah_num in section["ayah_numbers"]:
        indicators_html = ""
        if target.show_juz and (surah_num, ayah_num) in JUZ_LOOKUP:
            indicators_html += (
                f'<div class="juz-marker">'
                f'الجزء {to_arabic_number(JUZ_LOOKUP[(surah_num, ayah_num)])}'
                f"</div>"
            )

        if indicators_html:
            html += f'</div>{indicators_html}<div class="quran-text">'

        text = normalize_ayah_text(" ".join(ayahs[ayah_num]))
        text, has_sajdah_symbol = stylize_special_symbols(text, target)
        ayah_mark = f"{ARABIC_END_MARK}{to_arabic_number(ayah_num)}"

        if (surah_num, ayah_num) in JUZ_LOOKUP:
            html += f'<span class="ayah-anchor" id="a{surah_num}_{ayah_num}"></span>'

        html += text
        html += f' <span class="ayah-end">{ayah_mark}</span>'

        if (
            target.show_ruku
            and (surah_num, ayah_num) in ruku_ends
            and surah_num not in single_ruku_surahs
        ):
            html += f' <span class="ruku-marker">ع{to_arabic_number(ruku_ends[(surah_num, ayah_num)])}</span>'

        if target.show_sajdah and (surah_num, ayah_num) in SAJDAH_VERSES and not has_sajdah_symbol:
            html += '&nbsp;<span class="sajdah">۩</span>'

        html += " "

    html += "</div></div></body></html>"
    html = html.replace('<div class="quran-text"></div>', "")
    return html


def build_juz_index(ayah_to_file):
    html = '<html><head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/></head><body><div class="main-wrapper">'
    html += "<h1>فهرس الأجزاء</h1>"
    html += '<div class="index-list">'

    juz_starts = {v: k for k, v in JUZ_LOOKUP.items()}
    for j in range(1, 31):
        if j in juz_starts:
            s, a = juz_starts[j]
            surah_name = SURAH_NAMES.get(s, f"Surah {s}")
            target_file = ayah_to_file.get((s, a), f"surah_{s}.xhtml")
            html += (
                f'<div class="index-item"><a class="index-link" href="{target_file}#a{s}_{a}">'
                f"الجزء {to_arabic_number(j)} — {surah_name}</a></div>"
            )

    html += "</div></div></body></html>"
    return html


def build_surah_index(surah_first_file):
    html = '<html><head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/></head><body><div class="main-wrapper">'
    html += "<h1>فهرس السور</h1>"
    html += '<div class="index-list">'

    for s in range(1, 115):
        surah_name = SURAH_NAMES.get(s, f"Surah {s}")
        href = surah_first_file.get(s, f"surah_{s}.xhtml")
        html += (
            f'<div class="index-item"><a class="index-link" href="{href}">'
            f"{to_arabic_number(s)}. {surah_name}</a></div>"
        )

    html += "</div></div></body></html>"
    return html


# =========================
# EPUB CREATION
# =========================
def create_epub(structured, target, font_content):
    surah_last_ayah = {s: max(ayahs.keys()) for s, ayahs in structured.items()}
    ruku_ends, single_ruku_surahs = build_ruku_metadata(surah_last_ayah)
    section_plan, ayah_to_file, surah_first_file = plan_surah_sections(structured, target.split_threshold)

    book = epub.EpubBook()
    book.set_title(BOOK_TITLE)
    book.set_language(BOOK_LANGUAGE)
    book.direction = "rtl"
    book.set_identifier(f"{BOOK_IDENTIFIER}-{target.key}")
    book.add_author(BOOK_AUTHOR)

    modified_utc = datetime.now(timezone.utc).isoformat()
    book.add_metadata("DC", "publisher", BOOK_PUBLISHER)
    book.add_metadata("DC", "description", f"{BOOK_TITLE} — {target.label}")
    book.add_metadata("DC", "subject", "Religion, Islam, Quran")
    book.add_metadata("DC", "date", modified_utc)
    book.add_metadata("DC", "source", "https://qul.tarteel.ai/")
    book.add_metadata("DC", "rights", "Released under the MIT License")
    book.add_metadata(None, "meta", "", {"name": "ibooks:specified-fonts", "content": "true"})
    book.add_metadata(None, "meta", "", {"name": "specified-fonts", "content": "true"})
    book.add_metadata(None, "meta", "", {"name": "build-target", "content": target.key})
    book.add_metadata(None, "meta", "", {"property": "dcterms:modified", "content": modified_utc})

    try:
        if font_content is None:
            raise FileNotFoundError(FONT_PATH)
        font_item = epub.EpubItem(
            uid="font",
            file_name="fonts/AlQalam-Quran-IndoPak.ttf",
            media_type="application/vnd.ms-opentype",
            content=font_content,
        )
        book.add_item(font_item)
    except FileNotFoundError:
        print(f"Warning: Font {FONT_PATH} not found. EPUB will be built without embedded font.")

    if os.path.exists(COVER_PATH):
        with open(COVER_PATH, "rb") as f:
            book.set_cover("cover.png", f.read())
    else:
        print(f"Warning: Cover {COVER_PATH} not found.")

    style = epub.EpubItem(uid="style", file_name="style.css", media_type="text/css", content=build_css(target))
    book.add_item(style)

    spine = []
    toc = []

    title_page = epub.EpubHtml(
        title="Title Page",
        file_name="title_page.xhtml",
        lang="ar",
        content=build_title_html(target),
    )
    title_page.direction = "rtl"
    title_page.add_item(style)
    book.add_item(title_page)
    spine.append(title_page)

    credits_page = epub.EpubHtml(
        title="Attribution & Credits",
        file_name="credits_page.xhtml",
        lang="en",
        content=build_credits_html(target),
    )
    credits_page.direction = "ltr"
    credits_page.add_item(style)
    book.add_item(credits_page)
    spine.append(credits_page)

    if target.show_juz and JUZ_LOOKUP:
        juz_index = epub.EpubHtml(
            title="فهرس الأجزاء",
            file_name="index_juz.xhtml",
            lang="ar",
            content=build_juz_index(ayah_to_file),
        )
        juz_index.direction = "rtl"
        juz_index.add_item(style)
        book.add_item(juz_index)
        spine.append(juz_index)
        toc.append(juz_index)

    surah_index = epub.EpubHtml(
        title="فهرس السور",
        file_name="index_surah.xhtml",
        lang="ar",
        content=build_surah_index(surah_first_file),
    )
    surah_index.direction = "rtl"
    surah_index.add_item(style)
    book.add_item(surah_index)
    spine.append(surah_index)
    toc.append(surah_index)

    for surah in sorted(structured.keys()):
        surah_name = SURAH_NAMES.get(surah, str(surah))
        for section in section_plan[surah]:
            chapter_title = f"{to_arabic_number(surah)}. {surah_name}"
            if section["total_parts"] > 1:
                chapter_title += f" (Part {section['part_index']}/{section['total_parts']})"

            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=section["file_name"],
                lang="ar",
                content=build_surah_section_html(
                    surah,
                    structured[surah],
                    section,
                    target,
                    ruku_ends,
                    single_ruku_surahs,
                ),
            )
            chapter.direction = "rtl"
            chapter.add_item(style)
            book.add_item(chapter)
            spine.append(chapter)
            toc.append(chapter)

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())

    output_path = os.path.join(OUTPUT_DIR, target.output_name)
    epub.write_epub(
        output_path,
        book,
        {
            "compresslevel": 9,
            "package_direction": True,
            "epub3_pages": False,
        },
    )
    return output_path


def parse_targets(target_keys):
    keys = target_keys or DEFAULT_TARGET_KEYS
    unknown = [k for k in keys if k not in BUILD_TARGETS]
    if unknown:
        valid = ", ".join(sorted(BUILD_TARGETS.keys()))
        raise ValueError(f"Unknown target(s): {', '.join(unknown)}. Valid targets: {valid}")
    return [BUILD_TARGETS[k] for k in keys]


def main():
    parser = argparse.ArgumentParser(description="Build Quran EPUB editions.")
    parser.add_argument(
        "--targets",
        nargs="+",
        help=f"Build targets ({', '.join(DEFAULT_TARGET_KEYS)}). Default: all",
    )
    parser.add_argument(
        "--legacy-copy",
        action="store_true",
        help="Also copy full edition to releases/Holy_Quran.epub",
    )
    parser.add_argument(
        "--no-subset-font",
        action="store_true",
        help="Disable font subsetting and embed the full font file.",
    )
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    structured = load_data()
    font_content = prepare_font_content(structured, subset_font=not args.no_subset_font)
    targets = parse_targets(args.targets)

    built_files = []
    for target in targets:
        out = create_epub(structured, target, font_content)
        built_files.append(out)
        print(f"Built {target.key}: {out}")

    if args.legacy_copy:
        full_output = os.path.join(OUTPUT_DIR, BUILD_TARGETS["full"].output_name)
        legacy_output = os.path.join(OUTPUT_DIR, "Holy_Quran.epub")
        if os.path.exists(full_output):
            shutil.copyfile(full_output, legacy_output)
            built_files.append(legacy_output)
            print(f"Legacy copy created: {legacy_output}")

    print("Completed builds:")
    for path in built_files:
        print(f" - {path}")


if __name__ == "__main__":
    main()
