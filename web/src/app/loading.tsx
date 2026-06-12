export default function Loading() {
  return (
    <div className="animate-pulse" aria-label="Loading the directory" role="status">
      <div className="h-8 w-72 rounded-card bg-card-2" />
      <div className="mt-3 h-4 w-96 max-w-full rounded-card bg-card-2" />
      <div className="mt-8 space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-16 rounded-card border border-line bg-card-2" />
        ))}
      </div>
    </div>
  );
}
