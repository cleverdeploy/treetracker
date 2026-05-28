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
let upload = null; // { promise } — resolves to { id, needsLocation }

function deleteDraft(id) {
  if (id) fetch(`/api/sightings/${id}`, { method: 'DELETE' }).catch(() => {});
}

// Upload the photo immediately so the network time overlaps the user typing
// the tag. Returns { promise } resolving to { id, needsLocation }.
function startUpload(file) {
  const fd = new FormData();
  fd.append('photo', file);
  setStatus('Uploading photo…');
  const promise = fetch('/api/sightings', { method: 'POST', body: fd }).then(async (r) => {
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    const data = await r.json();
    return { id: data.id, needsLocation: data.needs_location };
  });
  const handle = { promise };
  promise.then(
    () => { if (upload === handle && !submitBtn.disabled) setStatus('✓ Photo ready'); },
    () => { if (upload === handle && !submitBtn.disabled) setStatus('Photo upload failed — tap Submit to retry.', 'error'); }
  );
  return handle;
}

function pickFile(input, other) {
  input.addEventListener('change', () => {
    if (!input.files[0]) return;
    other.value = '';
    // Supersede any prior upload: let it finish, then delete the draft it made
    // (aborting can't undo a create the server already accepted).
    if (upload) upload.promise.then((res) => deleteDraft(res.id), () => {});
    currentSightingId = null;

    selectedFile = input.files[0];
    preview.src = URL.createObjectURL(selectedFile);
    preview.hidden = false;
    previewWrap.classList.add('has-photo');

    upload = startUpload(selectedFile);
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
  if (!selectedFile || !upload) {
    setStatus('Pick a photo first.', 'error');
    return;
  }
  submitBtn.disabled = true;
  setStatus('Finishing upload…');

  let res;
  try {
    res = await upload.promise;
  } catch (err) {
    setStatus('Photo upload failed: ' + err.message, 'error');
    upload = startUpload(selectedFile); // re-arm for retry
    submitBtn.disabled = false;
    return;
  }

  const comment = form.querySelector('[name=comment]');
  setStatus('Saving…');
  try {
    const r = await fetch(`/api/sightings/${res.id}/finalize`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ manual_tag: manual.value, comment: comment ? comment.value : null }),
    });
    if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
    upload = null; // row is now pending — must not be deleted as a draft
    currentSightingId = res.id;
    if (res.needsLocation) {
      form.hidden = true;
      pinStep.hidden = false;
      initPinMap();
      setStatus('');
    } else {
      finish();
    }
  } catch (err) {
    setStatus('Submit failed: ' + err.message, 'error');
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
