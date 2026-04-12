"use client";

import { useState } from "react";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import PromptInput from "@/components/controls/PromptInput";
import OutputComparison from "@/components/outputs/OutputComparison";
import MetricsPanel from "@/components/metrics/MetricsPanel";
import { useInference } from "@/hooks/useInference";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const { data, execute, loading } = useInference();

  return (
    <div>
      <Header />

      <div className="flex h-screen">
        <Sidebar>
          <PromptInput value={prompt} onChange={setPrompt} />

          <button
            onClick={() => execute({ prompt })}
            className="w-full bg-blue-500 p-2 rounded"
          >
            Run
          </button>
        </Sidebar>

        <div className="flex-1 p-4 space-y-4">
          {loading && <div>Running...</div>}

          {data && (
            <>
              <OutputComparison
                raw={data.raw_output}
                final={data.final_output}
              />

              <MetricsPanel metrics={data.metrics} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
