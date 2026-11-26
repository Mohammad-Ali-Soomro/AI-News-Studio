import type { StoryRundown } from "../types/bulletin";

interface LiveTickerProps {
  stories: StoryRundown[];
  activeStory: StoryRundown | null;
}

export function LiveTicker({ stories, activeStory }: LiveTickerProps) {
  const tickerItems =
    stories.length > 0
      ? [
          ...(activeStory ? [activeStory.ticker_text] : []),
          ...stories
            .filter((s) => s.story_id !== activeStory?.story_id)
            .map((s) => s.ticker_text),
        ]
      : ["اے آئی نیوز اسٹوڈیو: تازہ ترین خبریں لوڈ ہو رہی ہیں"];

  const duplicated = [...tickerItems, ...tickerItems];

  return (
    <div className="fixed inset-x-0 bottom-0 z-30 border-t border-cyan-500/30 bg-slate-950/95 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-stretch">
        <div className="relative flex-1 overflow-hidden py-2">
          <div dir="rtl" className="animate-ticker-rtl items-center">
            {duplicated.map((line, idx) => (
              <span
                key={`ticker-${idx}`}
                className="font-urdu mx-6 inline-flex items-center gap-4 whitespace-nowrap text-sm font-medium text-slate-100"
              >
                <span className="h-2 w-2 shrink-0 rounded-full bg-cyan-400" />
                {line}
              </span>
            ))}
          </div>
        </div>

        <div
          dir="rtl"
          className="flex shrink-0 items-center bg-rose-600 px-4 py-2 text-xs font-bold text-white sm:px-5"
        >
          <span className="font-urdu">اہم خبریں</span>
        </div>
      </div>
    </div>
  );
}
