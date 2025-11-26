"""
Advanced AI optimization for parameter tuning and artifact removal.

This module provides:
1. Grid search optimization for threshold/erosion
2. Reference image comparison
3. Artifact detection
4. Seam optimization
"""

import cv2
import numpy as np
from typing import Tuple, Dict, List, Optional
from skimage.metrics import structural_similarity as ssim
import os


class AdvancedOptimizer:
    """
    Advanced AI optimization for stitching parameter tuning.
    """
    
    def __init__(self, stitcher):
        """
        Initialize optimizer with stitcher instance.
        
        Args:
            stitcher: Stitcher instance to use for stitching
        """
        self.stitcher = stitcher
        
    def grid_search_masking(self, img1_path: str, img2_path: str,
                           threshold_range: Tuple[int, int, int] = (10, 50, 10),
                           erosion_range: Tuple[int, int, int] = (60, 140, 20),
                           fixed_params: Dict = None) -> Dict:
        """
        Grid search to find optimal threshold and erosion parameters.
        
        Args:
            img1_path: Path to front fisheye image
            img2_path: Path to back fisheye image
            threshold_range: (min, max, step) for threshold
            erosion_range: (min, max, step) for erosion
            fixed_params: Fixed parameters (fov, pitch, roll, etc.)
            
        Returns:
            best_params: Dictionary with optimal parameters
        """
        if fixed_params is None:
            fixed_params = {
                'fov': 192.0,
                'yaw_f': 0.0, 'pitch_f': 6.0, 'roll_f': 1.1,
                'yaw_b': 180.0, 'pitch_b': 6.0, 'roll_b': 0.0
            }
        
        print("\n=== Grid Search Optimization ===")
        print(f"Threshold range: {threshold_range}")
        print(f"Erosion range: {erosion_range}")
        
        best_score = -float('inf')
        best_params = None
        results = []
        
        # Grid search
        for threshold in range(threshold_range[0], threshold_range[1], threshold_range[2]):
            for erosion in range(erosion_range[0], erosion_range[1], erosion_range[2]):
                print(f"\nTesting: threshold={threshold}, erosion={erosion}")
                
                # Create temp output path
                temp_output = f"calibration_test/grid_search_t{threshold}_e{erosion}.jpg"
                
                try:
                    # Stitch with these parameters
                    self.stitcher.stitch(
                        img1_path, img2_path, temp_output,
                        threshold=threshold,
                        erosion=erosion,
                        **fixed_params
                    )
                    
                    # Load result
                    result_img = cv2.imread(temp_output)
                    
                    # Score the result
                    score = self._score_stitching_quality(result_img)
                    
                    print(f"  Score: {score:.3f}")
                    
                    results.append({
                        'threshold': threshold,
                        'erosion': erosion,
                        'score': score,
                        'output_path': temp_output
                    })
                    
                    if score > best_score:
                        best_score = score
                        best_params = {
                            **fixed_params,
                            'threshold': threshold,
                            'erosion': erosion
                        }
                    
                    # Clean up temp file
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                        
                except Exception as e:
                    print(f"  Error: {e}")
                    continue
        
        print(f"\n=== Best Parameters Found ===")
        print(f"Threshold: {best_params['threshold']}")
        print(f"Erosion: {best_params['erosion']}")
        print(f"Score: {best_score:.3f}")
        
        return best_params
    
    def _score_stitching_quality(self, img: np.ndarray) -> float:
        """
        Score stitching quality based on multiple metrics.
        
        Metrics:
        1. Minimal black pixels (coverage)
        2. No artifacts (edge detection)
        3. Good contrast/sharpness
        
        Args:
            img: Stitched image to score
            
        Returns:
            score: Quality score (higher is better)
        """
        if img is None or img.size == 0:
            return -1000.0
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Coverage score (minimize black pixels)
        black_pixels = np.sum(gray < 10)
        total_pixels = gray.size
        coverage_score = (1.0 - black_pixels / total_pixels) * 100
        
        # 2. Artifact score (minimize high-frequency noise in seam regions)
        # Detect vertical seams (typically at image boundaries)
        h, w = gray.shape
        seam_region_left = gray[:, :w//10]  # Left 10%
        seam_region_right = gray[:, -w//10:]  # Right 10%
        
        # Calculate variance in seam regions (high variance = artifacts)
        seam_variance_left = np.var(seam_region_left)
        seam_variance_right = np.var(seam_region_right)
        artifact_score = -(seam_variance_left + seam_variance_right) / 2000  # Normalize
        
        # 3. Sharpness score (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness_score = np.var(laplacian) / 1000  # Normalize
        
        # 4. Detect ghosting/doubling artifacts
        # Use edge detection to find doubled edges
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / total_pixels
        # Too many edges can indicate ghosting
        ghosting_penalty = -abs(edge_density - 0.05) * 50  # Optimal around 5% edges
        
        # Combined score (weights tuned empirically)
        total_score = (
            coverage_score * 1.0 +      # Most important: minimize black borders
            artifact_score * 0.3 +       # Minimize seam artifacts
            sharpness_score * 0.2 +      # Prefer sharp images
            ghosting_penalty * 0.5       # Penalize ghosting
        )
        
        return total_score
    
    def compare_with_reference(self, test_img_path: str, reference_img_path: str) -> float:
        """
        Compare test image with reference image using multiple similarity metrics.
        
        Args:
            test_img_path: Path to test stitched image
            reference_img_path: Path to reference (correct) stitched image
            
        Returns:
            similarity_score: Similarity score (0-100, higher is better)
        """
        # Load images
        test_img = cv2.imread(test_img_path)
        ref_img = cv2.imread(reference_img_path)
        
        if test_img is None or ref_img is None:
            raise ValueError("Failed to load images")
        
        # Resize if needed
        if test_img.shape != ref_img.shape:
            test_img = cv2.resize(test_img, (ref_img.shape[1], ref_img.shape[0]))
        
        # Convert to grayscale
        test_gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)
        ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
        
        # 1. Structural Similarity Index (SSIM)
        ssim_score = ssim(ref_gray, test_gray)
        
        # 2. Peak Signal-to-Noise Ratio (PSNR)
        mse = np.mean((test_img.astype(float) - ref_img.astype(float)) ** 2)
        if mse == 0:
            psnr_score = 100.0
        else:
            psnr_score = 20 * np.log10(255.0 / np.sqrt(mse))
        
        # 3. Histogram similarity
        hist_test = cv2.calcHist([test_gray], [0], None, [256], [0, 256])
        hist_ref = cv2.calcHist([ref_gray], [0], None, [256], [0, 256])
        hist_similarity = cv2.compareHist(hist_test, hist_ref, cv2.HISTCMP_CORREL)
        
        # Combined score
        combined_score = (
            ssim_score * 40 +                    # SSIM: 0-1 → 0-40
            min(psnr_score / 50 * 40, 40) +      # PSNR: normalize to 0-40
            hist_similarity * 20                  # Hist: 0-1 → 0-20
        )
        
        print(f"\n=== Reference Comparison ===")
        print(f"SSIM: {ssim_score:.3f}")
        print(f"PSNR: {psnr_score:.2f} dB")
        print(f"Histogram Similarity: {hist_similarity:.3f}")
        print(f"Combined Score: {combined_score:.2f}/100")
        
        return combined_score
    
    def optimize_with_reference(self, img1_path: str, img2_path: str, 
                                reference_img_path: str,
                                threshold_range: Tuple[int, int, int] = (10, 50, 5),
                                erosion_range: Tuple[int, int, int] = (60, 140, 10),
                                fixed_params: Dict = None) -> Dict:
        """
        Optimize parameters to match a reference image.
        
        Args:
            img1_path: Path to front fisheye image
            img2_path: Path to back fisheye image
            reference_img_path: Path to reference (correct) stitched image
            threshold_range: (min, max, step) for threshold
            erosion_range: (min, max, step) for erosion
            fixed_params: Fixed parameters (fov, pitch, roll, etc.)
            
        Returns:
            best_params: Dictionary with optimal parameters
        """
        if fixed_params is None:
            fixed_params = {
                'fov': 192.0,
                'yaw_f': 0.0, 'pitch_f': 6.0, 'roll_f': 1.1,
                'yaw_b': 180.0, 'pitch_b': 6.0, 'roll_b': 0.0
            }
        
        print("\n=== Reference-Based Optimization ===")
        
        best_similarity = -float('inf')
        best_params = None
        
        # Grid search
        for threshold in range(threshold_range[0], threshold_range[1], threshold_range[2]):
            for erosion in range(erosion_range[0], erosion_range[1], erosion_range[2]):
                print(f"\nTesting: threshold={threshold}, erosion={erosion}")
                
                # Create temp output path
                temp_output = f"calibration_test/ref_opt_t{threshold}_e{erosion}.jpg"
                
                try:
                    # Stitch with these parameters
                    self.stitcher.stitch(
                        img1_path, img2_path, temp_output,
                        threshold=threshold,
                        erosion=erosion,
                        **fixed_params
                    )
                    
                    # Compare with reference
                    similarity = self.compare_with_reference(temp_output, reference_img_path)
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_params = {
                            **fixed_params,
                            'threshold': threshold,
                            'erosion': erosion
                        }
                    
                    # Clean up temp file
                    if os.path.exists(temp_output):
                        os.remove(temp_output)
                        
                except Exception as e:
                    print(f"  Error: {e}")
                    continue
        
        print(f"\n=== Best Match to Reference ===")
        print(f"Threshold: {best_params['threshold']}")
        print(f"Erosion: {best_params['erosion']}")
        print(f"Similarity: {best_similarity:.2f}/100")
        
        return best_params
    
    def detect_artifacts(self, img_path: str) -> Dict:
        """
        Detect and locate artifacts in stitched image.
        
        Artifacts include:
        - Ghosting/doubling
        - Seam visibility
        - Black borders
        - Color discontinuities
        
        Args:
            img_path: Path to stitched image
            
        Returns:
            artifact_info: Dictionary with artifact locations and severity
        """
        img = cv2.imread(img_path)
        if img is None:
            raise ValueError("Failed to load image")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        artifacts = {
            'black_borders': {},
            'ghosting_regions': [],
            'seam_issues': [],
            'overall_quality': 0.0
        }
        
        # 1. Detect black borders
        top_black = np.sum(gray[0, :] < 10) / w
        bottom_black = np.sum(gray[-1, :] < 10) / w
        left_black = np.sum(gray[:, 0] < 10) / h
        right_black = np.sum(gray[:, -1] < 10) / h
        
        artifacts['black_borders'] = {
            'top': top_black,
            'bottom': bottom_black,
            'left': left_black,
            'right': right_black
        }
        
        # 2. Detect ghosting (doubled edges)
        edges = cv2.Canny(gray, 50, 150)
        
        # Look for doubled vertical edges (common in seam areas)
        kernel = np.ones((1, 5), np.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Find regions with high edge density (potential ghosting)
        edge_map = cv2.resize(dilated_edges, (w//10, h//10))
        ghosting_threshold = np.percentile(edge_map, 95)
        ghosting_mask = edge_map > ghosting_threshold
        
        # Find contours of ghosting regions
        contours, _ = cv2.findContours(ghosting_mask.astype(np.uint8), 
                                      cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            if cv2.contourArea(contour) > 10:  # Significant region
                x, y, w_c, h_c = cv2.boundingRect(contour)
                artifacts['ghosting_regions'].append({
                    'x': x * 10,  # Scale back to original size
                    'y': y * 10,
                    'width': w_c * 10,
                    'height': h_c * 10
                })
        
        # 3. Calculate overall quality score
        quality_score = self._score_stitching_quality(img)
        artifacts['overall_quality'] = quality_score
        
        print(f"\n=== Artifact Detection ===")
        print(f"Black borders: Top={top_black:.1%}, Bottom={bottom_black:.1%}, "
              f"Left={left_black:.1%}, Right={right_black:.1%}")
        print(f"Ghosting regions found: {len(artifacts['ghosting_regions'])}")
        print(f"Overall quality: {quality_score:.2f}")
        
        return artifacts
