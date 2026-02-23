# EPUB Quran - Traditional Indo-Pak Script Edition

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A beautifully formatted digital edition of the **Holy Quran** in the traditional **Indo-Pak (South Asian)** script, specifically optimized for **Kindle** and other E-ink e-readers. This project focuses on high-quality typography, professional layout, and robust rendering for authentic Quranic reading.

## 🌟 Key Features

- **Authentic Indo-Pak Script**: Powered by high-resolution Nastaliq-style fonts for a traditional South Asian reading experience.
- **Kindle & E-ink Optimized**: custom CSS and character encoding fixes resolve common e-reader issues like overlapping Ayah markers and clipped Waqf (pause) signs.
- **Mushaf-Style Flow**: Continuous, justified text blocks that replicate the feel of a physical Mushaf while maintaining digital responsiveness.
- **Precise Metadata**: Accurate Juz (Parah) boundaries and Ruku markers, all beautifully formatted.
- **Clean & Fast**: Stripped of font-specific PUA artifacts and hidden control characters, ensuring a lightweight and bug-free EPUB.

## 👤 Credits & Attribution

This project was envisioned and developed by **Usama Bin Shahid**.

- **Source Text**: The authentic Indo-Pak Quranic text data was beautifully digitized and sourced from **Tarteel QUL**.
- **Metadata Support**: Juz, Ruku, and Page boundary mappings were algorithmically derived using the **AlQuran.cloud API**.
- **Typography**: The project utilizes the elegant **AlQalam Quran IndoPak** font to ensure an authentic South Asian aesthetic.

## 🚀 How to Use

### Installation
Ensure you have Python 3.8+ installed. Install the required ebook library dependencies:

```bash
pip install EbookLib lxml Pillow
```

### Build the Quran
Run the main publication script to generate your personal `Holy_Quran.epub`:

```bash
python quran_reader_pro.py
```

## 🛠️ Project Architecture

- **`quran_reader_pro.py`**: The core publication engine and layout orchestrator.
- **`indopak.json`**: Comprehensive source text database.
- **`quran_maps.py`**: Local mappings for Surah names and Juz starts.
- **`fonts/`**: Contains the critical `IndoPakQuran.ttf` asset.
- **`cover.png`**: High-contrast, minimal vector art cover design.

## 📄 License

This project is released under the **MIT License**. It is open-source and intended for the benefit of the global Muslim community.

---
*Developed with ❤️ for the benefit of the Ummah.*
