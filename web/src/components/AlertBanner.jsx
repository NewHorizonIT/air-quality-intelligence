import { AlertTriangle, CheckCircle } from 'lucide-react'
import { getLevel } from '../utils/levels'

const MESSAGES = {
  Good:           (pm25) => `Air quality is good. PM2.5 ${pm25.toFixed(0)} µg/m³ is within the WHO guideline.`,
  Moderate:       (pm25, x) => `Moderate air quality. PM2.5 ${pm25.toFixed(0)} µg/m³ is ${x}× the WHO guideline. Sensitive groups should limit prolonged outdoor activity.`,
  Unhealthy:      (pm25, x) => `Unhealthy air. PM2.5 ${pm25.toFixed(0)} µg/m³ is ${x}× the WHO guideline. Limit outdoor exertion; sensitive groups should stay indoors.`,
  'Very Unhealthy': (pm25, x) => `Very unhealthy — dangerous air expected. Forecast ${pm25.toFixed(0)} µg/m³ is ${x}× the WHO guideline. Avoid outdoor exertion; sensitive groups should stay indoors.`,
  Hazardous:      (pm25, x) => `Hazardous air quality. PM2.5 ${pm25.toFixed(0)} µg/m³ is ${x}× the WHO guideline. Everyone should stay indoors and wear N95 if going out.`,
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
