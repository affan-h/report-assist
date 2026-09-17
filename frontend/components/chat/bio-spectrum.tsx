import { cn } from "@/lib/utils";

export const getNeutralityColor = (score: number) => {
  if (score >= 0.8) return "bg-emerald-100 text-emerald-700 border-emerald-200"; // Excellent
  if (score >= 0.5) return "bg-amber-100 text-amber-700 border-amber-200"; // Moderate
  return "bg-rose-100 text-rose-700 border-rose-200"; // Biased
};

export const BiasSpectrum = ({
  score,
  icon,
}: {
  score: number;
  icon: string;
}) => {
  // Convert [-1, 1] range to [0, 100] percentage for CSS positioning
  const positionPct = ((Math.max(-1, Math.min(1, score)) + 1) / 2) * 100;

  return (
    <div className="w-full flex flex-col gap-1 mt-2">
      <div className="flex justify-between text-[10px] text-neutral-400 font-mono uppercase">
        <span>The Pessimistic (-1)</span>
        <span>Neutral (0)</span>
        <span>The Optimistic (+1)</span>
      </div>

      {/* The Track */}
      <div className="relative h-4 w-full rounded-full bg-gradient-to-r from-rose-200 via-neutral-200 to-emerald-200 border border-neutral-200 shadow-inner">
        {/* Center Marker (Neutral Zone) */}
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-neutral-400/50 -translate-x-1/2" />

        {/* The Agent Marker */}
        <div
          className="absolute top-1/2 -translate-y-1/2 transition-all duration-700 ease-out"
          style={{ left: `${positionPct}%` }}
        >
          <div className="relative -ml-3 w-6 h-6 flex items-center justify-center bg-white rounded-full shadow-sm border text-xs">
            {icon}
          </div>
          {/* Tooltip-like Score Label */}
          <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[9px] font-bold text-neutral-600 bg-white/80 px-1 rounded">
            {score.toFixed(2)}
          </div>
        </div>
      </div>
    </div>
  );
};
