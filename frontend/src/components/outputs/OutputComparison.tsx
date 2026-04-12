import React from "react"
import { Sparkles, FileTerminal } from "lucide-react"

export default function OutputComparison({ raw, final }: any) {
  const highlightDiff = (rawStr: string, finalStr: string) => {
    if (!rawStr || !finalStr) return finalStr;
    const rawTokens = rawStr.split(" ");
    const finalTokens = finalStr.split(" ");
    
    return finalTokens.map((t, idx) => {
      const cleanT = t.replace(/[.,!?]/g, "");
      const isNew = !rawStr.includes(cleanT);
      
      if (isNew) {
        return (
          <span key={idx} className="bg-emerald-500/20 text-emerald-300 rounded px-1.5 mx-[2px] border border-emerald-500/20 font-medium inline-block transition-all hover:bg-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]">
            {t}
          </span>
        );
      }
      return <span key={idx} className="text-slate-300">{t} </span>;
    });
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Raw Output Section */}
      <div className="relative overflow-hidden p-5 border border-slate-800 rounded-xl bg-slate-900/40 shadow-inner group transition-all hover:border-slate-700">
        <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none group-hover:opacity-10 transition-opacity">
           <FileTerminal className="w-32 h-32" />
        </div>
        <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4 flex items-center">
          <span className="w-1.5 h-1.5 rounded-full bg-slate-600 mr-2"></span>
          Pre-Rescue (Model Layer)
        </h3>
        <div className="relative z-10">
          <p className="text-slate-400 leading-relaxed font-serif text-[15px]">{raw}</p>
        </div>
      </div>

      {/* Final Output Section */}
      <div className="relative overflow-hidden p-5 border border-cyan-500/30 rounded-xl bg-slate-900/60 shadow-[0_0_30px_rgba(6,182,212,0.03)] group transition-all hover:border-cyan-500/50 hover:shadow-[0_0_30px_rgba(6,182,212,0.1)]">
        <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none group-hover:opacity-10 transition-opacity">
           <Sparkles className="w-32 h-32 text-cyan-400" />
        </div>
        <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest mb-4 flex items-center">
          <div className="relative mr-2 flex h-2 w-2 items-center justify-center">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-cyan-500"></span>
          </div>
          Post-Rescue (Pipeline Layer)
        </h3>
        <div className="relative z-10">
          <p className="leading-relaxed font-serif text-[15px] flex flex-wrap items-center">
            {highlightDiff(raw, final)}
          </p>
        </div>
      </div>
    </div>
  )
}
