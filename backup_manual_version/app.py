from flask import Flask, render_template, request, send_from_directory, jsonify
import os
from stitcher import Stitcher
import time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['RESULTS_FOLDER'] = 'static/results'
app.config['IMAGES_FOLDER'] = 'images'

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
    
    return process_stitching(path1, path2)

@app.route('/stitch_test', methods=['POST'])
def stitch_test():
    # Use images from the images folder
    path1 = os.path.join(app.config['IMAGES_FOLDER'], 'lens_01.png')
    path2 = os.path.join(app.config['IMAGES_FOLDER'], 'lens_02.png')
    
    if not os.path.exists(path1) or not os.path.exists(path2):
        return jsonify({'error': 'Test images not found in images/ folder'}), 404
        
    return process_stitching(path1, path2)

@app.route('/stitch_custom', methods=['POST'])
def stitch_custom():
    """Stitch with manual parameters."""
    data = request.json
    # Use images from the images folder for now, or we could allow uploads. 
    # For the "Manual Control" mode, using the test images is safest/easiest for the user to iterate.
    path1 = os.path.join(app.config['IMAGES_FOLDER'], 'lens_01.png')
    path2 = os.path.join(app.config['IMAGES_FOLDER'], 'lens_02.png')
    
    if not os.path.exists(path1) or not os.path.exists(path2):
        return jsonify({'error': 'Test images not found'}), 404

    output_filename = f"result_{int(time.time())}.jpg"
    output_path = os.path.join(app.config['RESULTS_FOLDER'], output_filename)

    try:
        # Extract parameters with defaults
        fov = float(data.get('fov', 200.0))
        yaw_f = float(data.get('yaw_f', 0.0))
        pitch_f = float(data.get('pitch_f', 0.0))
        roll_f = float(data.get('roll_f', 0.0))
        yaw_b = float(data.get('yaw_b', 180.0))
        pitch_b = float(data.get('pitch_b', 0.0))
        roll_b = float(data.get('roll_b', 0.0))
        threshold = int(data.get('threshold', 90))
        erosion = int(data.get('erosion', 3))
        
        stitcher.stitch(path1, path2, output_path, 
                       fov=fov,
                       yaw_f=yaw_f, pitch_f=pitch_f, roll_f=roll_f,
                       yaw_b=yaw_b, pitch_b=pitch_b, roll_b=roll_b,
                       threshold=threshold, erosion=erosion)
        
        return jsonify({'result_url': f"/static/results/{output_filename}"})
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
