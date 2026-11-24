/**
 * Dashboard.jsx — Trang tổng quan Air Quality
 *
 * Layout:
 *   Row 1: 4 KPI cards (avg PM2.5, % vượt WHO, worst station, best station)
 *   Row 2: Leaflet map (trái) + Top-10 bảng ô nhiễm (phải)
 *   Row 3: Daily trend chart (actual vs predicted)
 *
 * Data fetching:
 *   - fetchStations() → map markers + KPIs + top-10 table
 *   - fetchDaily()    → trend chart
 *   Hai request chạy song song tại mount.
 */

import AlertBanner from '../components/AlertBanner'
import KPICard     from '../components/KPICard'
import MapView     from '../components/MapView'
import Spinner     from '../components/Spinner'
import StationTable from '../components/StationTable'
import TrendChart  from '../components/TrendChart'
import { useApi }  from '../hooks/useApi'
import { fetchDaily, fetchStations } from '../utils/api'
import { WHO_PM25 } from '../utils/levels'

export default function Dashboard() {
  // ── Data fetching ────────────────────────────────────────────────────────
  // fetchStations: list 53 stations + latest_pm25 + level + coords
  const { data: stations, loading: stationsLoading, error: stationsError } =
    useApi(fetchStations)

  // fetchDaily: city-wide daily avg (actual + predicted) cho trend chart
  const { data: daily, loading: dailyLoading } = useApi(fetchDaily)

  // ── Derived KPI values (computed từ stations list) ───────────────────────
  // Chỉ tính khi stations đã load xong
  const kpis = stations
    ? (() => {
        // Trung bình PM2.5 mới nhất của tất cả stations
        const avgPm25 = stations.reduce((s, x) => s + x.latest_pm25, 0) / stations.length

        // % stations vượt ngưỡng WHO (15 µg/m³)
        const exceedCount = stations.filter((x) => x.latest_pm25 > WHO_PM25).length
        const whoExceedPct = Math.round((exceedCount / stations.length) * 100)

        // Worst: station có avg_pm25 cao nhất (index 0 vì API đã sort desc)
        const worst = stations[0]
        // Best: station có avg_pm25 thấp nhất (index cuối)
        const best  = stations[stations.length - 1]

        return { avgPm25, whoExceedPct, worst, best }
      })()
    : null

  // ── Loading / Error states ───────────────────────────────────────────────
  if (stationsLoading) return <Spinner text="Đang tải dữ liệu…" />
  if (stationsError)
    return (
      <div className="card text-red-600 text-sm">
        Không tải được dữ liệu: {stationsError}
        <p className="text-gray-400 mt-1 text-xs">
          Hãy đảm bảo API server đang chạy: <code>uvicorn api.main:app --reload</code>
        </p>
      </div>
    )

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ── Header ────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">
          Nền tảng Dự báo Chất lượng Không khí
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Tổng quan PM2.5 · 53 trạm quan trắc tại Delhi · Tập kiểm tra Q4/2025
        </p>
      </div>

      {/* ── Alert Banner: AQI alert dựa trên avg PM2.5 ─────────────────── */}
      {kpis && <AlertBanner pm25={kpis.avgPm25} />}

      {/* ── Row 1: KPI Cards ──────────────────────────────────────────── */}
      {kpis && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* KPI 1: Avg PM2.5 mới nhất */}
          <KPICard
            label="PM2.5 Trung bình TP"
            value={`${kpis.avgPm25.toFixed(1)} µg/m³`}
            sub={`Ngưỡng WHO: ${WHO_PM25} µg/m³`}
          />

          {/* KPI 2: % stations vượt WHO limit */}
          <KPICard
            label="Trạm vượt WHO"
            value={`${kpis.whoExceedPct}%`}
            sub={`${stations.filter((x) => x.latest_pm25 > WHO_PM25).length} trong ${stations.length} trạm`}
            subColor="#d0021b"
          />

          {/* KPI 3: Station ô nhiễm nhất */}
          <KPICard
            label="Ô nhiễm nhất"
            value={`${kpis.worst.avg_pm25} µg/m³`}
            sub={kpis.worst.name.replace(/,?\s*(Delhi\s*[-–]\s*\w+)$/i, '').trim()}
            subColor="#d0021b"
          />

          {/* KPI 4: Station sạch nhất */}
          <KPICard
            label="Sạch nhất"
            value={`${kpis.best.avg_pm25} µg/m³`}
            sub={kpis.best.name.replace(/,?\s*(Delhi\s*[-–]\s*\w+)$/i, '').trim()}
            subColor="#2d9e5f"
          />
        </div>
      )}

      {/* ── Row 2: Map + Table ────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Leaflet map: chiếm 3/5 chiều rộng trên màn lớn */}
        <div className="card lg:col-span-3 p-0 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100">
            <h2 className="text-sm font-semibold text-gray-700">Bản đồ trạm quan trắc</h2>
            <p className="text-xs text-gray-400">Màu = mức AQI hiện tại · Nhấp để xem chi tiết</p>
          </div>
          <div className="p-3">
            <MapView stations={stations} />
          </div>
        </div>

        {/* Top-10 bảng: chiếm 2/5 */}
        <div className="card lg:col-span-2">
          <h2 className="text-sm font-semibold text-gray-700 mb-1">
            Top 10 Ô nhiễm nhất
          </h2>
          <p className="text-xs text-gray-400 mb-3">Sắp xếp theo PM2.5 TB Q4 ↓</p>
          <StationTable stations={stations} />
        </div>
      </div>

      {/* ── Row 3: Trend Chart ────────────────────────────────────────── */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-700 mb-0.5">
          PM2.5 Trung bình Thành phố theo Ngày
        </h2>
        <p className="text-xs text-gray-400 mb-4">
          Thực tế vs dự báo ngày hôm sau của LightGBM · Q4/2025
        </p>
        {dailyLoading ? (
          <Spinner text="Đang tải biểu đồ…" />
        ) : (
          <TrendChart data={daily} />
        )}
      </div>
    </div>
  )
}
