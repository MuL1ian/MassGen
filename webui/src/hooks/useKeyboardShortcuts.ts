/**
 * useKeyboardShortcuts Hook
 *
 * Global keyboard shortcut handler for the webui.
 * Provides navigation and action shortcuts.
 */

import { useEffect, useCallback, useState } from 'react';
import { useAgentStore } from '../stores/agentStore';

export interface KeyboardShortcut {
  key: string;
  description: string;
  action: () => void;
  modifier?: 'ctrl' | 'alt' | 'shift' | 'meta';
  category: 'navigation' | 'agents' | 'modal' | 'general';
}

interface UseKeyboardShortcutsOptions {
  onOpenAnswerBrowser?: () => void;
  onOpenVoteBrowser?: () => void;
  onOpenWorkspaceBrowser?: () => void;
  onOpenTimeline?: () => void;
  onOpenShortcutsHelp?: () => void;
  onSelectAgent?: (agentId: string) => void;
  enabled?: boolean;
}

export function useKeyboardShortcuts(options: UseKeyboardShortcutsOptions = {}) {
  const {
    onOpenAnswerBrowser,
    onOpenVoteBrowser,
    onOpenWorkspaceBrowser,
    onOpenTimeline,
    onOpenShortcutsHelp,
    onSelectAgent,
    enabled = true,
  } = options;

  const agentOrder = useAgentStore((state) => state.agentOrder);

  // Track if a modal is currently open to prevent shortcuts
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Define all shortcuts
  const shortcuts: KeyboardShortcut[] = [
    // Navigation
    {
      key: 'a',
      description: 'Open Answer Browser',
      action: () => onOpenAnswerBrowser?.(),
      category: 'navigation',
    },
    {
      key: 'v',
      description: 'Open Vote Browser',
      action: () => onOpenVoteBrowser?.(),
      category: 'navigation',
    },
    {
      key: 'w',
      description: 'Open Workspace Browser',
      action: () => onOpenWorkspaceBrowser?.(),
      category: 'navigation',
    },
    {
      key: 't',
      description: 'Open Timeline',
      action: () => onOpenTimeline?.(),
      category: 'navigation',
    },
    // Agents (1-9 for quick navigation)
    ...agentOrder.slice(0, 9).map((agentId, index) => ({
      key: String(index + 1),
      description: `Navigate to Agent ${index + 1}`,
      action: () => {
        onSelectAgent?.(agentId);
      },
      category: 'agents' as const,
    })),
    // General
    {
      key: '?',
      description: 'Show keyboard shortcuts',
      action: () => onOpenShortcutsHelp?.(),
      category: 'general',
    },
    {
      key: 'Escape',
      description: 'Close modal / Deselect',
      action: () => {
        // Escape is handled at the modal level
      },
      category: 'modal',
    },
  ];

  // Keyboard event handler
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return;

      // Skip if focused on an input/textarea
      const target = event.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      // Skip if modal is open (except for Escape)
      if (isModalOpen && event.key !== 'Escape') {
        return;
      }

      // Find matching shortcut
      const shortcut = shortcuts.find((s) => {
        if (s.key.toLowerCase() !== event.key.toLowerCase()) return false;

        // Check modifiers
        if (s.modifier === 'ctrl' && !event.ctrlKey) return false;
        if (s.modifier === 'alt' && !event.altKey) return false;
        if (s.modifier === 'shift' && !event.shiftKey) return false;
        if (s.modifier === 'meta' && !event.metaKey) return false;

        // If no modifier required, ensure none are pressed (except shift for ?)
        if (!s.modifier && s.key !== '?') {
          if (event.ctrlKey || event.altKey || event.metaKey) return false;
        }

        return true;
      });

      if (shortcut) {
        event.preventDefault();
        shortcut.action();
      }
    },
    [enabled, isModalOpen, shortcuts]
  );

  // Register global listener
  useEffect(() => {
    if (enabled) {
      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
    }
  }, [enabled, handleKeyDown]);

  return {
    shortcuts,
    isModalOpen,
    setIsModalOpen,
  };
}

// Get shortcuts grouped by category
export function getShortcutsByCategory(shortcuts: KeyboardShortcut[]) {
  const grouped: Record<string, KeyboardShortcut[]> = {
    navigation: [],
    agents: [],
    modal: [],
    general: [],
  };

  shortcuts.forEach((shortcut) => {
    grouped[shortcut.category].push(shortcut);
  });

  return grouped;
}

export default useKeyboardShortcuts;
