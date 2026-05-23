const STRATFORD = [52.1917, -1.7080];
const form = document.getElementById('upload-form');
const photoCamera = document.getElementById('photo-camera');
const photoLibrary = document.getElementById('photo-library');
const preview = document.getElementById('preview');
const previewWrap = document.getElementById('preview-wrap');
const statusEl = document.getElementById('status');
const submitBtn = document.getElementById('submit-btn');
const pinStep = document.getElementById('pin-step');
const pinSave = document.getElementById('pin-save');
const doneEl = document.getElementById('done');

let pinMap, pinMarker, currentSightingId;
let selectedFile = null;

function pickFile(input, other) {
  input.addEventListener('change', () => {
    if (input.files[0]) {
      selectedFile = input.files[0];
      other.value = '';
      preview.src = URL.createObjectURL(selectedFile);
      previewWrap.hidden = false;
    }
  });
}
pickFile(photoCamera, photoLibrary);
pickFile(photoLibrary, photoCamera);

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const manual = form.querySelector('[name=manual_tag]');
  if (!manual.value.trim()) {
    setStatus('Enter the tag number.', 'error');
    manual.focus();
    return;
  }
  if (!selectedFile) {
    setStatus('Pick a photo first.', 'error');
    return;
  }
  submitBtn.disabled = true;
  setStatus('Uploading…');
  const fd = new FormData();
  fd.append('photo', selectedFile);
  const comment = form.querySelector('[name=comment]');
  if (comment && comment.value) fd.append('comment', comment.value);
  const manual = form.querySelector('[name=manual_tag]');
  if (manual && manual.value) fd.append('manual_tag', manual.value);
  try {
    const r = await fetch('/api/sightings', { method: 'POST', body: fd });
    if (!r.ok) {
      const t = await r.text();
      throw new Error(`${r.status} ${t}`);
    }
    const data = await r.json();
    currentSightingId = data.id;
    if (data.needs_location) {
      form.hidden = true;
      pinStep.hidden = false;
      initPinMap();
      setStatus('');
    } else {
      finish();
    }
  } catch (err) {
    setStatus('Upload failed: ' + err.message, 'error');
    submitBtn.disabled = false;
  }
});

function initPinMap() {
  pinMap = L.map('pin-map').setView(STRATFORD, 15);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap',
  }).addTo(pinMap);
  pinMap.on('click', (e) => {
    if (pinMarker) pinMarker.setLatLng(e.latlng);
    else pinMarker = L.marker(e.latlng).addTo(pinMap);
    pinSave.disabled = false;
  });
  setTimeout(() => pinMap.invalidateSize(), 50);
}

pinSave.addEventListener('click', async () => {
  if (!pinMarker) return;
  pinSave.disabled = true;
  const { lat, lng } = pinMarker.getLatLng();
  try {
    const r = await fetch(`/api/sightings/${currentSightingId}/location`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lon: lng }),
    });
    if (!r.ok) throw new Error(await r.text());
    finish();
  } catch (err) {
    setStatus('Save failed: ' + err.message, 'error');
    pinSave.disabled = false;
  }
});

function finish() {
  form.hidden = true;
  pinStep.hidden = true;
  doneEl.hidden = false;
}

function setStatus(msg, cls = '') {
  statusEl.textContent = msg;
  statusEl.className = 'status ' + cls;
}
