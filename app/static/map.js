const STRATFORD = [52.1917, -1.7080];
const map = L.map('map', { zoomControl: true }).setView(STRATFORD, 14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

const cluster = L.markerClusterGroup();
const markersByTag = new Map();          // tag_number -> Leaflet marker

fetch('/api/trees.geojson')
  .then(r => r.json())
  .then(fc => {
    if (!fc.features.length) return;
    const bounds = [];
    fc.features.forEach(f => {
      const [lon, lat] = f.geometry.coordinates;
      const p = f.properties;
      const m = L.marker([lat, lon]);
      const thumb = p.thumb_url ? `<img src="${p.thumb_url}" alt="" style="width:140px;height:100px;object-fit:cover;border-radius:6px;display:block;margin-bottom:6px">` : '';
      m.bindPopup(`${thumb}<strong>Tree #${p.tag_number}</strong><br><a href="/trees/${p.id}">View details →</a>`);
      cluster.addLayer(m);
      bounds.push([lat, lon]);
      markersByTag.set(p.tag_number, m);
    });
    map.addLayer(cluster);
    if (bounds.length > 1) map.fitBounds(bounds, { padding: [40, 40] });
  });

// Search by tag number
const form = document.getElementById('tree-search');
const input = document.getElementById('tree-search-input');
const results = document.getElementById('search-results');

function normalize(s) { return (s || '').replace(/\D/g, ''); }
function stripZeros(s) { return s.replace(/^0+/, '') || '0'; }

function focusMarker(marker) {
  const ll = marker.getLatLng();
  map.setView(ll, 19);
  setTimeout(() => marker.openPopup(), 250);
}

/**
 * Search ranking:
 *   1. exact tag match
 *   2. tag equals query with leading zeros stripped (so "1" → "0001")
 *   3. substring contains
 * Returns [[tag, marker], ...] in priority order.
 */
function searchMatches(q) {
  const qz = stripZeros(q);
  const exact = [];
  const trimmed = [];
  const substr = [];
  for (const [tag, m] of markersByTag.entries()) {
    if (tag === q) exact.push([tag, m]);
    else if (stripZeros(tag) === qz) trimmed.push([tag, m]);
    else if (tag.includes(q)) substr.push([tag, m]);
  }
  return [...exact, ...trimmed, ...substr];
}

function showMatches(matches, autoFocusBest) {
  if (matches.length === 0) {
    results.innerHTML = '<p class="muted">No matching tree.</p>';
    results.hidden = false;
    return;
  }
  if (autoFocusBest) {
    results.hidden = true;
    focusMarker(matches[0][1]);
    return;
  }
  const best = matches[0];
  const rest = matches.slice(1, 12);
  const restHtml = rest.length
    ? `<div class="search-more">also: ${rest.map(([t]) =>
        `<button type="button" data-tag="${t}">#${t}</button>`).join('')}</div>`
    : '';
  results.innerHTML =
    `<button type="button" class="best" data-tag="${best[0]}">Show #${best[0]}</button>` + restHtml;
  results.hidden = false;
}

results.addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-tag]');
  if (!btn) return;
  const m = markersByTag.get(btn.dataset.tag);
  if (m) { results.hidden = true; focusMarker(m); }
});

form.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = normalize(input.value);
  if (!q) return;
  showMatches(searchMatches(q), /* autoFocusBest */ true);
});

input.addEventListener('input', () => {
  const q = normalize(input.value);
  if (!q) { results.hidden = true; return; }
  showMatches(searchMatches(q), /* autoFocusBest */ false);
});
