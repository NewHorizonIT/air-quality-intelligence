export default function Spinner({ text = 'Loading…' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-gray-400">
      <div className="w-8 h-8 border-4 border-gray-200 border-t-brand rounded-full animate-spin" />
      <p className="text-sm">{text}</p>
    </div>
  )
}
