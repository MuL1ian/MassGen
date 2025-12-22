/**
 * Context Paths Step Component
 *
 * Configure read/write paths for agents.
 * Uses backend API to open native file picker dialogs.
 */

import { motion } from 'framer-motion';
import { FolderOpen, File, Plus, Trash2, BookOpen, Edit3, Loader2 } from 'lucide-react';
import { useState } from 'react';
import { useWizardStore, selectContextPaths } from '../../stores/wizardStore';

export function ContextPathsStep() {
  const contextPaths = useWizardStore(selectContextPaths);
  const addContextPath = useWizardStore((s) => s.addContextPath);
  const removeContextPath = useWizardStore((s) => s.removeContextPath);
  const updateContextPath = useWizardStore((s) => s.updateContextPath);

  const [newPath, setNewPath] = useState('');
  const [newType, setNewType] = useState<'read' | 'write'>('read');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAddPath = () => {
    if (newPath.trim()) {
      addContextPath(newPath.trim(), newType);
      setNewPath('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleAddPath();
    }
  };

  const browseFiles = async (mode: 'files' | 'directory') => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/browse/files', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode,
          multiple: mode === 'files',
          title: mode === 'files' ? 'Select Files' : 'Select Directory',
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to open file picker');
      }

      const data = await response.json();
      const paths = data.paths || [];

      // Add each selected path
      for (const path of paths) {
        if (path) {
          addContextPath(path, newType);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to open file picker');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="space-y-6"
    >
      <div>
        <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
          Context Paths
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Add files or directories that agents can access. Read paths are for reference,
          write paths allow agents to create and modify files.
        </p>
      </div>

      {/* Browse Buttons */}
      <div className="flex gap-4">
        <button
          type="button"
          onClick={() => browseFiles('files')}
          disabled={isLoading}
          className="flex-1 flex items-center justify-center gap-2 p-4 border-2 border-dashed
                     border-gray-300 dark:border-gray-600 rounded-lg
                     hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {isLoading ? (
            <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
          ) : (
            <File className="w-6 h-6 text-gray-400" />
          )}
          <span className="text-sm text-gray-600 dark:text-gray-400">Browse Files</span>
        </button>

        <button
          type="button"
          onClick={() => browseFiles('directory')}
          disabled={isLoading}
          className="flex-1 flex items-center justify-center gap-2 p-4 border-2 border-dashed
                     border-gray-300 dark:border-gray-600 rounded-lg
                     hover:border-blue-400 dark:hover:border-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20
                     disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {isLoading ? (
            <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
          ) : (
            <FolderOpen className="w-6 h-6 text-gray-400" />
          )}
          <span className="text-sm text-gray-600 dark:text-gray-400">Browse Directory</span>
        </button>
      </div>

      {error && (
        <div className="text-sm text-red-500 dark:text-red-400 bg-red-50 dark:bg-red-900/20 p-2 rounded">
          {error}
        </div>
      )}

      {/* Manual Path Entry */}
      <div className="flex gap-2">
        <div className="flex-1">
          <input
            type="text"
            value={newPath}
            onChange={(e) => setNewPath(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter path (relative or absolute)"
            className="w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                       rounded-lg text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={newType}
          onChange={(e) => setNewType(e.target.value as 'read' | 'write')}
          className="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                     rounded-lg text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="read">Read</option>
          <option value="write">Write</option>
        </select>
        <button
          type="button"
          onClick={handleAddPath}
          disabled={!newPath.trim()}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <Plus className="w-5 h-5" />
        </button>
      </div>

      {/* Path List */}
      {contextPaths.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Added Paths ({contextPaths.length})
          </h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {contextPaths.map((cp, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex items-center gap-2 p-2 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                {/* Type Icon */}
                {cp.type === 'read' ? (
                  <BookOpen className="w-4 h-4 text-green-500 flex-shrink-0" />
                ) : (
                  <Edit3 className="w-4 h-4 text-amber-500 flex-shrink-0" />
                )}

                {/* Path */}
                <span className="flex-1 text-sm text-gray-700 dark:text-gray-300 font-mono truncate">
                  {cp.path}
                </span>

                {/* Type Toggle */}
                <button
                  type="button"
                  onClick={() => updateContextPath(index, cp.path, cp.type === 'read' ? 'write' : 'read')}
                  className={`
                    px-2 py-1 text-xs rounded transition-colors
                    ${cp.type === 'read'
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50'
                      : 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 hover:bg-amber-200 dark:hover:bg-amber-900/50'
                    }
                  `}
                >
                  {cp.type}
                </button>

                {/* Remove Button */}
                <button
                  type="button"
                  onClick={() => removeContextPath(index)}
                  className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      )}

      {contextPaths.length === 0 && (
        <div className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
          No paths added yet. This step is optional - you can proceed without adding any paths.
        </div>
      )}

      <div className="text-xs text-gray-500 dark:text-gray-500 mt-4">
        Tip: Use relative paths from where MassGen is launched, or absolute paths for any location.
      </div>
    </motion.div>
  );
}
