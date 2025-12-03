/**
 * Notification Store for MassGen Web UI
 *
 * Manages toast-style notifications for events like new answers.
 */

import { create } from 'zustand';

export type NotificationType = 'answer' | 'vote' | 'info' | 'error';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  agentId?: string;
  modelName?: string;
  answerId?: string;  // For linking to specific answer in browser
  timestamp: number;
}

// Callback for when a notification is clicked
export type NotificationClickHandler = (notification: Notification) => void;

interface NotificationStore {
  notifications: Notification[];
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearAll: () => void;
}

export const useNotificationStore = create<NotificationStore>((set) => ({
  notifications: [],

  addNotification: (notification) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
    const newNotification: Notification = {
      ...notification,
      id,
      timestamp: Date.now(),
    };

    set((state) => ({
      notifications: [...state.notifications, newNotification],
    }));

    // Auto-remove after 5 seconds
    setTimeout(() => {
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      }));
    }, 5000);
  },

  removeNotification: (id) => {
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    }));
  },

  clearAll: () => {
    set({ notifications: [] });
  },
}));
