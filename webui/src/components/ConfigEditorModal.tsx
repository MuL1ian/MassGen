/**
 * Config Editor Modal
 *
 * Full-featured modal for viewing, editing, renaming, and managing config files.
 * Supports YAML syntax highlighting and validation.
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X,
  Save,
  FileCode,
  Loader2,
  AlertCircle,
  Check,
  Pencil,
  Trash2,
  Plus,
  FolderOpen,
  RefreshCw,
} from 'lucide-react';

interface UserConfig {
  name: string;
  path: string;
  modified: number;
  size: number;
}

interface ConfigEditorModalProps {
  isOpen: boolean;
  onClose: () => void;
  configPath: string | null;
  onConfigChange: (configPath: string) => void;
  onConfigSaved?: (configPath: string) => void;
}

export function ConfigEditorModal({
  isOpen,
  onClose,
  configPath,
  onConfigChange,
  onConfigSaved,
}: ConfigEditorModalProps) {
  // State for config content
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // State for user configs list
  const [userConfigs, setUserConfigs] = useState<UserConfig[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState(false);
  const [configDir, setConfigDir] = useState<string>('');

  // State for rename dialog
  const [isRenaming, setIsRenaming] = useState(false);
  const [newName, setNewName] = useState('');
  const [renameError, setRenameError] = useState<string | null>(null);

  // State for new config dialog
  const [isCreating, setIsCreating] = useState(false);
  const [newConfigName, setNewConfigName] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);

  // State for delete confirmation
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Track current editing config
  const [editingPath, setEditingPath] = useState<string | null>(null);

  // Check if content has been modified
  const hasChanges = content !== originalContent;

  // Check if this is a user config (editable)
  const isUserConfig = (editingPath?.includes('.config/massgen') || editingPath?.includes('.massgen/')) ?? false;

  // Fetch user configs list
  const fetchUserConfigs = useCallback(async () => {
    setLoadingConfigs(true);
    try {
      const res = await fetch('/api/config/user-configs');
      if (res.ok) {
        const data = await res.json();
        setUserConfigs(data.configs || []);
        setConfigDir(data.config_dir || '');
      }
    } catch (err) {
      console.error('Failed to fetch user configs:', err);
    } finally {
      setLoadingConfigs(false);
    }
  }, []);

  // Fetch config content
  const fetchConfigContent = useCallback(async (path: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/config/content?path=${encodeURIComponent(path)}`);
      if (res.ok) {
        const data = await res.json();
        setContent(data.content || '');
        setOriginalContent(data.content || '');
        setEditingPath(path);
      } else {
        const errData = await res.json();
        setError(errData.error || 'Failed to load config');
      }
    } catch (err) {
      setError('Error loading config content');
      console.error('Failed to fetch config content:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Load config when modal opens or path changes
  useEffect(() => {
    if (isOpen) {
      fetchUserConfigs();
      if (configPath) {
        fetchConfigContent(configPath);
      }
    }
  }, [isOpen, configPath, fetchConfigContent, fetchUserConfigs]);

  // Clear state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setContent('');
      setOriginalContent('');
      setEditingPath(null);
      setError(null);
      setSuccessMessage(null);
      setIsRenaming(false);
      setIsCreating(false);
      setIsDeleting(false);
    }
  }, [isOpen]);

  // Clear success message after delay
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Save config content
  const handleSave = async () => {
    if (!editingPath || !isUserConfig) return;

    setSaving(true);
    setError(null);
    try {
      const res = await fetch('/api/config/update', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: editingPath, content }),
      });

      if (res.ok) {
        setOriginalContent(content);
        setSuccessMessage('Config saved successfully');
        onConfigSaved?.(editingPath);
      } else {
        const errData = await res.json();
        setError(errData.error || 'Failed to save config');
      }
    } catch (err) {
      setError('Error saving config');
      console.error('Failed to save config:', err);
    } finally {
      setSaving(false);
    }
  };

  // Rename config
  const handleRename = async () => {
    if (!editingPath || !newName.trim()) return;

    setRenameError(null);
    try {
      const res = await fetch('/api/config/rename', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: editingPath, new_name: newName.trim() }),
      });

      if (res.ok) {
        const data = await res.json();
        setEditingPath(data.new_path);
        setIsRenaming(false);
        setNewName('');
        setSuccessMessage('Config renamed successfully');
        fetchUserConfigs();
        onConfigChange(data.new_path);
      } else {
        const errData = await res.json();
        setRenameError(errData.error || 'Failed to rename config');
      }
    } catch (err) {
      setRenameError('Error renaming config');
      console.error('Failed to rename config:', err);
    }
  };

  // Create new config
  const handleCreate = async () => {
    if (!newConfigName.trim()) return;

    setCreateError(null);
    try {
      // Create with default template content
      const defaultContent = `# MassGen Configuration
# Created: ${new Date().toISOString()}

agents:
  - id: agent_a
    type: openai
    model: gpt-4o
    backend_params:
      temperature: 0.7

orchestrator:
  timeout: 300
  voting_sensitivity: medium
`;

      const res = await fetch('/api/config/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          config: { _raw_yaml: defaultContent },
          filename: newConfigName.trim().endsWith('.yaml')
            ? newConfigName.trim()
            : `${newConfigName.trim()}.yaml`,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setIsCreating(false);
        setNewConfigName('');
        setSuccessMessage('Config created successfully');
        fetchUserConfigs();
        // Load the new config
        fetchConfigContent(data.path);
        onConfigChange(data.path);
      } else {
        const errData = await res.json();
        setCreateError(errData.error || 'Failed to create config');
      }
    } catch (err) {
      setCreateError('Error creating config');
      console.error('Failed to create config:', err);
    }
  };

  // Delete config
  const handleDelete = async () => {
    if (!editingPath) return;

    setDeleteError(null);
    try {
      const res = await fetch(`/api/config/delete?path=${encodeURIComponent(editingPath)}`, {
        method: 'DELETE',
      });

      if (res.ok) {
        setIsDeleting(false);
        setSuccessMessage('Config deleted successfully');
        fetchUserConfigs();
        // Switch to first available config or clear
        if (userConfigs.length > 1) {
          const nextConfig = userConfigs.find((c) => c.path !== editingPath);
          if (nextConfig) {
            fetchConfigContent(nextConfig.path);
            onConfigChange(nextConfig.path);
          }
        } else {
          setEditingPath(null);
          setContent('');
          setOriginalContent('');
        }
      } else {
        const errData = await res.json();
        setDeleteError(errData.error || 'Failed to delete config');
      }
    } catch (err) {
      setDeleteError('Error deleting config');
      console.error('Failed to delete config:', err);
    }
  };

  // Get current config name
  const currentConfigName = editingPath?.split('/').pop() || 'No config selected';

  // Format file size
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    return `${(bytes / 1024).toFixed(1)} KB`;
  };

  // Format date
  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-6xl h-[85vh] flex"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Sidebar - Config File List */}
            <div className="w-64 border-r border-gray-200 dark:border-gray-700 flex flex-col">
              {/* Sidebar Header */}
              <div className="p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-semibold text-gray-800 dark:text-gray-200">Your Configs</h3>
                  <button
                    onClick={fetchUserConfigs}
                    className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                    title="Refresh"
                  >
                    <RefreshCw
                      className={`w-4 h-4 text-gray-500 ${loadingConfigs ? 'animate-spin' : ''}`}
                    />
                  </button>
                </div>
                <p className="text-xs text-gray-500 truncate" title={configDir}>
                  {configDir}
                </p>
              </div>

              {/* Config List */}
              <div className="flex-1 overflow-y-auto p-2">
                {userConfigs.length === 0 && !loadingConfigs ? (
                  <div className="text-center py-4 text-gray-500 text-sm">No configs found</div>
                ) : (
                  userConfigs.map((config) => (
                    <button
                      key={config.path}
                      onClick={() => fetchConfigContent(config.path)}
                      className={`w-full text-left p-2 rounded-lg mb-1 transition-colors ${
                        editingPath === config.path
                          ? 'bg-blue-100 dark:bg-blue-900/40 border border-blue-300 dark:border-blue-700'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-blue-500 flex-shrink-0" />
                        <span className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
                          {config.name}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500 mt-1 pl-6">
                        {formatSize(config.size)} - {formatDate(config.modified)}
                      </div>
                    </button>
                  ))
                )}
              </div>

              {/* New Config Button */}
              <div className="p-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={() => setIsCreating(true)}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500
                           text-white rounded-lg transition-colors text-sm"
                >
                  <Plus className="w-4 h-4" />
                  New Config
                </button>
              </div>
            </div>

            {/* Main Content - Editor */}
            <div className="flex-1 flex flex-col min-w-0">
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center gap-3 min-w-0">
                  <FolderOpen className="w-5 h-5 text-blue-500 flex-shrink-0" />
                  <div className="min-w-0">
                    <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-200 truncate">
                      {currentConfigName}
                    </h2>
                    {editingPath && (
                      <p
                        className="text-xs text-gray-500 truncate max-w-lg"
                        title={editingPath}
                      >
                        {editingPath}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {/* Rename Button */}
                  {isUserConfig && editingPath && (
                    <button
                      onClick={() => {
                        setNewName(currentConfigName.replace('.yaml', '').replace('.yml', ''));
                        setIsRenaming(true);
                      }}
                      className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                      title="Rename"
                    >
                      <Pencil className="w-4 h-4 text-gray-500" />
                    </button>
                  )}
                  {/* Delete Button */}
                  {isUserConfig && editingPath && userConfigs.length > 1 && (
                    <button
                      onClick={() => setIsDeleting(true)}
                      className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                  )}
                  {/* Save Button */}
                  {isUserConfig && hasChanges && (
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500
                               disabled:bg-gray-400 text-white rounded-lg transition-colors text-sm"
                    >
                      {saving ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Save className="w-4 h-4" />
                      )}
                      Save
                    </button>
                  )}
                  {/* Close Button */}
                  <button
                    onClick={onClose}
                    className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
              </div>

              {/* Status Messages */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="bg-red-100 dark:bg-red-900/30 border-b border-red-200 dark:border-red-800 px-4 py-2"
                  >
                    <div className="flex items-center gap-2 text-red-700 dark:text-red-400 text-sm">
                      <AlertCircle className="w-4 h-4" />
                      {error}
                    </div>
                  </motion.div>
                )}
                {successMessage && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="bg-green-100 dark:bg-green-900/30 border-b border-green-200 dark:border-green-800 px-4 py-2"
                  >
                    <div className="flex items-center gap-2 text-green-700 dark:text-green-400 text-sm">
                      <Check className="w-4 h-4" />
                      {successMessage}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Editor Content */}
              <div className="flex-1 overflow-hidden p-4">
                {loading ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                  </div>
                ) : editingPath ? (
                  <div className="h-full flex flex-col">
                    {!isUserConfig && (
                      <div className="bg-amber-100 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg px-4 py-2 mb-4">
                        <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400 text-sm">
                          <AlertCircle className="w-4 h-4" />
                          This config is read-only. Only configs in ~/.config/massgen/ or ./.massgen/ can be edited.
                        </div>
                      </div>
                    )}
                    <textarea
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      readOnly={!isUserConfig}
                      className={`flex-1 w-full bg-gray-900 text-gray-100 font-mono text-sm p-4 rounded-lg
                               resize-none focus:outline-none focus:ring-2 focus:ring-blue-500
                               ${!isUserConfig ? 'cursor-not-allowed opacity-80' : ''}`}
                      spellCheck={false}
                    />
                    {hasChanges && (
                      <div className="text-xs text-amber-500 mt-2">
                        Unsaved changes
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-gray-500">
                    <FileCode className="w-16 h-16 mb-4 opacity-50" />
                    <p>Select a config file to edit</p>
                    <p className="text-sm mt-2">or create a new one</p>
                  </div>
                )}
              </div>
            </div>

            {/* Rename Dialog */}
            <AnimatePresence>
              {isRenaming && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 bg-black/50 flex items-center justify-center rounded-xl"
                  onClick={() => setIsRenaming(false)}
                >
                  <motion.div
                    initial={{ scale: 0.95 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0.95 }}
                    className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-96"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
                      Rename Config
                    </h3>
                    <input
                      type="text"
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="New name"
                      className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                               rounded-lg text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleRename();
                        if (e.key === 'Escape') setIsRenaming(false);
                      }}
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      Will be saved as: {newName.trim() || 'config'}.yaml
                    </p>
                    {renameError && (
                      <p className="text-sm text-red-500 mt-2">{renameError}</p>
                    )}
                    <div className="flex justify-end gap-2 mt-4">
                      <button
                        onClick={() => setIsRenaming(false)}
                        className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleRename}
                        disabled={!newName.trim()}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-400 text-white rounded-lg"
                      >
                        Rename
                      </button>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Create Dialog */}
            <AnimatePresence>
              {isCreating && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 bg-black/50 flex items-center justify-center rounded-xl"
                  onClick={() => setIsCreating(false)}
                >
                  <motion.div
                    initial={{ scale: 0.95 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0.95 }}
                    className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-96"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200 mb-4">
                      Create New Config
                    </h3>
                    <input
                      type="text"
                      value={newConfigName}
                      onChange={(e) => setNewConfigName(e.target.value)}
                      placeholder="Config name"
                      className="w-full px-3 py-2 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                               rounded-lg text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') handleCreate();
                        if (e.key === 'Escape') setIsCreating(false);
                      }}
                    />
                    <p className="text-xs text-gray-500 mt-2">
                      Will be created as: {newConfigName.trim() || 'config'}.yaml
                    </p>
                    {createError && (
                      <p className="text-sm text-red-500 mt-2">{createError}</p>
                    )}
                    <div className="flex justify-end gap-2 mt-4">
                      <button
                        onClick={() => setIsCreating(false)}
                        className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleCreate}
                        disabled={!newConfigName.trim()}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-400 text-white rounded-lg"
                      >
                        Create
                      </button>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Delete Confirmation Dialog */}
            <AnimatePresence>
              {isDeleting && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="absolute inset-0 bg-black/50 flex items-center justify-center rounded-xl"
                  onClick={() => setIsDeleting(false)}
                >
                  <motion.div
                    initial={{ scale: 0.95 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0.95 }}
                    className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-96"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <h3 className="text-lg font-semibold text-red-600 dark:text-red-400 mb-4">
                      Delete Config
                    </h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-4">
                      Are you sure you want to delete <strong>{currentConfigName}</strong>? This
                      action cannot be undone.
                    </p>
                    {deleteError && (
                      <p className="text-sm text-red-500 mb-4">{deleteError}</p>
                    )}
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setIsDeleting(false)}
                        className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleDelete}
                        className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg"
                      >
                        Delete
                      </button>
                    </div>
                  </motion.div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default ConfigEditorModal;
