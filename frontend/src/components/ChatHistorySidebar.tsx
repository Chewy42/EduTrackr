import React, { useEffect, useState } from "react";
import { FiClock, FiMessageSquare, FiTrash2 } from "react-icons/fi";
import { useAuth } from "../auth/AuthContext";
import { listChatSessions, ChatSession, deleteChatSession, clearExploreChatSessions } from "../lib/api";

type Props = {
  onSelectSession?: (sessionId: string) => void;
  currentSessionId?: string | null;
};

export default function ChatHistorySidebar({ onSelectSession, currentSessionId }: Props) {
	  const { jwt } = useAuth();
	  const [sessions, setSessions] = useState<ChatSession[]>([]);
	  const [loading, setLoading] = useState(false);
	  const [deletingId, setDeletingId] = useState<string | null>(null);
	  const [clearing, setClearing] = useState(false);

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

	  const handleDeleteSession = async (sessionId: string) => {
	    if (!jwt) return;
	    setDeletingId(sessionId);
	    try {
	      await deleteChatSession(jwt, sessionId);
	      setSessions(prev => prev.filter(s => s.id !== sessionId));
	    } catch (err) {
	      console.error(err);
	      // Fallback to a full refresh if something went wrong
	      refreshSessions();
	    } finally {
	      setDeletingId(null);
	    }
	  };

	  const handleClearAll = async () => {
	    if (!jwt) return;
	    if (!window.confirm("Clear all Explore chat history? This cannot be undone.")) {
	      return;
	    }
	    setClearing(true);
	    try {
	      await clearExploreChatSessions(jwt, currentSessionId ?? undefined);
	      setSessions(prev =>
	        prev.filter(s => s.title === "Onboarding" || (currentSessionId && s.id === currentSessionId))
	      );
	    } catch (err) {
	      console.error(err);
	      refreshSessions();
	    } finally {
	      setClearing(false);
	    }
	  };

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
	        <div className="flex items-center gap-1">
	          <button 
	            onClick={refreshSessions}
	            className="text-slate-400 hover:text-slate-600 p-1"
	            title="Refresh history"
	          >
	            <FiClock className="h-3 w-3" />
	          </button>
	          {exploreSessions.length > 0 && (
	            <button
	              onClick={handleClearAll}
	              className="text-slate-400 hover:text-red-500 p-1 disabled:opacity-40"
	              disabled={clearing}
	              title="Clear all Explore chats"
	            >
	              <FiTrash2 className="h-3 w-3" />
	            </button>
	          )}
	        </div>
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
	                <div
	                  role="button"
	                  tabIndex={0}
	                  onClick={() => onSelectSession?.(session.id)}
	                  onKeyDown={(e) => {
	                    if (e.key === 'Enter' || e.key === ' ') {
	                      e.preventDefault();
	                      onSelectSession?.(session.id);
	                    }
	                  }}
	                  className={`w-full px-4 py-3 hover:bg-slate-50 transition-colors group cursor-pointer ${
	                    currentSessionId === session.id ? "bg-blue-50/50 border-l-2 border-blue-500" : "border-l-2 border-transparent"
	                  }`}
	                >
	                  <div className="flex items-start gap-2">
	                    <FiMessageSquare className={`h-3 w-3 mt-0.5 ${
	                      currentSessionId === session.id ? "text-blue-500" : "text-slate-300 group-hover:text-slate-400"
	                    }`} />
	                    <div className="flex-1 min-w-0 flex items-start justify-between gap-2">
	                      <div className="min-w-0">
	                        <div className={`text-xs font-medium truncate ${
	                          currentSessionId === session.id ? "text-blue-700" : "text-slate-700"
	                        }`}>
	                          {session.title}
	                        </div>
	                        <div className="text-[10px] text-slate-400 mt-0.5">
	                          {new Date(session.created_at).toLocaleDateString()} • {new Date(session.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
	                        </div>
	                      </div>
	                      <button
	                        type="button"
	                        onClick={(e) => {
	                          e.stopPropagation();
	                          handleDeleteSession(session.id);
	                        }}
	                        className="shrink-0 p-1 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors disabled:opacity-40"
	                        disabled={deletingId === session.id || clearing}
	                        aria-label="Delete session"
	                      >
	                        <FiTrash2 className="h-3 w-3" />
	                      </button>
	                    </div>
	                  </div>
	                </div>
	              </li>
	            ))}
	          </ul>
	        )}
      </div>
    </aside>
  );
}
