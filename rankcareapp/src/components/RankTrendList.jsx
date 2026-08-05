'use client'
function RankTrendList({ data }) {
  const max = Math.max(...data.map((item) => item.avg));

  return (
    <div className="space-y-4">
      {data.map((item, index) => {
        const width = `${(item.avg / max) * 100}%`;

        return (
          <div key={item.id || item.label || `rank-trend-${index}`}>
            <div className="mb-2 flex items-center justify-between text-sm">
              <span className="font-medium text-slate-600">{item.date}</span>
              <span className="font-semibold text-slate-900">#{item.avg}</span>
            </div>
            <div className="h-3 rounded-full bg-slate-100">
              <div
                className="h-3 rounded-full bg-brand-600 transition-all"
                style={{ width }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default RankTrendList;