import { AnimatePresence, motion } from "framer-motion";
import { ExternalLink, Newspaper } from "lucide-react";
import type { StoryRundown } from "../types/bulletin";

interface InsightPanelProps {
  story: StoryRundown | null;
}

export function InsightPanel({ story }: InsightPanelProps) {
  return (
    <aside className="flex flex-col justify-between rounded-2xl border border-slate-800/90 bg-slate-900/75 p-5 backdrop-blur-md">
      <div>
        <div className="mb-4 flex items-center justify-between border-b border-slate-800 pb-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-cyan-400">
              Verified Context
            </p>
            <h2 className="text-base font-bold text-white">Insight Panel</h2>
          </div>
          {story?.source.publisher && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              <Newspaper className="h-3.5 w-3.5" />
              {story.source.publisher}
            </span>
          )}
        </div>

        <AnimatePresence mode="wait">
          {story ? (
            <motion.div
              key={story.story_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
              className="space-y-3"
            >
              {story.insight_panel.slice(0, 3).map((fact, idx) => (
                <div
                  key={`${story.story_id}-fact-${idx}`}
                  dir="rtl"
                  className="rounded-xl border border-slate-800 bg-slate-950/80 px-4 py-3 text-right"
                >
                  <div className="font-urdu text-xs font-semibold text-cyan-300">
                    {fact.key}
                  </div>
                  <div className="font-urdu mt-1 text-sm font-medium text-slate-100">
                    {fact.value}
                  </div>
                </div>
              ))}
            </motion.div>
          ) : (
            <div className="py-8 text-center text-sm text-slate-400">
              No story insights available.
            </div>
          )}
        </AnimatePresence>
      </div>

      {story?.source.source_url && (
        <div className="mt-5 border-t border-slate-800 pt-4">
          <p className="mb-2 text-xs text-slate-400 line-clamp-2">
            Source: {story.source.title}
          </p>
          <a
            href={story.source.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-950 px-3.5 py-2.5 text-xs font-semibold text-cyan-300 transition hover:border-cyan-500/60 hover:bg-slate-900"
          >
            Read original article on {story.source.publisher}
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      )}
    </aside>
  );
}
