import React, { useEffect, useState } from "react";
import { FiClock, FiMessageSquare } from "react-icons/fi";
import { useAuth } from "../auth/AuthContext";
import { listChatSessions, ChatSession } from "../lib/api";

type Props = {
  onSelectSession?: (sessionId: string) => void;
  currentSessionId?: string | null;
};

export default function ChatHistorySidebar({ onSelectSession, currentSessionId }: Props) {
  const { jwt } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(false);

  const refreshSessions = () => {
    if (!jwt) return;
    setLoading(true);
    listChatSessions(jwt)
      .then(setSessions)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    refreshSessions();
  }, [jwt]);

  // Filter out Onboarding sessions to keep Explore separate
  const exploreSessions = sessions.filter(s => s.title !== "Onboarding");

  return (
    <aside className="flex-1 flex flex-col h-full overflow-hidden bg-white">
      <div className="px-4 pt-4 pb-3 border-b border-slate-100 flex justify-between items-center">
        <div>
          <h2 className="text-sm font-semibold text-slate-800">
            Chat History
          </h2>
          <p className="text-[10px] text-slate-500">
            Your exploration sessions
          </p>
        </div>
        <button 
          onClick={refreshSessions}
          className="text-slate-400 hover:text-slate-600 p-1"
          title="Refresh history"
        >
          <FiClock className="h-3 w-3" />
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto">
        {loading && sessions.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-400">Loading...</div>
        ) : exploreSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-[11px] text-slate-400 px-4 gap-2">
            <FiMessageSquare className="h-4 w-4 opacity-20" />
            <span>No saved explore chats yet.</span>
          </div>
        ) : (
          <ul className="divide-y divide-slate-50">
            {exploreSessions.map((session) => (
              <li key={session.id}>
                <button
                  onClick={() => onSelectSession?.(session.id)}
                  className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors group ${
                    currentSessionId === session.id ? "bg-blue-50/50 border-l-2 border-blue-500" : "border-l-2 border-transparent"
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <FiMessageSquare className={`h-3 w-3 mt-0.5 ${
                      currentSessionId === session.id ? "text-blue-500" : "text-slate-300 group-hover:text-slate-400"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <div className={`text-xs font-medium truncate ${
                        currentSessionId === session.id ? "text-blue-700" : "text-slate-700"
                      }`}>
                        {session.title}
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">
                        {new Date(session.created_at).toLocaleDateString()} • {new Date(session.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                      </div>
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
