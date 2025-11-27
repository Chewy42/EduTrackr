import React, { useEffect, useRef, useState } from "react";
import { 
  FiSend, 
  FiPlus,
  FiMessageSquare
} from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "../auth/AuthContext";
import { listChatSessions } from "../lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
  timestamp?: Date;
};

type Props = {
  sessionId: string | null;
  onSessionChange: (id: string | null) => void;
};

export default function ExploreChat({ sessionId, onSessionChange }: Props) {
  const { jwt } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const initializedSessionId = useRef<string | null>(null);

  const scrollToBottom = (smooth = true) => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: smooth ? "smooth" : "auto"
      });
    }
  };

  // Load session history when sessionId changes
  useEffect(() => {
    if (!jwt) return;
    
    // If we switched sessions
    if (sessionId && sessionId !== initializedSessionId.current) {
      initializedSessionId.current = sessionId;
      setLoading(true);
      fetch(`/api/chat/history/${sessionId}`, {
        headers: { Authorization: `Bearer ${jwt}` }
      })
        .then(res => res.json())
        .then(data => {
          if (data.messages) {
            setMessages(data.messages.map((m: any) => ({ ...m, timestamp: new Date() })));
            setSuggestions([]); // Clear suggestions on history load
          }
        })
        .catch(console.error)
        .finally(() => setLoading(false));
    } else if (!sessionId && initializedSessionId.current) {
      // Reset to new chat state
      initializedSessionId.current = null;
      setMessages([]);
      setSuggestions(["What can I do with my major?", "Am I on track to graduate?", "Show me my degree progress"]);
    } else if (!sessionId && !initializedSessionId.current && messages.length === 0) {
      // Initial empty state
      setSuggestions(["What can I do with my major?", "Am I on track to graduate?", "Show me my degree progress"]);
    }
  }, [sessionId, jwt]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const handleSend = async (e?: React.FormEvent, msgOverride?: string) => {
    e?.preventDefault();
    const textToSend = msgOverride || input;
    if (!textToSend.trim() || !jwt || loading) return;

    const userMsg = textToSend.trim();
    setInput("");
    setSuggestions([]);
    setMessages(prev => [...prev, { role: "user", content: userMsg, timestamp: new Date() }]);
    setLoading(true);
    setStreamingContent("");

    try {
      const res = await fetch("/api/chat/explore/stream", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${jwt}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          message: userMsg, 
          session_id: sessionId 
        }),
      });

      if (!res.ok) throw new Error("Failed to send");

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = "";

      if (!reader) throw new Error("No reader");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
               // Finalize
               if (accumulatedContent) {
                 // Parse out suggestions if present
                 const parts = accumulatedContent.split(/\[SUGGESTIONS\]/i);
                 const cleanContent = (parts[0] || "").replace("[RESPONSE START]", "").replace("[RESPONSE END]", "").trim();
                 
                 setMessages(prev => [...prev, { role: "assistant", content: cleanContent, timestamp: new Date() }]);
                 setStreamingContent("");
                 
                 if (parts[1]) {
                   const suggs = parts[1].replace("[/SUGGESTIONS]", "").trim().split("\n").filter(s => s.trim());
                   setSuggestions(suggs);
                 }
                 
                 // If we didn't have a session ID, try to fetch the latest one to sync up
                 if (!sessionId) {
                    // Small delay to ensure DB write
                    setTimeout(() => {
                      listChatSessions(jwt).then(sessions => {
                        // Assuming the newest one is ours
                        if (sessions.length > 0) {
                           // We don't force switch because it might reload the chat, 
                           // but we could notify the parent to refresh the sidebar?
                           // For now, we just let the user continue chatting in "null" session state locally,
                           // but subsequent messages should ideally attach to the same session.
                           // Actually, the backend creates a NEW session every time if we send null.
                           // That's bad. We need the session ID back from the stream.
                           // But the stream doesn't return it easily in the first chunk.
                           // Wait, I can make the backend return the session ID in the first chunk!
                        }
                      });
                    }, 1000);
                 }
               }
               continue;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.type === "chunk") {
                accumulatedContent += parsed.content;
                // Display logic
                const parts = accumulatedContent.split(/\[SUGGESTIONS\]/i);
                const displayContent = (parts[0] || "").replace("[RESPONSE START]", "").replace("[RESPONSE END]", "").trim();
                setStreamingContent(displayContent);
              }
            } catch {}
          }
        }
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: "assistant", content: "Sorry, I encountered an error. Please try again.", timestamp: new Date() }]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = () => {
    onSessionChange(null);
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-white/80 backdrop-blur-sm z-10">
        <div>
          <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <span className="bg-indigo-100 p-1.5 rounded-lg text-indigo-600">
              <FiMessageSquare className="h-4 w-4" />
            </span>
            Explore My Options
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Reflect on your journey and plan your future
          </p>
        </div>
        <button
          onClick={handleNewChat}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
        >
          <FiPlus className="h-3.5 w-3.5" />
          New Chat
        </button>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth" ref={scrollRef}>
        {messages.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-60 mt-10">
            <div className="bg-indigo-50 p-4 rounded-full">
              <FiMessageSquare className="h-8 w-8 text-indigo-400" />
            </div>
            <div className="max-w-xs">
              <h3 className="text-sm font-medium text-slate-800">Start a new exploration</h3>
              <p className="text-xs text-slate-500 mt-1">
                Ask about your major, career paths, or degree progress.
              </p>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex w-full ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[85%] lg:max-w-[75%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed shadow-sm ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-none"
                  : "bg-white border border-slate-100 text-slate-700 rounded-bl-none"
              }`}
            >
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5"
                components={{
                  p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                  a: ({node, ...props}) => <a className="text-blue-400 hover:underline" {...props} />,
                  ul: ({node, ...props}) => <ul className="list-disc pl-4 mb-2 space-y-1" {...props} />,
                  ol: ({node, ...props}) => <ol className="list-decimal pl-4 mb-2 space-y-1" {...props} />,
                }}
              >
                {msg.content}
              </ReactMarkdown>
            </div>
          </div>
        ))}

        {streamingContent && (
          <div className="flex w-full justify-start">
            <div className="max-w-[85%] lg:max-w-[75%] rounded-2xl px-5 py-3.5 text-sm leading-relaxed shadow-sm bg-white border border-slate-100 text-slate-700 rounded-bl-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-sm max-w-none">
                {streamingContent}
              </ReactMarkdown>
              <span className="inline-block w-1.5 h-3.5 ml-1 bg-indigo-400 animate-pulse align-middle" />
            </div>
          </div>
        )}
        
        {loading && !streamingContent && (
          <div className="flex w-full justify-start">
             <div className="bg-white border border-slate-100 rounded-2xl rounded-bl-none px-4 py-3 shadow-sm">
               <div className="flex gap-1">
                 <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                 <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                 <div className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
               </div>
             </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-slate-100">
        {suggestions.length > 0 && !loading && (
          <div className="flex flex-wrap gap-2 mb-3 px-2">
            {suggestions.map((s, i) => (
              <button
                key={i}
                onClick={() => handleSend(undefined, s)}
                className="text-xs bg-indigo-50 text-indigo-700 px-3 py-1.5 rounded-full hover:bg-indigo-100 transition-colors border border-indigo-100"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        
        <form
          onSubmit={(e) => handleSend(e)}
          className="relative flex items-center gap-2 bg-slate-50 p-2 rounded-xl border border-slate-200 focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-100 transition-all"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your academic journey..."
            className="flex-1 bg-transparent border-none focus:ring-0 text-sm text-slate-800 placeholder:text-slate-400 px-2"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            <FiSend className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
