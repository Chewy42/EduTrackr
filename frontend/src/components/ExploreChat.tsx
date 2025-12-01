import React, { useEffect, useRef, useState, useCallback } from "react";
import { 
  FiSend, 
  FiPlus,
  FiMessageSquare
} from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "../auth/AuthContext";

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
  const [historyLoading, setHistoryLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const activeSessionRef = useRef<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isSendingRef = useRef(false); // Track if we're actively sending to prevent history clear

  const scrollToBottom = useCallback((smooth = true) => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: smooth ? "smooth" : "auto"
      });
    }
  }, []);

  // Load session history when sessionId changes
  useEffect(() => {
    if (!jwt) return;

    // Skip fetching history if we're in the middle of sending a message
    // (this means we just created a new session and already have the user's message in state)
    // Use ref instead of state to avoid stale closure issues
    if (isSendingRef.current) return;

    // Cancel any in-flight requests when switching sessions
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    // Track the current session to avoid race conditions
    activeSessionRef.current = sessionId;

    if (sessionId) {
      // Switching to an existing session - clear immediately for snappy UI
      setMessages([]);
      setSuggestions([]);
      setStreamingContent("");
      setHistoryLoading(true);

      const controller = new AbortController();
      abortControllerRef.current = controller;

      fetch(`/api/chat/history/${sessionId}`, {
        headers: { Authorization: `Bearer ${jwt}` },
        signal: controller.signal
      })
        .then(res => res.json())
        .then(data => {
          // Only update if this is still the active session and not actively sending
          if (activeSessionRef.current === sessionId && data.messages && !isSendingRef.current) {
            setMessages(data.messages.map((m: any) => ({
              role: m.role,
              content: m.content,
              timestamp: new Date()
            })));
          }
        })
        .catch(err => {
          if (err.name !== 'AbortError') {
            console.error(err);
          }
        })
        .finally(() => {
          if (activeSessionRef.current === sessionId) {
            setHistoryLoading(false);
          }
        });
    } else {
      // New chat - reset to initial state
      setMessages([]);
      setSuggestions(["What can I do with my major?", "Am I on track to graduate?", "Show me my degree progress"]);
      setStreamingContent("");
      setHistoryLoading(false);
    }
  }, [sessionId, jwt]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, scrollToBottom]);

  const handleSend = async (e?: React.FormEvent, msgOverride?: string) => {
    e?.preventDefault();
    const textToSend = msgOverride || input;
    if (!textToSend.trim() || !jwt || loading) return;

    const userMsg = textToSend.trim();
    const currentSessionId = sessionId; // Capture current session ID

    // Mark that we're sending to prevent useEffect from clearing messages
    isSendingRef.current = true;

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
          session_id: currentSessionId 
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
                 // Clean content - remove all response markers
                 let cleanContent = (parts[0] || "")
                   .replace(/\[RESPONSE START\]/gi, "")
                   .replace(/\[RESPONSE END\]/gi, "")
                   .replace(/\[\/RESPONSE\]/gi, "")
                   .trim();
                 
                 setMessages(prev => [...prev, { role: "assistant", content: cleanContent, timestamp: new Date() }]);
                 setStreamingContent("");
                 
                 if (parts[1]) {
                   const suggs = parts[1].replace(/\[\/SUGGESTIONS\]/gi, "").trim().split("\n").filter(s => s.trim());
                   setSuggestions(suggs);
                 }
               }
               continue;
            }
            try {
              const parsed = JSON.parse(data);
              if (parsed.type === "chunk") {
                accumulatedContent += parsed.content;
                // Display logic - parse out markers for clean display
                const parts = accumulatedContent.split(/\[SUGGESTIONS\]/i);
                const displayContent = (parts[0] || "")
                  .replace(/\[RESPONSE START\]/gi, "")
                  .replace(/\[RESPONSE END\]/gi, "")
                  .replace(/\[\/RESPONSE\]/gi, "")
                  .trim();
                setStreamingContent(displayContent);
              } else if (parsed.type === "suggestions" && Array.isArray(parsed.content)) {
                // Backend sent suggestions as a separate event
                setSuggestions(parsed.content.slice(0, 3));
              } else if (parsed.type === "session_id" && parsed.content && !currentSessionId) {
                // Backend returned a new session ID - sync it up
                onSessionChange(parsed.content);
                activeSessionRef.current = parsed.content;
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
      isSendingRef.current = false;
    }
  };

  const handleNewChat = () => {
    // Cancel any in-flight requests
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    // Clear local state immediately for responsive UI
    setMessages([]);
    setStreamingContent("");
    setInput("");
    setLoading(false);
    setHistoryLoading(false);
    setSuggestions(["What can I do with my major?", "Am I on track to graduate?", "Show me my degree progress"]);
    activeSessionRef.current = null;
    // Then notify parent to clear session ID
    onSessionChange(null);
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-white/80 backdrop-blur-sm z-10">
        <div>
          <h1 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <span className="bg-brand-100 p-1.5 rounded-lg text-brand-600">
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
        {historyLoading && (
          <div className="flex items-center justify-center h-full">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}

        {!historyLoading && messages.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4 opacity-60 mt-10">
            <div className="bg-brand-50 p-4 rounded-full">
              <FiMessageSquare className="h-8 w-8 text-brand-400" />
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
                  ? "bg-gradient-to-r from-brand-600 to-brand-500 text-white rounded-br-none"
                  : "bg-white border border-slate-100 text-slate-700 rounded-bl-none"
              }`}
            >
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0.5"
                components={{
                  p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                  a: ({node, ...props}) => <a className="text-brand-500 hover:underline" {...props} />,
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
              <span className="inline-block w-1.5 h-3.5 ml-1 bg-brand-400 animate-pulse align-middle" />
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
                className="text-xs bg-brand-50 text-brand-700 px-3 py-1.5 rounded-full hover:bg-brand-100 transition-colors border border-brand-100"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        
        <form
          onSubmit={(e) => handleSend(e)}
          className="relative flex items-center gap-2 bg-slate-50 p-2 rounded-xl border border-slate-200 focus-within:border-brand-300 focus-within:ring-2 focus-within:ring-brand-100 transition-all"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your academic journey..."
	            className="flex-1 bg-transparent border-none outline-none focus:outline-none focus-visible:outline-none focus:ring-0 text-sm text-slate-800 placeholder:text-slate-400 px-2"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="p-2 bg-gradient-to-r from-brand-600 to-brand-500 text-white rounded-lg hover:from-brand-600 hover:to-brand-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            <FiSend className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
