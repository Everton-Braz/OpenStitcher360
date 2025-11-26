import cv2
import numpy as np
import subprocess
import os

class Stitcher:
    def __init__(self):
        self.output_w = 4096
        self.output_h = 2048
        self.ffmpeg_path = "ffmpeg"

    def unwarp_with_ffmpeg(self, input_path, output_path, fov, yaw, pitch, roll):
        # Construct filter chain
        # v360=fisheye:e:ih_fov={fov}:iv_fov={fov}:yaw={yaw}:pitch={pitch}:roll={roll}:w={w}:h={h}
        
        filter_str = f"v360=fisheye:e:ih_fov={fov}:iv_fov={fov}:yaw={yaw}:pitch={pitch}:roll={roll}:w={self.output_w}:h={self.output_h}"
        
        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", input_path,
            "-vf", filter_str,
            output_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def get_mask_and_weight(self, img, threshold, erosion):
        """
        Create a binary mask and a distance-based weight map.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 1. Adaptive Threshold Mask
        _, mask_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, mask_fixed = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        mask = cv2.bitwise_and(mask_otsu, mask_fixed)
        
        # Morphological cleanup
        kernel_close = np.ones((15, 15), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=2)
        
        # Erode to remove the dark vignette edge
        if erosion > 0:
            kernel_erode = np.ones((3, 3), np.uint8)
            mask = cv2.erode(mask, kernel_erode, iterations=erosion)
        
        # 2. Distance Transform Weighting
        dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        
        # Normalize
        max_dist = dist.max()
        if max_dist > 0:
            weight = dist / max_dist
        else:
            weight = dist
            
        # Linear falloff (power 1.0) is generally safe
        weight = np.power(weight, 1.0)
        
        return mask.astype(np.float32) / 255.0, weight

    def build_gaussian_pyramid(self, img, levels):
        gp = [img]
        for i in range(levels):
            img = cv2.pyrDown(img)
            gp.append(img)
        return gp

    def build_laplacian_pyramid(self, gp):
        levels = len(gp)
        lp = [gp[-1]]
        for i in range(levels-1, 0, -1):
            size = (gp[i-1].shape[1], gp[i-1].shape[0])
            GE = cv2.pyrUp(gp[i], dstsize=size)
            L = cv2.subtract(gp[i-1], GE)
            lp.append(L)
        return lp

    def blend_pyramids(self, lp_a, lp_b, mask_pyramid):
        LS = []
        for la, lb, mask in zip(lp_a, lp_b, mask_pyramid[::-1]):
            if len(la.shape) == 3 and len(mask.shape) == 2:
                mask = mask[..., np.newaxis]
            ls = la * mask + lb * (1.0 - mask)
            LS.append(ls)
        return LS

    def reconstruct_from_pyramid(self, LS):
        ls_ = LS[0]
        for i in range(1, len(LS)):
            size = (LS[i].shape[1], LS[i].shape[0])
            ls_ = cv2.pyrUp(ls_, dstsize=size)
            ls_ = cv2.add(ls_, LS[i])
        return ls_

    def stitch(self, img1_path, img2_path, output_path, 
               fov=200.0, 
               yaw_f=0.0, pitch_f=0.0, roll_f=0.0, 
               yaw_b=180.0, pitch_b=0.0, roll_b=0.0,
               threshold=90, erosion=3):
        
        # 1. Unwarp using FFmpeg with custom parameters
        eq_front_path = output_path.replace(".jpg", "_front.jpg")
        eq_back_path = output_path.replace(".jpg", "_back.jpg")
        
        try:
            # Front image
            self.unwarp_with_ffmpeg(img1_path, eq_front_path, fov, yaw_f, pitch_f, roll_f)
            
            # Back image
            self.unwarp_with_ffmpeg(img2_path, eq_back_path, fov, yaw_b, pitch_b, roll_b)
            
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Error: {e.stderr.decode()}")
            raise

        img_f = cv2.imread(eq_front_path)
        img_b = cv2.imread(eq_back_path)
        
        if img_f is None or img_b is None:
            raise ValueError("Failed to load unwarped images")

        h, w = img_f.shape[:2]

        # 2. Create Masks and Weights
        print(f"Creating masks (thresh={threshold}, erosion={erosion})...")
        mask_f, weight_f = self.get_mask_and_weight(img_f, threshold, erosion)
        mask_b, weight_b = self.get_mask_and_weight(img_b, threshold, erosion)
        
        # 3. Create Blending Mask
        sum_weights = weight_f + weight_b
        
        # --- ROBUST HOLE FILLING ---
        hole_mask = sum_weights < 0.01
        
        if np.any(hole_mask):
            print("Filling holes...")
            gray_f = cv2.cvtColor(img_f, cv2.COLOR_BGR2GRAY)
            gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
            
            # Lower threshold for data existence check
            has_data_f = (gray_f > 20).astype(np.float32)
            has_data_b = (gray_b > 20).astype(np.float32)
            
            weight_f[hole_mask] = has_data_f[hole_mask]
            weight_b[hole_mask] = has_data_b[hole_mask]
            
            sum_weights = weight_f + weight_b
        
        valid_pixels = sum_weights > 0.0001
        sum_weights[~valid_pixels] = 1.0
        
        blend_mask = weight_f / sum_weights
        
        # 4. Multi-band blending
        print("Multi-band blending...")
        
        img_f_float = img_f.astype(np.float32)
        img_b_float = img_b.astype(np.float32)
        
        levels = 6
        gp_f = self.build_gaussian_pyramid(img_f_float, levels)
        gp_b = self.build_gaussian_pyramid(img_b_float, levels)
        
        lp_f = self.build_laplacian_pyramid(gp_f)
        lp_b = self.build_laplacian_pyramid(gp_b)
        
        gp_mask = self.build_gaussian_pyramid(blend_mask, levels)
        
        LS = self.blend_pyramids(lp_f, lp_b, gp_mask)
        
        blended = self.reconstruct_from_pyramid(LS)
        
        # 5. Final cleanup
        blended = np.clip(blended, 0, 255)
        
        # Final safety fill
        final_holes = (np.sum(blended, axis=2) < 10) & ((cv2.cvtColor(img_f, cv2.COLOR_BGR2GRAY) > 20) | (cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY) > 20))
        if np.any(final_holes):
            print("Final safety fill...")
            max_img = np.maximum(img_f, img_b)
            blended[final_holes] = max_img[final_holes]
            
        cv2.imwrite(output_path, blended.astype(np.uint8))
        
        return output_path
