/**
 * ShapChart.jsx
 *
 * Biểu đồ thanh ngang hiển thị top-10 SHAP values cho 1 dự đoán.
 *
 * SHAP (SHapley Additive exPlanations) giải thích tại sao model đưa ra
 * một dự đoán cụ thể:
 *   - Giá trị dương  (đỏ)  = feature đẩy PM2.5 lên cao
 *   - Giá trị âm     (xanh) = feature kéo PM2.5 xuống thấp
 *   - Độ lớn |shap| = mức độ ảnh hưởng (đơn vị µg/m³)
 *
 * Props:
 *   shapValues — Array<{ feature: string, value: number, feature_value: number }>
 *                Nguồn: POST /api/predict → response.shap_values
 *                Đã sorted by |value| desc, top-10
 */

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

/** Map tên feature kỹ thuật → nhãn thân thiện cho người đọc */
const FEAT_LABELS = {
  pm25_lag1:              'PM2.5 hôm qua',
  pm25_lag2:              'PM2.5 2 ngày trước',
  pm25_lag3:              'PM2.5 3 ngày trước',
  pm25_lag7:              'PM2.5 7 ngày trước',
  pm25_roll7_mean:        'TB 7 ngày',
  pm25_roll14_mean:       'TB 14 ngày',
  pm25_roll30_mean:       'TB 30 ngày',
  pm25_roll7_std:         'SD 7 ngày',
  pm25_roll14_std:        'SD 14 ngày',
  month_sin:              'Tháng (sin)',
  month_cos:              'Tháng (cos)',
  dow_sin:                'Thứ trong tuần (sin)',
  dow_cos:                'Thứ trong tuần (cos)',
  season_winter:          'Mùa đông',
  season_spring:          'Mùa xuân',
  season_monsoon:         'Mùa mưa',
  temperature:            'Nhiệt độ',
  wind_speed:             'Tốc độ gió',
  wind_direction:         'Hướng gió',
  precipitation:          'Lượng mưa',
  humidity:               'Độ ẩm',
  et0:                    'Bốc thoát hơi nước',
  dist_nearest_plant_km:  'Khoảng cách nhà máy',
  capacity_weighted_dist: 'Mật độ công nghiệp',
  n_plants_50km:          'Nhà máy trong 50 km',
}

/** Custom tooltip: hiển thị feature value + shap contribution */
function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-xs max-w-56">
      <p className="font-semibold text-gray-800 mb-1">
        {FEAT_LABELS[d.feature] ?? d.feature}
      </p>
      <p className="text-gray-500">
        Feature value: <strong className="text-gray-800">{d.feature_value}</strong>
      </p>
      <p style={{ color: d.value >= 0 ? '#d0021b' : '#2d9e5f' }}>
        SHAP: <strong>{d.value > 0 ? '+' : ''}{d.value.toFixed(2)} µg/m³</strong>
      </p>
    </div>
  )
}

export default function ShapChart({ shapValues }) {
  if (!shapValues?.length) return null

  // Đảo ngược thứ tự để feature quan trọng nhất hiển thị ở trên cùng
  // (Recharts BarChart ngang render từ dưới lên)
  const data = [...shapValues].reverse().map((d) => ({
    ...d,
    label: FEAT_LABELS[d.feature] ?? d.feature,
  }))

  return (
    <ResponsiveContainer width="100%" height={data.length * 36 + 20}>
      <BarChart
        data={data}
        layout="vertical"   // thanh ngang
        margin={{ top: 0, right: 60, left: 8, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />

        {/* Trục X = SHAP value (µg/m³), có thể âm hoặc dương */}
        <XAxis
          type="number"
          unit=" µg"
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
          domain={['auto', 'auto']}
        />

        {/* Trục Y = tên feature */}
        <YAxis
          type="category"
          dataKey="label"
          width={130}
          tick={{ fontSize: 11, fill: '#374151' }}
          axisLine={false}
          tickLine={false}
        />

        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f9fafb' }} />

        <Bar dataKey="value" radius={[0, 3, 3, 0]} maxBarSize={22}>
          {/* Tô màu từng bar: đỏ nếu dương (tăng PM2.5), xanh nếu âm (giảm PM2.5) */}
          {data.map((entry) => (
            <Cell
              key={entry.feature}
              fill={entry.value >= 0 ? '#d0021b' : '#2d9e5f'}
              fillOpacity={0.85}
            />
          ))}
          {/* Nhãn giá trị hiển thị bên phải mỗi thanh */}
          <LabelList
            dataKey="value"
            position="right"
            formatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(1)}`}
            style={{ fontSize: 10, fill: '#6b7280' }}
          />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
