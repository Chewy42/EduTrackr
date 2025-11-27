import React, { useState } from "react";
import ExploreChat from "./ExploreChat";
import ChatHistorySidebar from "./ChatHistorySidebar";

export default function ExploreChatLayout() {
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);

  return (
    <div className="flex h-full w-full gap-4 p-4">
      <div className="flex-1 min-w-0 bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <ExploreChat sessionId={selectedSessionId} onSessionChange={setSelectedSessionId} />
      </div>
      <div className="hidden xl:flex w-80 flex-col bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <ChatHistorySidebar 
          currentSessionId={selectedSessionId} 
          onSelectSession={setSelectedSessionId} 
        />
      </div>
    </div>
  );
}
