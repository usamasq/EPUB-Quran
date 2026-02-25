import argparse
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from ebooklib import epub

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

INPUT_JSON = os.path.join(PROJECT_ROOT, "data", "indopak.json")
RUKU_MAP_JSON = os.path.join(PROJECT_ROOT, "data", "ruku_starts.json")
TAFSIR_JSON = os.path.join(PROJECT_ROOT, "abridged-explanation-of-the-quran.json")
COVER_PATH = os.path.join(PROJECT_ROOT, "assets", "cover.png")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "releases")
PROJECT_REPO_URL = "https://github.com/usamasq/EPUB-Quran"
PROJECT_RELEASES_URL = "https://github.com/usamasq/EPUB-Quran/releases"
PROJECT_SITE_URL = "https://usamasq.github.io/EPUB-Quran/"
PROJECT_CONTACT_URL = "mailto:usamasq@gmail.com"

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
    show_tafsir: bool = True


BUILD_TARGETS = {
    "main": BuildTarget(
        key="main",
        label="Universal Edition",
        output_name="Holy-Quran.epub",
        profile="compat",
        variant="lite",
        split_threshold=100,
        show_tafsir=True,
    ),
}
DEFAULT_TARGET_KEYS = ["main"]


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

    try:
        with open(TAFSIR_JSON, encoding="utf-8") as f:
            tafsir_raw = json.load(f)
    except FileNotFoundError:
        tafsir_raw = {}
        print(f"Warning: {TAFSIR_JSON} not found.")
        
    tafsir = {}
    redirects = {}
    for key, value in tafsir_raw.items():
        parts = key.split(":")
        if len(parts) == 2:
            s, a = map(int, parts)
            if isinstance(value, dict) and "text" in value:
                tafsir[(s, a)] = value["text"]
            elif isinstance(value, str):
                redirects[(s, a)] = value

    for (s, a), redirect_val in redirects.items():
        parts = redirect_val.split(":")
        if len(parts) == 2:
            ts, ta = map(int, parts)
            tafsir[(s, a)] = tafsir.get((ts, ta), "Explanation available in another verse.")

    return structured, tafsir


# =========================
# QURAN MAPS
# =========================
from quran_maps import SURAH_NAMES, JUZ_LOOKUP, SAJDAH_VERSES, JUZ_NAMES

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
    # Bumped sizes significantly: Arabic script naturally renders smaller visually than Latin.
    # 2.4em/2.3em should give it parity with standard English book text on a Kindle.
    quran_font_size = "2.4em" if target.variant == "full" else "2.3em"
    quran_line_height = "2.5" if target.variant == "full" else "2.3"
    body_margin = "3% 5%" if target.variant == "full" else "2.8% 4.2%"
    body_text = "#000000"
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
html, body {{
    margin: 0;
    padding: 0;
}}

body {{
    font-family: serif;
    margin: {body_margin};
    color: {body_text};
    -webkit-hyphens: none;
    hyphens: none;
}}

.main-wrapper {{
    text-align: right;
}}

h1 {{
    text-align: center;
    color: {accent};
    margin: 1.2em 0 0.9em;
    font-size: 2.12em;
}}

h1.surah-header {{
    text-align: center;
    color: {accent};
    margin: 1.5em 0 1em;
    font-size: 2.2em;
    border-top: 4px double {accent};
    border-bottom: 4px double {accent};
    padding: 0.4em 0 0.2em;
    background-color: rgba(23, 77, 53, 0.05);
    line-height: 1.4;
}}

.bismillah {{
    text-align: center;
    font-size: 1.85em;
    margin-bottom: 1.2em;
    color: #111111;
    line-height: 2;
    font-weight: bold;
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
    font-size: 0.9em;
    color: {accent};
    font-weight: normal;
    text-decoration: none;
}}

.ayah-anchor {{
    display: inline;
}}

.quran-text {{
    text-align: right;
    line-height: {quran_line_height};
    font-size: {quran_font_size};
    word-spacing: 0em;
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

.ornament {{
    font-size: 2em;
    color: #8d9b95;
    margin: 0.6em 0;
}}

.credits-page {{
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
    }}
    h1, .main-title {{
        color: #90c8ae;
    }}
    h1.surah-header {{
        color: #90c8ae;
        border-top-color: #3b6251;
        border-bottom-color: #3b6251;
        background-color: rgba(65, 122, 98, 0.08);
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
        background: transparent;
        border-color: #2a4338;
    }}
    .credit-card {{
        background: transparent;
        border-color: #2a3f36;
    }}
    .build-meta {{
        border-top-color: #264238;
        color: #a6b9b2;
    }}
    rt {{
        color: #8fa49a;
    }}
    .tafsir-container {{
        background: transparent;
        border-color: #2d4b3f;
    }}
    .tafsir-text {{
        color: #d1dfd9;
    }}
}}

/* WBW Grammar Colors */
.p {{ color: #d35400; }} /* Preposition */
.v {{ color: #27ae60; }} /* Verb */
.n {{ color: #2980b9; }} /* Noun */
.pn {{ color: #8e44ad; }} /* Proper Noun */
.pro {{ color: #c0392b; }} /* Pronoun */
.adj {{ color: #16a085; }} /* Adjective */
.dem {{ color: #f39c12; }} /* Demonstrative */
.rel {{ color: #d35400; }} /* Relative Pronoun */
.neg {{ color: #e74c3c; }} /* Negative Particle */
.con {{ color: #bdc3c7; }} /* Conjunction */
.cond {{ color: #7f8c8d; }} /* Conditional Particle */
.inc {{ color: #95a5a6; }} /* Inceptive Particle */
.acc {{ color: #34495e; }} /* Accusative Particle */
.amd {{ color: #2c3e50; }} /* Amendment Particle */
.ans {{ color: #e67e22; }} /* Answer Particle */
.av {{ color: #2ecc71; }} /* Imperative Verbal Noun */
.caus {{ color: #f1c40f; }} /* Particle of Cause */
.cert {{ color: #1abc9c; }} /* Particle of Certainty */
.circ {{ color: #3498db; }} /* Circumstantial Particle */
.com {{ color: #9b59b6; }} /* Comitative Particle */
.def {{ color: #1abc9c; }} /* Prefix Particle */
.emph {{ color: #c0392b; }} /* Emphatic Prefix */
.eq {{ color: #e74c3c; }} /* Equalization Particle */
.exh {{ color: #e67e22; }} /* Exhortation Particle */
.exp {{ color: #f1c40f; }} /* Exceptive Particle */
.fut {{ color: #2ecc71; }} /* Future Particle */
.in {{ color: #3498db; }} /* Initials */
.int {{ color: #9b59b6; }} /* Interrogative Particle */
.intg {{ color: #34495e; }} /* Interrogative Prefix */
.loc {{ color: #16a085; }} /* Location Noun */
.ndem {{ color: #f39c12; }} /* Demonstrative Pronoun Prefix */
.pcl {{ color: #d35400; }} /* Particle */
.prp {{ color: #e74c3c; }} /* Purpose Particle */
.res {{ color: #7f8c8d; }} /* Restriction Particle */
.ret {{ color: #bdc3c7; }} /* Retraction Particle */
.rslt {{ color: #95a5a6; }} /* Result Particle */
.sup {{ color: #2c3e50; }} /* Supplemental Particle */
.sur {{ color: #e67e22; }} /* Surprise Particle */
.t {{ color: #f1c40f; }} /* Time Noun */
.voc {{ color: #e74c3c; }} /* Vocative Particle */

/* Tafsir Link styling */
.tafsir-ayah-link {{
    text-decoration: none !important;
    border: none !important;
    font-weight: bold;
    color: {accent} !important;
}}

/* Tafsir Appendix styling */
.tafsir-container {{
    border: 1px solid #e0eae5;
    border-radius: 8px;
    padding: 1.4em 1.2em;
    margin-bottom: 1.8em;
    text-align: left;
    background-color: #fdfcf8;
    box-shadow: 0 1px 3px rgba(23, 77, 53, 0.05);
}}

.tafsir-header {{
    font-weight: bold;
    color: {accent};
    margin-bottom: 0.8em;
    font-size: 1.15em;
    border-bottom: 2px solid #e0eae5;
    padding-bottom: 0.4em;
}}

.tafsir-backlink {{
    float: right;
    font-size: 0.85em;
    color: {accent_soft};
    text-decoration: none;
    border: 1px solid #d3ddd8;
    padding: 0.2em 0.6em;
    border-radius: 4px;
    background: #ffffff;
}}

.tafsir-text {{
    font-family: serif;
    font-size: 1.1em;
    line-height: 1.75;
    color: #111111;
    text-align: justify;
    text-justify: inter-word;
}}
"""


def build_title_html(target):
    return f"""<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" dir="rtl" lang="ar">
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>Title Page</title></head>
<body epub:type="frontmatter" dir="rtl"><div class="main-wrapper" dir="rtl">
    <div class="title-page">
        <div class="ornament">﴾ ❖ ﴿</div>
        <h1 class="main-title" epub:type="title">{BOOK_TITLE}</h1>
        <div class="ornament">﴾ ❖ ﴿</div>
    </div>
</div></body></html>"""


def build_credits_html(target):
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>Publication Information</title></head>
<body epub:type="frontmatter"><div class="main-wrapper" dir="ltr">
    <div class="credits-page">
        <div class="credits-header">
            <div class="credits-title">Publication Information</div>
            <div class="credits-sub">Details regarding this digital edition of the Holy Quran.</div>
        </div>
        <div class="credit-grid">
            <div class="credit-card">
                <h3>Translation & Tafsir Source</h3>
                The Arabic text, Tafsir (Explanation), and Word-By-Word grammatical data were provided by 
                <a href="https://qul.tarteel.ai/">Tarteel QUL</a>. We are deeply grateful for their robust open-source contributions to Islamic knowledge.
            </div>
            <div class="credit-card">
                <h3>Open Source Project</h3>
                <strong>Repository:</strong> <a href="{PROJECT_REPO_URL}">{PROJECT_REPO_URL}</a><br/>
                Compiled and formatted with care by <strong>Usama Bin Shahid</strong>. For any feedback, corrections, or suggestions, please reach out via <a href="{PROJECT_CONTACT_URL}">Email</a> (usamasq@gmail.com).
            </div>
            <div class="credit-card">
                <h3>Acknowledgments</h3>
                May Allah (SWT) accept this humble effort and make it a source of guidance and benefit for all who read it. We ask for your prayers for the developers, contributors, and their families.
            </div>
        </div>
        <div class="build-meta">
            Target: {target.output_name} ({target.label})<br/>
            Build: {built_at}<br/>
            Publisher: {BOOK_PUBLISHER}
        </div>
    </div>
</div></body></html>"""


def build_surah_section_html(surah_num, ayahs, section, target, ruku_ends, single_ruku_surahs, tafsir):
    arabic_num = to_arabic_number(surah_num)
    surah_name = SURAH_NAMES.get(surah_num, f"Surah {surah_num}")
    title = f"{arabic_num}. {surah_name}"
    if section["total_parts"] > 1:
        title = f"{title} (Part {section['part_index']}/{section['total_parts']})"

    html = f"""<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" dir="rtl" lang="ar">
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>{title}</title></head>
<body epub:type="bodymatter chapter" dir="rtl"><div class="main-wrapper" dir="rtl">"""

    if section["is_first"]:
        html += f'<h1 class="surah-header" epub:type="title">{arabic_num}. {surah_name}</h1>'
        if surah_num not in [1, 9]:
            html += '<div class="bismillah" dir="rtl">بِسۡمِ اللهِ الرَّحۡمٰنِ الرَّحِيۡمِ</div>'
    else:
        html += (
            f'<div class="part-title">{surah_name} — Part {section["part_index"]} '
            f'of {section["total_parts"]}</div>'
        )

    html += '<div class="quran-text" dir="rtl">'

    for ayah_num in section["ayah_numbers"]:
        indicators_html = ""
        if target.show_juz and (surah_num, ayah_num) in JUZ_LOOKUP:
            indicators_html += (
                f'<div class="juz-marker" epub:type="pagebreak">'
                f'الجزء {to_arabic_number(JUZ_LOOKUP[(surah_num, ayah_num)])}'
                f"</div>"
            )

        if indicators_html:
            html += f'</div>{indicators_html}<div class="quran-text" dir="rtl">'

        # Using Ornate Parentheses ﴿ ﴾ instead of the ARABIC_END_MARK ۝ 
        # because Kindle's default fonts lack the ligature tables to wrap the circle around Eastern Arabic digits.
        ayah_number_arabic = to_arabic_number(ayah_num)
        has_sajdah_symbol = False

        html += f'<span class="ayah-anchor" id="a{surah_num}_{ayah_num}">\u200b</span>'

        if target.show_tafsir and tafsir and (surah_num, ayah_num) in tafsir:
            linked_number = f'<a href="tafsir_surah_{surah_num}.xhtml#t{surah_num}_{ayah_num}" class="tafsir-ayah-link" epub:type="noteref" title="Explanation">{ayah_number_arabic}</a>'
        else:
            linked_number = ayah_number_arabic
            
        ayah_mark = f"&#xFD3F;{linked_number}&#xFD3E;"

        text = normalize_ayah_text(" ".join(ayahs[ayah_num]))
        text, has_sajdah_symbol = stylize_special_symbols(text, target)
        html += text
            
        html += f' <span class="ayah-end">{ayah_mark}</span>'

        if (
            target.show_ruku
            and (surah_num, ayah_num) in ruku_ends
            and surah_num not in single_ruku_surahs
        ):
            html += f' <span class="ruku-marker" epub:type="pagebreak">ع{to_arabic_number(ruku_ends[(surah_num, ayah_num)])}</span>'

        if target.show_sajdah and (surah_num, ayah_num) in SAJDAH_VERSES and not has_sajdah_symbol:
            html += '&nbsp;<span class="sajdah">۩</span>'

        html += " "

    html += "</div></div></body></html>"
    html = html.replace('<div class="quran-text"></div>', "")
    return html

def build_tafsir_section_html(surah_num, ayahs_list, target, tafsir, ayah_to_file):
    from quran_maps import SURAH_NAMES
    arabic_num = to_arabic_number(surah_num)
    surah_name = SURAH_NAMES.get(surah_num, f"Surah {surah_num}")
    title = f"Tafsir - {surah_name}"
    
    html = f"""<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>{title}</title></head>
<body epub:type="bodymatter chapter"><div class="main-wrapper" dir="ltr">"""

    html += f'<h1 epub:type="title" dir="ltr">Explanation (Tafsir) - {surah_name}</h1>'

    has_content = False
    for ayah_num in sorted(ayahs_list):
        if (surah_num, ayah_num) in tafsir:
            has_content = True
            tafsir_text = tafsir[(surah_num, ayah_num)]
            target_file = ayah_to_file.get((surah_num, ayah_num), f"surah_{surah_num}.xhtml")
            ayah_link = f"{target_file}#a{surah_num}_{ayah_num}"
                
            html += f"""
            <div class="tafsir-container" dir="ltr" id="t{surah_num}_{ayah_num}">
                <div class="tafsir-header">
                    Ayah {surah_num}:{ayah_num}
                    <a href="{ayah_link}" class="tafsir-backlink" epub:type="backlink">⏎ Back to Ayah</a>
                </div>
                <div class="tafsir-text" epub:type="commentary">{tafsir_text}</div>
            </div>"""

    html += "</div></body></html>"
    if not has_content:
        return None
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
            juz_name = JUZ_NAMES.get(j, "")
            target_file = ayah_to_file.get((s, a), f"surah_{s}.xhtml")
            
            display_text = f"الجزء {to_arabic_number(j)}"
            if juz_name:
                display_text += f" ({juz_name})"
            display_text += f" — {surah_name}"

            html += (
                f'<div class="index-item"><a class="index-link" href="{target_file}#a{s}_{a}">'
                f"{display_text}</a></div>"
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
def create_epub(structured, tafsir, target):
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
    book.add_metadata(None, "meta", "", {"name": "build-target", "content": target.key})

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
        title="Publication Information",
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
                    tafsir
                ),
            )
            chapter.direction = "rtl"
            chapter.add_item(style)
            book.add_item(chapter)
            spine.append(chapter)
            toc.append(chapter)

    if target.show_tafsir:
        for surah in sorted(structured.keys()):
            surah_name = SURAH_NAMES.get(surah, str(surah))
            tafsir_html = build_tafsir_section_html(surah, list(structured[surah].keys()), target, tafsir, ayah_to_file)
            if tafsir_html:
                t_chapter = epub.EpubHtml(
                    title=f"Tafsir - {surah_name}",
                    file_name=f"tafsir_surah_{surah}.xhtml",
                    lang="en",
                    content=tafsir_html
                )
                t_chapter.direction = "ltr"
                t_chapter.add_item(style)
                book.add_item(t_chapter)
                spine.append(t_chapter)
                toc.append(t_chapter)

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
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    structured, tafsir = load_data()
    targets = parse_targets(args.targets)

    built_files = []
    for target in targets:
        out = create_epub(structured, tafsir, target)
        built_files.append(out)
        print(f"Built {target.key}: {out}")

    print("Completed builds:")
    for path in built_files:
        print(f" - {path}")


if __name__ == "__main__":
    main()
