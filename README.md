# EPUB Quran - Traditional Indo-Pak Script Edition

[![Version](https://img.shields.io/badge/Version-1.0-green.svg)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A beautifully formatted digital edition of the **Holy Quran** in the traditional **Indo-Pak (South Asian)** script, specifically optimized for **Kindle** and other E-ink e-readers. This project focuses on high-quality typography, professional layout, and robust rendering for authentic Quranic reading.

## 📥 Download v1.0

You can download the pre-built EPUB directly from the **[Releases](https://github.com/usamasq/EPUB-Quran/releases)** section of this repository.

- **[Download Holy_Quran.epub (v1.0)](https://github.com/usamasq/EPUB-Quran/releases/tag/v1.0)**

## 🌟 Key Features

- **Authentic Indo-Pak Script**: Powered by high-resolution Nastaliq-style fonts for a traditional South Asian reading experience.
- **Kindle & E-ink Optimized**: Custom CSS and character encoding fixes resolve common e-reader issues like overlapping Ayah markers and clipped Waqf (pause) signs.
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

## 🗺️ Roadmap

We are committed to continuously improving this project for the Ummah. Planned features include:

- [ ] **Interactive Tafsir**: Integration of classical South Asian Tafasir available in a popup or toggle mode.
- [ ] **Word-for-Word Translation**: Urdu and English word-for-word translations for enhanced learning.
- [ ] **Custom Style Presets**: Native support for more e-reader themes and font size variations.
- [ ] **Audio Synchronization**: Potential for Media Overlay support to sync with popular recitations.
- [ ] **Web-Based Personalization**: A simple web tool to generate a custom EPUB with specific translations or scripts.

## 📄 License

This project is released under the **MIT License**. It is open-source and intended for the benefit of the global Muslim community.

---
*Developed with ❤️ for the benefit of the Ummah.*
