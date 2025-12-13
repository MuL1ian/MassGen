/**
 * AgentCarousel Component
 *
 * Displays agents with responsive layout:
 * - 1-3 agents: Grid layout where cards expand to fill space
 * - 4+ agents: Carousel with navigation
 */

import { motion, AnimatePresence, useMotionValue, useTransform, PanInfo } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useState, useCallback } from 'react';
import { useAgentStore, selectAgents, selectAgentOrder, selectSelectedAgent, selectQuestion, selectPreparationStatus, selectPreparationDetail } from '../stores/agentStore';
import { AgentCard } from './AgentCard';

const MAX_VISIBLE = 3;
const CARD_WIDTH = 360;

export function AgentCarousel() {
  const agents = useAgentStore(selectAgents);
  const agentOrder = useAgentStore(selectAgentOrder);
  const selectedAgent = useAgentStore(selectSelectedAgent);
  const question = useAgentStore(selectQuestion);
  const preparationStatus = useAgentStore(selectPreparationStatus);
  const preparationDetail = useAgentStore(selectPreparationDetail);

  const [startIndex, setStartIndex] = useState(0);
  const x = useMotionValue(0);

  const totalAgents = agentOrder.length;
  const maxStartIndex = Math.max(0, totalAgents - MAX_VISIBLE);

  // Use grid mode for 1-3 agents, carousel mode for 4+
  const useGridMode = totalAgents <= MAX_VISIBLE;

  // Calculate visible agents
  const visibleAgentIds = useGridMode
    ? agentOrder
    : agentOrder.slice(startIndex, startIndex + MAX_VISIBLE);

  // Shadow visibility (only for carousel mode)
  const hasLeftShadow = !useGridMode && startIndex > 0;
  const hasRightShadow = !useGridMode && startIndex < maxStartIndex;

  // Navigation handlers
  const goLeft = useCallback(() => {
    setStartIndex((prev) => Math.max(0, prev - 1));
  }, []);

  const goRight = useCallback(() => {
    setStartIndex((prev) => Math.min(maxStartIndex, prev + 1));
  }, [maxStartIndex]);

  // Drag/swipe handler
  const handleDragEnd = useCallback(
    (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
      const threshold = CARD_WIDTH / 3;

      if (info.offset.x > threshold && startIndex > 0) {
        goLeft();
      } else if (info.offset.x < -threshold && startIndex < maxStartIndex) {
        goRight();
      }
    },
    [startIndex, maxStartIndex, goLeft, goRight]
  );

  // Transform for shadow opacity based on drag
  const leftShadowOpacity = useTransform(x, [-100, 0], [0, 0.8]);
  const rightShadowOpacity = useTransform(x, [0, 100], [0.8, 0]);

  if (totalAgents === 0) {
    // Show preparation status if available, otherwise show default messages
    const hasPrompt = question && question.trim().length > 0;
    const message = preparationStatus
      ? preparationStatus
      : hasPrompt
        ? 'Starting coordination...'
        : 'Waiting for prompt...';

    return (
      <div className="flex flex-col items-center justify-center h-[400px] gap-4">
        {/* Pulsing dots animation */}
        <div className="flex items-center gap-2">
          <motion.div
            className="w-3 h-3 bg-blue-500 rounded-full"
            animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 1.2, delay: 0 }}
          />
          <motion.div
            className="w-3 h-3 bg-purple-500 rounded-full"
            animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 1.2, delay: 0.2 }}
          />
          <motion.div
            className="w-3 h-3 bg-blue-500 rounded-full"
            animate={{ scale: [1, 1.3, 1], opacity: [0.5, 1, 0.5] }}
            transition={{ repeat: Infinity, duration: 1.2, delay: 0.4 }}
          />
        </div>
        <motion.span
          className="text-gray-500 dark:text-gray-400"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ repeat: Infinity, duration: 2 }}
        >
          {message}
        </motion.span>
        {/* Show detail if available */}
        {preparationDetail && (
          <motion.span
            className="text-gray-600 dark:text-gray-500 text-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.7 }}
          >
            {preparationDetail}
          </motion.span>
        )}
      </div>
    );
  }

  // Grid mode: 1-3 agents fill the space
  if (useGridMode) {
    const gridCols = totalAgents === 1 ? 'grid-cols-1' : totalAgents === 2 ? 'grid-cols-2' : 'grid-cols-3';

    return (
      <div className={`grid ${gridCols} gap-4 py-4`}>
        <AnimatePresence mode="popLayout" initial={false}>
          {visibleAgentIds.map((agentId) => {
            const agent = agents[agentId];
            if (!agent) return null;

            return (
              <motion.div
                key={agentId}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{
                  type: 'spring',
                  stiffness: 300,
                  damping: 30,
                }}
                className="h-[450px] min-w-0"
              >
                <AgentCard
                  agent={agent}
                  isWinner={selectedAgent === agentId}
                  isVisible={true}
                />
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    );
  }

  // Carousel mode: 4+ agents with navigation
  return (
    <div className="relative">
      {/* Left Navigation Button */}
      <button
        onClick={goLeft}
        disabled={!hasLeftShadow}
        className={`
          absolute left-0 top-1/2 -translate-y-1/2 z-10
          p-2 rounded-full bg-gray-800/80 border border-gray-600
          transition-opacity duration-200
          ${hasLeftShadow ? 'opacity-100 hover:bg-gray-700' : 'opacity-30 cursor-not-allowed'}
        `}
        aria-label="Show previous agent"
      >
        <ChevronLeft className="w-6 h-6 text-gray-300" />
      </button>

      {/* Right Navigation Button */}
      <button
        onClick={goRight}
        disabled={!hasRightShadow}
        className={`
          absolute right-0 top-1/2 -translate-y-1/2 z-10
          p-2 rounded-full bg-gray-800/80 border border-gray-600
          transition-opacity duration-200
          ${hasRightShadow ? 'opacity-100 hover:bg-gray-700' : 'opacity-30 cursor-not-allowed'}
        `}
        aria-label="Show next agent"
      >
        <ChevronRight className="w-6 h-6 text-gray-300" />
      </button>

      {/* Left Shadow Indicator */}
      <motion.div
        className="absolute left-12 top-0 bottom-0 w-16 shadow-indicator-left z-5 pointer-events-none"
        style={{ opacity: hasLeftShadow ? leftShadowOpacity : 0 }}
        animate={{
          opacity: hasLeftShadow ? 0.8 : 0,
        }}
      >
        {hasLeftShadow && (
          <motion.div
            className="absolute left-2 top-1/2 -translate-y-1/2"
            animate={{ x: [-5, 0, -5] }}
            transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
          >
            <div className="w-2 h-20 bg-gradient-to-r from-blue-500/50 to-transparent rounded-full" />
          </motion.div>
        )}
      </motion.div>

      {/* Right Shadow Indicator */}
      <motion.div
        className="absolute right-12 top-0 bottom-0 w-16 shadow-indicator-right z-5 pointer-events-none"
        style={{ opacity: hasRightShadow ? rightShadowOpacity : 0 }}
        animate={{
          opacity: hasRightShadow ? 0.8 : 0,
        }}
      >
        {hasRightShadow && (
          <motion.div
            className="absolute right-2 top-1/2 -translate-y-1/2"
            animate={{ x: [5, 0, 5] }}
            transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
          >
            <div className="w-2 h-20 bg-gradient-to-l from-blue-500/50 to-transparent rounded-full" />
          </motion.div>
        )}
      </motion.div>

      {/* Carousel Container */}
      <motion.div
        className="flex gap-4 px-14 py-4 overflow-hidden cursor-grab active:cursor-grabbing"
        drag="x"
        dragConstraints={{ left: 0, right: 0 }}
        dragElastic={0.2}
        onDragEnd={handleDragEnd}
        style={{ x }}
      >
        <AnimatePresence mode="popLayout" initial={false}>
          {visibleAgentIds.map((agentId) => {
            const agent = agents[agentId];
            if (!agent) return null;

            return (
              <motion.div
                key={agentId}
                layout
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{
                  type: 'spring',
                  stiffness: 300,
                  damping: 30,
                }}
                style={{ width: CARD_WIDTH, minWidth: CARD_WIDTH }}
                className="h-[450px]"
              >
                <AgentCard
                  agent={agent}
                  isWinner={selectedAgent === agentId}
                  isVisible={true}
                />
              </motion.div>
            );
          })}
        </AnimatePresence>
      </motion.div>

      {/* Pagination Dots */}
      {totalAgents > MAX_VISIBLE && (
        <div className="flex justify-center gap-2 mt-2">
          {Array.from({ length: totalAgents }).map((_, idx) => (
            <button
              key={idx}
              onClick={() => setStartIndex(Math.min(idx, maxStartIndex))}
              className={`
                w-2 h-2 rounded-full transition-all duration-200
                ${
                  idx >= startIndex && idx < startIndex + MAX_VISIBLE
                    ? 'bg-blue-500 scale-125'
                    : 'bg-gray-600 hover:bg-gray-500'
                }
              `}
              aria-label={`Go to agent ${idx + 1}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default AgentCarousel;
