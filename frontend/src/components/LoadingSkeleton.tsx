export default function LoadingSkeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="loading-skeleton" aria-live="polite" aria-busy="true">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="loading-skeleton__row" />
      ))}
    </div>
  );
}
