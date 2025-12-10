/**
 * ConvergenceAnimation Component
 *
 * Brief celebration overlay when final answer is complete.
 * Shows a golden glow effect before transitioning to the full-screen view.
 */

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, Sparkles } from 'lucide-react';
import { useAgentStore, selectSelectedAgent, selectAgents, selectViewMode, selectRestoredFromSnapshot } from '../stores/agentStore';

export function ConvergenceAnimation() {
  const selectedAgent = useAgentStore(selectSelectedAgent);
  const agents = useAgentStore(selectAgents);
  const viewMode = useAgentStore(selectViewMode);
  const restoredFromSnapshot = useAgentStore(selectRestoredFromSnapshot);
  const [dismissed, setDismissed] = useState(false);

  // Show celebration when entering finalComplete mode, but not when restored from snapshot
  const showAnimation = viewMode === 'finalComplete' && selectedAgent && !dismissed && !restoredFromSnapshot;

  // Get winner's model name for display
  const winnerAgent = selectedAgent ? agents[selectedAgent] : null;
  const winnerDisplayName = winnerAgent?.modelName
    ? `${selectedAgent} (${winnerAgent.modelName})`
    : selectedAgent;

  // Auto-dismiss after 1.5 seconds (brief celebration)
  useEffect(() => {
    if (showAnimation) {
      const timer = setTimeout(() => {
        setDismissed(true);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [showAnimation]);

  // Reset dismissed state when going back to coordination
  useEffect(() => {
    if (viewMode === 'coordination') {
      setDismissed(false);
    }
  }, [viewMode]);

  return (
    <AnimatePresence>
      {showAnimation && (
        <>
          {/* Full-screen golden overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-50 pointer-events-none"
          >
            {/* Radial glow from center */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1.5, opacity: [0, 0.3, 0] }}
              transition={{ duration: 1.5, ease: 'easeOut' }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="w-96 h-96 rounded-full bg-yellow-400 blur-3xl" />
            </motion.div>

            {/* Center celebration card */}
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              transition={{ duration: 0.4, type: 'spring', stiffness: 300 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="bg-gray-900/95 border-2 border-yellow-500 rounded-2xl p-8 shadow-2xl shadow-yellow-500/30 final-answer-glow">
                <div className="flex flex-col items-center gap-4">
                  {/* Trophy with shake animation */}
                  <motion.div
                    animate={{ rotate: [0, 10, -10, 10, -10, 0] }}
                    transition={{ duration: 0.6, repeat: 1 }}
                  >
                    <Trophy className="w-16 h-16 text-yellow-500" />
                  </motion.div>

                  {/* Text */}
                  <div className="text-center">
                    <h2 className="text-2xl font-bold text-yellow-400 flex items-center justify-center gap-2">
                      <Sparkles className="w-6 h-6" />
                      Final Answer Ready!
                      <Sparkles className="w-6 h-6" />
                    </h2>
                    <p className="text-gray-400 mt-2">
                      Winner: <span className="text-yellow-300 font-semibold">{winnerDisplayName}</span>
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export default ConvergenceAnimation;
