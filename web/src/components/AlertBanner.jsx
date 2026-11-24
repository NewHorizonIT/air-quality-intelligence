import { AlertTriangle, CheckCircle } from 'lucide-react'
import { getLevel } from '../utils/levels'

const MESSAGES = {
  Good:             (pm25) => `Chất lượng không khí tốt. PM2.5 ${pm25.toFixed(0)} µg/m³ nằm trong ngưỡng an toàn của WHO.`,
  Moderate:         (pm25, x) => `Chất lượng không khí trung bình. PM2.5 ${pm25.toFixed(0)} µg/m³ gấp ${x} lần ngưỡng WHO. Nhóm nhạy cảm nên hạn chế hoạt động ngoài trời kéo dài.`,
  Unhealthy:        (pm25, x) => `Không khí không tốt. PM2.5 ${pm25.toFixed(0)} µg/m³ gấp ${x} lần ngưỡng WHO. Hạn chế vận động ngoài trời; nhóm nhạy cảm nên ở trong nhà.`,
  'Very Unhealthy': (pm25, x) => `Không khí rất xấu — nguy hiểm. PM2.5 dự báo ${pm25.toFixed(0)} µg/m³ gấp ${x} lần ngưỡng WHO. Tránh hoạt động ngoài trời; nhóm nhạy cảm phải ở trong nhà.`,
  Hazardous:        (pm25, x) => `Không khí nguy hại. PM2.5 ${pm25.toFixed(0)} µg/m³ gấp ${x} lần ngưỡng WHO. Tất cả mọi người nên ở trong nhà, đeo khẩu trang N95 nếu ra ngoài.`,
}

export default function AlertBanner({ pm25, whoLimit = 15 }) {
  const level   = getLevel(pm25)
  const ratio   = (pm25 / whoLimit).toFixed(1)
  const message = MESSAGES[level.name]?.(pm25, ratio) ?? ''
  const Icon    = level.name === 'Good' ? CheckCircle : AlertTriangle

  return (
    <div
      className="flex items-start gap-3 px-4 py-3.5 rounded-lg border-l-4"
      style={{ backgroundColor: level.bg, borderColor: level.color }}
    >
      <Icon size={20} style={{ color: level.color }} className="flex-shrink-0 mt-0.5" />
      <p className="text-sm leading-relaxed" style={{ color: '#333' }}>
        <strong style={{ color: level.color }}>{level.name}</strong>
        {' — '}
        {message}
      </p>
    </div>
  )
}
