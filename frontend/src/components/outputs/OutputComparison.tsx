import React, { useState, useEffect } from "react"
import { Sparkles, FileTerminal } from "lucide-react"
import { motion } from "framer-motion"

interface OutputComparisonProps {
  raw: string;
  final: string;
}

export default function OutputComparison({ raw, final }: OutputComparisonProps) {
  const [displayedText, setDisplayedText] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    if (!final) {
      setDisplayedText("");
      return;
    }
    
    setIsTyping(true);
    let i = 0;
    const intervalId = setInterval(() => {
      setDisplayedText(final.slice(0, i));
      i++;
      if (i > final.length) {
        clearInterval(intervalId);
        setIsTyping(false);
      }
    }, 15); // Adjust typing speed here

    return () => clearInterval(intervalId);
  }, [final]);

  const highlightDiff = (rawStr: string, currentDisplayed: string) => {
    if (!rawStr || !currentDisplayed) return currentDisplayed;
    const rawTokens = rawStr.split(" ");
    const displayedTokens = currentDisplayed.split(" ");
    
    return displayedTokens.map((t, idx) => {
      const cleanT = t.replace(/[.,!?]/g, "");
      const isNew = !rawStr.includes(cleanT);
      
      if (isNew) {
        return (
          <span key={idx} className="bg-emerald-500/20 text-emerald-300 rounded px-1.5 mx-[2px] border border-emerald-500/20 font-medium inline-block transition-all shadow-[0_0_10px_rgba(16,185,129,0.1)]">
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
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5 }}
        className="relative overflow-hidden p-5 border border-slate-800 rounded-xl bg-slate-900/40 shadow-inner group transition-all hover:border-slate-700"
      >
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
      </motion.div>

      {/* Final Output Section */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className="relative overflow-hidden p-5 border border-cyan-500/30 rounded-xl bg-slate-900/60 shadow-[0_0_30px_rgba(6,182,212,0.03)] group transition-all hover:border-cyan-500/50 hover:shadow-[0_0_30px_rgba(6,182,212,0.1)]"
      >
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
            {highlightDiff(raw, displayedText)}
            {isTyping && <span className="typewriter-cursor"></span>}
          </p>
        </div>
        
        {/* Floating particles effect when complete */}
        {!isTyping && displayedText.length > 0 && (
          <>
            <div className="particle" style={{ left: '10%', animation: 'float-particle 4s infinite 0.1s' }}></div>
            <div className="particle" style={{ left: '30%', animation: 'float-particle 5s infinite 0.8s' }}></div>
            <div className="particle" style={{ left: '60%', animation: 'float-particle 3.5s infinite 1.2s' }}></div>
            <div className="particle" style={{ left: '85%', animation: 'float-particle 4.5s infinite 0.4s' }}></div>
          </>
        )}
      </motion.div>
    </div>
  )
}
