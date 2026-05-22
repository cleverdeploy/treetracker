const STRATFORD = [52.1917, -1.7080];

document.querySelectorAll('.queue-item').forEach(initQueueItem);

function initQueueItem(item) {
  const id = item.dataset.id;
  const result = item.querySelector('.result');
  const finalTag = item.querySelector('.final-tag');
  const reason = item.querySelector('.reject-reason');
  const approveBtn = item.querySelector('.approve');
  const rejectBtn = item.querySelector('.reject');
  const mapToggle = item.querySelector('.map-toggle');
  const mapDiv = item.querySelector('.mini-map');
  let map, marker;
  let lat = parseFloat(item.dataset.lat) || null;
  let lon = parseFloat(item.dataset.lon) || null;

  mapToggle.addEventListener('toggle', () => {
    if (!mapToggle.open || map) return;
    map = L.map(mapDiv).setView(lat && lon ? [lat, lon] : STRATFORD, lat ? 17 : 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, attribution: '© OpenStreetMap',
    }).addTo(map);
    if (lat && lon) marker = L.marker([lat, lon]).addTo(map);
    map.on('click', (e) => {
      lat = e.latlng.lat; lon = e.latlng.lng;
      if (marker) marker.setLatLng(e.latlng);
      else marker = L.marker(e.latlng).addTo(map);
    });
    setTimeout(() => map.invalidateSize(), 50);
  });

  approveBtn.addEventListener('click', async () => {
    approveBtn.disabled = true;
    try {
      const body = { final_tag: finalTag.value };
      if (lat && lon) { body.lat = lat; body.lon = lon; }
      const r = await fetch(`/api/sightings/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error(await r.text());
      result.textContent = '✓ approved';
      result.style.color = '#6ee7b7';
      item.style.opacity = 0.55;
      rejectBtn.disabled = true;
    } catch (err) {
      result.textContent = 'failed: ' + err.message;
      result.style.color = 'var(--danger)';
      approveBtn.disabled = false;
    }
  });

  rejectBtn.addEventListener('click', async () => {
    rejectBtn.disabled = true;
    try {
      const r = await fetch(`/api/sightings/${id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason.value || 'no reason' }),
      });
      if (!r.ok) throw new Error(await r.text());
      result.textContent = '✗ rejected';
      result.style.color = 'var(--muted)';
      item.style.opacity = 0.4;
      approveBtn.disabled = true;
    } catch (err) {
      result.textContent = 'failed: ' + err.message;
      result.style.color = 'var(--danger)';
      rejectBtn.disabled = false;
    }
  });
}
