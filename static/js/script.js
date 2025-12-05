document.addEventListener('DOMContentLoaded', () => {
    const dropZones = document.querySelectorAll('.drop-zone');
    const stitchBtn = document.getElementById('stitch-btn');
    const testBtn = document.getElementById('test-btn');
    const customBtn = document.getElementById('customBtn');
    const resultSection = document.getElementById('result-section');
    const resultImg = document.getElementById('result-img');
    const downloadBtn = document.getElementById('download-btn');
    const loader = document.querySelector('.loader');
    const btnText = document.querySelector('.btn-text');
    const errorDiv = document.getElementById('error-div');

    let file1 = null;
    let file2 = null;

    dropZones.forEach(zone => {
        const input = zone.querySelector('input');
        const status = zone.querySelector('.status');

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.classList.add('active');
        });

        zone.addEventListener('dragleave', () => {
            zone.classList.remove('active');
        });

        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.classList.remove('active');
            const file = e.dataTransfer.files[0];
            handleFile(file, zone.id);
        });

        input.addEventListener('change', (e) => {
            const file = e.target.files[0];
            handleFile(file, zone.id);
        });
    });

    function handleFile(file, zoneId) {
        if (!file) return;

        const zone = document.getElementById(zoneId);
        const status = zone.querySelector('.status');

        if (file.type.startsWith('image/')) {
            status.textContent = file.name;
            status.style.color = '#3b82f6';

            if (zoneId === 'drop-zone-1') file1 = file;
            else file2 = file;
        } else {
            status.textContent = 'Invalid file type';
            status.style.color = '#ef4444';
        }
    }

    // Helper to run stitching request
    async function runStitchRequest(url, options) {
        // UI Loading State
        if (stitchBtn) stitchBtn.disabled = true;
        if (testBtn) testBtn.disabled = true;
        if (customBtn) customBtn.disabled = true;

        loader.classList.remove('hidden');
        resultSection.classList.add('hidden');
        if (errorDiv) errorDiv.classList.add('hidden');

        try {
            const response = await fetch(url, options);
            const data = await response.json();

            if (response.ok) {
                resultImg.src = data.result_url + '?t=' + new Date().getTime();
                downloadBtn.href = data.result_url;
                resultSection.classList.remove('hidden');
                resultSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                throw new Error(data.error || 'Stitching failed');
            }
        } catch (error) {
            console.error('Error:', error);
            if (errorDiv) {
                errorDiv.textContent = error.message;
                errorDiv.classList.remove('hidden');
            } else {
                alert('Error: ' + error.message);
            }
        } finally {
            if (stitchBtn) stitchBtn.disabled = false;
            if (testBtn) testBtn.disabled = false;
            if (customBtn) customBtn.disabled = false;
            loader.classList.add('hidden');
        }
    }

    if (stitchBtn) {
        stitchBtn.addEventListener('click', async () => {
            if (!file1 || !file2) {
                alert('Please select both images first.');
                return;
            }

            const formData = new FormData();
            formData.append('image1', file1);
            formData.append('image2', file2);

            await runStitchRequest('/stitch', {
                method: 'POST',
                body: formData
            });
        });
    }

    if (testBtn) {
        testBtn.addEventListener('click', async () => {
            await runStitchRequest('/stitch_test', {
                method: 'POST'
            });
        });
    }

    if (customBtn) {
        customBtn.addEventListener('click', async () => {
            const formData = new FormData();
            if (file1) formData.append('image1', file1);
            if (file2) formData.append('image2', file2);

            // Global params
            formData.append('fov', document.getElementById('fov').value);
            formData.append('threshold', document.getElementById('threshold').value);
            formData.append('erosion', document.getElementById('erosion').value);
            formData.append('color_correction', document.getElementById('color_correction').checked);

            // Front Lens params
            formData.append('yaw_f', document.getElementById('yaw_f').value);
            formData.append('pitch_f', document.getElementById('pitch_f').value);
            formData.append('roll_f', document.getElementById('roll_f').value);
            formData.append('shift_x_f', document.getElementById('shift_x_f').value);
            formData.append('shift_y_f', document.getElementById('shift_y_f').value);
            formData.append('mask_radius_f', document.getElementById('mask_radius_f').value);
            formData.append('mask_softness_f', document.getElementById('mask_softness_f').value);
            formData.append('mask_aspect_f', document.getElementById('mask_aspect_f').value);

            // Back Lens params
            formData.append('yaw_b', document.getElementById('yaw_b').value);
            formData.append('pitch_b', document.getElementById('pitch_b').value);
            formData.append('roll_b', document.getElementById('roll_b').value);
            formData.append('shift_x_b', document.getElementById('shift_x_b').value);
            formData.append('shift_y_b', document.getElementById('shift_y_b').value);
            formData.append('mask_radius_b', document.getElementById('mask_radius_b').value);
            formData.append('mask_softness_b', document.getElementById('mask_softness_b').value);
            formData.append('mask_aspect_b', document.getElementById('mask_aspect_b').value);

            await runStitchRequest('/stitch_custom', {
                method: 'POST',
                body: formData
            });
        });
    }

    // Auto Stitch with AI calibration
    const autoBtn = document.getElementById('auto-btn');
    const autoParamsDiv = document.getElementById('auto-params');
    const autoParamsContent = document.getElementById('auto-params-content');

    if (autoBtn) {
        autoBtn.addEventListener('click', async () => {
            // Hide previous params
            if (autoParamsDiv) autoParamsDiv.classList.add('hidden');

            // Show loading message
            if (btnText) btnText.textContent = 'AI is analyzing images...';

            const formData = new FormData();
            if (file1) formData.append('image1', file1);
            if (file2) formData.append('image2', file2);

            try {
                const response = await fetch('/stitch_auto', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (response.ok) {
                    // Show result image
                    resultImg.src = data.result_url + '?t=' + new Date().getTime();
                    downloadBtn.href = data.result_url;
                    resultSection.classList.remove('hidden');

                    // Display calibrated parameters
                    if (data.parameters && autoParamsContent) {
                        const params = data.parameters;
                        autoParamsContent.innerHTML = `
                            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
                                <div><strong>FOV:</strong> ${params.fov}</div>
                                <div><strong>Threshold:</strong> ${params.threshold}</div>
                                <div><strong>Erosion:</strong> ${params.erosion}</div>
                            </div>
                            <div style="margin-top: 1rem; display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                                <div>
                                    <strong>Front Lens:</strong><br>
                                    Yaw: ${params.yaw_f}° | Pitch: ${params.pitch_f}° | Roll: ${params.roll_f}°
                                </div>
                                <div>
                                    <strong>Back Lens:</strong><br>
                                    Yaw: ${params.yaw_b}° | Pitch: ${params.pitch_b}° | Roll: ${params.roll_b}°
                                </div>
                            </div>
                        `;
                        autoParamsDiv.classList.remove('hidden');

                        // Update manual controls with calibrated values
                        document.getElementById('fov').value = params.fov;
                        document.getElementById('threshold').value = params.threshold;
                        document.getElementById('erosion').value = params.erosion;
                        document.getElementById('yaw_f').value = params.yaw_f;
                        document.getElementById('pitch_f').value = params.pitch_f;
                        document.getElementById('roll_f').value = params.roll_f;
                        document.getElementById('yaw_b').value = params.yaw_b;
                        document.getElementById('pitch_b').value = params.pitch_b;
                        document.getElementById('roll_b').value = params.roll_b;
                    }

                    resultSection.scrollIntoView({ behavior: 'smooth' });
                } else {
                    throw new Error(data.error || 'Auto-stitching failed');
                }
            } catch (error) {
                console.error('Error:', error);
                if (errorDiv) {
                    errorDiv.textContent = error.message;
                    errorDiv.classList.remove('hidden');
                } else {
                    alert('Error: ' + error.message);
                }
            } finally {
                if (autoBtn) {
                    autoBtn.innerHTML = '🤖 Auto Stitch (AI)';
                    autoBtn.disabled = false;
                }
            }
        });
    }

    // Optimize Masking with Grid Search
    const optimizeBtn = document.getElementById('optimize-btn');

    if (optimizeBtn) {
        optimizeBtn.addEventListener('click', async () => {
            const formData = new FormData();
            if (file1) formData.append('image1', file1);
            if (file2) formData.append('image2', file2);

            formData.append('fov', document.getElementById('fov').value);
            formData.append('yaw_f', document.getElementById('yaw_f').value);
            formData.append('pitch_f', document.getElementById('pitch_f').value);
            formData.append('roll_f', document.getElementById('roll_f').value);
            formData.append('shift_x_f', document.getElementById('shift_x_f').value);
            formData.append('shift_y_f', document.getElementById('shift_y_f').value);
            formData.append('mask_radius_f', document.getElementById('mask_radius_f').value);

            formData.append('yaw_b', document.getElementById('yaw_b').value);
            formData.append('pitch_b', document.getElementById('pitch_b').value);
            formData.append('roll_b', document.getElementById('roll_b').value);
            formData.append('shift_x_b', document.getElementById('shift_x_b').value);
            formData.append('shift_y_b', document.getElementById('shift_y_b').value);
            formData.append('mask_radius_b', document.getElementById('mask_radius_b').value);

            // Show loading
            optimizeBtn.disabled = true;
            optimizeBtn.textContent = '⏳ Optimizing (2-3 min)...';
            if (errorDiv) errorDiv.classList.add('hidden');

            try {
                const response = await fetch('/optimize_grid_search', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();

                if (response.ok) {
                    // Show result
                    resultImg.src = data.result_url + '?t=' + new Date().getTime();
                    downloadBtn.href = data.result_url;
                    resultSection.classList.remove('hidden');

                    // Display optimized parameters
                    if (data.parameters && autoParamsContent) {
                        const p = data.parameters;
                        autoParamsContent.innerHTML = `
                            <div style="margin-bottom: 1rem;"><strong>🎯 Optimized Masking Parameters:</strong></div>
                            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                                <div><strong>Threshold:</strong> ${p.threshold}</div>
                                <div><strong>Erosion:</strong> ${p.erosion}</div>
                            </div>
                        `;
                        autoParamsDiv.classList.remove('hidden');

                        // Update form
                        document.getElementById('threshold').value = p.threshold;
                        document.getElementById('erosion').value = p.erosion;
                    }

                    resultSection.scrollIntoView({ behavior: 'smooth' });
                } else {
                    throw new Error(data.error || 'Optimization failed');
                }
            } catch (error) {
                console.error('Error:', error);
                if (errorDiv) {
                    errorDiv.textContent = error.message;
                    errorDiv.classList.remove('hidden');
                } else {
                    alert('Error: ' + error.message);
                }
            } finally {
                optimizeBtn.disabled = false;
                optimizeBtn.textContent = '⚡ Optimize Masking';
            }
        });
    }
    // Zoom and Pan Controls
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const zoomResetBtn = document.getElementById('zoom-reset');

    let currentScale = 1;
    let isDragging = false;
    let startX, startY, translateX = 0, translateY = 0;

    function updateTransform() {
        if (resultImg) {
            resultImg.style.transform = `scale(${currentScale}) translate(${translateX}px, ${translateY}px)`;
        }
    }

    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', () => {
            currentScale += 0.2;
            updateTransform();
        });
    }

    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', () => {
            if (currentScale > 0.4) {
                currentScale -= 0.2;
                updateTransform();
            }
        });
    }

    if (zoomResetBtn) {
        zoomResetBtn.addEventListener('click', () => {
            currentScale = 1;
            translateX = 0;
            translateY = 0;
            updateTransform();
        });
    }

    // Pan functionality
    if (resultImg) {
        resultImg.addEventListener('mousedown', (e) => {
            if (currentScale > 1) {
                isDragging = true;
                startX = e.clientX - translateX;
                startY = e.clientY - translateY;
                resultImg.style.cursor = 'grabbing';
                e.preventDefault(); // Prevent default drag behavior
            }
        });

        window.addEventListener('mousemove', (e) => {
            if (isDragging) {
                translateX = e.clientX - startX;
                translateY = e.clientY - startY;
                updateTransform();
            }
        });

        window.addEventListener('mouseup', () => {
            if (isDragging) {
                isDragging = false;
                resultImg.style.cursor = 'grab';
            }
        });

        // Wheel zoom
        resultImg.addEventListener('wheel', (e) => {
            if (e.ctrlKey) {
                e.preventDefault();
                if (e.deltaY < 0) {
                    currentScale += 0.1;
                } else {
                    if (currentScale > 0.4) currentScale -= 0.1;
                }
                updateTransform();
            }
        });
    }
});
