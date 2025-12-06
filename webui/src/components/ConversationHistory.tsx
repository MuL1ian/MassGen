/**
 * ConversationHistory - Compact conversation history display
 *
 * Shows previous turns in a dropdown/popover format:
 * - Compact header that shows turn count
 * - Click to expand full chat history in a floating panel
 * - Does NOT take up vertical space in main layout
 */

import { useState, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Bot, ExternalLink, ChevronDown, ChevronUp, MessageSquare, X } from 'lucide-react';
import { useAgentStore } from '../stores/agentStore';

interface ConversationHistoryProps {
  /** Callback when user clicks to view full response in browser */
  onViewResponse?: (turn: number) => void;
}

export function ConversationHistory({
  onViewResponse,
}: ConversationHistoryProps) {
  const conversationHistory = useAgentStore((s) => s.conversationHistory);
  const [isOpen, setIsOpen] = useState(false);
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());
  const panelRef = useRef<HTMLDivElement>(null);

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  // Parse conversation history into messages
  const messages = useMemo(() => {
    const result: Array<{
      role: 'user' | 'assistant';
      content: string;
      turn: number;
    }> = [];

    for (const msg of conversationHistory) {
      result.push({
        role: msg.role,
        content: msg.content,
        turn: msg.turn || 1,
      });
    }

    return result;
  }, [conversationHistory]);

  // Count unique turns (any turn that has at least one message)
  const uniqueTurns = useMemo(() => {
    const turns = new Set<number>();
    for (const msg of messages) {
      turns.add(msg.turn);
    }
    return turns;
  }, [messages]);

  // Get completed turn pairs for "View in browser" functionality
  const completedTurns = useMemo(() => {
    const turns = new Set<number>();
    for (let i = 0; i < messages.length - 1; i += 2) {
      if (messages[i]?.role === 'user' && messages[i + 1]?.role === 'assistant') {
        turns.add(messages[i].turn);
      }
    }
    return turns;
  }, [messages]);

  const turnCount = uniqueTurns.size;

  // Don't render if no history
  if (messages.length === 0) {
    return null;
  }

  // Check if message needs truncation
  const needsTruncation = (text: string) => {
    return text.split('\n').length > 5 || text.length > 500;
  };

  // Truncate for display
  const truncateForDisplay = (text: string) => {
    const lines = text.split('\n').slice(0, 5);
    const truncated = lines.join('\n');
    if (truncated.length > 500) {
      return truncated.slice(0, 500) + '...';
    }
    return text.split('\n').length > 5 ? truncated + '...' : truncated;
  };

  // Toggle individual message expansion
  const toggleMessageExpanded = (idx: number) => {
    setExpandedMessages(prev => {
      const next = new Set(prev);
      if (next.has(idx)) {
        next.delete(idx);
      } else {
        next.add(idx);
      }
      return next;
    });
  };

  return (
    <div className="relative" ref={panelRef}>
      {/* Compact toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-gray-200/80 dark:bg-gray-700/80
                   rounded-full hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors text-sm"
      >
        <MessageSquare className="w-3.5 h-3.5 text-blue-500" />
        <span className="text-gray-700 dark:text-gray-300">
          {turnCount} {turnCount === 1 ? 'turn' : 'turns'}
        </span>
        {isOpen ? (
          <ChevronUp className="w-3.5 h-3.5 text-gray-500" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-gray-500" />
        )}
      </button>

      {/* Floating panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-2 w-[650px] max-w-[90vw] bg-white dark:bg-gray-800
                       rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50 overflow-hidden"
          >
            {/* Panel header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/80">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Conversation History
              </span>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-colors"
              >
                <X className="w-4 h-4 text-gray-500" />
              </button>
            </div>

            {/* Messages */}
            <div className="max-h-[400px] overflow-y-auto p-4 space-y-3">
              {messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                const isAssistant = msg.role === 'assistant';
                const isTruncatable = isAssistant && needsTruncation(msg.content);
                const isExpanded = expandedMessages.has(idx);
                const displayText = (isTruncatable && !isExpanded)
                  ? truncateForDisplay(msg.content)
                  : msg.content;

                return (
                  <div
                    key={`${msg.turn}-${msg.role}-${idx}`}
                    className={`flex ${isUser ? 'justify-start' : 'justify-end'}`}
                  >
                    <div
                      className={`max-w-[90%] rounded-lg px-3 py-2 ${
                        isUser
                          ? 'bg-blue-50 dark:bg-blue-900/30 border-l-2 border-blue-400'
                          : 'bg-gray-100 dark:bg-gray-700/50 border-r-2 border-green-400'
                      }`}
                    >
                      {/* Header */}
                      <div className={`flex items-center gap-1.5 mb-1 ${isUser ? '' : 'justify-end'}`}>
                        {isUser ? (
                          <>
                            <User className="w-3 h-3 text-blue-500" />
                            <span className="text-xs font-medium text-blue-600 dark:text-blue-400">You</span>
                            <span className="text-xs text-gray-400">· Turn {msg.turn}</span>
                          </>
                        ) : (
                          <>
                            <span className="text-xs text-gray-400">Turn {msg.turn} ·</span>
                            <span className="text-xs font-medium text-green-600 dark:text-green-400">MassGen</span>
                            <Bot className="w-3 h-3 text-green-500" />
                          </>
                        )}
                      </div>

                      {/* Content */}
                      <p className={`text-sm whitespace-pre-wrap ${
                        isUser
                          ? 'text-gray-800 dark:text-gray-200'
                          : 'text-gray-700 dark:text-gray-300'
                      }`}>
                        {displayText}
                      </p>

                      {/* Actions for assistant messages */}
                      {isAssistant && (
                        <div className="flex items-center gap-2 mt-1.5">
                          {isTruncatable && (
                            <button
                              onClick={() => toggleMessageExpanded(idx)}
                              className="text-xs text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
                            >
                              {isExpanded ? '▲ Show less' : '▼ Show more'}
                            </button>
                          )}
                          {onViewResponse && completedTurns.has(msg.turn) && (
                            <button
                              onClick={() => onViewResponse(msg.turn)}
                              className="flex items-center gap-1 text-xs text-blue-500 hover:text-blue-400 transition-colors"
                            >
                              <ExternalLink className="w-3 h-3" />
                              Browser
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
