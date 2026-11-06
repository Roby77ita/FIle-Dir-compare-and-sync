# File/Dir Compare & Sync (by Roby 77)

[![Version](https://img.shields.io/badge/version-5.54-blue.svg)](https://github.com/Roby77ita/FIle-Dir-compare-and-sync/releases)
[![Python](https://img.shields.io/badge/python-3.x-yellow.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

A powerful **file synchronization** and **directory comparison** tool for Windows, perfect for **backup** and **NAS management**.

**File/Dir Compare & Sync** is a professional, high-performance Python desktop application with a modern graphical user interface (GUI) designed to compare, analyze, and synchronize local directories or network shares.

Built with multi-threaded efficiency and recursive folder inspection, it is the perfect tool for backing up large media libraries, managing file shares, and tracking down differences between folders without risking data loss.

## 📸 Screenshots
*(Sostituisci questo testo con un'immagine del tuo programma. Trascina un'immagine nel file README su GitHub per caricarla automaticamente e generare il link!)*
![File/Dir Compare & Sync Interface](link_alla_tua_immagine_qui.png)

## 🚀 Key Features

- **Parallel & Fast Directory Scanning**: Scans source and destination paths efficiently. If folders are located on separate physical volumes, the application forces parallel scanning to maximize performance on modern hardware.
- **Intuitive Visual Grid & Comparison Legend**: Displays a side-by-side folder structure highlighting file status at a glance:
  - **Identical Items** (White)
  - **Missing Elements** (Red)
  - **Size Discrepancies** (Yellow)
  - **Newer/Older Dates** (Green/Orange)
- **Smart Synchronization Options**:
  - **Copy Changes**: Copies missing or modified files from left to right without altering extra items in the destination folder.
  - **Mirror Sync (1 → 2)**: Replicates the source folder perfectly into the destination, updating changes and safely removing orphan files from the target drive after explicit user confirmation.
  - **Subfolder Grouping**: Option to automatically synchronize inside a folder matching the source's name within the target path.
- **Safe Operations & Interruption Handling**: Features a non-blocking background process and a dedicated copy-progress window with real-time speed metrics and time remaining. If stopped, it safely reports and counts the exact files left to copy.
- **Advanced Display Filters**: Filter both view trees instantly by missing items, date variations, size mismatches, or utilizing a live regex text search. Includes a smart **"Similar Names" filter** to identify duplicate copies or case-mismatches.
- **Windows Built-in Fixes & Admin Tools**: Detects Windows "Access Denied" errors and provides a one-click **"Repair Permissions" button** to safely reset folder ownership and full control rights via `icacls`.
- **Modern Look with Custom Themes**: Features adjustable GUI layouts with multiple dark/light theme accents (Modern, Dark, Blue, Purple, Dark Gray) and crisp text rendering for HiDPI/4K displays.
- **Profile Management**: Save and recall named configurations for your frequent source and destination combinations with a single click.

## 🛠️ Installation & Usage

1. Ensure you have **Python 3.x** installed on your system (with the standard `tkinter` library included).
2. Go to the [Releases](https://github.com/Roby77ita/FIle-Dir-compare-and-sync/releases) page and download the latest `.py` file.
3. Open your terminal or command prompt and run the application:
   ```bash
   python File_Dir_Compare_Sync_5_54.py
4. How to use: Select your Source folder (Left) and Destination folder (Right), click "Confronta" (Compare) to view differences, and then use "Copia modifiche" (Copy changes) or "Sincronizza 1 → 2" (Sync) to apply your changes safely.

📋 Requirements
Python 3.x (with standard tkinter library included).

Cross-platform: Optimized for Windows with legacy support for macOS and Linux file-handling.

🤝 Contributing & Support
If you encounter any bugs or have suggestions, please open an Issue.

📄 License & Disclaimer / Licenza e Clausola di Esclusione Responsabilità
This software is provided "as is", without warranty of any kind, express or implied. In no event shall the author (Roby77) be liable for any claim, damages, or other liability, including but not limited to data loss, arising from the use of this software.

Questo software è fornito "così com'è", senza alcuna garanzia esplicita o implicita. In nessun caso l'autore (Roby77) potrà essere ritenuto responsabile per qualsiasi reclamo, danno o altra responsabilità, inclusa la perdita di dati, derivante dall'uso di questo software.

<img width="1912" height="1131" alt="screen" src="https://github.com/user-attachments/assets/3c6167b7-9feb-4417-8a64-dad2ffae7f14" />

