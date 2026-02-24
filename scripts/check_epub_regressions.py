import argparse
import glob
import json
import os
import re
import sys
import zipfile
from collections import defaultdict

from lxml import etree

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

INPUT_JSON = os.path.join(PROJECT_ROOT, "data", "indopak.json")
RUKU_MAP_JSON = os.path.join(PROJECT_ROOT, "data", "ruku_starts.json")


def load_expected_counts():
    with open(INPUT_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    total_ayahs = len({(int(v["surah"]), int(v["ayah"])) for v in raw.values()})

    with open(RUKU_MAP_JSON, encoding="utf-8") as f:
        ruku_map = {int(k): tuple(v) for k, v in json.load(f).items()}

    per_surah = defaultdict(int)
    for _, (surah, _) in sorted(ruku_map.items()):
        per_surah[surah] += 1
    single_surah_count = sum(1 for n in per_surah.values() if n <= 1)
    expected_ruku_visible = len(ruku_map) - single_surah_count

    return total_ayahs, expected_ruku_visible


def list_epubs(args_epubs):
    if args_epubs:
        return args_epubs
    return sorted(glob.glob(os.path.join(PROJECT_ROOT, "releases", "*.epub")))


def ensure_required_files(zf, epub_path):
    required = {"mimetype", "META-INF/container.xml", "EPUB/content.opf", "EPUB/style.css"}
    names = set(zf.namelist())
    missing = sorted(required - names)
    if missing:
        raise AssertionError(f"{epub_path}: missing required files: {missing}")


def validate_xml_and_links(zf, epub_path):
    xhtml_files = [n for n in zf.namelist() if n.endswith(".xhtml")]
    ids = set()

    for name in xhtml_files:
        try:
            root = etree.fromstring(zf.read(name))
        except Exception as exc:
            raise AssertionError(f"{epub_path}: invalid XHTML in {name}: {exc}") from exc
        for el in root.xpath("//*[@id]"):
            ids.add((name.split("/")[-1], el.get("id")))

    broken = []
    for name in xhtml_files:
        root = etree.fromstring(zf.read(name))
        for el in root.xpath("//*[@href]"):
            href = el.get("href")
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target_file = href
            frag = ""
            if "#" in href:
                target_file, frag = href.split("#", 1)
            if target_file and ("EPUB/" + target_file not in zf.namelist()):
                broken.append((name, href, "missing file"))
            if frag and (target_file, frag) not in ids:
                broken.append((name, href, "missing fragment"))

    if broken:
        sample = broken[:8]
        raise AssertionError(f"{epub_path}: broken internal links found: {sample}")


def count_markers(zf):
    surah_files = [n for n in zf.namelist() if n.startswith("EPUB/surah_") and n.endswith(".xhtml")]
    counts = {
        "ayah_end": 0,
        "ruku": 0,
        "juz": 0,
        "sajdah": 0,
        "unstyled_sajdah": 0,
    }
    for name in surah_files:
        text = zf.read(name).decode("utf-8", "replace")
        counts["ayah_end"] += text.count('class="ayah-end"')
        counts["ruku"] += text.count('class="ruku-marker"')
        counts["juz"] += text.count('class="juz-marker"')
        counts["sajdah"] += text.count('class="sajdah"')
        cleaned = re.sub(r'<span class="sajdah">۩</span>', "", text)
        counts["unstyled_sajdah"] += cleaned.count("۩")
    return counts


def run_checks(epub_path, expected_ayahs, expected_ruku_visible):
    with zipfile.ZipFile(epub_path) as zf:
        ensure_required_files(zf, epub_path)
        validate_xml_and_links(zf, epub_path)
        counts = count_markers(zf)
        opf = zf.read("EPUB/content.opf").decode("utf-8", "replace")
        css = zf.read("EPUB/style.css").decode("utf-8", "replace")

    if counts["ayah_end"] != expected_ayahs:
        raise AssertionError(
            f"{epub_path}: ayah marker count mismatch. expected={expected_ayahs} actual={counts['ayah_end']}"
        )
    if counts["ruku"] != expected_ruku_visible:
        raise AssertionError(
            f"{epub_path}: ruku marker count mismatch. expected={expected_ruku_visible} actual={counts['ruku']}"
        )
    if counts["juz"] != 30:
        raise AssertionError(f"{epub_path}: juz marker count mismatch. expected=30 actual={counts['juz']}")
    if counts["sajdah"] != 15:
        raise AssertionError(f"{epub_path}: sajdah marker count mismatch. expected=15 actual={counts['sajdah']}")
    if counts["unstyled_sajdah"] != 0:
        raise AssertionError(f"{epub_path}: unstyled sajdah symbols remain in output")
    if 'page-progression-direction="rtl"' not in opf:
        raise AssertionError(f"{epub_path}: spine direction metadata missing")
    if opf.count('property="dcterms:modified"') != 1:
        raise AssertionError(f"{epub_path}: dcterms:modified meta must occur exactly once")
    if 'property="dcterms:modified" content="' in opf:
        raise AssertionError(f"{epub_path}: invalid dcterms:modified serialization detected")
    if "direction:" in css:
        raise AssertionError(f"{epub_path}: CSS must not contain direction property declarations")

    print(
        f"[PASS] {os.path.basename(epub_path)} "
        f"(ayah={counts['ayah_end']}, ruku={counts['ruku']}, juz={counts['juz']}, sajdah={counts['sajdah']})"
    )


def main():
    parser = argparse.ArgumentParser(description="Regression checks for generated Quran EPUB files.")
    parser.add_argument("--epubs", nargs="*", help="Explicit epub paths. Default: releases/*.epub")
    args = parser.parse_args()

    epubs = list_epubs(args.epubs)
    if not epubs:
        print("[FAIL] No EPUB files found to validate.")
        return 1

    expected_ayahs, expected_ruku_visible = load_expected_counts()
    print(f"[INFO] Expected ayahs={expected_ayahs}, expected visible ruku markers={expected_ruku_visible}")

    for epub_path in epubs:
        run_checks(epub_path, expected_ayahs, expected_ruku_visible)

    print("[RESULT] All regression checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
