/**
 * ConversationHistory - Shows previous turns in a chat-like format
 *
 * Displays user questions and final answers from previous turns,
 * allowing users to see the conversation context before the current turn.
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, User, Bot, MessageSquare } from 'lucide-react';
import { useAgentStore } from '../stores/agentStore';

interface ConversationHistoryProps {
  /** Callback when a turn is clicked for details */
  onTurnClick?: (turn: number) => void;
}

export function ConversationHistory({ onTurnClick }: ConversationHistoryProps) {
  const conversationHistory = useAgentStore((s) => s.conversationHistory);
  const currentTurn = useAgentStore((s) => s.turnNumber);
  const [isExpanded, setIsExpanded] = useState(true);

  // Group messages by turn (pairs of user + assistant messages)
  const turnPairs = useMemo(() => {
    const pairs: Array<{
      turn: number;
      userMessage: string;
      assistantMessage: string;
    }> = [];

    // Process messages in pairs - each turn should have user then assistant
    for (let i = 0; i < conversationHistory.length; i += 2) {
      const userMsg = conversationHistory[i];
      const assistantMsg = conversationHistory[i + 1];

      // Only show completed turns (have both user and assistant)
      if (userMsg?.role === 'user' && assistantMsg?.role === 'assistant') {
        pairs.push({
          turn: userMsg.turn || Math.floor(i / 2) + 1,
          userMessage: userMsg.content,
          assistantMessage: assistantMsg.content,
        });
      }
    }

    return pairs;
  }, [conversationHistory]);

  // Don't render if no completed turns
  if (turnPairs.length === 0) {
    return null;
  }

  // Truncate text for display
  const truncate = (text: string, maxLength: number = 150) => {
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength).trim() + '...';
  };

  return (
    <div className="mb-4">
      {/* Header - collapsible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors mb-2"
      >
        <MessageSquare className="w-4 h-4" />
        <span>Previous Turns ({turnPairs.length})</span>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-3">
              {turnPairs.map((pair) => (
                <motion.div
                  key={pair.turn}
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-gray-50 dark:bg-gray-800/50 rounded-lg p-3 border border-gray-200 dark:border-gray-700"
                >
                  {/* Turn header */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                      Turn {pair.turn}
                    </span>
                    {onTurnClick && (
                      <button
                        onClick={() => onTurnClick(pair.turn)}
                        className="text-xs text-blue-500 hover:text-blue-400 transition-colors"
                      >
                        View Details
                      </button>
                    )}
                  </div>

                  {/* Messages */}
                  <div className="flex gap-4">
                    {/* User message */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-1">
                        <User className="w-3.5 h-3.5 text-blue-500" />
                        <span className="text-xs font-medium text-blue-500">You</span>
                      </div>
                      <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">
                        {pair.userMessage}
                      </p>
                    </div>

                    {/* Separator */}
                    <div className="w-px bg-gray-200 dark:bg-gray-700" />

                    {/* Assistant message */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5 mb-1">
                        <Bot className="w-3.5 h-3.5 text-green-500" />
                        <span className="text-xs font-medium text-green-500">MassGen</span>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                        {truncate(pair.assistantMessage, 200)}
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Current turn indicator */}
            <div className="mt-3 flex items-center gap-2">
              <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 dark:via-gray-600 to-transparent" />
              <span className="text-xs text-gray-500 dark:text-gray-400 px-2">
                Turn {currentTurn} (Current)
              </span>
              <div className="flex-1 h-px bg-gradient-to-r from-transparent via-gray-300 dark:via-gray-600 to-transparent" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
