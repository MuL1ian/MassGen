/**
 * NotificationToast Component
 *
 * Displays toast notifications in the bottom-right corner.
 * Used for new answer notifications, vote notifications, etc.
 * Notifications are clickable to open relevant browser (answers/votes).
 */

import { motion, AnimatePresence } from 'framer-motion';
import { X, MessageSquare, Vote, Info, AlertCircle } from 'lucide-react';
import { useNotificationStore, type Notification, type NotificationClickHandler } from '../stores/notificationStore';

const iconMap = {
  answer: MessageSquare,
  vote: Vote,
  info: Info,
  error: AlertCircle,
};

const colorMap = {
  answer: 'border-blue-500 bg-blue-500/10',
  vote: 'border-amber-500 bg-amber-500/10',
  info: 'border-gray-500 bg-gray-500/10',
  error: 'border-red-500 bg-red-500/10',
};

const iconColorMap = {
  answer: 'text-blue-400',
  vote: 'text-amber-400',
  info: 'text-gray-400',
  error: 'text-red-400',
};

interface NotificationCardProps {
  notification: Notification;
  onClick?: NotificationClickHandler;
}

function NotificationCard({ notification, onClick }: NotificationCardProps) {
  const removeNotification = useNotificationStore((s) => s.removeNotification);
  const Icon = iconMap[notification.type];

  const handleClick = () => {
    if (onClick) {
      onClick(notification);
      removeNotification(notification.id);
    }
  };

  const handleClose = (e: React.MouseEvent) => {
    e.stopPropagation();
    removeNotification(notification.id);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 100, scale: 0.9 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 100, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      onClick={handleClick}
      className={`
        relative flex items-start gap-3 p-4 rounded-lg border-l-4 shadow-lg
        bg-gray-800/95 backdrop-blur-sm min-w-[280px] max-w-[360px]
        ${colorMap[notification.type]}
        ${onClick ? 'cursor-pointer hover:bg-gray-700/95' : ''}
      `}
    >
      <Icon className={`w-5 h-5 mt-0.5 flex-shrink-0 ${iconColorMap[notification.type]}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-100 text-sm">{notification.title}</span>
          {notification.modelName && (
            <span className="text-xs text-gray-400">({notification.modelName})</span>
          )}
        </div>
        <p className="text-sm text-gray-300 mt-1 line-clamp-2">{notification.message}</p>
        {onClick && (
          <p className="text-xs text-gray-500 mt-1">Click to view details</p>
        )}
      </div>

      <button
        onClick={handleClose}
        className="p-1 hover:bg-gray-600 rounded transition-colors flex-shrink-0"
      >
        <X className="w-4 h-4 text-gray-400" />
      </button>
    </motion.div>
  );
}

interface NotificationToastProps {
  onNotificationClick?: NotificationClickHandler;
}

export function NotificationToast({ onNotificationClick }: NotificationToastProps) {
  const notifications = useNotificationStore((s) => s.notifications);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      <AnimatePresence mode="popLayout">
        {notifications.map((notification) => (
          <NotificationCard
            key={notification.id}
            notification={notification}
            onClick={onNotificationClick}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

export default NotificationToast;
