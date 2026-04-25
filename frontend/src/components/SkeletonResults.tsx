"use client"

export default function SkeletonResults() {
  return (
    <div className="space-y-6 animate-fade-up">
      {/* Output comparison skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-5 border border-slate-800 rounded-xl bg-slate-900/40">
          <div className="skeleton-shimmer h-3 w-40 mb-4" />
          <div className="space-y-2">
            <div className="skeleton-shimmer h-4 w-full" />
            <div className="skeleton-shimmer h-4 w-4/5" />
            <div className="skeleton-shimmer h-4 w-3/5" />
          </div>
        </div>
        <div className="p-5 border border-cyan-500/20 rounded-xl bg-slate-900/60">
          <div className="skeleton-shimmer h-3 w-44 mb-4" />
          <div className="space-y-2">
            <div className="skeleton-shimmer h-4 w-full" />
            <div className="skeleton-shimmer h-4 w-5/6" />
            <div className="skeleton-shimmer h-4 w-2/3" />
          </div>
        </div>
      </div>

      {/* Metrics skeleton */}
      <div className="p-5 border rounded-xl bg-slate-900/40 border-slate-800">
        <div className="skeleton-shimmer h-3 w-36 mb-6" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="p-4 bg-slate-950/50 rounded-lg border border-slate-800/80">
              <div className="skeleton-shimmer h-2.5 w-20 mb-3" />
              <div className="skeleton-shimmer h-8 w-16 mb-2" />
              <div className="skeleton-shimmer h-2 w-24" />
            </div>
          ))}
        </div>
        <div className="mt-4 p-4 bg-emerald-950/20 border border-emerald-900/30 rounded-lg">
          <div className="skeleton-shimmer h-3 w-28 mb-2" />
          <div className="skeleton-shimmer h-4 w-full" />
        </div>
      </div>
    </div>
  )
}
