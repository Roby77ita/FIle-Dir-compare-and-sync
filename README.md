# FIle-Dir-compare-and-sync
Compare and sync your files and directory
# File/Dir Compare & Sync v4.65 (by Roby 77)

**File/Dir Compare & Sync** is a professional, high-performance Python desktop application created with AI with a modern graphical user interface (GUI) designed to compare, analyze, and synchronize local directories or network shares.

Built with multi-threaded efficiency and recursive folder inspection, it is the perfect tool for backing up large media libraries, managing file shares, and tracking down differences between folders without risking data loss.

### 🚀 Key Features

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

### 🛠️ Requirements

- **Python 3.x** (with standard `tkinter` library included).
- **Cross-platform**: Optimized for Windows with legacy support for macOS and Linux file-handling.
## License & Disclaimer / Licenza e Clausola di Esclusione Responsabilità

This software is provided "as is", without warranty of any kind, express or implied. In no event shall the author (Roby77) be liable for any claim, damages, or other liability, including but not limited to data loss, arising from the use of this software.

Questo software è fornito "così com'è", senza alcuna garanzia esplicita o implicita. In nessun caso l'autore (Roby77) potrà essere ritenuto responsabile per qualsiasi reclamo, danno o altra responsabilità, inclusa la perdita di dati, derivante dall'uso di questo software.

- **FFmpeg/FFprobe** is a trademark of Fabrice Bellard (and the FFmpeg developers) and is not bundled with this application.
- **FFmpeg/FFprobe** è un marchio registrato di Fabrice Bellard (e degli sviluppatori di FFmpeg) e non è incluso in questa applicazione.
