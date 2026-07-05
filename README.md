# 🎬 GIF Snipper

![GIF Snipper Demonstration](https://github.com/albatrossSKY/gif-snipper/blob/main/snipgif.gif?raw=true)
![GIF Snipper photo](https://github.com/albatrossSKY/gif-snipper/blob/main/gifsnipper.png?raw=true)
![GIF Snipper photo1](https://github.com/albatrossSKY/gif-snipper/blob/main/gifsnipper1.png?raw=true)

A high-performance Windows desktop application that captures selected screen regions and records them directly into animated GIFs. It includes a post-capture editor for spatial cropping, timeline trimming, scaling, drawing annotations, redacting sensitive content, and instant sharing.

---

## ✨ Features

### 1. Snipping & Live Capture
- **DPI-Aware Region Snipping**: A full-screen overlay that darkens the display, allowing click-and-drag selection of target coordinates. Matches Windows display scaling perfectly.
- **Flashing Red Border Frame**: Displays a pulsing red frame exactly around the capturing area, confirming what is being recorded in real-time.
- **Draggable Status Widget**: A floating bar showing elapsed time, frame count, and a "Stop" button. Can be dragged anywhere on the screen if it blocks content.
- **Global Stop Hook**: Press `Esc` globally from any window to immediately stop recording and open the Editor.

### 2. Editor Workspace (WYSIWYG)
- **Loop Preview Player**: Plays back your recorded frames in a continuous loop.
- **Visual Spatial Cropping**: Re-adjust your screen crop dynamically by dragging corner/edge handles on the canvas player.
- **Timeline Trimming (Clip)**: A custom dual-handle range slider at the bottom of the player to trim out unwanted start or end frames.
- **Scaling / Resizing**: Scale down the GIF dimensions (75%, 50%, 25%, or custom sizes) with automatic aspect-ratio lock.

### 3. Annotations & Redactions
- **Freehand Brush 🖌**: Draw lines in multiple stroke sizes.
- **Vector Arrow Tool ↗**: Draw pointing arrows that automatically calculate and paint sharp pointed arrowheads at the destination coordinate.
- **Highlight Overlay 🖍**: Draw semi-transparent highlighter blocks (ideal for highlighting buttons or text).
- **Redaction Box ⬛**: Draw opaque solid black blocks to censor passwords, emails, API keys, or private data.
- **Color Swatches & Size Slider**: Choose from multiple colors (Red, Yellow, Green, Blue, White, Black) and adjust brush size from 2px to 20px.

### 4. Smart Exporter & Clipboard Integration
- **Copy to Clipboard 📋**: Compiles and copies the animated GIF directly to your system clipboard using native Windows file-drop formats (via PowerShell). Paste it instantly (`Ctrl + V`) into Discord, Slack, Microsoft Teams, Outlook, or Explorer folders.
- **Size Optimization ⚡**:
  - *Quantization*: Reduce color palette limit (256, 128, 64, 32 colors) to save bandwidth.
  - *Frame Skipping*: Skip every 2nd or 3rd frame (halving or tripling frame count) while scaling duration delays to maintain correct playback speed.

---

## 🚀 Getting Started

### Prerequisites
- Windows OS (designed and tested for Windows 10/11)
- Python 3.10+

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/gif-snipper.git
   cd gif-snipper
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

---

## 🛠 Project Structure

- `main.py`: Entry point and Control Dashboard panel.
- `capture_overlay.py`: Full-screen snip selection canvas.
- `recorder.py`: Screen grabbing loop running on background thread, transparent border frame, and global Escape key hooks.
- `editor.py`: Interactive timeline slider, spatial crop overlay, drawing logic, optimization controls, and GIF compiler.
- `theme.py`: Color palette variables and flat widget styling rules.
- `requirements.txt`: Python package requirements.
- `.gitignore`: Avoids committing system caches, local temporary files, and output GIFs.
