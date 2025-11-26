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

    testBtn.addEventListener('click', async () => {
        await runStitchRequest('/stitch_test', {
            method: 'POST'
        });
    });

    customBtn.addEventListener('click', async () => {
        const params = {
            fov: document.getElementById('fov').value,
            threshold: document.getElementById('threshold').value,
            erosion: document.getElementById('erosion').value,
            yaw_f: document.getElementById('yaw_f').value,
            pitch_f: document.getElementById('pitch_f').value,
            roll_f: document.getElementById('roll_f').value,
            yaw_b: document.getElementById('yaw_b').value,
            pitch_b: document.getElementById('pitch_b').value,
            roll_b: document.getElementById('roll_b').value
        };

        await runStitchRequest('/stitch_custom', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(params)
        });
    });
});
