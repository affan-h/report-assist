import { useState, useMemo, type FC } from "react";
import { X, BarChart, Grid, Sparkles } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { API_URL, FigureMetadata } from "@/lib/chat-utils";

interface ArtifactViewerProps {
  type: "bar" | "heatmap";
  figureData?: FigureMetadata;
}

export const ArtifactViewer: FC<ArtifactViewerProps> = ({
  type,
  figureData,
}) => {
  const [isZoomed, setIsZoomed] = useState(false);

  const imageUrl = useMemo(() => {
    if (!figureData?.filename) return null;
    return `${API_URL}/api/v1/process/storage/${figureData.sessId}/${figureData.runId}/${figureData.filename}`;
  }, [figureData]);

  if (!figureData) {
    return (
      <div className="w-full h-48 flex items-center justify-center bg-neutral-100/70 border border-neutral-200 border-dashed rounded-lg my-2">
        <div className="flex items-center text-neutral-400 text-sm font-medium">
          {type === "bar" ? (
            <BarChart className="h-4 w-4 mr-2" />
          ) : (
            <Grid className="h-4 w-4 mr-2" />
          )}
          Generating visualization...
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Thumbnail */}
      <div className="p-2 border rounded-xl bg-white shadow-sm overflow-hidden mt-3 mb-3">
        <div
          className="relative group cursor-zoom-in overflow-hidden rounded-lg"
          onClick={() => setIsZoomed(true)}
        >
          <img
            src={imageUrl || ""}
            alt="Analysis Chart"
            className="w-full h-auto max-h-72 object-contain transition-transform duration-500 group-hover:scale-[1.02]"
            onError={(e) =>
              (e.currentTarget.src =
                "https://placehold.co/600x400?text=Error+Loading+Image")
            }
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors flex items-center justify-center">
            <span className="opacity-0 group-hover:opacity-100 bg-black/70 backdrop-blur-md text-white text-xs font-medium px-3 py-1.5 rounded-full shadow-sm transform translate-y-2 group-hover:translate-y-0 transition-all">
              Click to Expand
            </span>
          </div>
        </div>
      </div>

      {/* Modal Overlay */}
      {isZoomed && imageUrl && (
        <div
          className="fixed inset-0 z-[9999] bg-neutral-950/95 backdrop-blur-md animate-in fade-in duration-200 flex flex-col"
          onClick={() => setIsZoomed(false)}
        >
          {/* Close Button */}
          <button className="absolute top-4 right-4 p-2 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors z-50">
            <X className="h-6 w-6" />
          </button>

          {/* Image Container */}
          <div className="flex-1 flex items-center justify-center p-4 md:p-12 pb-[35vh]">
            <img
              src={imageUrl}
              alt="Full Analysis"
              className="max-w-full max-h-full object-contain shadow-2xl animate-in zoom-in-95 duration-300"
              onClick={(e) => e.stopPropagation()}
            />
          </div>

          {/* Insight HUD */}
          <div
            className="absolute bottom-0 inset-x-0 h-[30vh] md:h-[35vh] bg-neutral-900 border-t border-white/10 text-neutral-200 animate-in slide-in-from-bottom-10 duration-300 flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4 border-b border-white/10 bg-neutral-900 flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-400" />
              <h4 className="font-semibold text-white">AI Visual Analysis</h4>
            </div>
            <ScrollArea className="flex-1 p-6">
              <div className="max-w-4xl mx-auto prose prose-invert prose-sm">
                <p className="whitespace-pre-wrap leading-relaxed text-neutral-300 font-light tracking-wide text-base">
                  {figureData.explanation ||
                    "No specific explanation provided for this figure."}
                </p>
              </div>
            </ScrollArea>
          </div>
        </div>
      )}
    </>
  );
};
