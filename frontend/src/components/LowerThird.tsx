import { AnimatePresence, motion } from "framer-motion";
import type { StoryRundown } from "../types/bulletin";

interface LowerThirdProps {
  story: StoryRundown | null;
}

export function LowerThird({ story }: LowerThirdProps) {
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800/90 bg-slate-900/90 shadow-lg">
      <div className="flex flex-col sm:flex-row">
        <div className="flex shrink-0 items-center justify-center bg-gradient-to-br from-cyan-500 to-emerald-500 px-5 py-3 text-slate-950 sm:w-44">
          <div className="text-center">
            <div className="text-[11px] font-bold uppercase tracking-widest">
              {story?.category ?? "News"}
            </div>
            <div className="text-xs font-semibold">
              {story?.anchor === "Anchor_A" ? "Anchor: Uzma" : story?.anchor ?? "Anchor"}
            </div>
          </div>
        </div>

        <div className="flex-1 px-5 py-3">
          <AnimatePresence mode="wait">
            <motion.div
              key={story?.story_id ?? "empty-lower-third"}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.25 }}
              dir="rtl"
              className="text-right"
            >
              <p className="font-urdu text-base font-bold text-white sm:text-lg">
                {story?.headline ?? "خبرنامہ لوڈ ہو رہا ہے"}
              </p>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
