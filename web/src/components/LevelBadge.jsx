import { LEVEL_MAP } from '../utils/levels'

export default function LevelBadge({ level, size = 'sm' }) {
  const info = LEVEL_MAP[level]
  if (!info) return null

  const padding = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm'

  return (
    <span
      className={`inline-flex items-center rounded-full font-semibold ${padding}`}
      style={{ backgroundColor: info.color, color: 'white' }}
    >
      {level}
    </span>
  )
}
