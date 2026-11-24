/**
 * StationTable.jsx
 *
 * Bảng Top-10 stations ô nhiễm nhất, xếp theo avg_pm25 giảm dần.
 * Dữ liệu đã được sort từ API (/api/stations trả theo avg_pm25 desc).
 *
 * Props:
 *   stations — Array<{ name, latest_pm25, avg_pm25, level, date }>
 *              Nguồn: GET /api/stations (toàn bộ 53 stations, chỉ hiển thị 10)
 */

import LevelBadge from './LevelBadge'

export default function StationTable({ stations }) {
  if (!stations?.length) return null

  // Chỉ lấy 10 stations đầu (đã sorted desc bởi API)
  const top10 = stations.slice(0, 10)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-gray-400 uppercase tracking-wider border-b border-gray-100">
            <th className="pb-2 text-left font-medium w-6">#</th>
            <th className="pb-2 text-left font-medium">Trạm</th>
            <th className="pb-2 text-right font-medium">Mới nhất</th>
            <th className="pb-2 text-right font-medium">TB Q4</th>
            <th className="pb-2 text-left font-medium pl-3">Mức</th>
          </tr>
        </thead>
        <tbody>
          {top10.map((s, i) => (
            <tr
              key={s.name}
              className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
            >
              {/* Rank — đánh số từ 1 */}
              <td className="py-2 text-gray-400 text-xs">{i + 1}</td>

              {/* Tên station: rút gọn phần ", Delhi - DPCC" để bảng gọn hơn */}
              <td className="py-2 text-gray-800 font-medium leading-tight">
                <span title={s.name}>
                  {s.name.replace(/,?\s*(Delhi\s*[-–]\s*\w+)$/i, '').trim()}
                </span>
              </td>

              {/* PM2.5 mới nhất quan sát được */}
              <td className="py-2 text-right font-mono text-gray-700">
                {s.latest_pm25}
              </td>

              {/* PM2.5 trung bình toàn test period */}
              <td className="py-2 text-right font-mono text-gray-500">
                {s.avg_pm25}
              </td>

              {/* Level badge tái dùng component có sẵn */}
              <td className="py-2 pl-3">
                <LevelBadge level={s.level} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
