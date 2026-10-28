import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

/** GET /api/stations — list all stations with summary stats */
export const fetchStations = () =>
  client.get('/stations').then((r) => r.data)

/** GET /api/history/:station?days=N — PM2.5 history for a station */
export const fetchHistory = (station, days = 30) =>
  client.get(`/history/${encodeURIComponent(station)}`, { params: { days } }).then((r) => r.data)

/** POST /api/predict — predict next-day PM2.5 */
export const fetchPrediction = (station, date) =>
  client.post('/predict', { station, date }).then((r) => r.data)

/** GET /api/daily — city-wide daily averages (actual + predicted) */
export const fetchDaily = () =>
  client.get('/daily').then((r) => r.data)
