from flask import Flask, render_template, request, send_from_directory, jsonify, session
import os
from stitcher import Stitcher
import time
import secrets

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULTS_FOLDER'] = 'static/results'
app.config['IMAGES_FOLDER'] = 'images'
app.secret_key = secrets.token_hex(16)  # For session management

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

stitcher = Stitcher()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stitch', methods=['POST'])
def stitch():
    if 'image1' not in request.files or 'image2' not in request.files:
        return jsonify({'error': 'Missing images'}), 400
    
    img1 = request.files['image1']
    img2 = request.files['image2']
    
    if img1.filename == '' or img2.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    path1 = os.path.join(app.config['UPLOAD_FOLDER'], img1.filename)
    path2 = os.path.join(app.config['UPLOAD_FOLDER'], img2.filename)
    
    img1.save(path1)
    img2.save(path2)
    
    # Store uploaded image paths in session
    session['uploaded_img1'] = path1
    session['uploaded_img2'] = path2
    
    return process_stitching(path1, path2)

@app.route('/stitch_test', methods=['POST'])
def stitch_test():
    # Use images from the images folder
    path1 = os.path.join(app.config['IMAGES_FOLDER'], 'lens_01.png')
    path2 = os.path.join(app.config['IMAGES_FOLDER'], 'lens_02.png')
    
    if not os.path.exists(path1) or not os.path.exists(path2):
        return jsonify({'error': 'Test images not found in images/ folder'}), 404
    
    # Store test image paths in session
    session['uploaded_img1'] = path1
    session['uploaded_img2'] = path2
        
    return process_stitching(path1, path2)

def handle_uploaded_files():
    """Helper to handle file uploads in any route."""
    if 'image1' in request.files and 'image2' in request.files:
        img1 = request.files['image1']
        img2 = request.files['image2']
        
        if img1.filename != '' and img2.filename != '':
            path1 = os.path.join(app.config['UPLOAD_FOLDER'], img1.filename)
            path2 = os.path.join(app.config['UPLOAD_FOLDER'], img2.filename)
            
            img1.save(path1)
            img2.save(path2)
            
            session['uploaded_img1'] = path1
            session['uploaded_img2'] = path2
            return True
    return False

@app.route('/stitch_custom', methods=['POST'])
def stitch_custom():
    """Stitch with manual parameters."""
    handle_uploaded_files()
    
    # Get data from form (if multipart) or json
    data = request.form.to_dict() if request.form else (request.json or {})
    
    # Use uploaded images if available, otherwise fall back to test images
    path1 = session.get('uploaded_img1', os.path.join(app.config['IMAGES_FOLDER'], 'lens_01.png'))
    path2 = session.get('uploaded_img2', os.path.join(app.config['IMAGES_FOLDER'], 'lens_02.png'))
    
    if not os.path.exists(path1) or not os.path.exists(path2):
        return jsonify({'error': 'No images available. Please upload or use test images first.'}), 404

    output_filename = f"result_{int(time.time())}.jpg"
    output_path = os.path.join(app.config['RESULTS_FOLDER'], output_filename)

    try:
        # Extract parameters with defaults
        fov = float(data.get('fov', 192.0))
        yaw_f = float(data.get('yaw_f', 0.0))
        pitch_f = float(data.get('pitch_f', 6.0))
        roll_f = float(data.get('roll_f', 1.1))
        shift_x_f = int(data.get('shift_x_f', 0))
        shift_y_f = int(data.get('shift_y_f', 0))
        mask_radius_f = int(data.get('mask_radius_f', 0))
        mask_softness_f = int(data.get('mask_softness_f', 10))
        mask_aspect_f = float(data.get('mask_aspect_f', 1.0))
        
        yaw_b = float(data.get('yaw_b', 180.0))
        pitch_b = float(data.get('pitch_b', 6.0))
        roll_b = float(data.get('roll_b', 0.0))
        shift_x_b = int(data.get('shift_x_b', 0))
        shift_y_b = int(data.get('shift_y_b', 0))
        mask_radius_b = int(data.get('mask_radius_b', 0))
        mask_softness_b = int(data.get('mask_softness_b', 10))
        mask_aspect_b = float(data.get('mask_aspect_b', 1.0))
        
        threshold = int(data.get('threshold', 31))
        erosion = int(data.get('erosion', 52))
        color_correction = data.get('color_correction') == 'true'
        
        stitcher.stitch(path1, path2, output_path, 
                       fov=fov,
                       yaw_f=yaw_f, pitch_f=pitch_f, roll_f=roll_f, shift_x_f=shift_x_f, shift_y_f=shift_y_f, mask_radius_f=mask_radius_f, mask_softness_f=mask_softness_f, mask_aspect_f=mask_aspect_f,
                       yaw_b=yaw_b, pitch_b=pitch_b, roll_b=roll_b, shift_x_b=shift_x_b, shift_y_b=shift_y_b, mask_radius_b=mask_radius_b, mask_softness_b=mask_softness_b, mask_aspect_b=mask_aspect_b,
                       threshold=threshold, erosion=erosion, color_correction=color_correction)
        
        return jsonify({'result_url': f"/static/results/{output_filename}"})
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 500

@app.route('/stitch_auto', methods=['POST'])
def stitch_auto():
    """Auto-stitch with AI parameter calibration."""
    handle_uploaded_files()
    
    # Use uploaded images if available, otherwise fall back to test images
    path1 = session.get('uploaded_img1', os.path.join(app.config['IMAGES_FOLDER'], 'lens_01.png'))
    path2 = session.get('uploaded_img2', os.path.join(app.config['IMAGES_FOLDER'], 'lens_02.png'))
    
    if not os.path.exists(path1) or not os.path.exists(path2):
        return jsonify({'error': 'No images available. Please upload or use test images first.'}), 404

    output_filename = f"result_auto_{int(time.time())}.jpg"
    output_path = os.path.join(app.config['RESULTS_FOLDER'], output_filename)

    try:
        # Auto-stitch (returns output path and parameters)
        result_path, params = stitcher.stitch_auto(path1, path2, output_path)
        
        # Return result URL and calibrated parameters
        return jsonify({
            'result_url': f"/static/results/{output_filename}",
            'parameters': params
        })
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


def process_stitching(path1, path2):
    output_filename = f"result_{int(time.time())}.jpg"
    output_path = os.path.join(app.config['RESULTS_FOLDER'], output_filename)
    
    try:
        stitcher.stitch(path1, path2, output_path)
        return jsonify({'result_url': f"/static/results/{output_filename}"})
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/detect_radius', methods=['POST'])
def detect_radius():
    try:
        # Get uploaded files
        files = os.listdir(app.config['UPLOAD_FOLDER'])
        images = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        if not images:
            return jsonify({'error': 'No images found'}), 400
            
        # Use the first image (Front Lens) for detection
        # Assuming both lenses have similar radius
        img_path = os.path.join(app.config['UPLOAD_FOLDER'], images[0])
        
        from auto_calibrator import AutoCalibrator
        calibrator = AutoCalibrator()
        radius = calibrator.detect_lens_radius(img_path)
        
        return jsonify({'radius': radius})
        
    except Exception as e:
        print(f"Error detecting radius: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/optimize_grid_search', methods=['POST'])
def optimize_grid_search():
    """Grid search optimization for threshold/erosion."""
    from advanced_optimizer import AdvancedOptimizer
    
    handle_uploaded_files()
    
    # Get image paths
    path1 = session.get('uploaded_img1', os.path.join(app.config['IMAGES_FOLDER'], 'lens_01.png'))
    path2 = session.get('uploaded_img2', os.path.join(app.config['IMAGES_FOLDER'], 'lens_02.png'))
    
    if not os.path.exists(path1) or not os.path.exists(path2):
        return jsonify({'error': 'No images available'}), 404
    
    try:
        optimizer = AdvancedOptimizer(stitcher)
        
        # Get fixed parameters from request
        data = request.form.to_dict() if request.form else (request.json or {})
        fixed_params = {
            'fov': float(data.get('fov', 192.0)),
            'yaw_f': float(data.get('yaw_f', 0.0)),
            'pitch_f': float(data.get('pitch_f', 6.0)),
            'roll_f': float(data.get('roll_f', 1.1)),
            'shift_x_f': int(data.get('shift_x_f', 0)),
            'shift_y_f': int(data.get('shift_y_f', 0)),
            'yaw_b': float(data.get('yaw_b', 180.0)),
            'pitch_b': float(data.get('pitch_b', 6.0)),
            'roll_b': float(data.get('roll_b', 0.0)),
            'shift_x_b': int(data.get('shift_x_b', 0)),
            'shift_y_b': int(data.get('shift_y_b', 0))
        }
        
        # Run grid search
        best_params = optimizer.grid_search_masking(path1, path2, fixed_params=fixed_params)
        
        # Stitch with best parameters
        output_filename = f"result_optimized_{int(time.time())}.jpg"
        output_path = os.path.join(app.config['RESULTS_FOLDER'], output_filename)
        
        stitcher.stitch(path1, path2, output_path, **best_params)
        
        return jsonify({
            'result_url': f"/static/results/{output_filename}",
            'parameters': best_params
        })
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/detect_artifacts', methods=['POST'])
def detect_artifacts():
    """Detect artifacts in the latest result image."""
    from advanced_optimizer import AdvancedOptimizer
    
    data = request.json or {}
    image_url = data.get('image_url')
    
    if not image_url:
        return jsonify({'error': 'No image URL provided'}), 400
    
    # Convert URL to file path
    image_path = image_url.replace('/static/results/', 'static/results/')
    
    if not os.path.exists(image_path):
        return jsonify({'error': 'Image not found'}), 404
    
    try:
        optimizer = AdvancedOptimizer(stitcher)
        artifacts = optimizer.detect_artifacts(image_path)
        
        return jsonify(artifacts)
    except Exception as e:
        print(e)
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
