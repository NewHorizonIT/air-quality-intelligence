export const WHO_PM25 = 15.0

export const LEVELS = [
  { name: 'Good',           min: 0,   max: 30,       color: '#2d9e5f', bg: '#e8f5e9', textColor: 'white' },
  { name: 'Moderate',       min: 30,  max: 60,       color: '#8dc63f', bg: '#f9fbe7', textColor: 'white' },
  { name: 'Unhealthy',      min: 60,  max: 120,      color: '#f5a623', bg: '#fff3e0', textColor: 'white' },
  { name: 'Very Unhealthy', min: 120, max: 250,      color: '#d0021b', bg: '#fdecea', textColor: 'white' },
  { name: 'Hazardous',      min: 250, max: Infinity,  color: '#7b0000', bg: '#f5e5e5', textColor: 'white' },
]

export function getLevel(value) {
  return LEVELS.find((l) => value <= l.max) ?? LEVELS[LEVELS.length - 1]
}

export const LEVEL_MAP = Object.fromEntries(LEVELS.map((l) => [l.name, l]))
