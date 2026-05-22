const STRATFORD = [52.1917, -1.7080];
const map = L.map('map', { zoomControl: true }).setView(STRATFORD, 14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
}).addTo(map);

const cluster = L.markerClusterGroup();
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
    });
    map.addLayer(cluster);
    if (bounds.length > 1) map.fitBounds(bounds, { padding: [40, 40] });
  });
