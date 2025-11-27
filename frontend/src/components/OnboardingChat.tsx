import React, { useEffect, useRef, useState } from "react";
import { 
  FiSend, 
  FiCheckCircle, 
  FiCpu, 
  FiUploadCloud, 
  FiRefreshCw,
  FiAlertCircle,
  FiChevronDown
} from "react-icons/fi";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth } from "../auth/AuthContext";

type Message = {
  role: "user" | "assistant";
  content: string;
  timestamp?: Date;
};

type OnboardingMode =
  | "undecided"
  | "upcoming_semester"
  | "four_year_plan"
  | "view_progress";

type OnboardingStep = "welcome" | "analyzing" | "conversation" | "ready";

// Smart quick replies based on conversation context
const getContextualQuickReplies = (messages: Message[], mode: OnboardingMode): string[] => {
  const messageCount = messages.length;
  const lastMessage = messages[messageCount - 1]?.content?.toLowerCase() || "";
  
  // Initial state - offer main options
  if (messageCount <= 1 || mode === "undecided") {
    return [
      "Plan my next semester",
      "Show my degree progress", 
      "Map out my 4-year plan"
    ];
  }
  
  // If discussing semester planning
  if (mode === "upcoming_semester" || lastMessage.includes("semester") || lastMessage.includes("schedule")) {
    return [
      "I want 12-15 credits",
      "Show available electives",
      "I prefer morning classes"
    ];
  }
  
  // If discussing degree progress
  if (mode === "view_progress" || lastMessage.includes("progress") || lastMessage.includes("remaining")) {
    return [
      "What's left to graduate?",
      "Show GE requirements",
      "List my completed courses"
    ];
  }
  
  // If discussing 4-year plan
  if (mode === "four_year_plan" || lastMessage.includes("year") || lastMessage.includes("plan")) {
    return [
      "Balance my course load",
      "When should I take electives?",
      "Summer courses available?"
    ];
  }
  
  // Default fallback
  return [
    "Tell me more",
    "What do you recommend?",
    "Let's try something else"
  ];
};

export default function OnboardingChat() {
  const { jwt, mergePreferences, preferences } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<OnboardingMode>("undecided");
  const [step, setStep] = useState<OnboardingStep>("welcome");
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const initialized = useRef(false);
  const [streamingContent, setStreamingContent] = useState<string>("");

  const scrollToBottom = (smooth = true) => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: smooth ? "smooth" : "auto"
      });
    }
  };

  const handleScroll = () => {
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      setShowScrollButton(scrollHeight - scrollTop - clientHeight > 100);
    }
  };

  useEffect(() => {
    // Initial load - only run once per tab
    const initChat = async () => {
      if (!jwt || initialized.current) return;
      initialized.current = true;

      setStep("analyzing");
      setLoading(true);
      setError(null);
      
      try {
        const res = await fetch("/api/chat/onboarding", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${jwt}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ mode }),
        });
        if (res.ok) {
          const data = await res.json();
          setSessionId(data.session_id);
          // Always take messages from server response to avoid local duplicates
          setMessages((data.messages || []).map((m: Message) => ({ ...m, timestamp: new Date() })));
          if (data.suggestions) {
            setSuggestions(data.suggestions);
          }
          setStep("conversation");
        } else {
          const errData = await res.json().catch(() => ({}));
          setError(errData.error || "Failed to initialize chat. Please try again.");
          setStep("welcome");
        }
      } catch (err) {
        console.error("Chat init failed", err);
        setError("Connection failed. Please check your internet and try again.");
        setStep("welcome");
        initialized.current = false;
      } finally {
        setLoading(false);
      }
    };
    initChat();
  }, [jwt]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Scroll when streaming content updates
  useEffect(() => {
    if (streamingContent) {
      scrollToBottom(false); // Don't use smooth scroll for streaming
    }
  }, [streamingContent]);

  // Focus input after loading completes
  useEffect(() => {
    if (!loading && inputRef.current && step === "conversation") {
      inputRef.current.focus();
    }
  }, [loading, step]);

  const handleReset = async () => {
    if (!jwt || loading) return;
    if (!window.confirm("Start fresh? This will clear your current conversation.")) {
      return;
    }
    
    setLoading(true);
    setMessages([]);
    setSuggestions([]);
    setMode("undecided");
    setError(null);
    setStep("analyzing");
    
    try {
      const res = await fetch("/api/chat/onboarding", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${jwt}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ reset: true, mode: "undecided" }),
      });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.session_id);
        // Replace local history with server-provided messages to avoid duplicates
        setMessages((data.messages || []).map((m: Message) => ({ ...m, timestamp: new Date() })));
        if (data.suggestions) {
          setSuggestions(data.suggestions);
        }
        setStep("conversation");
      }
    } catch (err) {
      console.error("Chat reset failed", err);
      setError("Failed to reset chat. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleReupload = async () => {
    if (!jwt || loading) return;
    if (!window.confirm("This will delete your current transcript data and return you to the upload screen. Continue?")) {
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/program-evaluations", {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      });
      if (res.ok) {
        // Clear local chat state and force preferences to reflect no evaluation
        setMessages([]);
        setSuggestions([]);
        mergePreferences({ hasProgramEvaluation: false });
        window.location.reload();
      } else {
        console.error("Reupload delete failed", await res.text());
      }
    } catch (err) {
      console.error("Reupload delete failed", err);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (e?: React.FormEvent, msgOverride?: string) => {
    e?.preventDefault();
    const textToSend = msgOverride || input;
    
    if (!textToSend.trim() || !jwt || loading) return;

    const userMsg = textToSend.trim();
    const lower = userMsg.toLowerCase();
    setError(null);

    let nextMode: OnboardingMode = mode;
    if (mode === "undecided") {
      if (
        lower.includes("upcoming") ||
        lower.includes("next semester") ||
        lower.includes("next term")
      ) {
        nextMode = "upcoming_semester";
      } else if (
        lower.includes("4-year") ||
        lower.includes("four year") ||
        lower.includes("four-year") ||
        lower.includes("4 year")
      ) {
        nextMode = "four_year_plan";
      } else if (lower.includes("progress")) {
        nextMode = "view_progress";
      }
      if (nextMode !== mode) {
        setMode(nextMode);
      }
    }

    setInput("");
    setSuggestions([]);
    setMessages((prev) => [...prev, { role: "user", content: userMsg, timestamp: new Date() }]);
    setLoading(true);
    setStreamingContent("");

    try {
      const res = await fetch("/api/chat/onboarding/stream", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${jwt}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userMsg, mode: nextMode }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        setError(errData.error || "Failed to send message. Please try again.");
        setLoading(false);
        return;
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = "";

      if (!reader) {
        throw new Error("No response body");
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              // Finalize the message - filter out [SUGGESTIONS marker
              if (accumulatedContent) {
                const parts = accumulatedContent.split(/\[SUGGESTIONS/i);
                const cleanContent = (parts[0] || accumulatedContent).trim();
                setMessages((prev) => [
                  ...prev,
                  { role: "assistant", content: cleanContent, timestamp: new Date() }
                ]);
                setStreamingContent("");
              }
              continue;
            }

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === "chunk") {
                accumulatedContent += parsed.content;
                // Filter out [SUGGESTIONS text from display
                const parts = accumulatedContent.split(/\[SUGGESTIONS/i);
                const displayContent = (parts[0] || accumulatedContent).trim();
                setStreamingContent(displayContent);
              } else if (parsed.type === "suggestions") {
                setSuggestions(parsed.content || []);
              } else if (parsed.error) {
                setError(parsed.error);
              }
            } catch {
              // Ignore parse errors for incomplete chunks
            }
          }
        }
      }
    } catch (err) {
      console.error("Chat send failed", err);
      setError("Connection failed. Please check your internet and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleFinish = async () => {
    if (!jwt || loading) return;
    setStep("ready");
    try {
      await fetch("/api/auth/preferences", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${jwt}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ onboardingComplete: true }),
      });
      mergePreferences({ onboardingComplete: true });
    } catch (err) {
      console.error("Finish failed", err);
      setStep("conversation");
      setError("Failed to complete onboarding. Please try again.");
    }
  };

  // Progress indicator based on conversation length
  const conversationProgress = Math.min(100, Math.max(10, messages.length * 15));

  // Always show 3 quick reply buttons - use API suggestions or contextual defaults
  const contextualReplies = getContextualQuickReplies(messages, mode);
  const quickReplies = suggestions.length >= 3 
    ? suggestions.slice(0, 3) 
    : suggestions.length > 0 
      ? [...suggestions, ...contextualReplies.slice(0, 3 - suggestions.length)]
      : contextualReplies;

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-100 p-4 md:p-8">
      <div className="flex flex-col h-[92vh] md:h-[88vh] w-full max-w-4xl overflow-hidden rounded-2xl bg-white shadow-xl">
        
        {/* Header */}
        <div className="border-b border-slate-200 bg-white px-5 md:px-8 py-5">
          <div className="flex items-center justify-between gap-4">
            {/* Left: Logo & Title */}
            <div className="flex items-center gap-4 min-w-0">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white shadow-md">
                <FiCpu className="text-2xl" />
              </div>
              <div className="min-w-0">
                <h1 className="text-xl md:text-2xl font-bold text-slate-800">
                  Academic Advisor
                </h1>
                <p className="text-sm md:text-base text-slate-500 mt-0.5">
                  Let's plan your path to graduation
                </p>
              </div>
            </div>

            {/* Right: Action Buttons */}
            <div className="flex items-center gap-3 shrink-0">
              <div className="hidden md:flex items-center gap-2">
                <button
                  onClick={handleReset}
                  disabled={loading || step === "analyzing"}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <FiRefreshCw className={`text-lg ${loading ? "animate-spin" : ""}`} />
                  Start Over
                </button>
                <button
                  onClick={handleReupload}
                  disabled={loading}
                  className="inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium text-slate-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <FiUploadCloud className="text-lg" />
                  New Program Evaluation
                </button>
              </div>
              {!preferences.onboardingComplete && (
                <button
                  onClick={handleFinish}
                  disabled={loading || messages.length < 1}
                  className="inline-flex items-center gap-2 rounded-xl bg-green-600 px-5 py-3 text-base font-semibold text-white shadow-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <FiCheckCircle className="text-xl" />
                  <span className="hidden sm:inline">Go to Dashboard</span>
                  <span className="sm:hidden">Done</span>
                </button>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="mt-4 h-2 w-full bg-slate-200 rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-600 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${conversationProgress}%` }}
            />
          </div>
        </div>

        {/* Messages Area */}
        <div 
          ref={scrollRef} 
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto bg-slate-50 p-5 md:p-8 space-y-5 relative"
        >
          {/* Analyzing State */}
          {step === "analyzing" && (
            <div className="flex flex-col items-center justify-center h-full py-16">
              <div className="h-20 w-20 rounded-2xl bg-blue-600 flex items-center justify-center shadow-lg">
                <FiCpu className="text-4xl text-white animate-pulse" />
              </div>
              <h3 className="mt-8 text-2xl font-bold text-slate-800">Reading Your Transcript</h3>
              <p className="mt-3 text-lg text-slate-500 text-center max-w-md">
                We're analyzing your courses and progress to give you personalized recommendations...
              </p>
              <div className="mt-8 flex gap-3">
                <div className="h-3 w-3 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <div className="h-3 w-3 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <div className="h-3 w-3 bg-blue-600 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="flex items-center gap-4 p-5 bg-red-50 border border-red-200 rounded-xl text-base">
              <FiAlertCircle className="text-red-500 text-xl shrink-0" />
              <p className="text-red-700 font-medium">{error}</p>
              <button 
                onClick={() => setError(null)}
                className="ml-auto text-red-400 hover:text-red-600 text-2xl font-light transition-colors"
              >
                ×
              </button>
            </div>
          )}

          {/* Messages */}
          {step === "conversation" && messages.map((msg, i) => {
            const isAi = msg.role === "assistant";
            
            return (
              <div 
                key={i} 
                className={`flex ${isAi ? "justify-start" : "justify-end"}`}
              >
                {isAi && (
                  <div className="shrink-0 mr-4 mt-1">
                    <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
                      <FiCpu className="text-white text-lg" />
                    </div>
                  </div>
                )}
                <div
                  className={[
                    "max-w-[85%] md:max-w-[75%] rounded-2xl px-5 md:px-6 py-4 text-base md:text-lg leading-relaxed",
                    isAi
                      ? "bg-white text-slate-700 shadow-sm border border-slate-200"
                      : "bg-blue-600 text-white shadow-md",
                  ].join(" ")}
                >
                  {isAi ? (
                    <div className="prose prose-lg prose-slate max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        components={{
                          strong: ({ children }) => <strong className="text-blue-600 font-bold">{children}</strong>,
                          ul: ({ children }) => <ul className="my-3 space-y-2">{children}</ul>,
                          li: ({ children }) => <li className="flex items-start gap-3"><span className="text-blue-600 mt-1 text-xl">•</span><span>{children}</span></li>,
                          p: ({ children }) => <p className="my-2">{children}</p>,
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Streaming Message */}
          {streamingContent && step === "conversation" && (
            <div className="flex justify-start">
              <div className="shrink-0 mr-4 mt-1">
                <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
                  <FiCpu className="text-white text-lg" />
                </div>
              </div>
              <div className="max-w-[85%] md:max-w-[75%] rounded-2xl px-5 md:px-6 py-4 text-base md:text-lg leading-relaxed bg-white text-slate-700 shadow-sm border border-slate-200">
                <div className="prose prose-lg prose-slate max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      strong: ({ children }) => <strong className="text-blue-600 font-bold">{children}</strong>,
                      ul: ({ children }) => <ul className="my-3 space-y-2">{children}</ul>,
                      li: ({ children }) => <li className="flex items-start gap-3"><span className="text-blue-600 mt-1 text-xl">•</span><span>{children}</span></li>,
                      p: ({ children }) => <p className="my-2">{children}</p>,
                    }}
                  >
                    {streamingContent}
                  </ReactMarkdown>
                </div>
                <span className="inline-block w-2 h-5 bg-blue-600 animate-pulse ml-1" />
              </div>
            </div>
          )}

          {/* Typing Indicator - only show when loading but not streaming yet */}
          {loading && !streamingContent && messages.length > 0 && step === "conversation" && (
            <div className="flex justify-start">
              <div className="flex items-center gap-4">
                <div className="h-10 w-10 rounded-xl bg-blue-600 flex items-center justify-center shadow-md">
                  <FiCpu className="text-white text-lg animate-pulse" />
                </div>
                <div className="bg-white px-5 py-4 rounded-2xl shadow-sm border border-slate-200">
                  <div className="flex gap-2">
                    <div className="h-3 w-3 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <div className="h-3 w-3 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <div className="h-3 w-3 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Scroll to bottom button */}
          {showScrollButton && (
            <button
              onClick={() => scrollToBottom()}
              className="fixed bottom-44 right-8 h-12 w-12 bg-white rounded-full shadow-lg border border-slate-200 flex items-center justify-center text-slate-500 hover:text-blue-600 hover:border-blue-300 transition-all"
            >
              <FiChevronDown className="text-xl" />
            </button>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-slate-200 bg-white p-5 md:p-6 space-y-4">
          {/* Quick Reply Buttons - Always show 3 */}
          {!loading && step === "conversation" && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              {quickReplies.map((reply, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(undefined, reply)}
                  className="px-4 py-3.5 rounded-xl bg-slate-100 text-slate-700 text-sm md:text-base font-medium hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 transition-all border border-slate-200 text-left"
                >
                  {reply}
                </button>
              ))}
            </div>
          )}

          {/* Input Form */}
          <form onSubmit={(e) => handleSend(e)} className="relative">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={step === "analyzing" ? "Please wait..." : "Type your question or request..."}
              className="w-full rounded-xl border-2 border-slate-200 bg-white pl-5 pr-16 py-4 text-base md:text-lg placeholder:text-slate-400 focus:border-blue-500 focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={loading || step === "analyzing"}
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || step === "analyzing"}
              className="absolute right-2 top-1/2 -translate-y-1/2 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600 text-white shadow-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <FiSend className="text-lg" />
            </button>
          </form>

          {/* Mobile action buttons */}
          <div className="flex md:hidden items-center justify-center gap-6 pt-3 border-t border-slate-200">
            <button
              onClick={handleReset}
              disabled={loading || step === "analyzing"}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-500 hover:text-red-600 transition-colors disabled:opacity-50"
            >
              <FiRefreshCw className={`text-lg ${loading ? "animate-spin" : ""}`} />
              Start Over
            </button>
            <div className="h-5 w-px bg-slate-300" />
            <button
              onClick={handleReupload}
              disabled={loading}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-slate-500 hover:text-blue-600 transition-colors disabled:opacity-50"
            >
              <FiUploadCloud className="text-lg" />
              New Transcript
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
