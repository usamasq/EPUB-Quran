import re

with open(r'c:\Users\usama\Desktop\EPUB Quran\README.md', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace Header and Intro
intro_replacement = '''# EPUB Quran

EPUB Quran is a meticulously compiled, single-file Arabic Quran explicitly optimized for e-readers (Kindle, Kobo) and mobile reading apps. It features crash-free rendering, optimized typography for small screens, and proper Arabic text alignment.

Compiled and maintained by **[Usama Bin Shahid](https://www.linkedin.com/in/usamasq/)**.

[![Live Static Page](https://img.shields.io/badge/Website-Download%20Page-1f6d4b)](https://usamasq.github.io/EPUB-Quran/)

## Important Features
- **Crash-Free E-Reader Compatibility**: Long Surahs are intelligently split into smaller chapters to prevent out-of-memory crashes on Kindle and older e-readers.
- **Optimized Mobile Typography**: Font sizing and spacing are explicitly optimized for mobile devices and smaller screens.
- **Universal Support**: One standard `.epub` file provides comprehensive compatibility across Apple Books, Android readers, and Kindle.
- **Responsive Arabic Text**: Relies on native reader fonts to ensure smooth rendering and rapid page-turns without embedding bloated typography files.
'''
text = re.sub(
    r'^# EPUB Quran - Indo-Pak Script Editions\n\nA production-oriented Quran EPUB pipeline with multiple build variants.*?\[!\[Live Static Page\].*?\n',
    intro_replacement,
    text, flags=re.DOTALL
)

# Remove old Build Targets and Device Matrix sections completely
# Also clean up the Each tagged release includes part that the powershell script missed
text = re.sub(
    r'Each tagged release includes:\n\n- `Holy_Quran_full\.epub`\n- `Holy_Quran_full_compat\.epub`\n- `Holy_Quran_lite\.epub`\n- `Holy_Quran_lite_compat\.epub`\n- `SHA256SUMS\.txt`',
    'Each tagged release includes:\n\n- `Holy-Quran.epub`\n- `SHA256SUMS.txt`',
    text, flags=re.DOTALL
)

text = re.sub(
    r'## Build Targets\n\n- `full`: Enhanced typography profile, no surah chunking\.\n- `full_compat`: Compatibility profile with long-surah chunking\.\n- `lite`: Lighter visual profile with long-surah chunking\.\n- `lite_compat`: Most conservative compatibility \+ tighter chunking\.\n\n',
    '',
    text, flags=re.DOTALL
)

text = re.sub(
    r'## Device Matrix \(Recommended\)\n\n\| Device/Reader \| Recommended File \|\n\|---\|---\|\n\| Kindle \(modern firmware\) \| `Holy_Quran_full\.epub` \|\n\| Kindle \(older firmware\) \| `Holy_Quran_full_compat\.epub` \|\n\| Android Lithium / mixed engines \| `Holy_Quran_lite_compat\.epub` \|\n\| Android Moon\+ / KOReader \| `Holy_Quran_lite\.epub` \|\n\| Apple Books \| `Holy_Quran_full\.epub` \|\n\n',
    '',
    text, flags=re.DOTALL
)

# Fix build commands
text = text.replace(
    'Build all variants:\n\n```bash\npython scripts/quran_reader_pro.py\n```\n\nBuild specific targets:\n\n```bash\npython scripts/quran_reader_pro.py --targets full lite\n```',
    'Build the EPUB:\n\n```bash\npython scripts/quran_reader_pro.py\n```'
)

with open(r'c:\Users\usama\Desktop\EPUB Quran\README.md', 'w', encoding='utf-8') as f:
    f.write(text)
