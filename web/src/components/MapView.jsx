/**
 * MapView.jsx
 *
 * Leaflet map hiển thị 53 trạm quan trắc Delhi.
 * Mỗi station = 1 CircleMarker, màu tương ứng mức AQI.
 * Click vào marker → Popup hiển thị tên + PM2.5 + level.
 *
 * Lưu ý kỹ thuật:
 *   - Phải import leaflet/dist/leaflet.css để marker/popup render đúng
 *   - MapContainer cần style height tường minh — Leaflet không dùng được 100%
 *   - center & zoom là toạ độ Delhi (28.65, 77.23) ở mức zoom 10
 *
 * Props:
 *   stations — Array<{ name, lat, lng, latest_pm25, level }>
 *              Nguồn: GET /api/stations
 */

import 'leaflet/dist/leaflet.css'
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'

/** Màu fill marker theo mức AQI — phải khớp với levels.js */
const LEVEL_COLORS = {
  Good:            '#2d9e5f',
  Moderate:        '#8dc63f',
  Unhealthy:       '#f5a623',
  'Very Unhealthy':'#d0021b',
  Hazardous:       '#7b0000',
}

/** Trung tâm Delhi và zoom ban đầu */
const DELHI_CENTER = [28.65, 77.23]
const DEFAULT_ZOOM = 10

export default function MapView({ stations }) {
  if (!stations?.length) return null

  return (
    // Wrapper div để map không "thoát" ra ngoài card
    <div className="rounded-xl overflow-hidden" style={{ height: 340 }}>
      <MapContainer
        center={DELHI_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '100%', width: '100%' }}
        // scrollWheelZoom=false tránh zoom khi scroll trang
        scrollWheelZoom={false}
      >
        {/* OpenStreetMap tile — không cần API key */}
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />

        {/* Render 1 CircleMarker per station */}
        {stations.map((s) => (
          <CircleMarker
            key={s.name}
            center={[s.lat, s.lng]}
            radius={8}
            pathOptions={{
              fillColor: LEVEL_COLORS[s.level] ?? '#6b7280',
              fillOpacity: 0.85,
              color: '#fff',       // viền trắng để tách biệt các marker chồng nhau
              weight: 1.5,
            }}
          >
            {/* Popup: click marker để xem chi tiết */}
            <Popup>
              <div className="text-xs leading-relaxed">
                {/* Rút gọn tên: bỏ ", Delhi - DPCC" */}
                <p className="font-semibold text-gray-800 mb-1">
                  {s.name.replace(/,?\s*(Delhi\s*[-–]\s*\w+)$/i, '').trim()}
                </p>
                <p>
                  PM2.5:{' '}
                  <strong style={{ color: LEVEL_COLORS[s.level] }}>
                    {s.latest_pm25} µg/m³
                  </strong>
                </p>
                <p>Mức: <strong>{s.level}</strong></p>
                <p className="text-gray-400 mt-1">TB Q4: {s.avg_pm25} µg/m³</p>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}
