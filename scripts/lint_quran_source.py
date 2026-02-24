import json
import os
import sys
import unicodedata
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

INPUT_JSON = os.path.join(PROJECT_ROOT, "data", "indopak.json")
RUKU_MAP_JSON = os.path.join(PROJECT_ROOT, "data", "ruku_starts.json")
JUZ_MAP_JSON = os.path.join(PROJECT_ROOT, "data", "juz_starts.json")
PAGE_MAP_JSON = os.path.join(PROJECT_ROOT, "data", "page_map.json")

EXPECTED_AYAHS = 6236


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def fail(msg):
    print(f"[FAIL] {msg}")
    return 1


def main():
    errors = 0
    warnings = 0

    raw = load_json(INPUT_JSON)
    ruku_map = {int(k): tuple(v) for k, v in load_json(RUKU_MAP_JSON).items()}
    juz_map = {int(k): tuple(v) for k, v in load_json(JUZ_MAP_JSON).items()}
    page_map = {int(k): tuple(v) for k, v in load_json(PAGE_MAP_JSON).items()}

    ayah_positions = set()
    char_counter = Counter()
    pua_count = 0
    control_counter = Counter()

    for entry in raw.values():
        s = int(entry["surah"])
        a = int(entry["ayah"])
        ayah_positions.add((s, a))
        text = entry["text"]
        for ch in text:
            char_counter[ch] += 1
            code = ord(ch)
            if 0xE000 <= code <= 0xF8FF:
                pua_count += 1
            if unicodedata.category(ch) == "Cf":
                control_counter[ch] += 1

    print(f"[INFO] Total ayahs in source: {len(ayah_positions)}")
    if len(ayah_positions) != EXPECTED_AYAHS:
        errors += fail(f"Expected {EXPECTED_AYAHS} ayahs, found {len(ayah_positions)}")

    print(f"[INFO] Ruku starts: {len(ruku_map)}")
    for ruku_num, pos in ruku_map.items():
        if pos not in ayah_positions:
            errors += fail(f"Ruku #{ruku_num} points to missing ayah {pos}")

    print(f"[INFO] Juz starts: {len(juz_map)}")
    if len(juz_map) != 30:
        errors += fail(f"Expected 30 Juz starts, found {len(juz_map)}")
    for juz_num, pos in juz_map.items():
        if pos not in ayah_positions:
            errors += fail(f"Juz #{juz_num} points to missing ayah {pos}")

    print(f"[INFO] Page map entries: {len(page_map)}")
    for page, pos in page_map.items():
        if pos not in ayah_positions:
            errors += fail(f"Page #{page} points to missing ayah {pos}")

    if pua_count > 0:
        warnings += 1
        print(f"[WARN] Private-use codepoints detected in source text: {pua_count}")

    if control_counter:
        print("[INFO] Control-format chars detected:")
        for ch, count in sorted(control_counter.items(), key=lambda kv: ord(kv[0])):
            name = unicodedata.name(ch, "UNKNOWN")
            print(f"  - U+{ord(ch):04X} {name}: {count}")

    print("[INFO] Frequent Quranic marks:")
    for cp in ["\u06D6", "\u06D7", "\u06D8", "\u06D9", "\u06DA", "\u06DB", "\u06DC", "\u06DE", "\u06E9"]:
        print(f"  - U+{ord(cp):04X} {unicodedata.name(cp, '?')}: {char_counter[cp]}")

    if errors:
        print(f"[RESULT] FAILED with {errors} error(s), {warnings} warning(s).")
        return 1

    print(f"[RESULT] PASSED with {warnings} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
