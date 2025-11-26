import os
import itertools
from stitcher import Stitcher

def batch_test():
    # 1. Setup
    img1_path = os.path.abspath("static/uploads/lens_01.png")
    img2_path = os.path.abspath("static/uploads/lens_02.png")
    
    if not os.path.exists(img1_path) or not os.path.exists(img2_path):
        print(f"Error: Could not find input images at {img1_path} or {img2_path}")
        # Fallback to checking if user provided other names, but for now let's error out or ask user to rename
        return

    output_dir = "batch_results"
    os.makedirs(output_dir, exist_ok=True)
    
    stitcher = Stitcher()
    
    # 2. Define Parameter Ranges
    # Adjust these ranges based on what you want to test
    
    # Alignment Parameters
    yaw_b_values = [179.0, 179.5, 180.0, 180.5, 181.0]
    shift_x_b_values = [-10, -5, 0, 5, 10]
    
    # Masking Parameters
    # Assuming user found ~1380 to be good, let's test around that
    mask_radius_values = [1370, 1380, 1390] 
    
    # Blending Parameters
    threshold_values = [40, 60]
    erosion_values = [60, 80]
    
    # Fixed Parameters
    fov = 192
    pitch_f = 6
    roll_f = 1.1
    pitch_b = 6
    roll_b = 0
    
    # 3. Generate Combinations
    # We use itertools.product to generate all combinations
    # Be careful! 5 * 5 * 3 * 2 * 2 = 300 combinations. That's a lot.
    # Let's reduce the scope for the first run or prioritize.
    
    # Strategy: Test Alignment first (Yaw/Shift) with fixed Mask/Blend
    print("--- Phase 1: Alignment Testing ---")
    combinations_alignment = list(itertools.product(yaw_b_values, shift_x_b_values))
    
    fixed_mask = 1380
    fixed_thresh = 50
    fixed_erosion = 80
    
    total = len(combinations_alignment)
    print(f"Generating {total} images for alignment test...")
    
    for i, (yaw, shift) in enumerate(combinations_alignment):
        filename = f"align_Y{yaw}_S{shift}.jpg"
        output_path = os.path.join(output_dir, filename)
        
        print(f"[{i+1}/{total}] Stitching: Yaw={yaw}, Shift={shift}")
        
        try:
            stitcher.stitch(
                img1_path, img2_path, output_path,
                fov=fov,
                yaw_f=0, pitch_f=pitch_f, roll_f=roll_f, shift_x_f=0, shift_y_f=0, mask_radius_f=fixed_mask,
                yaw_b=yaw, pitch_b=pitch_b, roll_b=roll_b, shift_x_b=shift, shift_y_b=0, mask_radius_b=fixed_mask,
                threshold=fixed_thresh, erosion=fixed_erosion
            )
        except Exception as e:
            print(f"Failed to stitch {filename}: {e}")

    # Strategy: Test Masking second (Radius/Thresh/Erosion) with fixed Alignment
    # Let's assume Yaw=180, Shift=0 is "okay" for now, or pick the best from Phase 1 manually.
    # For this script, I'll comment it out to save time, or run a small subset.
    
    print("\nBatch processing complete. Check the 'batch_results' folder.")

if __name__ == "__main__":
    batch_test()
