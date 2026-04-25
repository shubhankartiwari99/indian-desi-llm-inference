import React, { useEffect, useState } from "react";
import { BarChart3, Zap, BrainCircuit, Lightbulb, Activity } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import AnimatedCounter from "@/components/ui/AnimatedCounter";
import type { InferenceMetrics, InferenceMetadata } from "@/types/inference";

interface MetricsPanelProps {
  metrics?: InferenceMetrics;
  interventionType?: string;
  metadata?: InferenceMetadata;
}

export default function MetricsPanel({ metrics, interventionType, metadata }: MetricsPanelProps) {
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    if (metrics) {
      setPulse(true);
      const timer = setTimeout(() => setPulse(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [metrics]);

  if (!metrics) return null;

  const collapseLabel = metrics.collapse_ratio < 0.3 ? "Heavy shaping" : 
                        metrics.collapse_ratio < 0.6 ? "Moderate shaping" : "Light shaping";
  
  const collapseColor = metrics.collapse_ratio < 0.3 ? "text-rose-400" :
                        metrics.collapse_ratio < 0.6 ? "text-amber-400" : "text-emerald-400";
                        
  const collapseBgColor = metrics.collapse_ratio < 0.3 ? "#fb7185" :
                          metrics.collapse_ratio < 0.6 ? "#fbbf24" : "#34d399";

  const klValue = metrics.kl_divergence || 0.0;
  const klInterpretation = klValue < 0.1 ? "Minimal Shift" :
                           klValue <= 0.5 ? "Moderate Transformation" : "Strong Behavioral Shift";

  let insightText = "";
  if (metrics.collapse_ratio < 0.3 && metrics.kl_divergence > 1.0) {
      insightText = "Severe entropy collapse and high KL metric indicates structural transformation of the distribution manifold.";
  } else if (metrics.collapse_ratio > 0.6 && metrics.kl_divergence < 0.5) {
      insightText = "Minimal shaping. The distribution preserves raw topology without significant semantic shift.";
  } else {
      insightText = "Moderate shaping. Target policies compressed entropy while managing distributional shift.";
  }

  const formatSource = (src: string) => {
      if (!src) return "Unknown";
      if (src === "mock_inference_pipeline") return "Mock Pipeline";
      if (src === "kaggle_qwen7b_pipeline") return "Kaggle (Qwen 7B)";
      if (src === "gguf_inference_pipeline_fallback") return "Local GGUF (Fallback)";
      if (src === "gguf_inference_pipeline") return "Local GGUF";
      return src;
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.3
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { 
      opacity: 1, 
      y: 0,
      transition: { type: "spring", stiffness: 300, damping: 24 }
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className={`space-y-4 p-5 rounded-xl bg-slate-900/40 border shadow-2xl relative overflow-hidden transition-colors duration-1000 ${
        pulse ? 'border-cyan-500/50 shadow-[0_0_30px_rgba(6,182,212,0.15)]' : 'border-slate-800'
      }`}
    >
      <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-transparent pointer-events-none" />
      
      <div className="flex items-center justify-between mb-2 relative z-10">
         <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-500 animate-pulse" />
            <h3 className="text-[10px] font-bold text-cyan-400 uppercase tracking-widest">System Trace Metrics</h3>
         </div>
         {metadata && (
            <motion.div 
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-4 text-[10px] font-mono text-slate-500 uppercase tracking-wider bg-slate-950/50 px-3 py-1.5 rounded-full border border-slate-800/50"
            >
               <span className="flex items-center gap-1.5">
                 <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                 {formatSource(metadata.source)}
               </span>
               <span className="w-px h-3 bg-slate-800" />
               <span className="text-cyan-400 font-bold">{metadata.latency_ms}ms</span>
            </motion.div>
         )}
      </div>
      
      <AnimatePresence>
        {interventionType && (
          <motion.div 
            initial={{ opacity: 0, height: 0, marginBottom: 0 }}
            animate={{ opacity: 1, height: "auto", marginBottom: 16 }}
            className="p-3 bg-cyan-950/30 border border-cyan-900/50 rounded-lg flex items-center relative z-10 overflow-hidden group"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            <Zap className="w-4 h-4 text-cyan-400 mr-2" />
            <span className="text-cyan-500 text-[10px] font-bold tracking-widest uppercase mr-3">Runtime Action</span> 
            <span className="font-mono text-cyan-100 text-xs px-2.5 py-1 bg-cyan-900/50 rounded-md border border-cyan-800/50 shadow-inner">
              {interventionType}
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="grid grid-cols-2 lg:grid-cols-4 gap-4 relative z-10"
      >
        <motion.div variants={itemVariants} className="metric-card p-4 bg-slate-950/80 rounded-lg border border-slate-800/80 flex flex-col justify-between group">
          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-3 flex items-center gap-1.5">
             <BrainCircuit className="w-3 h-3 group-hover:text-cyan-400 transition-colors" /> Collapse Ratio
          </div>
          <div className="flex items-center gap-4">
            <div className="radial-gauge shrink-0" style={{ '--gauge-value': Math.min(100, metrics.collapse_ratio * 100), '--gauge-color': collapseBgColor } as React.CSSProperties}>
              <span className={`radial-gauge-value ${collapseColor}`}>
                <AnimatedCounter value={metrics.collapse_ratio} decimals={2} />
              </span>
            </div>
            <div className="mt-1 text-[10px] font-medium text-slate-400 uppercase tracking-wider">{collapseLabel}</div>
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="metric-card p-4 bg-slate-950/80 rounded-lg border border-slate-800/80 flex flex-col justify-between">
          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2 flex items-center gap-1.5">
            KL Divergence
          </div>
          <div className="flex items-baseline space-x-2">
             <span className="text-3xl font-light tracking-tight text-purple-400">
                <AnimatedCounter value={klValue} decimals={2} duration={1500} />
             </span>
          </div>
          <div className="mt-1 text-[10px] font-medium text-purple-500/70 uppercase tracking-wider">{klInterpretation}</div>
        </motion.div>

        <motion.div variants={itemVariants} className="metric-card p-4 bg-slate-950/80 rounded-lg border border-slate-800/80 flex flex-col justify-between">
          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2 flex items-center gap-1.5">
            Raw Entropy
          </div>
          <div className="flex items-baseline space-x-2">
             <span className="text-3xl font-light tracking-tight text-slate-200">
                <AnimatedCounter value={metrics.entropy_raw} decimals={2} duration={1200} />
             </span>
          </div>
          <div className="mt-1 text-[10px] font-medium text-slate-500 uppercase tracking-wider">Pre-Intervention</div>
        </motion.div>

        <motion.div variants={itemVariants} className="metric-card p-4 bg-slate-950/80 rounded-lg border border-slate-800/80 flex flex-col justify-between relative overflow-hidden">
          <div className="absolute inset-0 bg-emerald-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mb-2 flex items-center gap-1.5">
            Final Entropy
          </div>
          <div className="flex items-baseline space-x-2">
             <span className="text-3xl font-light tracking-tight text-emerald-300">
                <AnimatedCounter value={metrics.entropy_final} decimals={2} duration={1800} />
             </span>
          </div>
          <div className="mt-1 text-[10px] font-medium text-emerald-500/60 uppercase tracking-wider">Post-Intervention</div>
        </motion.div>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6, duration: 0.5 }}
        className="mt-4 p-4 bg-emerald-950/20 border border-emerald-900/30 rounded-lg flex items-start gap-3 relative z-10"
      >
        <Lightbulb className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5 animate-pulse" />
        <div>
           <h4 className="text-[10px] text-emerald-500/80 font-bold uppercase tracking-widest mb-1.5">System Insight</h4>
           <p className="text-sm text-slate-300 leading-relaxed max-w-2xl">
             {insightText}
           </p>
        </div>
      </motion.div>
    </motion.div>
  );
}
