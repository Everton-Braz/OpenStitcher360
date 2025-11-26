import cv2
import numpy as np
import os

def detect_lens_circle(image_path):
    print(f"Processing {image_path}...")
    img = cv2.imread(image_path)
    if img is None:
        print("Failed to load image")
        return 0

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # 1. Threshold to separate image from black background
    # Fisheye images usually have a sharp transition to black
    # We use a low threshold (e.g., 20) to catch the image content
    _, thresh = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)

    # 2. Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        print("No contours found")
        return 0

    # 3. Find largest contour (assumed to be the lens circle)
    largest_contour = max(contours, key=cv2.contourArea)

    # 4. Find enclosing circle
    ((cx, cy), radius) = cv2.minEnclosingCircle(largest_contour)
    
    print(f"Detected Center: ({cx:.1f}, {cy:.1f})")
    print(f"Detected Radius: {radius:.1f}")
    
    # Verify if it makes sense (should be roughly half the image size)
    # The lens circle might be slightly larger than the image if cropped, 
    # or smaller if fully contained.
    
    # We want a radius that is slightly smaller than the physical edge to cut it off.
    # So we might want to subtract a small safety margin (e.g. 1-2%)
    safe_radius = radius * 0.99
    print(f"Recommended Safe Radius: {safe_radius:.1f}")

    return int(safe_radius)

# Test on the uploaded image
# Note: The user uploaded 'uploaded_image_1764012155737.png'
# I need to find where it is or use a placeholder if I can't access it directly.
# I will assume it's in the current directory or I'll search for it.
# For now, I'll search for png files in the workspace.

if __name__ == "__main__":
    # Find a png file to test with
    files = [f for f in os.listdir('.') if f.endswith('.png') or f.endswith('.jpg')]
    if files:
        # Prefer the one with 'uploaded' in name
        uploaded = [f for f in files if 'uploaded' in f]
        target = uploaded[0] if uploaded else files[0]
        detect_lens_circle(target)
    else:
        print("No images found to test")
