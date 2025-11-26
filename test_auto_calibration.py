"""
Test script for automatic calibration module.

This script tests the auto-calibration functionality on test images.
"""

import sys
import os
from auto_calibrator import AutoCalibrator
from stitcher import Stitcher


def test_auto_calibration():
    """Test automatic parameter calibration."""
    print("=" * 60)
    print("AUTO-CALIBRATION TEST")
    print("=" * 60)
    
    # Check if test images exist
    img1_path = "images/test_front.jpg"
    img2_path = "images/test_back.jpg"
    
    if not os.path.exists("images"):
        print("Error: 'images' directory not found")
        print("Please create an 'images' directory with test_front.jpg and test_back.jpg")
        return False
    
    if not os.path.exists(img1_path) or not os.path.exists(img2_path):
        print(f"Error: Test images not found")
        print(f"Looking for: {img1_path} and {img2_path}")
        print("\nPlease provide test fisheye images:")
        print("  - images/test_front.jpg (front fisheye)")
        print("  - images/test_back.jpg (back fisheye)")
        return False
    
    try:
        # Initialize auto-calibrator
        print("\nInitializing auto-calibrator...")
        calibrator = AutoCalibrator()
        
        print(f"\nAvailable matchers: {calibrator.get_available_matchers()}")
        
        # Run auto-calibration
        print("\nStarting automatic parameter optimization...")
        print("This may take 30-60 seconds...\n")
        
        params = calibrator.optimize_parameters(img1_path, img2_path, matcher_name='auto')
        
        # Display results
        print("\n" + "=" * 60)
        print("AUTO-CALIBRATED PARAMETERS")
        print("=" * 60)
        print(f"FOV:        {params['fov']}")
        print(f"Threshold:  {params['threshold']}")
        print(f"Erosion:    {params['erosion']}")
        print(f"\nFront Lens:")
        print(f"  Yaw:      {params['yaw_f']}")
        print(f"  Pitch:    {params['pitch_f']}")
        print(f"  Roll:     {params['roll_f']}")
        print(f"\nBack Lens:")
        print(f"  Yaw:      {params['yaw_b']}")
        print(f"  Pitch:    {params['pitch_b']}")
        print(f"  Roll:     {params['roll_b']}")
        print("=" * 60)
        
        # Test stitching with auto-calibrated parameters
        print("\nStitching with auto-calibrated parameters...")
        stitcher = Stitcher()
        
        # Save output in dedicated calibration_test folder
        os.makedirs('calibration_test', exist_ok=True)
        output_path = "calibration_test/output_auto_calibrated.jpg"
        
        result = stitcher.stitch(
            img1_path, img2_path, output_path,
            fov=params['fov'],
            yaw_f=params['yaw_f'],
            pitch_f=params['pitch_f'],
            roll_f=params['roll_f'],
            yaw_b=params['yaw_b'],
            pitch_b=params['pitch_b'],
            roll_b=params['roll_b'],
            threshold=params['threshold'],
            erosion=params['erosion']
        )
        
        print(f"\n✓ SUCCESS: Auto-stitched output saved to: {output_path}")
        print("\nCompare this with manually stitched results to verify quality.")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_auto_calibration()
    sys.exit(0 if success else 1)
