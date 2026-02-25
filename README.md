# EPUB Quran

EPUB Quran is a meticulously compiled, single-file Arabic Quran explicitly optimized for e-readers (Kindle, Kobo) and mobile reading apps. It features crash-free rendering, optimized typography for small screens, and proper Arabic text alignment.

Compiled and maintained by **Usama Bin Shahid** ([usamasq@gmail.com](mailto:usamasq@gmail.com)).

[![Live Static Page](https://img.shields.io/badge/Website-Download%20Page-1f6d4b)](https://usamasq.github.io/EPUB-Quran/)

## Important Features
- **Complete Built-in Tafsir**: This EPUB includes **all 114 chapters of English Tafsir** directly inside the book. Every single Arabic Ayah marker serves as a direct, clickable hyperlink jumping straight to its contextual explanation, with a back-link to return exactly to where you were reading.
- **Authentic Mushaf Layout**: Features full block justification, tighter line-height parity, beautifully ornate Surah headers, and Ornate Parentheses for Ayah markers, replicating a traditional physical page.
- **Native Dark Mode**: Fully supports E-Reader dark modes (`@media prefers-color-scheme: dark`) with inverted colors and preserved contrast.
- **Crash-Free E-Reader Compatibility**: Long Surahs are intelligently split into smaller 70-Ayah chapters to prevent out-of-memory crashes on Kindle and older e-readers.
- **Universal Support**: One standard `.epub` file provides comprehensive compatibility across Apple Books, Android readers, and Kindle.
- **Responsive Arabic Text**: Relies on native reader fonts to ensure smooth rendering and rapid page-turns without embedding bloated typography files.

## Reporting Errors
This text has been carefully compiled from open-source databases. However, because it is rendered dynamically, **we ask all readers to please report any textual errors, missing letters, or formatting issues.** If you spot anything that looks incorrect, contact us immediately at [usamasq@gmail.com](mailto:usamasq@gmail.com) so we can issue a fix.

## Start Here (GitHub Visitors)

- **Static download page:** [https://usamasq.github.io/EPUB-Quran/](https://usamasq.github.io/EPUB-Quran/)
- **Tagged releases:** [https://github.com/usamasq/EPUB-Quran/releases](https://github.com/usamasq/EPUB-Quran/releases)
- **Latest direct downloads (one-click):**
  - [Holy Quran.epub](https://github.com/usamasq/EPUB-Quran/releases/latest/download/Holy%20Quran.epub)
  - [SHA256SUMS.txt](https://github.com/usamasq/EPUB-Quran/releases/latest/download/SHA256SUMS.txt)

If someone lands on the repository homepage first, this section is the direct path to the static site and the downloadable EPUB.

## Release Downloads

All downloadable files are published per tag in GitHub Releases:

- [GitHub Releases](https://github.com/usamasq/EPUB-Quran/releases)
- [Project Download Page](https://usamasq.github.io/EPUB-Quran/)

Each tagged release includes:

- `Holy Quran.epub`
- `SHA256SUMS.txt`

If an older tag is missing the correct file, run the **Release EPUB** workflow manually from GitHub Actions with the existing exact `tag_name` (for example `v1.1.0`, not `v1.1*`) to refresh assets for that tag.

## Local Usage

Install dependencies:

```bash
pip install -r requirements.txt
```

Build the EPUB:

```bash
python scripts/quran_reader_pro.py
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
- Arabic rendering relies on each reader's native system serif/Arabic fonts (Kindle-first behavior).

## Data Credits

- Quran text source: [Tarteel QUL](https://qul.tarteel.ai/)
- Structural mapping references: [AlQuran.cloud](https://alquran.cloud/)
- Typeface strategy: native system serif/Arabic fonts per reader engine, optimized with a large base font size and full justification for parity with English books.

## CI and Release

- `.github/workflows/ci.yml` runs lint, build, regression checks, and `epubcheck` on push/PR.
- `.github/workflows/release.yml` runs the same validations on tag push (`v*`) and uploads all EPUB assets + checksums to the tag release.

## License

MIT License.
