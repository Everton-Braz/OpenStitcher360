# OpenStitcher360

A dual fisheye image stitcher for 360° cameras, creating seamless equirectangular panoramas with vibrant, artifact-free results.

## 🎯 Features

- **FFmpeg-based Fisheye Unwarping**: Leverages FFmpeg's `v360` filter for high-quality fisheye-to-equirectangular conversion
- **Simple Weighted Blending**: Direct blending approach that preserves original color vibrancy
- **No Washed-Out Colors**: Fixed the common "washed-out" artifact by using simple weighted blending instead of multi-band pyramids
- **Manual Parameter Control**: Fine-tune FOV, pitch, roll, yaw, threshold, and erosion for perfect alignment
- **Modern Web UI**: Sleek, dark-themed interface with real-time parameter adjustment
- **Flask Backend**: Lightweight Python server with OpenCV integration

## 🔧 Setup

### Prerequisites
- Python 3.7+
- FFmpeg (must be in PATH or specify path in code)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Everton-Braz/OpenStitcher360.git
   cd OpenStitcher360
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg:**
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **Linux**: `sudo apt install ffmpeg`
   - **macOS**: `brew install ffmpeg`

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Open your browser at** `http://127.0.0.1:5000`

## 📖 Usage

1. Upload **Front Lens** and **Back Lens** images from your 360° camera
2. Adjust parameters using the manual controls:
   - **FOV**: Field of view (typically 190-200°)
   - **Threshold**: Brightness threshold for masking (20-90)
   - **Erosion**: Edge removal iterations (3-60)
   - **Pitch/Roll/Yaw**: Lens orientation adjustments
3. Click **Stitch Images**
4. Download the seamless equirectangular result

## 🎨 Optimal Settings (Example)

Based on successful testing, here are example settings that produced seamless results:

- **FOV**: 192
- **Threshold**: 30
- **Erosion**: 45
- **Front Lens**:
  - Yaw: 0, Pitch: 6, Roll: 1.13
- **Back Lens**:
  - Yaw: 180, Pitch: 6, Roll: 0, Shift Y: -3

*Note: Optimal settings vary by camera model and image content.*

## 🐛 Known Issues & Fixes

### ✅ Fixed: Washed-Out Colors

**Problem**: Stitched images appeared washed-out with low contrast and saturation.

**Root Cause**: Multi-band Laplacian pyramid blending was averaging colors across frequency bands, reducing overall vibrancy.

**Solution**: Switched to **simple weighted blending** based on distance transform weights. This preserves original pixel values while still creating smooth transitions.

**Code Changes** (in `stitcher.py`):
- Disabled FFmpeg circular masking (line 19: `if False and mask_radius > 0:`)
- Replaced pyramid blending with direct weighted blend (line 293: `USE_SIMPLE_BLEND = True`)

## 🏗️ Technical Approach

1. **Unwarp**: FFmpeg's `v360` filter converts dual fisheye to equirectangular
2. **Mask Generation**: Distance transform creates smooth blending weights
3. **Simple Blend**: Direct weighted average preserves color vibrancy
4. **No Pyramids**: Avoids the color degradation from multi-band blending

## 📁 Project Structure

```
OpenStitcher360/
├── app.py                  # Flask web server
├── stitcher.py             # Core stitching logic
├── templates/
│   └── index.html          # Web UI
├── static/
│   ├── css/style.css       # Glassmorphism styling
│   ├── js/script.js        # Frontend logic
│   └── results/            # Output directory
└── requirements.txt        # Python dependencies
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

Built as an open-source alternative to proprietary 360° camera SDKs, leveraging the power of FFmpeg and OpenCV.

