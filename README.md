# Batch Image Converter Pro

A high-performance, multithreaded graphical user interface (GUI) built in Python for batch image processing. This application acts as a front-end wrapper for the powerful ImageMagick engine, allowing users to visually manage bulk image conversions, resizing, and watermarking without needing to touch the command line.

![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green.svg)
![ImageMagick](https://img.shields.io/badge/Engine-ImageMagick-orange.svg)
![License](https://img.shields.io/badge/License-MIT-blue.svg)

## ✨ Features
* **100% Portable:** The ImageMagick engine is fully bundled into the executable. No installation or system PATH configurations are required for end-users.
* **Parallel Processing Engine:** Utilizes Python's `ThreadPoolExecutor` to process multiple images simultaneously across available CPU cores, drastically reducing conversion time for massive batches while preventing I/O bottlenecks.
* **WYSIWYG Visual Watermarking:** Features a draggable, scroll-to-resize graphical watermark object. The UI calculates exact affine scaling translations to accurately map visual coordinates to the final high-resolution output.
* **Smart Drag & Drop Queue:** Append files from multiple directories into a dynamic visual `QListWidget` queue.
* **Non-Destructive Editing:** Automatically appends `_edited` to output files to protect original source data from being overwritten.
* **Privacy Controls:** One-click option to strip EXIF metadata and hidden GPS coordinates from output files.

## 🚀 Installation & Usage

### For Standard Users (Windows)
1. Go to the **Releases** section on the right side of this page.
2. Download `converter.exe`.
3. Double-click to run. No installation required.

### For Developers (Running from Source)
If you wish to run the code directly or compile it yourself:
1. Clone the repository:
   ```bash
   git clone [https://github.com/HoneyBeans/Batch-Image-Converter-Pro.git](https://github.com/HoneyBeans/Batch-Image-Converter-Pro.git)
