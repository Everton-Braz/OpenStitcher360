"""
Automatic parameter calibration for dual fisheye image stitching.

This module provides AI-based feature matching and parameter optimization
to automatically determine optimal stitching parameters (FOV, yaw, pitch, roll,
threshold, erosion) without manual tuning.

Implements three tiers of feature matching:
1. ORB (Oriented FAST and Rotated BRIEF) - CPU-only, fast, baseline
2. SIFT (Scale-Invariant Feature Transform) - CPU-only, accurate, requires opencv-contrib
3. SuperGlue + SuperPoint - GPU-accelerated, state-of-the-art, requires PyTorch

The system automatically falls back to simpler methods if advanced ones are unavailable.
"""

import cv2
import numpy as np
from abc import ABC, abstractmethod
import subprocess
import os
from typing import Tuple, List, Dict, Optional


class FeatureMatcher(ABC):
    """
    Abstract base class for feature detection and matching algorithms.
    """
    
    @abstractmethod
    def detect_features(self, image: np.ndarray) -> Tuple[List, np.ndarray]:
        """
        Detect keypoints and extract descriptors from an image.
        
        Args:
            image: Input image (BGR or grayscale)
            
        Returns:
            keypoints: List of cv2.KeyPoint objects
            descriptors: Numpy array of feature descriptors
        """
        pass
    
    @abstractmethod
    def match_features(self, desc1: np.ndarray, desc2: np.ndarray,
                      kp1: List, kp2: List) -> List:
        """
        Match features between two sets of descriptors.
        
        Args:
            desc1: Descriptors from first image
            desc2: Descriptors from second image
            kp1: Keypoints from first image
            kp2: Keypoints from second image
            
        Returns:
            matches: List of cv2.DMatch objects
        """
        pass
    
    def estimate_homography(self, matches: List, kp1: List, kp2: List,
                           min_matches: int = 10) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Estimate homography matrix from matched features using RANSAC.
        
        Args:
            matches: List of cv2.DMatch objects
            kp1: Keypoints from first image
            kp2: Keypoints from second image
            min_matches: Minimum number of matches required
            
        Returns:
            H: 3x3 homography matrix (or None if insufficient matches)
            inliers: Boolean mask of inlier matches (or None)
        """
        if len(matches) < min_matches:
            print(f"Warning: Only {len(matches)} matches found (minimum {min_matches} required)")
            return None, None
        
        # Extract matched point coordinates
        pts1 = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        pts2 = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        
        # Compute homography with RANSAC
        H, mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, 5.0)
        
        if H is None:
            print("Warning: Failed to compute homography")
            return None, None
        
        inliers = mask.ravel().astype(bool) if mask is not None else None
        num_inliers = np.sum(inliers) if inliers is not None else 0
        
        print(f"Homography: {len(matches)} matches, {num_inliers} inliers ({100*num_inliers/len(matches):.1f}%)")
        
        return H, inliers


class ORBFeatureMatcher(FeatureMatcher):
    """
    ORB (Oriented FAST and Rotated BRIEF) feature matcher.
    Fast, CPU-only, always available. Baseline method.
    """
    
    def __init__(self, n_features: int = 2000):
        """
        Initialize ORB detector.
        
        Args:
            n_features: Maximum number of features to detect
        """
        self.detector = cv2.ORB_create(nfeatures=n_features)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        
    def detect_features(self, image: np.ndarray) -> Tuple[List, np.ndarray]:
        """Detect ORB keypoints and descriptors."""
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        
        if descriptors is None:
            descriptors = np.array([])
            
        return keypoints, descriptors
    
    def match_features(self, desc1: np.ndarray, desc2: np.ndarray,
                      kp1: List, kp2: List) -> List:
        """Match ORB descriptors using brute-force matching with ratio test."""
        if len(desc1) == 0 or len(desc2) == 0:
            return []
        
        # KNN match with k=2 for ratio test
        matches = self.matcher.knnMatch(desc1, desc2, k=2)
        
        # Apply Lowe's ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.75 * n.distance:
                    good_matches.append(m)
        
        return good_matches


class SIFTFeatureMatcher(FeatureMatcher):
    """
    SIFT (Scale-Invariant Feature Transform) feature matcher.
    More accurate than ORB, requires opencv-contrib-python.
    """
    
    def __init__(self, n_features: int = 2000):
        """
        Initialize SIFT detector.
        
        Args:
            n_features: Maximum number of features to detect
        """
        try:
            self.detector = cv2.SIFT_create(nfeatures=n_features)
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
            self.available = True
        except AttributeError:
            print("Warning: SIFT not available (requires opencv-contrib-python)")
            self.available = False
    
    def detect_features(self, image: np.ndarray) -> Tuple[List, np.ndarray]:
        """Detect SIFT keypoints and descriptors."""
        if not self.available:
            return [], np.array([])
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        
        if descriptors is None:
            descriptors = np.array([])
            
        return keypoints, descriptors
    
    def match_features(self, desc1: np.ndarray, desc2: np.ndarray,
                      kp1: List, kp2: List) -> List:
        """Match SIFT descriptors using brute-force matching with ratio test."""
        if not self.available or len(desc1) == 0 or len(desc2) == 0:
            return []
        
        # KNN match with k=2 for ratio test
        matches = self.matcher.knnMatch(desc1, desc2, k=2)
        
        # Apply Lowe's ratio test
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < 0.7 * n.distance:  # Stricter ratio for SIFT
                    good_matches.append(m)
        
        return good_matches


class AutoCalibrator:
    """
    Automatic parameter calibration for dual fisheye stitching.
    
    Uses feature matching to automatically determine optimal stitching parameters:
    - FOV (Field of View)
    - Yaw, Pitch, Roll (rotation angles for front and back lenses)
    - Threshold (vignette masking)
    - Erosion (mask edge removal)
    """
    
    def __init__(self, output_w: int = 4096, output_h: int = 2048, ffmpeg_path: str = "ffmpeg"):
        """
        Initialize auto-calibrator.
        
        Args:
            output_w: Output equirectangular width
            output_h: Output equirectangular height
            ffmpeg_path: Path to ffmpeg executable
        """
        self.output_w = output_w
        self.output_h = output_h
        self.ffmpeg_path = ffmpeg_path
        
        # Try to initialize matchers in order of preference
        self.matchers = self._initialize_matchers()
        
    def _initialize_matchers(self) -> Dict[str, FeatureMatcher]:
        """Initialize available feature matchers."""
        matchers = {}
        
        # ORB is always available
        matchers['orb'] = ORBFeatureMatcher(n_features=3000)
        print("✓ ORB matcher initialized")
        
        # Try SIFT
        try:
            sift = SIFTFeatureMatcher(n_features=3000)
            if sift.available:
                matchers['sift'] = sift
                print("✓ SIFT matcher initialized")
        except Exception as e:
            print(f"✗ SIFT matcher unavailable: {e}")
        
        # TODO: Add SuperGlue in Phase 2
        
        return matchers
    
    def get_available_matchers(self) -> List[str]:
        """Return list of available matcher names."""
        return list(self.matchers.keys())
    
    def _unwarp_fisheye(self, input_path: str, output_path: str, 
                       fov: float, yaw: float, pitch: float, roll: float) -> bool:
        """
        Unwarp fisheye image to equirectangular using FFmpeg.
        
        Args:
            input_path: Path to fisheye image
            output_path: Path to save equirectangular image
            fov: Field of view in degrees
            yaw, pitch, roll: Rotation angles in degrees
            
        Returns:
            success: True if conversion succeeded
        """
        filter_str = f"v360=fisheye:e:ih_fov={fov}:iv_fov={fov}:yaw={yaw}:pitch={pitch}:roll={roll}:w={self.output_w}:h={self.output_h}"
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-vf", filter_str,
            output_path
        ]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            return True
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr.decode()}")
            return False
    
    def _decompose_homography_to_angles(self, H: np.ndarray) -> Tuple[float, float, float]:
        """
        Decompose homography matrix to estimate pitch and roll adjustments.
        
        For dual fisheye stitching, we primarily care about:
        - Pitch: Vertical alignment (up/down tilt)
        - Roll: Rotation around optical axis
        
        Args:
            H: 3x3 homography matrix
            
        Returns:
            yaw_deg: Yaw adjustment (degrees)
            pitch_deg: Pitch adjustment (degrees)
            roll_deg: Roll adjustment (degrees)
        """
        # Decompose homography using SVD
        # H ≈ s * R * K, where R is rotation, s is scale, K is intrinsics
        
        # Normalize H
        H_norm = H / H[2, 2]
        
        # Extract rotation-like component (simplified)
        # For small angles, we can approximate from the matrix elements
        
        # Roll: rotation around Z-axis (in-plane rotation)
        roll_rad = np.arctan2(H_norm[1, 0], H_norm[0, 0])
        roll_deg = np.degrees(roll_rad)
        
        # Pitch: rotation around X-axis (up/down tilt)
        # Approximate from vertical shift and scale
        pitch_rad = np.arctan2(-H_norm[2, 1], np.sqrt(H_norm[0, 1]**2 + H_norm[1, 1]**2))
        pitch_deg = np.degrees(pitch_rad)
        
        # Yaw: rotation around Y-axis (left/right pan)
        # Usually minimal for overlap-based stitching
        yaw_rad = np.arctan2(H_norm[2, 0], H_norm[2, 2])
        yaw_deg = np.degrees(yaw_rad)
        
        return yaw_deg, pitch_deg, roll_deg
    
    def _extract_overlap_regions(self, img1: np.ndarray, img2: np.ndarray, 
                                 overlap_width: int = 500) -> Tuple[np.ndarray, np.ndarray]:
        """
        Extract overlapping regions from two equirectangular images.
        
        For dual fisheye:
        - Front image: Use right edge (wraps to back)
        - Back image: Use left edge (wraps to front)
        
        Args:
            img1: First equirectangular image (front lens)
            img2: Second equirectangular image (back lens)
            overlap_width: Width of overlap region in pixels
            
        Returns:
            overlap1: Overlap region from img1 (right edge)
            overlap2: Overlap region from img2 (left edge)
        """
        h, w = img1.shape[:2]
        
        # Front lens: right edge
        overlap1 = img1[:, -overlap_width:]
        
        # Back lens: left edge
        overlap2 = img2[:, :overlap_width]
        
        return overlap1, overlap2
    
    def optimize_parameters(self, img1_path: str, img2_path: str,
                           matcher_name: str = 'auto',
                           max_iterations: int = 3) -> Dict[str, float]:
        """
        Automatically optimize stitching parameters using feature matching.
        
        Args:
            img1_path: Path to front fisheye image
            img2_path: Path to back fisheye image
            matcher_name: Feature matcher to use ('auto', 'orb', 'sift', 'superglue')
            max_iterations: Maximum refinement iterations
            
        Returns:
            params: Dictionary of optimal parameters
        """
        print("\n=== Auto-Calibration Started ===")
        
        # Select matcher
        if matcher_name == 'auto':
            # Use best available
            if 'sift' in self.matchers:
                matcher_name = 'sift'
            else:
                matcher_name = 'orb'
        
        if matcher_name not in self.matchers:
            raise ValueError(f"Matcher '{matcher_name}' not available. Available: {self.get_available_matchers()}")
        
        matcher = self.matchers[matcher_name]
        print(f"Using matcher: {matcher_name.upper()}")
        
        # Initial parameter guess (based on known-good values for Insta360)
        fov = 192.0
        pitch_f = 6.0   # User-confirmed optimal value
        roll_f = 1.1    # User-confirmed optimal value for front lens
        pitch_b = 6.0   # Match front lens pitch
        roll_b = 0.0
        
        # Iterative refinement
        for iteration in range(max_iterations):
            print(f"\n--- Iteration {iteration + 1}/{max_iterations} ---")
            
            # Unwarp fisheye images to equirectangular
            # Save temp files in dedicated calibration_test folder
            os.makedirs('calibration_test', exist_ok=True)
            temp_front = "calibration_test/temp_front_calibration.jpg"
            temp_back = "calibration_test/temp_back_calibration.jpg"
            
            self._unwarp_fisheye(img1_path, temp_front, fov, 0, pitch_f, roll_f)
            self._unwarp_fisheye(img2_path, temp_back, fov, 180, pitch_b, roll_b)
            
            # Load unwarped images
            eq_front = cv2.imread(temp_front)
            eq_back = cv2.imread(temp_back)
            
            # Extract overlap regions (wider for better feature detection)
            overlap1, overlap2 = self._extract_overlap_regions(eq_front, eq_back, overlap_width=500)
            
            # Detect and match features
            print("Detecting features...")
            kp1, desc1 = matcher.detect_features(overlap1)
            kp2, desc2 = matcher.detect_features(overlap2)
            
            print(f"Found {len(kp1)} features in front, {len(kp2)} in back")
            
            print("Matching features...")
            matches = matcher.match_features(desc1, desc2, kp1, kp2)
            
            if len(matches) < 10:
                print(f"Warning: Only {len(matches)} matches found. Results may be unreliable.")
                break
            
            # Estimate homography
            H, inliers = matcher.estimate_homography(matches, kp1, kp2)
            
            if H is None:
                print("Warning: Failed to estimate homography. Using current parameters.")
                break
            
            # Decompose homography to rotation angles
            yaw_delta, pitch_delta, roll_delta = self._decompose_homography_to_angles(H)
            
            print(f"Estimated adjustments: yaw={yaw_delta:.2f}°, pitch={pitch_delta:.2f}°, roll={roll_delta:.2f}°")
            
            # Update parameters
            # Apply half the correction to each lens for pitch
            pitch_f += pitch_delta / 2
            pitch_b += pitch_delta / 2
            
            # Apply roll correction to front lens
            roll_f += roll_delta
            
            # Check convergence
            if abs(pitch_delta) < 0.1 and abs(roll_delta) < 0.1:
                print("Converged!")
                break
            
            # Cleanup temp files
            try:
                os.remove(temp_front)
                os.remove(temp_back)
            except:
                pass
        
        # Estimate threshold and erosion from vignette
        threshold, erosion = self._estimate_masking_params(img1_path)
        
        params = {
            'fov': fov,
            'yaw_f': 0.0,
            'pitch_f': round(pitch_f, 1),
            'roll_f': round(roll_f, 1),
            'yaw_b': 180.0,
            'pitch_b': round(pitch_b, 1),
            'roll_b': round(roll_b, 1),
            'threshold': threshold,
            'erosion': erosion
        }
        
        print("\n=== Auto-Calibration Complete ===")
        print(f"Optimized parameters: {params}")
        
        return params
    
    def _estimate_masking_params(self, fisheye_path: str) -> Tuple[int, int]:
        """
        Estimate threshold and erosion parameters from fisheye vignette.
        
        Args:
            fisheye_path: Path to fisheye image
            
        Returns:
            threshold: Recommended threshold value
            erosion: Recommended erosion iterations
        """
        # Load fisheye image
        img = cv2.imread(fisheye_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Analyze intensity distribution
        # Vignette creates dark edges
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        
        # Find threshold where cumulative histogram reaches 5% (dark pixels)
        cumsum = np.cumsum(hist)
        total = cumsum[-1]
        threshold_idx = np.where(cumsum > 0.05 * total)[0][0]
        
        # Recommend threshold slightly above this
        threshold = max(10, min(50, int(threshold_idx * 1.2)))
        
        # Erosion: estimate based on image size and vignette width
        # Assume vignette is ~5% of radius
        h, w = img.shape[:2]
        radius = min(h, w) / 2
        erosion = int(radius * 0.05)
        erosion = max(50, min(150, erosion))
        
        print(f"Estimated masking: threshold={threshold}, erosion={erosion}")
        
        return threshold, erosion

    def detect_lens_radius(self, image_path: str) -> int:
        """
        Automatically detect the radius of the valid lens circle.
        
        Args:
            image_path: Path to fisheye image
            
        Returns:
            radius: Detected radius (with safety margin)
        """
        img = cv2.imread(image_path)
        if img is None:
            return 0
            
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Threshold to separate image from black background
        # Fisheye images usually have a sharp transition to black
        _, thresh = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 0
            
        # Find largest contour (assumed to be the lens circle)
        largest_contour = max(contours, key=cv2.contourArea)
        
        # Find enclosing circle
        ((cx, cy), radius) = cv2.minEnclosingCircle(largest_contour)
        
        # Apply safety margin (99% of detected radius) to cut off the bright edge
        safe_radius = int(radius * 0.99)
        
        print(f"Detected lens radius: {radius:.1f} -> Safe radius: {safe_radius}")
        
        return safe_radius
