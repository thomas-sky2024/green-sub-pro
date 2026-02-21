# GreenSub Pro

GreenSub Pro is a powerful, standalone desktop application built for content creators and video editors to quickly render subtitle files (SRT, ASS, VTT) onto solid background colors (green screen, blue screen, etc.) alongside the original audio track.

Built explicitly with optimization in mind, GreenSub Pro utilizes native UI components (PySide6) and a robust FFmpeg backend capable of tapping into Apple Silicon (M1/M2/M3) hardware-accelerated encoding via VideoToolbox.

---

## 🌟 Key Features

- **Blazing Fast Rendering:** Supports hardware-accelerated H.264 and HEVC encoding via Apple VideoToolbox, alongside high-quality CPU encoders (libx264/libx265).
- **Live Preview:** Real-time seeking and frame previews. Instantly visualize your subtitle formatting before rendering.
- **Advanced Subtitle Styling:** Fully customize your text!
  - **Typography:** Font family, Size, Bold, Italic formatting.
  - **Colors:** Text Color, Outline Color, and Outline Opacity sliders.
  - **Placement:** Vertical Margin positioning and Drop Shadow adjustments.
- **Professional Guidelines:** Includes toggles for Title Safe (80%) and Action Safe (90%) boundaries, supporting both Landscape (16:9) and Portrait (9:16) rendering.
- **Drag & Drop:** Streamlined media ingestion via a unified drag-and-drop queue for Video/Audio and Subtitle tracks.

---

## 📸 Screenshots

> *Add your awesome application screenshots here!*
> 
> *Example format:* `![GreenSub Pro Main Window](assets/screenshot.png)`

---

## 🏗 Architecture

GreenSub Pro is designed with a clean, decoupled architecture separating the User Interface from the core video processing logic.

### Tech Stack
- **UI Framework:** PySide6 (Qt for Python)
- **Engine Core:** Python 3 + FFmpegCLI
- **Hardware Acceleration:** Native FFmpeg VideoToolbox binding for macOS.

### Key Modules
1. **`ui/` (User Interface):**
   - `main_window.py`: The central application window, managing layout, panels, property grids, and preview scaling.
   - `drag_drop.py`: Subclassed widgets for handling system file drops.
2. **`core/` (Rendering Engine):**
   - `ffmpeg_builder.py`: A stateless CLI generator that translates Python and UI properties into safe, complex FFmpeg `filter_complex` graphs.
   - `ffmpeg_runner.py`: The asynchronous subprocess executor that handles process piping, progress polling, and error reporting without freezing the UI.
   - `media_engine.py`: The top-level facade combining the builder and runner to trigger previews and handle render jobs.
   - `subtitle_manager.py`: Parses `.srt` timecodes to provide the UI with an interactive timeline/cue list.
3. **`tests/`:** Comprehensive unit and integration test suite asserting the stability of string escaping and filter generation.

---

## 🚀 How to Use

### 1. Requirements

- **Python 3.10+**
- **FFmpeg:** Must be installed and accessible in your system's PATH.
  ```bash
  brew install ffmpeg
  ```

### 2. Installation

Clone the repository and install the Python dependencies:

```bash
git clone https://github.com/thomas-sky2024/green-sub-pro.git
cd green-sub-pro

# (Optional but recommended) Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```
*(Note: If `requirements.txt` is missing, you can generate it using `pip freeze > requirements.txt` or manually install PySide6 via `pip install PySide6`)*

### 3. Running the App

```bash
python main.py
```

### 4. Basic Workflow

1. **Load Media:** Drag and drop your source video (or audio) file into the "Media Files" list. 
2. **Load Subtitles:** Drag and drop your corresponding `.srt`, `.vtt`, or `.ass` file.
3. **Customize Style:** Use the right-hand panel to pick your font, colors, stroke thickness, and positioning. Scrub the timeline to preview the exact look.
4. **Set Render Settings:** 
   - Choose a background (Green, Blue, or Custom Chrome Color).
   - Pick your encoder (e.g., `hevc_videotoolbox` for M1/M2 Macs).
   - Choose the Quality and Format container.
5. **Render Export:** Click `▶ Start Rendering`, select a save location, and watch it fly!

---

## 🛠 Testing

GreenSub Pro includes a robust test suite for the internal FFmpeg query builder to ensure path escaping, colour code formatting (`&H00...`), and string rendering behaves consistently across platforms.

To run the tests:
```bash
python -m unittest discover tests
```

---

## 🤝 Contributing
Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/thomas-sky2024/green-sub-pro/issues).

## 📝 License
This project is for personal or commercial use. Please ensure you comply with the FFmpeg distribution licenses if bundling the standalone application.
