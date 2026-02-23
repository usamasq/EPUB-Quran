import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from ebooklib import epub
import os

INPUT_JSON = "indopak.json"
RUKU_MAP_JSON = "ruku_starts.json"
PAGE_MAP_JSON = "page_map.json"
FONT_PATH = "fonts/IndoPakQuran.ttf"
COVER_PATH = "cover.png"
OUTPUT_EPUB = "Holy_Quran.epub"

# =========================
# EPUB METADATA CONFIGURATION
# =========================
BOOK_TITLE = "القرآن الكريم"
BOOK_LANGUAGE = "ar"
BOOK_IDENTIFIER = "holy-quran"
BOOK_AUTHOR = "Usama Bin Shahid (Compiler), Tarteel QUL (Text)"
BOOK_PUBLISHER = "Usama Bin Shahid"

# =========================
# HELPER FUNCTIONS
# =========================
def to_arabic_number(n):
    """Converts standard integers to Arabic numeral strings."""
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    return "".join(arabic_digits[int(d)] for d in str(n))

def load_json_map(filename):
    try:
        with open(filename, encoding="utf-8") as f:
            raw = json.load(f)
        return {int(k): tuple(v) for k,v in raw.items()}
    except FileNotFoundError:
        print(f"Warning: {filename} not found. Those markers will be skipped.")
        return {}

RUKU_MAP = load_json_map(RUKU_MAP_JSON)
RUKU_LOOKUP = {tuple(v):k for k,v in RUKU_MAP.items()}

PAGE_MAP = load_json_map(PAGE_MAP_JSON)
# (surah, ayah) -> [page1, page2, ...] (usually just one)
PAGE_LOOKUP = defaultdict(list)
for pg, (s, a) in PAGE_MAP.items():
    PAGE_LOOKUP[(s, a)].append(pg)

# Build RUKU_ENDS: maps (surah, ayah) -> surah_ruku_num (for the ENDING ayah of each ruku)
def build_ruku_ends():
    """Maps each ruku ENDING position to its surah-relative ruku number"""
    from quran_maps import SURAH_NAMES
    
    ruku_ends = {}
    ruku_starts_list = sorted(RUKU_MAP.items())  # [(global_ruku_num, (surah, ayah)), ...]
    
    # For each ruku, find where it ends
    for idx, (global_ruku_num, (surah, ayah)) in enumerate(ruku_starts_list):
        # Find the next ruku start position
        if idx + 1 < len(ruku_starts_list):
            next_global_ruku, (next_surah, next_ayah) = ruku_starts_list[idx + 1]
            if next_surah == surah:
                # Same surah, so this ruku ends at the ayah before the next ruku
                ending_ayah = next_ayah - 1
            else:
                # Different surah, ruku ends at last ayah of current surah
                # We'll handle this in build_surah_html by checking the total ayahs
                ending_ayah = None
        else:
            # Last ruku in Quran, will be handled in build_surah_html
            ending_ayah = None
        
        # Calculate surah-relative ruku number
        surah_ruku_count = 0
        for gn, (s, a) in ruku_starts_list:
            if s == surah and gn <= global_ruku_num:
                surah_ruku_count += 1
        
        if ending_ayah is not None:
            ruku_ends[(surah, ending_ayah)] = surah_ruku_count
    
    return ruku_ends

RUKU_ENDS = build_ruku_ends()

# =========================
# SURAH NAMES & METADATA
# =========================
from quran_maps import SURAH_NAMES, JUZ_LOOKUP, SAJDAH_VERSES

# =========================
# READER CSS
# =========================
GLOBAL_CSS = """
@font-face {
    font-family: 'IndoPak';
    src: url('fonts/IndoPakQuran.ttf');
    font-weight: normal;
    font-style: normal;
}
body {
    direction: rtl;
    font-family: 'IndoPak', serif;
    margin: 3% 5%;
    color: #000;
    background-color: #fff;
    text-rendering: optimizeLegibility;
    font-feature-settings: "liga" 1, "ccmp" 1;
}
h1 { text-align: center; color: #111; margin-top: 1.5em; margin-bottom: 1em; font-size: 2.2em; letter-spacing: 0.05em; }

/* Beautification for Titles & Markers */
.bismillah { text-align: center; font-size: 1.8em; margin-bottom: 1.5em; color: #111; line-height: 2; }
.juz-marker { display: block; text-align: center; font-size: 1.1em; margin: 1em 0; color: #333; font-weight: bold; border-bottom: 2px solid #ccc; padding-bottom: 5px; clear: both; }
.ruku-marker { display: inline-block; color: #666; margin: 0 0.5em; font-size: 0.85em; vertical-align: middle; font-weight: bold; border: 1px solid #ccc; border-radius: 50%; width: 1.6em; height: 1.6em; line-height: 1.6em; text-align: center; }
.sajdah { color: darkred; font-size: 1.2em; margin: 0 0.4em; font-weight: bold; vertical-align: middle; }

/* Page Indicator for E-ink/Readers */
/* Page Indicator for E-ink/Readers - Removed per user request
.page-marker { display: block; font-size: 0.7em; color: #888; text-align: left; margin: 1.5em 0; border-top: 1px solid #eee; padding-top: 0.5em; page-break-before: always; clear: both; }
*/
.ayah-end { white-space: nowrap; margin-right: 0.2em; }

/* Continuous Mushaf Flow Styling */
.quran-text {
    text-align: justify;
    text-justify: inter-word;
    line-height: 3.2; /* Increased to prevent marker clipping/overlap */
    font-size: 1.6em;
    word-spacing: 0; /* Resetting to prevent breaking ligatures */
    letter-spacing: 0; /* Resetting to prevent breaking ligatures */
}
.ayah { 
    display: inline; /* Forces continuous reading flow instead of list format */
}
.surah-separator {
    text-align: center;
    font-size: 1.2em;
    color: #ccc;
    margin: 2em 0;
    letter-spacing: 0.3em;
    page-break-before: always;
    clear: both;
}

/* Title Page & Credits Page Styling */
.title-page { text-align: center; margin-top: 30%; }
.main-title { font-size: 3.5em; color: #111; margin-bottom: 0.2em; font-family: 'IndoPak', serif; }
.sub-title { font-size: 1.2em; color: #555; font-family: sans-serif; margin-top: 0; direction: ltr; }
.ornament { font-size: 2em; color: #888; margin: 20px 0; }

.credits-page { text-align: center; direction: ltr; margin: 10%; font-family: sans-serif; line-height: 1.8; color: #333; }
.credits-page h2 { text-align: center; border-bottom: 1px solid #ccc; padding-bottom: 10px; margin-bottom: 30px; color: #222; }
.credit-item { margin-bottom: 25px; background: #fdfdfd; padding: 20px; border-radius: 8px; border: 1px solid #eaeaea; text-align: left; }
.credit-item strong { display: block; font-size: 1.1em; color: #111; margin-bottom: 5px; }

/* Dark Mode / Night Mode Support */
@media (prefers-color-scheme: dark) {
    body { color: #e0e0e0; background-color: #121212; }
    h1, .bismillah, .main-title, .credits-page h2, .credit-item strong { color: #ffffff; }
    .juz-marker { color: #dddddd; border-bottom-color: #444; }
    .ruku-marker, .sub-title, .ornament { color: #666666; }
    .surah-separator { color: #444; }
    .credit-item { background: #1e1e1e; border-color: #333; color: #ccc; }
    .sajdah { color: #ff6b6b; }
}
"""

# =========================
# LOAD QURAN
# =========================
def load_data():
    with open(INPUT_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    structured = defaultdict(lambda: defaultdict(list))
    for key in sorted(raw.keys(), key=lambda x: tuple(map(int,x.split(":")))):
        item = raw[key]
        s = int(item["surah"])
        a = int(item["ayah"])
        structured[s][a].append(item["text"])
    return structured

# =========================
# BUILD PAGES (TITLE & CREDITS)
# =========================
def build_title_html():
    return f"""<html dir="rtl">
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>Title Page</title></head>
<body>
    <div class="title-page">
        <div class="ornament">﴾ ❖ ﴿</div>
        <h1 class="main-title">{BOOK_TITLE}</h1>
        <div class="ornament">﴾ ❖ ﴿</div>
    </div>
</body></html>"""

def build_credits_html():
    return f"""<html dir="ltr">
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>Attribution & Credits</title></head>
<body>
    <div class="credits-page">
        <h2>Attribution & Credits</h2>
        <div class="credit-item">
            <strong>Compilation & Formatting</strong>
            This digital EPUB edition was meticulously compiled, formatted, and structured by <strong>{BOOK_PUBLISHER}</strong>.
        </div>
        <div class="credit-item">
            <strong>Text Data (JSON)</strong>
            The authentic Indo-Pak Quranic text used in this digital publication was beautifully digitized and sourced from the <em>Tarteel QUL Website</em>.
        </div>
        <div class="credit-item">
            <strong>Typography</strong>
            Typeset using the beautiful <em>AlQalam Quran IndoPak</em> font to ensure an authentic, traditional South Asian reading experience on e-readers.
        </div>
        <div class="credit-item">
            <strong>Metadata Mapping</strong>
            Juz and Ruku boundary mappings were algorithmically mapped using the <em>AlQuran.cloud API</em>.
        </div>
    </div>
</body></html>"""

# =========================
# BUILD SURAH FILE
# =========================
def build_surah_html(surah_num, ayahs):
    arabic_num = to_arabic_number(surah_num)
    name = f"{arabic_num}. {SURAH_NAMES.get(surah_num, f'Surah {surah_num}')}"
    
    html = f"""<html dir="rtl">
<head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/><title>{name}</title></head>
<body><h1>{name}</h1>"""
    # Add visual separator before this surah (except the first one)
    if surah_num > 1:
        html += '<div class="surah-separator">✦ ✦ ✦</div>'
    
    if surah_num not in [1, 9]:
        html += '<div class="bismillah">بِسۡمِ اللهِ الرَّحۡمٰنِ الرَّحِيۡمِ</div>'

    html += '<div class="quran-text">'

    for ayah_num in sorted(ayahs.keys()):
        # Collect indicators for this ayah
        indicators_html = ""
        
        if (surah_num, ayah_num) in PAGE_LOOKUP:
            for pg in PAGE_LOOKUP[(surah_num, ayah_num)]:
                # We no longer need visible page markers as per user request
                pass

        if (surah_num, ayah_num) in JUZ_LOOKUP:
            indicators_html += f'<div class=\"juz-marker\">الجزء {to_arabic_number(JUZ_LOOKUP[(surah_num, ayah_num)])}</div>'

        # If we have indicators or this is the start of the surah (except first ayah of surah_1), 
        # ensure we close previous quran-text block and open a new one.
        if indicators_html:
            html += f'</div>{indicators_html}<div class="quran-text">'

        # 1. Join the raw words
        text = " ".join(ayahs[ayah_num])
        
        # 2. Strip existing \u06DD, strip raw Arabic digits, and strip invisible/control characters
        # \ufeff: BOM, \u200f: RLM, \u200b: ZWSP, \u2002: En Space, \u2003: Em Space, \u200c: ZWNJ, \u200d: ZWJ
        strip_chars = ['\u06DD', '\ufeff', '\u200f', '\u200b', '\u2002', '\u2003', '\u200c', '\u200d']
        for char_to_strip in strip_chars:
            text = text.replace(char_to_strip, '')
        
        # Strip Arabic/Western digits from the end (usually the ayah marker in the source json)
        text = re.sub(r'\s*[\u0660-\u0669\u06F0-\u06F90-9]+\s*$', '', text)
        
        # Strip private use area characters which are often font-specific artifacts
        text = re.sub(r'[\uE000-\uF8FF]', '', text)
        
        # Add a hair space between consecutive mark characters that might overlap
        # Waqf marks: 0x6d6-0x6dc (ۖۗۘۙۚۛۜ)
        text = re.sub(r'([\u06d6-\u06dc])([\u06d6-\u06dc])', r'\1&#x200A;\2', text)
        
        # 3. Add the proper sequence back: \u06DD (End of Ayah Symbol) + The exact Ayah Number.
        # Use Arabic digits (to_arabic_number) as many Indo-Pak fonts are specifically 
        # tuned for Arabic digits when forming the enclosed-circle ligature.
        # Wrap in a span to prevent breaking and force tight rendering.
        ayah_mark = f"\u06DD{to_arabic_number(ayah_num)}"
        text = f'{text} <span class="ayah-end">{ayah_mark}</span>'
        
        html += f'<span class="ayah" id="a{surah_num}_{ayah_num}">{text}'
        
        # Add ruku marker at the END of this ayah if it ends a ruku
        if (surah_num, ayah_num) in RUKU_ENDS:
            surah_ruku = RUKU_ENDS[(surah_num, ayah_num)]
            html += f' <span class="ruku-marker">ع{to_arabic_number(surah_ruku)}</span>'
        
        if (surah_num, ayah_num) in SAJDAH_VERSES:
            html += '&nbsp;<span class="sajdah">۩</span>'
        
        html += ' </span>'

    html += "</div></body></html>"
    html = html.replace('<div class="quran-text"></div>', '')
    return html

# =========================
# JUZ (PARAH) INDEX
# =========================
def build_juz_index():
    html = '<html dir="rtl"><head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/></head><body>'
    html += '<h1>فهرس الأجزاء</h1>'
    html += '<div style="margin: 20px 5%; line-height: 2;">'
    
    juz_starts = {v: k for k, v in JUZ_LOOKUP.items()}
    
    for j in range(1, 31):
        if j in juz_starts:
            s, a = juz_starts[j]
            surah_name = SURAH_NAMES.get(s, f"Surah {s}")
            html += f'<div style="margin-bottom: 0.5em; font-size: 1.2em; border-bottom: 1px solid #eee; padding-bottom: 5px;"><a style="text-decoration: none; color: inherit;" href="surah_{s}.xhtml#a{s}_{a}">الجزء {to_arabic_number(j)} — {surah_name}</a></div>'
            
    html += "</div></body></html>"
    return html

# =========================
# SURAH INDEX
# =========================
def build_surah_index():
    html = '<html dir="rtl"><head><meta charset="utf-8"/><link rel="stylesheet" href="style.css"/></head><body>'
    html += '<h1>فهرس السور</h1>'
    html += '<div style="margin: 20px 5%; line-height: 2;">'
    
    for s in range(1, 115):
        surah_name = SURAH_NAMES.get(s, f"Surah {s}")
        html += f'<div style="margin-bottom: 0.5em; font-size: 1.2em; border-bottom: 1px solid #eee; padding-bottom: 5px;"><a style="text-decoration: none; color: inherit;" href="surah_{s}.xhtml">{to_arabic_number(s)}. {surah_name}</a></div>'
            
    html += "</div></body></html>"
    return html

# =========================
# EPUB CREATION
# =========================
def create_epub(structured):
    book = epub.EpubBook()
    
    book.set_title(BOOK_TITLE)
    book.set_language(BOOK_LANGUAGE)
    book.direction = "rtl"
    book.set_identifier(BOOK_IDENTIFIER)
    book.add_author(BOOK_AUTHOR)
    
    book.add_metadata("DC", "publisher", BOOK_PUBLISHER)
    book.add_metadata("DC", "subject", "Religion, Islam, Quran")
    book.add_metadata("DC", "description", "The Holy Quran featuring an authentic Indo-Pak script format. Built with complete Juz/Parah and Ruku navigation tailored specifically for modern e-readers and Kindle devices.")
    book.add_metadata("DC", "date", datetime.now(timezone.utc).isoformat())

    try:
        with open(FONT_PATH,"rb") as f:
            font_content = f.read()
        font_item = epub.EpubItem(uid="font", file_name="fonts/IndoPakQuran.ttf", media_type="font/ttf", content=font_content)
        book.add_item(font_item)
    except FileNotFoundError:
        print(f"Warning: Font {FONT_PATH} not found. EPUB will be built without embedded font.")

    if os.path.exists(COVER_PATH):
        book.set_cover("cover.png", open(COVER_PATH, 'rb').read())
    else:
        print(f"Warning: Cover {COVER_PATH} not found.")

    style = epub.EpubItem(uid="style", file_name="style.css", media_type="text/css", content=GLOBAL_CSS)
    book.add_item(style)

    spine = []
    toc = []

    title_page = epub.EpubHtml(title="Title Page", file_name="title_page.xhtml", lang="ar", content=build_title_html())
    title_page.add_item(style)
    book.add_item(title_page)
    spine.append(title_page)

    credits_page = epub.EpubHtml(title="Attribution & Credits", file_name="credits_page.xhtml", lang="en", content=build_credits_html())
    credits_page.add_item(style)
    book.add_item(credits_page)
    spine.append(credits_page)

    if JUZ_LOOKUP:
        juz_index = epub.EpubHtml(title="فهرس الأجزاء", file_name="index_juz.xhtml", lang="ar", content=build_juz_index())
        juz_index.add_item(style)
        book.add_item(juz_index)
        spine.append(juz_index)
        toc.append(juz_index)

    surah_index = epub.EpubHtml(title="فهرس السور", file_name="index_surah.xhtml", lang="ar", content=build_surah_index())
    surah_index.add_item(style)
    book.add_item(surah_index)
    spine.append(surah_index)
    toc.append(surah_index)

    for s in structured.keys():
        chapter = epub.EpubHtml(title=f"{to_arabic_number(s)}. {SURAH_NAMES.get(s, str(s))}", file_name=f"surah_{s}.xhtml", lang="ar", content=build_surah_html(s, structured[s]))
        chapter.add_item(style)
        book.add_item(chapter)
        spine.append(chapter)
        toc.append(chapter)

    book.toc = toc
    book.spine = spine
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())
    
    epub.write_epub(OUTPUT_EPUB, book)

if __name__ == "__main__":
    structured = load_data()
    create_epub(structured)
    print(f"Success! {OUTPUT_EPUB} generated with enhanced metadata and beautiful attribution pages.")