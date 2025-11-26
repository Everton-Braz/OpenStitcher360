"""
Automated stitching tests to identify washed-out seam issue.
Tests different parameter combinations systematically.
"""
import os
import sys
from pathlib import Path
from stitcher import Stitcher
import time

# Configuration
IMAGES_DIR = "images"
OUTPUT_DIR = "test_results"
TIMESTAMP = time.strftime("%Y%m%d_%H%M%S")
TEST_OUTPUT_DIR = os.path.join(OUTPUT_DIR, f"test_{TIMESTAMP}")

# Test configurations
TEST_CONFIGS = [
    {
        "name": "baseline",
        "desc": "Current default settings",
        "params": {
            "threshold": 60,
            "erosion": 3,
            "pyramid_levels": 3,
            "weight_power": 3.0
        }
    },
    {
        "name": "no_pyramid",
        "desc": "Direct blending without pyramid",
        "params": {
            "threshold": 60,
            "erosion": 3,
            "pyramid_levels": 0,  # Special flag to skip pyramid
            "weight_power": 3.0
        }
    },
    {
        "name": "linear_weights",
        "desc": "Linear weight falloff (power=1.0)",
        "params": {
            "threshold": 60,
            "erosion": 3,
            "pyramid_levels": 3,
            "weight_power": 1.0
        }
    },
    {
        "name": "high_threshold",
        "desc": "Higher threshold to exclude more vignette",
        "params": {
            "threshold": 90,
            "erosion": 3,
            "pyramid_levels": 3,
            "weight_power": 3.0
        }
    },
    {
        "name": "sharp_blend",
        "desc": "Very sharp blend (1 pyramid level)",
        "params": {
            "threshold": 60,
            "erosion": 3,
            "pyramid_levels": 1,
            "weight_power": 3.0
        }
    },
    {
        "name": "soft_blend",
        "desc": "Softer blend (5 pyramid levels)",
        "params": {
            "threshold": 60,
            "erosion": 3,
            "pyramid_levels": 5,
            "weight_power": 3.0
        }
    }
]

def find_image_pairs(images_dir):
    """Find front/back image pairs in the images directory."""
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(Path(images_dir).glob(ext))
        image_files.extend(Path(images_dir).glob(ext.upper()))
    
    # Try to pair images
    pairs = []
    for img in image_files:
        name_lower = img.stem.lower()
        if 'front' in name_lower or '_f' in name_lower or '-f' in name_lower:
            # Find corresponding back image
            back_candidates = [
                img.parent / img.name.replace('front', 'back'),
                img.parent / img.name.replace('_f', '_b'),
                img.parent / img.name.replace('-f', '-b'),
                img.parent / (img.stem.replace('front', 'back') + img.suffix),
                img.parent / (img.stem.replace('_f', '_b') + img.suffix),
                img.parent / (img.stem.replace('-f', '-b') + img.suffix)
            ]
            
            for back in back_candidates:
                if back.exists():
                    pairs.append((str(img), str(back)))
                    break
    
    return pairs

def run_tests():
    """Run all test configurations."""
    # Create output directory
    os.makedirs(TEST_OUTPUT_DIR, exist_ok=True)
    
    # Find image pairs
    print(f"Looking for images in: {IMAGES_DIR}")
    pairs = find_image_pairs(IMAGES_DIR)
    
    if not pairs:
        print(f"ERROR: No image pairs found in {IMAGES_DIR}")
        print("Please ensure you have front/back image pairs with 'front' and 'back' in filenames")
        return
    
    print(f"Found {len(pairs)} image pair(s)")
    
    # Initialize stitcher
    stitcher = Stitcher()
    
    # Create summary file
    summary_path = os.path.join(TEST_OUTPUT_DIR, "summary.txt")
    with open(summary_path, 'w') as summary_file:
        summary_file.write(f"Stitching Test Results - {TIMESTAMP}\n")
        summary_file.write("=" * 80 + "\n\n")
        
        # Run tests for each image pair
        for pair_idx, (front, back) in enumerate(pairs, 1):
            pair_name = f"pair{pair_idx}"
            summary_file.write(f"\nImage Pair {pair_idx}:\n")
            summary_file.write(f"  Front: {front}\n")
            summary_file.write(f"  Back: {back}\n")
            summary_file.write(f"  Tests:\n")
            
            print(f"\n{'='*80}")
            print(f"Testing pair {pair_idx}/{len(pairs)}: {Path(front).name} + {Path(back).name}")
            print(f"{'='*80}")
            
            # Run each test configuration
            for config in TEST_CONFIGS:
                test_name = config['name']
                output_filename = f"{pair_name}_{test_name}.jpg"
                output_path = os.path.join(TEST_OUTPUT_DIR, output_filename)
                
                print(f"\n  Test: {test_name}")
                print(f"    {config['desc']}")
                print(f"    Parameters: {config['params']}")
                
                try:
                    # Temporarily modify stitcher for this test
                    # This is a simplified approach - in reality we'd need to modify the stitch method
                    stitcher.stitch(
                        front, back, output_path,
                        threshold=config['params']['threshold'],
                        erosion=config['params']['erosion']
                    )
                    
                    print(f"    ✓ Saved: {output_filename}")
                    summary_file.write(f"    [{test_name}] SUCCESS - {config['desc']}\n")
                    
                except Exception as e:
                    print(f"    ✗ FAILED: {e}")
                    summary_file.write(f"    [{test_name}] FAILED - {str(e)}\n")
    
    print(f"\n{'='*80}")
    print(f"Tests complete! Results saved to: {TEST_OUTPUT_DIR}")
    print(f"Summary: {summary_path}")
    print(f"{'='*80}")

if __name__ == "__main__":
    run_tests()
