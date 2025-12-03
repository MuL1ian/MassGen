/**
 * KeyboardShortcutsModal Component
 *
 * Displays available keyboard shortcuts in a modal dialog.
 * Triggered by pressing '?' key.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { X, Keyboard } from 'lucide-react';
import type { KeyboardShortcut } from '../hooks/useKeyboardShortcuts';
import { getShortcutsByCategory } from '../hooks/useKeyboardShortcuts';

interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
  shortcuts: KeyboardShortcut[];
}

const categoryLabels: Record<string, string> = {
  navigation: 'Navigation',
  agents: 'Agent Selection',
  modal: 'Modal Controls',
  general: 'General',
};

const categoryOrder = ['navigation', 'agents', 'general', 'modal'];

function KeyBadge({ keyName, modifier }: { keyName: string; modifier?: string }) {
  return (
    <div className="flex items-center gap-1">
      {modifier && (
        <>
          <kbd className="px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs font-mono text-gray-300 min-w-[28px] text-center">
            {modifier === 'ctrl' && 'Ctrl'}
            {modifier === 'alt' && 'Alt'}
            {modifier === 'shift' && 'Shift'}
            {modifier === 'meta' && '⌘'}
          </kbd>
          <span className="text-gray-500">+</span>
        </>
      )}
      <kbd className="px-2 py-1 bg-gray-700 border border-gray-600 rounded text-xs font-mono text-gray-300 min-w-[28px] text-center">
        {keyName === 'Escape' ? 'Esc' : keyName}
      </kbd>
    </div>
  );
}

export function KeyboardShortcutsModal({ isOpen, onClose, shortcuts }: KeyboardShortcutsModalProps) {
  const groupedShortcuts = getShortcutsByCategory(shortcuts);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-lg bg-gray-800 rounded-xl border border-gray-600 shadow-2xl z-50 overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900/50">
              <div className="flex items-center gap-3">
                <Keyboard className="w-5 h-5 text-blue-400" />
                <h2 className="text-lg font-semibold text-gray-100">Keyboard Shortcuts</h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {/* Shortcuts List */}
            <div className="p-6 max-h-[60vh] overflow-y-auto custom-scrollbar space-y-6">
              {categoryOrder.map((category) => {
                const categoryShortcuts = groupedShortcuts[category];
                if (!categoryShortcuts || categoryShortcuts.length === 0) return null;

                return (
                  <div key={category}>
                    <h3 className="text-sm font-medium text-gray-400 mb-3 uppercase tracking-wider">
                      {categoryLabels[category]}
                    </h3>
                    <div className="space-y-2">
                      {categoryShortcuts.map((shortcut) => (
                        <div
                          key={shortcut.key + shortcut.description}
                          className="flex items-center justify-between py-2 px-3 bg-gray-700/30 rounded-lg"
                        >
                          <span className="text-sm text-gray-300">{shortcut.description}</span>
                          <KeyBadge keyName={shortcut.key} modifier={shortcut.modifier} />
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Footer */}
            <div className="px-6 py-3 border-t border-gray-700 bg-gray-900/50 text-center text-xs text-gray-500">
              Press <kbd className="px-1.5 py-0.5 bg-gray-700 border border-gray-600 rounded text-gray-400">?</kbd> anytime to show this help
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

export default KeyboardShortcutsModal;
