"use client"

import { useState, useEffect } from "react"
import { useInference } from "@/hooks/useInference"
import { Activity, Play, Settings2, ShieldCheck, Cpu, Terminal, Network, Shield, Zap } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import OutputComparison from "@/components/outputs/OutputComparison"
import MetricsPanel from "@/components/metrics/MetricsPanel"
import SkeletonResults from "@/components/SkeletonResults"
import AnimatedCounter from "@/components/ui/AnimatedCounter"

// Simulated live telemetry for the hero dashboard
function LiveTelemetry() {
  const [uptime, setUptime] = useState(0);
  const [requests, setRequests] = useState(14028);
  const [memory, setMemory] = useState(42);

  useEffect(() => {
    const timer = setInterval(() => {
      setUptime(prev => prev + 1);
      setRequests(prev => prev + Math.floor(Math.random() * 3));
      setMemory(prev => {
        const next = prev + (Math.random() * 2 - 1);
        return Math.min(Math.max(next, 30), 80);
      });
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="grid grid-cols-3 gap-3 mb-8">
      <div className="bg-slate-900/40 border border-slate-800/50 rounded-lg p-3 flex flex-col justify-center">
        <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">System Uptime</span>
        <span className="font-mono text-sm text-cyan-400">{Math.floor(uptime / 60)}h {uptime % 60}m {uptime % 2 === 0 ? ':' : ' '}</span>
      </div>
      <div className="bg-slate-900/40 border border-slate-800/50 rounded-lg p-3 flex flex-col justify-center">
        <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">Evaluations</span>
        <span className="font-mono text-sm text-emerald-400">{(requests / 1000).toFixed(1)}k</span>
      </div>
      <div className="bg-slate-900/40 border border-slate-800/50 rounded-lg p-3 flex flex-col justify-center">
        <span className="text-[9px] uppercase tracking-widest text-slate-500 font-bold mb-1">VRAM Allocation</span>
        <span className="font-mono text-sm text-amber-400">{memory.toFixed(1)}%</span>
      </div>
    </div>
  );
}

export default function Home() {
  const [prompt, setPrompt] = useState("")
  const [useMock, setUseMock] = useState(true)
  const { data, execute, loading, error } = useInference()

  return (
    <main className="max-w-7xl mx-auto px-6 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
      
      {/* Sidebar Controls */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="lg:col-span-4 space-y-6"
      >
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-800 rounded-xl p-5 shadow-2xl relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
          
          <div className="flex items-center justify-between mb-4 relative z-10">
            <div className="flex items-center gap-2">
              <Settings2 className="w-4 h-4 text-slate-400" />
              <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">Inference Parameters</h2>
            </div>
          </div>
          
          <div className="space-y-4 relative z-10">
            <div className="flex items-center justify-between bg-slate-950 p-3 rounded-lg border border-slate-800/50 transition-colors hover:border-slate-700">
              <span className="text-[10px] uppercase font-bold tracking-widest text-slate-400">
                Mode: <span className={useMock ? "text-cyan-400" : "text-amber-400"}>{useMock ? 'Mock (Fast)' : 'Real (Kaggle/Local)'}</span>
              </span>
              <button
                onClick={() => setUseMock(!useMock)}
                className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${useMock ? 'bg-cyan-500' : 'bg-slate-700'}`}
              >
                <span className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${useMock ? 'translate-x-5' : 'translate-x-1'}`} />
              </button>
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold tracking-widest text-slate-500 mb-2 block">Instruction Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Enter a prompt to evaluate..."
                className="w-full h-32 bg-slate-950/80 border border-slate-800 rounded-lg p-3 text-sm text-slate-300 focus:outline-none focus:border-cyan-500/50 transition-colors resize-none font-serif shadow-inner"
              />
            </div>

            <button
              onClick={() => execute({ prompt, use_mock: useMock })}
              disabled={loading || !prompt.trim()}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-cyan-500 hover:bg-cyan-400 disabled:bg-slate-800 disabled:text-slate-500 text-slate-950 px-6 py-3.5 text-xs font-bold uppercase tracking-widest transition-all shadow-[0_0_20px_rgba(6,182,212,0.15)] hover:shadow-[0_0_30px_rgba(6,182,212,0.3)] disabled:shadow-none active:scale-[0.98]"
            >
              {loading ? <Cpu className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
              {loading ? "Evaluating Pipeline..." : "Execute Evaluation"}
            </button>
          </div>
        </div>
        
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="bg-slate-900/40 border border-emerald-900/30 rounded-xl p-5 relative overflow-hidden"
        >
           <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
             <Shield className="w-24 h-24" />
           </div>
           <div className="flex items-start gap-3 relative z-10">
             <ShieldCheck className="w-5 h-5 text-emerald-500 mt-0.5" />
             <div>
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-emerald-500/80 mb-1">System Boundary</h3>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  This evaluation interface explicitly isolates stochastic model generation from deterministic runtime interventions.
                </p>
             </div>
           </div>
        </motion.div>
      </motion.div>

      {/* Main Display */}
      <div className="lg:col-span-8 relative">
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-red-950/30 border border-red-900/50 text-red-400 text-sm flex items-start gap-3">
            <Activity className="w-5 h-5 shrink-0" />
            <div>
              <div className="font-bold uppercase tracking-widest text-[10px] mb-1">Pipeline Error</div>
              {error}
            </div>
          </div>
        )}

        <AnimatePresence mode="wait">
          {!data && !loading && (
             <motion.div 
               key="empty-state"
               initial={{ opacity: 0, scale: 0.95 }}
               animate={{ opacity: 1, scale: 1 }}
               exit={{ opacity: 0, scale: 0.95, filter: "blur(4px)" }}
               transition={{ duration: 0.4 }}
               className="h-full min-h-[500px] border border-slate-800/80 rounded-2xl bg-slate-900/40 p-10 flex flex-col relative overflow-hidden shadow-2xl"
             >
               {/* Decorative background grid */}
               <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-20 pointer-events-none" />
               
               <div className="relative z-10">
                 <div className="flex items-center gap-3 mb-8">
                   <div className="p-3 bg-cyan-950/50 rounded-xl border border-cyan-900/50">
                     <Network className="w-6 h-6 text-cyan-400" />
                   </div>
                   <div>
                     <h2 className="text-xl font-bold text-slate-200">System Ready</h2>
                     <p className="text-xs text-slate-500 tracking-widest uppercase mt-1">Awaiting Evaluation Payload</p>
                   </div>
                 </div>

                 <LiveTelemetry />

                 <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
                   <div className="p-5 rounded-xl border border-slate-800/60 bg-slate-950/50">
                     <Terminal className="w-5 h-5 text-slate-500 mb-3" />
                     <h3 className="text-sm font-bold text-slate-300 mb-2">How it works</h3>
                     <p className="text-xs text-slate-500 leading-relaxed">
                       Enter a prompt in the sidebar. The system will forward it to the designated model, 
                       intercept the raw stochastic output, and apply deterministic distribution shaping policies 
                       before rendering the final result.
                     </p>
                   </div>
                   <div className="p-5 rounded-xl border border-slate-800/60 bg-slate-950/50">
                     <Zap className="w-5 h-5 text-amber-500 mb-3" />
                     <h3 className="text-sm font-bold text-slate-300 mb-2">Telemetry</h3>
                     <p className="text-xs text-slate-500 leading-relaxed">
                       The dashboard captures Kl-Divergence, Entropy Collapse, and Latency metrics to quantify 
                       the exact topological shift caused by the runtime intervention.
                     </p>
                   </div>
                 </div>
               </div>
             </motion.div>
          )}

          {loading && (
            <motion.div 
              key="loading-state"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="absolute inset-0 z-20 bg-[#030712]"
            >
              <SkeletonResults />
            </motion.div>
          )}

          {data && !loading && (
            <motion.div 
              key="results-state"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="space-y-6"
            >
              <OutputComparison raw={data.raw_output} final={data.final_output} />
              <MetricsPanel metrics={data.metrics} interventionType={data.intervention_type} metadata={data.metadata} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  )
}
