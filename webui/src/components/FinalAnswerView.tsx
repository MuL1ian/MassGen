/**
 * FinalAnswerView Component
 *
 * Full-screen display of the completed final answer.
 * Features tabbed interface for Answer and Workspace views.
 */

import { useState, useMemo, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, FileText, Folder, Trophy, ChevronDown, ChevronRight, File, RefreshCw, History, Copy, Check, Loader2, Send, Plus } from 'lucide-react';
import { useAgentStore, selectSelectedAgent, selectAgents, selectResolvedFinalAnswer, selectAgentOrder } from '../stores/agentStore';
import type { AnswerWorkspace } from '../types';
import { FileViewerModal } from './FileViewerModal';
import { ConversationHistory } from './ConversationHistory';

// Types for workspace API responses
interface WorkspaceInfo {
  name: string;
  path: string;
  type: 'current' | 'historical';
  date?: string;
  agentId?: string;
}

interface WorkspacesResponse {
  current: WorkspaceInfo[];
  historical: WorkspaceInfo[];
}

interface AnswerWorkspacesResponse {
  workspaces: AnswerWorkspace[];
  current: WorkspaceInfo[];
}

interface FileInfo {
  path: string;
  size: number;
  modified: number;
  operation?: 'create' | 'modify' | 'delete';
}

// Map workspace name to agent ID (e.g., "workspace1" -> agent at index 0)
function getAgentIdFromWorkspace(workspaceName: string, agentOrder: string[]): string | undefined {
  const match = workspaceName.match(/workspace(\d+)/);
  if (match) {
    const index = parseInt(match[1], 10) - 1;
    return agentOrder[index];
  }
  return undefined;
}

// Format file size for display
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// File tree types and helpers
interface FileTreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children: FileTreeNode[];
  size?: number;
  modified?: number;
}

function buildFileTree(files: FileInfo[]): FileTreeNode[] {
  const root: FileTreeNode[] = [];

  files.forEach((file) => {
    const parts = file.path.split('/').filter(Boolean);
    let current = root;

    parts.forEach((part, idx) => {
      const isLast = idx === parts.length - 1;
      let node = current.find((n) => n.name === part);

      if (!node) {
        node = {
          name: part,
          path: parts.slice(0, idx + 1).join('/'),
          isDirectory: !isLast,
          children: [],
          size: isLast ? file.size : undefined,
          modified: isLast ? file.modified : undefined,
        };
        current.push(node);
      }

      if (!isLast) {
        node.isDirectory = true;
        current = node.children;
      }
    });
  });

  // Sort: directories first, then files alphabetically
  const sortNodes = (nodes: FileTreeNode[]): FileTreeNode[] => {
    return nodes.sort((a, b) => {
      if (a.isDirectory && !b.isDirectory) return -1;
      if (!a.isDirectory && b.isDirectory) return 1;
      return a.name.localeCompare(b.name);
    }).map(node => ({
      ...node,
      children: sortNodes(node.children),
    }));
  };

  return sortNodes(root);
}

interface FileNodeProps {
  node: FileTreeNode;
  depth: number;
  onFileClick?: (filePath: string) => void;
}

function FileNode({ node, depth, onFileClick }: FileNodeProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  const handleClick = () => {
    if (node.isDirectory) {
      setIsExpanded(!isExpanded);
    } else if (onFileClick) {
      onFileClick(node.path);
    }
  };

  return (
    <div>
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        className={`
          flex items-center gap-1 py-1.5 px-2 hover:bg-gray-100 dark:hover:bg-gray-700/30 rounded cursor-pointer
          text-sm text-gray-700 dark:text-gray-300
          ${!node.isDirectory && onFileClick ? 'hover:bg-blue-100 dark:hover:bg-blue-900/30' : ''}
        `}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={handleClick}
      >
        {node.isDirectory ? (
          isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )
        ) : (
          <span className="w-4" />
        )}

        {node.isDirectory ? (
          <Folder className="w-4 h-4 text-blue-400" />
        ) : (
          <File className="w-4 h-4 text-gray-400" />
        )}

        <span className="flex-1">{node.name}</span>

        {!node.isDirectory && node.size !== undefined && (
          <span className="text-xs text-gray-500 dark:text-gray-500">
            {formatFileSize(node.size)}
          </span>
        )}
      </motion.div>

      <AnimatePresence>
        {node.isDirectory && isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {node.children.map((child) => (
              <FileNode key={child.path} node={child} depth={depth + 1} onFileClick={onFileClick} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

type TabType = 'answer' | 'workspace';

interface FinalAnswerViewProps {
  onBackToAgents: () => void;
  onFollowUp?: (question: string) => void;
  onNewSession?: () => void;
  isConnected?: boolean;
}

export function FinalAnswerView({ onBackToAgents, onFollowUp, onNewSession, isConnected = true }: FinalAnswerViewProps) {
  const [activeTab, setActiveTab] = useState<TabType>('answer');
  const [copied, setCopied] = useState(false);
  const [followUpQuestion, setFollowUpQuestion] = useState('');

  const finalAnswer = useAgentStore(selectResolvedFinalAnswer);
  const selectedAgent = useAgentStore(selectSelectedAgent);
  const agents = useAgentStore(selectAgents);
  const agentOrder = useAgentStore(selectAgentOrder);

  const winnerAgent = selectedAgent ? agents[selectedAgent] : null;
  const displayName = winnerAgent?.modelName
    ? `${selectedAgent} (${winnerAgent.modelName})`
    : selectedAgent;

  // Workspace state
  const [workspaces, setWorkspaces] = useState<WorkspacesResponse>({ current: [], historical: [] });
  const [workspaceFiles, setWorkspaceFiles] = useState<FileInfo[]>([]);
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [answerWorkspaces, setAnswerWorkspaces] = useState<AnswerWorkspace[]>([]);
  const [selectedAnswerLabel, setSelectedAnswerLabel] = useState<string>('current');

  // File viewer modal state
  const [fileViewerOpen, setFileViewerOpen] = useState(false);
  const [selectedFilePath, setSelectedFilePath] = useState<string>('');

  // Handle file click from workspace browser
  const handleFileClick = useCallback((filePath: string) => {
    setSelectedFilePath(filePath);
    setFileViewerOpen(true);
  }, []);

  // Fetch workspaces
  const fetchWorkspaces = useCallback(async () => {
    setIsLoadingWorkspaces(true);
    setWorkspaceError(null);
    try {
      const response = await fetch('/api/workspaces');
      if (!response.ok) throw new Error('Failed to fetch workspaces');
      const data: WorkspacesResponse = await response.json();
      setWorkspaces(data);
    } catch (err) {
      setWorkspaceError(err instanceof Error ? err.message : 'Failed to load workspaces');
    } finally {
      setIsLoadingWorkspaces(false);
    }
  }, []);

  // Fetch workspace files
  const fetchWorkspaceFiles = useCallback(async (workspace: WorkspaceInfo) => {
    setIsLoadingFiles(true);
    setWorkspaceError(null);
    try {
      const response = await fetch(`/api/workspace/browse?path=${encodeURIComponent(workspace.path)}`);
      if (!response.ok) throw new Error('Failed to fetch workspace files');
      const data = await response.json();
      setWorkspaceFiles(data.files || []);
    } catch (err) {
      setWorkspaceError(err instanceof Error ? err.message : 'Failed to load files');
      setWorkspaceFiles([]);
    } finally {
      setIsLoadingFiles(false);
    }
  }, []);

  // Fetch answer workspaces
  const fetchAnswerWorkspaces = useCallback(async () => {
    const sessionId = useAgentStore.getState().sessionId;
    if (!sessionId) return;
    try {
      const response = await fetch(`/api/sessions/${sessionId}/answer-workspaces`);
      if (response.ok) {
        const data: AnswerWorkspacesResponse = await response.json();
        setAnswerWorkspaces(data.workspaces || []);
      }
    } catch (err) {
      console.error('Failed to fetch answer workspaces:', err);
    }
  }, []);

  // Map workspaces to winner agent
  const winnerWorkspace = useMemo(() => {
    if (!selectedAgent) return null;
    const ws = workspaces.current.find((w) => {
      const agentId = getAgentIdFromWorkspace(w.name, agentOrder);
      return agentId === selectedAgent;
    });
    return ws || null;
  }, [workspaces, selectedAgent, agentOrder]);

  // Fetch workspaces when workspace tab is active
  useEffect(() => {
    if (activeTab === 'workspace') {
      fetchWorkspaces();
      fetchAnswerWorkspaces();
    }
  }, [activeTab, fetchWorkspaces, fetchAnswerWorkspaces]);

  // Fetch files when workspace is available
  useEffect(() => {
    if (winnerWorkspace && activeTab === 'workspace') {
      fetchWorkspaceFiles(winnerWorkspace);
    }
  }, [winnerWorkspace, activeTab, fetchWorkspaceFiles]);

  // Build file tree
  const fileTree = useMemo(() => buildFileTree(workspaceFiles), [workspaceFiles]);

  // Copy to clipboard
  const handleCopy = useCallback(async () => {
    if (finalAnswer && finalAnswer !== '__PENDING__') {
      await navigator.clipboard.writeText(finalAnswer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [finalAnswer]);

  // Handle follow-up question submission
  const handleFollowUpSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (followUpQuestion.trim() && onFollowUp) {
      onFollowUp(followUpQuestion.trim());
      setFollowUpQuestion('');
    }
  }, [followUpQuestion, onFollowUp]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 20 }}
      transition={{ duration: 0.3, delay: 0.1 }}
      className="fixed inset-0 bg-white dark:bg-gray-900 z-40 flex flex-col"
    >
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <button
          onClick={onBackToAgents}
          className="flex items-center gap-2 px-4 py-2 bg-gray-200 dark:bg-gray-700
                     hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg transition-colors
                     text-gray-700 dark:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Agents
        </button>

        <div className="flex items-center gap-3">
          <Trophy className="w-6 h-6 text-yellow-500" />
          <div className="text-center">
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
              Final Answer
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              from <span className="text-yellow-600 dark:text-yellow-400 font-medium">{displayName}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500
                       rounded-lg transition-colors text-white"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy
              </>
            )}
          </button>
          {onNewSession && (
            <button
              onClick={onNewSession}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-500
                         rounded-lg transition-colors text-white"
            >
              <Plus className="w-4 h-4" />
              New Session
            </button>
          )}
        </div>
      </header>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 px-6 bg-gray-50 dark:bg-gray-800/50">
        <button
          onClick={() => setActiveTab('answer')}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'answer'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-200'
          }`}
        >
          <FileText className="w-4 h-4" />
          Answer
        </button>
        <button
          onClick={() => setActiveTab('workspace')}
          className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'workspace'
              ? 'border-blue-500 text-blue-600 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-200'
          }`}
        >
          <Folder className="w-4 h-4" />
          Workspace
        </button>
      </div>

      {/* Tab Content */}
      <main className="flex-1 overflow-hidden">
        <AnimatePresence mode="wait">
          {activeTab === 'answer' ? (
            <motion.div
              key="answer"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ duration: 0.2 }}
              className="h-full overflow-y-auto custom-scrollbar p-6"
            >
              <div className="max-w-4xl mx-auto space-y-6">
                {/* Conversation History - shown at top for context */}
                <ConversationHistory />

                {/* Final Answer Content */}
                <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                  {!finalAnswer || finalAnswer === '__PENDING__' ? (
                    <div className="flex flex-col items-center justify-center py-12 text-gray-500">
                      <Loader2 className="w-8 h-8 mb-4 animate-spin text-blue-500" />
                      <p>Loading final answer...</p>
                    </div>
                  ) : (
                    <pre className="whitespace-pre-wrap text-gray-800 dark:text-gray-200 font-mono text-sm leading-relaxed">
                      {finalAnswer}
                    </pre>
                  )}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="workspace"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="h-full flex flex-col"
            >
              {/* Workspace toolbar */}
              <div className="px-6 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center gap-4">
                {/* Version selector */}
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-amber-500" />
                  <span className="text-sm text-gray-500 dark:text-gray-400">Version:</span>
                  <div className="relative">
                    <select
                      value={selectedAnswerLabel}
                      onChange={(e) => {
                        const label = e.target.value;
                        setSelectedAnswerLabel(label);
                        if (label === 'current' && winnerWorkspace) {
                          fetchWorkspaceFiles(winnerWorkspace);
                        } else {
                          const answerWs = answerWorkspaces.find(w => w.answerLabel === label);
                          if (answerWs) {
                            fetchWorkspaceFiles({
                              name: answerWs.answerLabel,
                              path: answerWs.workspacePath,
                              type: 'historical'
                            });
                          }
                        }
                      }}
                      className="appearance-none bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600
                                 rounded-lg px-3 py-1.5 pr-8 text-sm text-gray-700 dark:text-gray-200
                                 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="current">Current</option>
                      {answerWorkspaces
                        .filter(w => w.agentId === selectedAgent)
                        .map((ws) => (
                          <option key={ws.answerId} value={ws.answerLabel}>
                            {ws.answerLabel}
                          </option>
                        ))}
                    </select>
                    <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" />
                  </div>
                </div>

                {/* Refresh button */}
                <button
                  onClick={() => { fetchWorkspaces(); fetchAnswerWorkspaces(); }}
                  disabled={isLoadingWorkspaces}
                  className="ml-auto p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-lg transition-colors
                             text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                  title="Refresh workspaces"
                >
                  <RefreshCw className={`w-4 h-4 ${isLoadingWorkspaces ? 'animate-spin' : ''}`} />
                </button>
              </div>

              {/* Error display */}
              {workspaceError && (
                <div className="px-6 py-2 bg-red-50 dark:bg-red-900/30 border-b border-red-200 dark:border-red-700 text-red-600 dark:text-red-300 text-sm">
                  {workspaceError}
                </div>
              )}

              {/* File tree */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-6">
                <div className="max-w-4xl mx-auto">
                  {isLoadingWorkspaces || isLoadingFiles ? (
                    <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                      <RefreshCw className="w-8 h-8 mb-4 animate-spin" />
                      <p>Loading workspace...</p>
                    </div>
                  ) : !winnerWorkspace ? (
                    <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                      <Folder className="w-12 h-12 mb-4 opacity-50" />
                      <p>No workspace found for winner</p>
                    </div>
                  ) : workspaceFiles.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                      <Folder className="w-12 h-12 mb-4 opacity-50" />
                      <p>No files in workspace</p>
                    </div>
                  ) : (
                    <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                      <div className="mb-3 text-sm text-gray-500 dark:text-gray-400 flex items-center gap-2">
                        <Folder className="w-4 h-4" />
                        <span>{winnerWorkspace.name}</span>
                        <span className="text-gray-400">-</span>
                        <span>{workspaceFiles.length} files</span>
                      </div>
                      {fileTree.map((node) => (
                        <FileNode key={node.path} node={node} depth={0} onFileClick={handleFileClick} />
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      {/* Follow-up Input Footer */}
      {onFollowUp && (
        <footer className="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 px-6 py-4">
          <form onSubmit={handleFollowUpSubmit} className="max-w-4xl mx-auto flex gap-4">
            <input
              type="text"
              value={followUpQuestion}
              onChange={(e) => setFollowUpQuestion(e.target.value)}
              placeholder="Ask a follow-up question..."
              disabled={!isConnected}
              className="flex-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg px-4 py-3
                       text-gray-900 dark:text-gray-100 placeholder-gray-500
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                       disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              type="submit"
              disabled={!followUpQuestion.trim() || !isConnected}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-400 dark:disabled:bg-gray-600
                       disabled:cursor-not-allowed rounded-lg transition-colors text-white
                       flex items-center gap-2"
            >
              <Send className="w-5 h-5" />
              <span>Continue</span>
            </button>
          </form>
        </footer>
      )}

      {/* File Viewer Modal */}
      <FileViewerModal
        isOpen={fileViewerOpen}
        onClose={() => setFileViewerOpen(false)}
        filePath={selectedFilePath}
        workspacePath={winnerWorkspace?.path || ''}
      />
    </motion.div>
  );
}

export default FinalAnswerView;
