export default function KPICard({ label, value, sub, subColor }) {
  return (
    <div className="card flex flex-col gap-1">
      <p className="text-xs text-gray-500 font-medium">{label}</p>
      <p className="text-3xl font-bold text-gray-900 leading-tight">{value}</p>
      {sub && (
        <p className="text-xs mt-0.5" style={{ color: subColor ?? '#6b7280' }}>
          {sub}
        </p>
      )}
    </div>
  )
}
