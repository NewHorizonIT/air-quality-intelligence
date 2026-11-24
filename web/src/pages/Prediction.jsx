/**
 * Prediction.jsx — Trang Prediction Demo
 *
 * Layout:
 *   Row 0: Controls — dropdown station + date picker + nút Predict
 *   Row 1: Result card (PM2.5 + AlertBanner) | 30-day history chart
 *   Row 2: SHAP explanation chart (top-10 feature contributions)
 *
 * Data fetching:
 *   - fetchStations()               → populate station dropdown (tại mount)
 *   - fetchPrediction(station, date) → kết quả dự đoán + SHAP (khi submit)
 *   - fetchHistory(station, 30)     → 30-day PM2.5 history (khi submit, song song)
 *
 * Lưu ý về date picker:
 *   - Chỉ cho phép chọn ngày trong test set: 2025-10-01 → 2025-12-30
 *   - Giá trị min/max set trên input[type=date] để browser enforce
 */

import { useState } from 'react'

import AlertBanner from '../components/AlertBanner'
import KPICard     from '../components/KPICard'
import ShapChart   from '../components/ShapChart'
import Spinner     from '../components/Spinner'
import TrendChart  from '../components/TrendChart'
import { useApi }  from '../hooks/useApi'
import { fetchHistory, fetchPrediction, fetchStations } from '../utils/api'

/** Giới hạn ngày bắt đầu: ngày đầu tiên có đủ 30 ngày lịch sử trong test set */
const DATE_MIN = '2025-10-01'
/** Giới hạn ngày kết thúc: hôm nay (live path cho phép predict bất kỳ ngày nào) */
const DATE_MAX = new Date().toISOString().slice(0, 10)

export default function Prediction() {
  // ── State form ───────────────────────────────────────────────────────────
  const [station, setStation] = useState('')
  const [date, setDate]       = useState(DATE_MIN)   // default: ngày đầu test set

  // ── Station list (load 1 lần khi mount để populate dropdown) ─────────────
  const { data: stations, loading: stationsLoading } = useApi(fetchStations)

  // ── Prediction result + SHAP ─────────────────────────────────────────────
  // skip=true: không tự fetch, chỉ fetch khi user bấm Predict
  const {
    data:    prediction,
    loading: predLoading,
    error:   predError,
    refetch: runPredict,
  } = useApi(
    () => fetchPrediction(station, date),
    [station, date],  // deps: re-build fetcher khi station/date thay đổi
    true,             // skip: chờ user submit
  )

  // ── 30-day history (cũng skip, fetch song song với prediction) ───────────
  const {
    data:    history,
    loading: histLoading,
    refetch: runHistory,
  } = useApi(
    () => fetchHistory(station, 30),
    [station],
    true,
  )

  /** Xử lý submit: validate rồi gọi cả 2 request song song */
  function handlePredict() {
    if (!station) return
    runPredict()
    runHistory()
  }

  // ── Render ───────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* ── Header ────────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dự đoán PM2.5</h1>
        <p className="text-sm text-gray-500 mt-1">
          Chọn trạm và ngày để xem dự báo PM2.5 ngày hôm sau cùng giải thích SHAP.
          <span className="ml-1 text-gray-400">
            (Oct–Dec 2025: test set · Ngày khác: dự đoán real-time qua OpenAQ)
          </span>
        </p>
      </div>

      {/* ── Row 0: Controls ───────────────────────────────────────────── */}
      <div className="card">
        <div className="flex flex-wrap gap-4 items-end">
          {/* Station dropdown */}
          <div className="flex-1 min-w-48">
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Trạm quan trắc
            </label>
            {stationsLoading ? (
              <div className="text-xs text-gray-400">Đang tải danh sách trạm…</div>
            ) : (
              <select
                value={station}
                onChange={(e) => setStation(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800
                           focus:outline-none focus:ring-2 focus:ring-blue-200 bg-white"
              >
                <option value="">— Chọn trạm quan trắc —</option>
                {/* Sort theo tên để dễ tìm */}
                {[...(stations ?? [])]
                  .sort((a, b) => a.name.localeCompare(b.name))
                  .map((s) => (
                    <option key={s.name} value={s.name}>
                      {/* Rút gọn tên để dropdown không quá dài */}
                      {s.name.replace(/,?\s*(Delhi\s*[-–]\s*\w+)$/i, '').trim()}
                    </option>
                  ))}
              </select>
            )}
          </div>

          {/* Date picker — giới hạn trong test set range */}
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Ngày
            </label>
            <input
              type="date"
              value={date}
              min={DATE_MIN}
              max={DATE_MAX}
              onChange={(e) => setDate(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-800
                         focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </div>

          {/* Predict button */}
          <button
            onClick={handlePredict}
            disabled={!station || predLoading}
            className="btn-primary disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {predLoading ? 'Đang dự đoán…' : 'Dự đoán PM2.5'}
          </button>
        </div>
      </div>

      {/* ── Error state ───────────────────────────────────────────────── */}
      {predError && (
        <div className="card border-red-100 bg-red-50 text-red-600 text-sm">
          {predError}
        </div>
      )}

      {/* ── Kết quả: chỉ hiện sau khi có prediction data ──────────────── */}
      {prediction && (
        <>
          {/* ── Row 1: Result + History ─────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Result card */}
            <div className="card space-y-4">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">
                  Dự báo PM2.5 ngày hôm sau
                </p>
                <p className="text-xs text-gray-500">
                  {/* Hiển thị ngày được dự đoán = date + 1 day */}
                  Trạm: <strong>{prediction.station.replace(/,?\s*(Delhi\s*[-–]\s*\w+)$/i, '').trim()}</strong>
                  {' · '}
                  Dự báo cho{' '}
                  <strong>
                    {new Date(
                      new Date(prediction.date + 'T00:00:00').getTime() + 86_400_000
                    ).toLocaleDateString('vi-VN', { day: 'numeric', month: 'long', year: 'numeric' })}
                  </strong>
                </p>
              </div>

              {/* Badge nguồn dữ liệu: test set (Q4-2025) hay real-time */}
              <div className="flex items-center gap-2">
                {prediction.source === 'live' ? (
                  <span className="inline-flex items-center gap-1 text-xs font-medium
                                   bg-blue-50 text-blue-600 border border-blue-200
                                   px-2 py-0.5 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                    Real-time (OpenAQ)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs font-medium
                                   bg-gray-50 text-gray-500 border border-gray-200
                                   px-2 py-0.5 rounded-full">
                    Test Set (Q4-2025)
                  </span>
                )}
              </div>

              {/* KPI chính: giá trị dự đoán */}
              <KPICard
                label="PM2.5 Dự đoán"
                value={`${prediction.predicted_pm25} µg/m³`}
                sub={
                  prediction.actual_pm25 != null
                    ? `Thực tế ngày hôm sau: ${prediction.actual_pm25} µg/m³ · ` +
                      `Khoảng tin cậy: ${prediction.confidence_low}–${prediction.confidence_high} µg/m³`
                    : `Khoảng tin cậy: ${prediction.confidence_low}–${prediction.confidence_high} µg/m³ · ` +
                      `(Chưa có ground truth)`
                }
              />

              {/* Alert banner theo mức AQI của dự đoán */}
              <AlertBanner pm25={prediction.predicted_pm25} />
            </div>

            {/* 30-day history chart: context PM2.5 của station này */}
            <div className="card">
              <h2 className="text-sm font-semibold text-gray-700 mb-0.5">
                Lịch sử 30 ngày
              </h2>
              <p className="text-xs text-gray-400 mb-3">
                PM2.5 quan sát tại trạm này (30 ngày gần nhất)
              </p>
              {histLoading ? (
                <Spinner text="Đang tải lịch sử…" />
              ) : history ? (
                // Reuse TrendChart với showPredicted=false — chỉ hiện line actual
                // Map history array → { date, actual } (không cần predicted key)
                <TrendChart
                  data={history.map((h) => ({ date: h.date, actual: h.pm25 }))}
                  showPredicted={false}
                />
              ) : null}
            </div>
          </div>

          {/* ── Row 2: SHAP Explanation ──────────────────────────────── */}
          <div className="card">
            <h2 className="text-sm font-semibold text-gray-700 mb-0.5">
              Tại sao có kết quả này?
            </h2>
            <p className="text-xs text-gray-400 mb-4">
              Giá trị SHAP của 10 đặc trưng ảnh hưởng nhất đến dự đoán.{' '}
              <span className="text-red-500 font-medium">Đỏ</span> = đẩy PM2.5 lên ·{' '}
              <span className="text-green-600 font-medium">Xanh</span> = kéo PM2.5 xuống.
              Đơn vị: µg/m³.
            </p>
            <ShapChart shapValues={prediction.shap_values} />
          </div>
        </>
      )}

      {/* ── Empty state: hướng dẫn khi chưa predict ──────────────────── */}
      {!prediction && !predLoading && !predError && (
        <div className="card text-center py-10 text-gray-400 text-sm">
          <p className="text-2xl mb-2">🌫️</p>
          <p>Chọn trạm và ngày rồi bấm <strong>Dự đoán PM2.5</strong></p>
          <p className="text-xs mt-1">
            Oct–Dec 2025: test set · Từ 2026 trở đi: dự đoán real-time qua OpenAQ
          </p>
        </div>
      )}
    </div>
  )
}
