export default function Loading() {
  return (
    <div className="animate-pulse" aria-label="Loading agency data" role="status">
      <div className="h-8 w-64 rounded-card bg-card-2" />
      <div className="mt-3 h-4 w-44 rounded-card bg-card-2" />
      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-28 rounded-card border border-line bg-card-2" />
        ))}
      </div>
      <div className="mt-8 h-64 rounded-card border border-line bg-card-2" />
    </div>
  );
}
