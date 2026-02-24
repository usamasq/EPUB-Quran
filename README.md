# EPUB Quran - Indo-Pak Script Editions

A production-oriented Quran EPUB pipeline with multiple build variants, reader compatibility profiles, release automation, and validation checks.

Compiled and maintained by **[Usama Bin Shahid](https://www.linkedin.com/in/usamasq/)**.

[![Live Static Page](https://img.shields.io/badge/Website-Download%20Page-1f6d4b)](https://usamasq.github.io/EPUB-Quran/)

## Start Here (GitHub Visitors)

- **Static download page:** [https://usamasq.github.io/EPUB-Quran/](https://usamasq.github.io/EPUB-Quran/)
- **Tagged releases:** [https://github.com/usamasq/EPUB-Quran/releases](https://github.com/usamasq/EPUB-Quran/releases)
- **Latest direct downloads (one-click):**
  - [Holy_Quran_full.epub](https://github.com/usamasq/EPUB-Quran/releases/latest/download/Holy_Quran_full.epub)
  - [Holy_Quran_full_compat.epub](https://github.com/usamasq/EPUB-Quran/releases/latest/download/Holy_Quran_full_compat.epub)
  - [Holy_Quran_lite.epub](https://github.com/usamasq/EPUB-Quran/releases/latest/download/Holy_Quran_lite.epub)
  - [Holy_Quran_lite_compat.epub](https://github.com/usamasq/EPUB-Quran/releases/latest/download/Holy_Quran_lite_compat.epub)
  - [SHA256SUMS.txt](https://github.com/usamasq/EPUB-Quran/releases/latest/download/SHA256SUMS.txt)

If someone lands on the repository homepage first, this section is the direct path to the static site and all downloadable EPUB variants.

## Release Downloads

All downloadable files are published per tag in GitHub Releases:

- [GitHub Releases](https://github.com/usamasq/EPUB-Quran/releases)
- [Project Download Page](https://usamasq.github.io/EPUB-Quran/)

Each tagged release includes:

- `Holy_Quran_full.epub`
- `Holy_Quran_full_compat.epub`
- `Holy_Quran_lite.epub`
- `Holy_Quran_lite_compat.epub`
- `SHA256SUMS.txt`

If an older tag is missing new variant files, run the **Release EPUB** workflow manually from GitHub Actions with the existing exact `tag_name` (for example `v1.1.0`, not `v1.1*`) to refresh assets for that tag.

## Build Targets

- `full`: Enhanced typography profile, no surah chunking.
- `full_compat`: Compatibility profile with long-surah chunking.
- `lite`: Lighter visual profile with long-surah chunking.
- `lite_compat`: Most conservative compatibility + tighter chunking.

## Local Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Build all variants:

```bash
python scripts/quran_reader_pro.py
```

Build specific targets:

```bash
python scripts/quran_reader_pro.py --targets full lite
```

## Validation and Quality Gates

Source data lint:

```bash
python scripts/lint_quran_source.py
```

EPUB structural + regression checks:

```bash
python scripts/check_epub_regressions.py
```

Optional Kindle Previewer conversion check:

```bash
python scripts/check_kindle_previewer.py --command-template "\"C:/Path/To/Kindle Previewer 3.exe\" -convert \"{epub}\" -output \"{out_dir}\""
```

## Reader Behavior Notes

- Single-ruku surahs intentionally suppress ruku marker display.
- Quranic annotation mark sequences are normalized with thin spacing to avoid overlap.
- Sajdah symbols are styled consistently and deduplicated.
- Embedded font metadata is tuned for broader EPUB engine compatibility.

## Device Matrix (Recommended)

| Device/Reader | Recommended File |
|---|---|
| Kindle (modern firmware) | `Holy_Quran_full.epub` |
| Kindle (older firmware) | `Holy_Quran_full_compat.epub` |
| Android Lithium / mixed engines | `Holy_Quran_lite_compat.epub` |
| Android Moon+ / KOReader | `Holy_Quran_lite.epub` |
| Apple Books | `Holy_Quran_full.epub` |

## Data Credits

- Quran text source: [Tarteel QUL](https://qul.tarteel.ai/)
- Structural mapping references: [AlQuran.cloud](https://alquran.cloud/)
- Typeface: AlQalam Quran IndoPak

## CI and Release

- `.github/workflows/ci.yml` runs lint, build, regression checks, and `epubcheck` on push/PR.
- `.github/workflows/release.yml` runs the same validations on tag push (`v*`) and uploads all EPUB assets + checksums to the tag release.

## License

MIT License.
