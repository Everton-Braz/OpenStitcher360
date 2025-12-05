import cv2
import numpy as np
import subprocess
import os

class Stitcher:
    def __init__(self):
        self.output_w = 4096
        self.output_h = 2048
        self.ffmpeg_path = "ffmpeg"

    def unwarp_with_ffmpeg(self, input_path, output_path, fov, yaw, pitch, roll, shift_x=0, shift_y=0, mask_radius=0, mask_softness=0, mask_aspect=1.0):
        # Construct filter chain
        filters = []
        
        # 1. Circular Mask (if radius > 0)
        # TEMPORARILY COMPLETELY DISABLED: Testing if FFmpeg masking causes washed-out colors
        # We apply this BEFORE shift/crop to ensure we mask the original lens circle
        if False and mask_radius > 0:  # DISABLED
            # geq filter to set pixels outside radius to black
            # r, g, b channels
            # formula: if(lte(hypot(X-W/2,Y-H/2),radius), p(X,Y), 0)
            # We use 'p(X,Y)' to keep original pixel value
            
            # Aspect Ratio logic:
            # We scale the Y component by mask_aspect.
            # Note: We subtract shift because we're measuring distance FROM the shifted center
            # TEMPORARILY DISABLED: Testing if mask_aspect causes washed-out colors
            dist_expr = f"hypot((X-W/2-({shift_x})),(Y-H/2-({shift_y}))*1.0)"
            
            # HARD EDGE ONLY to preserve color information.
            # We do NOT apply softness here because fading to black destroys the color of the edge pixels,
            # causing dark halos/washed-out look when blended.
            # Softness will be handled by the blending weights in OpenCV.
            mask_expr = f"if(lte({dist_expr},{mask_radius}),p(X,Y),0)"
            filters.append(f"geq=r='{mask_expr}':g='{mask_expr}':b='{mask_expr}'")

        # 2. Shift Center (using pad/crop)
        if shift_x != 0 or shift_y != 0:
            pad_l = max(0, int(shift_x))
            pad_r = max(0, int(-shift_x))
            pad_t = max(0, int(shift_y))
            pad_b = max(0, int(-shift_y))
            
            crop_x = max(0, int(-shift_x))
            crop_y = max(0, int(-shift_y))
            
            filters.append(f"pad=w=iw+{pad_l}+{pad_r}:h=ih+{pad_t}+{pad_b}:x={pad_l}:y={pad_t}:color=black")
            filters.append(f"crop=w=iw-{pad_l}-{pad_r}:h=ih-{pad_t}-{pad_b}:x={crop_x}:y={crop_y}")

        # 3. Unwarp (v360)
        filters.append(f"v360=input=fisheye:output=e:ih_fov={fov}:iv_fov={fov}:yaw={yaw}:pitch={pitch}:roll={roll}:w=4096:h=2048")
        
        filter_str = ",".join(filters)
        
        cmd = [
            self.ffmpeg_path, '-y',
            '-i', input_path,
            '-vf', filter_str,
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    def correct_color(self, source, target, mask_src, mask_tgt):
        """
        Matches the color distribution of the source image to the target image
        using statistical analysis in the LAB color space (Reinhard et al.),
        calculated ONLY on the overlapping regions defined by the masks.
        """
        # Find overlap region
        overlap = cv2.bitwise_and(mask_src, mask_tgt)
        
        # If overlap is too small, return original source
        if cv2.countNonZero(overlap) < 100:
            return source

        # Convert to LAB
        src_lab = cv2.cvtColor(source, cv2.COLOR_BGR2LAB).astype("float32")
        tgt_lab = cv2.cvtColor(target, cv2.COLOR_BGR2LAB).astype("float32")

        # Create boolean mask for indexing
        mask_bool = overlap > 0

        # Compute statistics ONLY in the overlap region
        # Source stats
        l_src = src_lab[..., 0][mask_bool]
        a_src = src_lab[..., 1][mask_bool]
        b_src = src_lab[..., 2][mask_bool]
        
        if len(l_src) == 0: return source

        (l_mean_src, l_std_src) = (l_src.mean(), l_src.std())
        (a_mean_src, a_std_src) = (a_src.mean(), a_src.std())
        (b_mean_src, b_std_src) = (b_src.mean(), b_src.std())

        # Target stats
        l_tgt = tgt_lab[..., 0][mask_bool]
        a_tgt = tgt_lab[..., 1][mask_bool]
        b_tgt = tgt_lab[..., 2][mask_bool]

        if len(l_tgt) == 0: return source

        (l_mean_tgt, l_std_tgt) = (l_tgt.mean(), l_tgt.std())
        (a_mean_tgt, a_std_tgt) = (a_tgt.mean(), a_tgt.std())
        (b_mean_tgt, b_std_tgt) = (b_tgt.mean(), b_tgt.std())

        # Apply correction to the ENTIRE source image
        (l, a, b) = cv2.split(src_lab)
        
        # Subtract source mean
        l -= l_mean_src
        a -= a_mean_src
        b -= b_mean_src

        # Scale by ratio of std devs
        l = (l_std_tgt / (l_std_src + 1e-5)) * l
        a = (a_std_tgt / (a_std_src + 1e-5)) * a
        b = (b_std_tgt / (b_std_src + 1e-5)) * b

        # Add target mean
        l += l_mean_tgt
        a += a_mean_tgt
        b += b_mean_tgt

        # Clip and merge
        l = np.clip(l, 0, 255)
        a = np.clip(a, 0, 255)
        b = np.clip(b, 0, 255)

        transfer = cv2.merge([l, a, b])
        transfer = cv2.cvtColor(transfer.astype("uint8"), cv2.COLOR_LAB2BGR)
        
        return transfer

    def correct_vignette(self, img):
        """
        Correct vignette (darkening at edges) using radial correction.
        This prevents dark vignette pixels from being blended in the seam area.
        """
        h, w = img.shape[:2]
        cx, cy = w / 2, h / 2
        
        # Create radial distance map
        y_coords, x_coords = np.ogrid[:h, :w]
        distances = np.sqrt((x_coords - cx)**2 + (y_coords - cy)**2)
        
        # Normalize distances
        max_dist = np.sqrt(cx**2 + cy**2)
        distances_norm = distances / max_dist
        
        # Create correction factor (brighten edges more than center)
        # Using a quadratic falloff: 1 at center, increases toward edges
        correction = 1.0 + (distances_norm ** 2) * 1.5  # Boost edges by up to 150%
        
        # Apply correction
        corrected = img.astype(np.float32) * correction[:, :, np.newaxis]
        corrected = np.clip(corrected, 0, 255).astype(np.uint8)
        
        return corrected

    def get_mask_and_weight(self, img, threshold, erosion):
        """
        Create a binary mask and a distance-based weight map.
        Uses simple brightness thresholding for reliable masking.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Simple threshold - only keep bright pixels (threshold default should be ~50-90)
        _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
        
        # Aggressive morphological cleanup to fill gaps
        kernel_close = np.ones((25, 25), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close, iterations=3)
        
        # Erode to remove the dark vignette edge
        if erosion > 0:
            kernel_erode = np.ones((5, 5), np.uint8)
            mask = cv2.erode(mask, kernel_erode, iterations=erosion)
        
        # Distance Transform Weighting
        dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
        
        # Normalize
        max_dist = dist.max()
        if max_dist > 0:
            weight = dist / max_dist
        else:
            weight = dist
            
        # Steeper falloff to avoid blending vignette
        weight = np.power(weight, 3.0)
        
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
               fov=192.0, 
               yaw_f=0.0, pitch_f=6.0, roll_f=1.1, shift_x_f=0, shift_y_f=0, mask_radius_f=0, mask_softness_f=10, mask_aspect_f=1.0,
               yaw_b=180.0, pitch_b=6.0, roll_b=0.0, shift_x_b=0, shift_y_b=0, mask_radius_b=0, mask_softness_b=10, mask_aspect_b=1.0,
               threshold=31, erosion=52, color_correction=False):
        
        # 1. Unwarp using FFmpeg with custom parameters
        eq_front_path = output_path.replace(".jpg", "_front.jpg")
        eq_back_path = output_path.replace(".jpg", "_back.jpg")
        
        try:
            # Front image
            self.unwarp_with_ffmpeg(img1_path, eq_front_path, fov, yaw_f, pitch_f, roll_f, shift_x_f, shift_y_f, mask_radius_f, mask_softness_f, mask_aspect_f)
            
            # Back image
            self.unwarp_with_ffmpeg(img2_path, eq_back_path, fov, yaw_b, pitch_b, roll_b, shift_x_b, shift_y_b, mask_radius_b, mask_softness_b, mask_aspect_b)
            
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg Error: {e.stderr.decode()}")
            raise

        img_f = cv2.imread(eq_front_path)
        img_b = cv2.imread(eq_back_path)
        
        if img_f is None or img_b is None:
            raise ValueError("Failed to load unwarped images")

        # APPLY VIGNETTE CORRECTION BEFORE ANY OTHER PROCESSING
        # This prevents dark vignette pixels from causing washed-out seams
        # DISABLED: Too aggressive, causing overall brightness issues
        # print("Applying vignette correction...")
        # img_f = self.correct_vignette(img_f)
        # img_b = self.correct_vignette(img_b)

        h, w = img_f.shape[:2]

        # 2. Create Masks and Weights
        print(f"Creating masks (thresh={threshold}, erosion={erosion})...")
        mask_f, weight_f = self.get_mask_and_weight(img_f, threshold, erosion)
        mask_b, weight_b = self.get_mask_and_weight(img_b, threshold, erosion)

        # 1.5 Color Correction (Optional) - MOVED AFTER MASK GENERATION
        if color_correction:
            print("Applying color correction (overlap-based)...")
            
            # Convert float masks back to uint8 for bitwise operations
            mask_f_uint8 = (mask_f * 255).astype(np.uint8)
            mask_b_uint8 = (mask_b * 255).astype(np.uint8)
            
            # Match Back lens to Front lens using ONLY the overlap region
            img_b = self.correct_color(img_b, img_f, mask_b_uint8, mask_f_uint8)
            
        # 3. Create Blending Mask - SIMPLE VERSION (no hole filling)
        sum_weights = weight_f + weight_b
        sum_weights = np.maximum(sum_weights, 1e-10)  # Prevent division by zero
        blend_mask = weight_f / sum_weights
        
        # 4. Multi-band blending
        print("Multi-band blending...")
        
        # TESTING: Simple weighted blend instead of pyramid blending
        # to see if pyramid blending is causing washed-out colors
        USE_SIMPLE_BLEND = True
        
        if USE_SIMPLE_BLEND:
            # Direct weighted blend - no pyramids
            blend_mask_3ch = blend_mask[..., np.newaxis]
            result = (img_f.astype(np.float32) * blend_mask_3ch + 
                     img_b.astype(np.float32) * (1.0 - blend_mask_3ch))
            result = np.clip(result, 0, 255).astype(np.uint8)
        else:
            # Original pyramid blending
            # Create pyramids (fewer levels = sharper seam, less washed-out effect)
            levels = 3
            lp_f = self.build_laplacian_pyramid(self.build_gaussian_pyramid(img_f, levels))
            lp_b = self.build_laplacian_pyramid(self.build_gaussian_pyramid(img_b, levels))
            mask_pyr = self.build_gaussian_pyramid(blend_mask, levels)
            
            # Blend
            LS = self.blend_pyramids(lp_f, lp_b, mask_pyr)
            
            # Reconstruct
            result = self.reconstruct_from_pyramid(LS)
            
            # Clip values
            result = np.clip(result, 0, 255).astype(np.uint8)
        
        cv2.imwrite(output_path, result)
        print(f"Stitched image saved to {output_path}")

    def stitch_auto(self, img1_path, img2_path, output_path):
        from auto_calibrator import AutoCalibrator
        calibrator = AutoCalibrator()
        
        # 1. Calibrate
        params = calibrator.calibrate(img1_path, img2_path)
        
        # 2. Stitch with calibrated params
        self.stitch(img1_path, img2_path, output_path, **params)
        
        return output_path, params
