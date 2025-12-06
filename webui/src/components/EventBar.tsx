/**
 * EventBar Component
 *
 * Horizontal bar showing vote and answer events as chips.
 * Shows only important events: votes cast and new answers.
 */

import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, FileText } from 'lucide-react';
import { useAgentStore } from '../stores/agentStore';

interface VoteEvent {
  type: 'vote';
  voterId: string;
  targetId: string;
  key: string;
}

interface AnswerEvent {
  type: 'answer';
  agentId: string;
  answerNumber: number;
  key: string;
}

type EventItem = VoteEvent | AnswerEvent;

export function EventBar() {
  // Get raw state with simple selectors
  const agents = useAgentStore((state) => state.agents);
  const answers = useAgentStore((state) => state.answers);

  // Compute events with useMemo to avoid infinite loops
  const events = useMemo(() => {
    const eventList: EventItem[] = [];

    // Get vote events from agents
    Object.values(agents).forEach((agent) => {
      if (agent.voteTarget) {
        eventList.push({
          type: 'vote',
          voterId: agent.id,
          targetId: agent.voteTarget,
          key: `vote-${agent.id}`,
        });
      }
    });

    // Get answer events from stored answers
    answers.forEach((answer) => {
      eventList.push({
        type: 'answer',
        agentId: answer.agentId,
        answerNumber: answer.answerNumber,
        key: `answer-${answer.id}`,
      });
    });

    // Return last 10 events
    return eventList.slice(-10);
  }, [agents, answers]);

  if (events.length === 0) {
    return (
      <div className="bg-gray-100/30 dark:bg-gray-800/30 border-t border-gray-200 dark:border-gray-700 px-4 py-2">
        <div className="flex items-center gap-2 text-gray-500 text-sm">
          <span>No events yet</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-100/30 dark:bg-gray-800/30 border-t border-gray-200 dark:border-gray-700 px-4 py-2">
      <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar">
        <AnimatePresence mode="popLayout">
          {events.map((event) => (
            <motion.div
              key={event.key}
              initial={{ opacity: 0, scale: 0.8, x: 20 }}
              animate={{ opacity: 1, scale: 1, x: 0 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ type: 'spring', stiffness: 500, damping: 30 }}
              className={`
                flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium
                whitespace-nowrap shrink-0
                ${event.type === 'vote'
                  ? 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 border border-amber-300 dark:border-amber-700/50'
                  : 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 border border-blue-300 dark:border-blue-700/50'
                }
              `}
            >
              {event.type === 'vote' ? (
                <>
                  <Check className="w-3 h-3" />
                  <span>{event.voterId}</span>
                  <span className="text-gray-500">voted for</span>
                  <span className="text-amber-600 dark:text-amber-200">{event.targetId}</span>
                </>
              ) : (
                <>
                  <FileText className="w-3 h-3" />
                  <span>{event.agentId}</span>
                  <span className="text-gray-500">Answer</span>
                  <span className="text-blue-600 dark:text-blue-200">#{event.answerNumber}</span>
                </>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default EventBar;
