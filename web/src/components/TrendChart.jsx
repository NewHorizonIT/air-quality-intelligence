/**
 * TrendChart.jsx
 *
 * Biểu đồ đường hiển thị PM2.5 trung bình thành phố theo ngày:
 *   - Line "actual"    = PM2.5 quan sát thực tế (màu brand navy)
 *   - Line "predicted" = Dự đoán next-day của LightGBM (màu cam, nét đứt)
 *
 * Props:
 *   data           — Array<{ date: string, actual: number, predicted?: number }>
 *                    Nguồn: GET /api/daily  hoặc  GET /api/history (actual only)
 *   showPredicted  — boolean (default: true); set false khi dùng cho history-only chart
 */

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

/** Rút gọn nhãn ngày trên trục X: "2025-10-15" → "Oct 15" */
function fmtDate(iso) {
  const d = new Date(iso + 'T00:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

/** Custom tooltip hiển thị cả actual & predicted cùng ngày */
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs">
      <p className="font-semibold text-gray-700 mb-1">{fmtDate(label)}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }}>
          {p.name}: <strong>{p.value} µg/m³</strong>
        </p>
      ))}
    </div>
  )
}

export default function TrendChart({ data, showPredicted = true }) {
  if (!data?.length) return null

  return (
    // ResponsiveContainer lấy 100% chiều rộng container cha, cố định chiều cao 220px
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        {/* Grid ngang để dễ đọc giá trị */}
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />

        {/* Trục X: hiển thị mỗi 7 ngày để tránh chồng chữ */}
        <XAxis
          dataKey="date"
          tickFormatter={fmtDate}
          interval={6}
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
        />

        {/* Trục Y: PM2.5 µg/m³, bắt đầu từ 0 */}
        <YAxis
          unit=" µg"
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
          width={48}
        />

        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          formatter={(v) => (v === 'actual' ? 'PM2.5 thực tế' : 'PM2.5 dự đoán')}
        />

        {/* Line actual: màu brand navy, solid */}
        <Line
          type="monotone"
          dataKey="actual"
          name="actual"
          stroke="#1f3c88"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />

        {/* Line predicted: chỉ render khi showPredicted=true (tắt cho history-only chart) */}
        {showPredicted && (
          <Line
            type="monotone"
            dataKey="predicted"
            name="predicted"
            stroke="#f5a623"
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={false}
            activeDot={{ r: 4 }}
          />
        )}
      </LineChart>
    </ResponsiveContainer>
  )
}
