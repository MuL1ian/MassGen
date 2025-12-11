/**
 * AnswerBrowserModal Component
 *
 * Modal dialog for browsing all answers and workspace files from agents.
 * Includes tabs for Answers and Workspace views.
 */

import { useState, useMemo, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, FileText, User, Clock, ChevronDown, Trophy, Folder, File, ChevronRight, RefreshCw, History, Vote, ArrowRight, Eye, GitBranch } from 'lucide-react';
import { useAgentStore, selectAnswers, selectAgents, selectAgentOrder, selectSelectedAgent, selectFinalAnswer, selectVoteDistribution, resolveAnswerContent } from '../stores/agentStore';
import type { Answer, AnswerWorkspace, TimelineNode as TimelineNodeType } from '../types';
import { FileViewerModal } from './FileViewerModal';
import { TimelineView } from './timeline';

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

// Map workspace name to agent ID (e.g., "workspace1" -> agent at index 0)
function getAgentIdFromWorkspace(workspaceName: string, agentOrder: string[]): string | undefined {
  const match = workspaceName.match(/workspace(\d+)/);
  if (match) {
    const index = parseInt(match[1], 10) - 1; // workspace1 = index 0
    return agentOrder[index];
  }
  return undefined;
}

interface FileInfo {
  path: string;
  size: number;
  modified: number;
  operation?: 'create' | 'modify' | 'delete';
}

interface AnswerBrowserModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: TabType;
}

type TabType = 'answers' | 'votes' | 'workspace' | 'timeline';

function formatTimestamp(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

// ============================================================================
// Workspace File Tree Components
// ============================================================================

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

// Format file size for display
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
          flex items-center gap-1 py-1 px-2 hover:bg-gray-700/30 dark:hover:bg-gray-700/30 rounded cursor-pointer
          text-sm text-gray-700 dark:text-gray-300
          ${!node.isDirectory && onFileClick ? 'hover:bg-blue-900/30' : ''}
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

        {/* File size for non-directories */}
        {!node.isDirectory && node.size !== undefined && (
          <span className="text-xs text-gray-500 dark:text-gray-500">
            {formatFileSize(node.size)}
          </span>
        )}

        {/* View icon for files */}
        {!node.isDirectory && onFileClick && (
          <Eye className="w-3.5 h-3.5 text-gray-500 hover:text-blue-400 opacity-0 group-hover:opacity-100 transition-opacity" />
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

// ============================================================================
// Main Modal Component
// ============================================================================

export function AnswerBrowserModal({ isOpen, onClose, initialTab = 'answers' }: AnswerBrowserModalProps) {
  const answers = useAgentStore(selectAnswers);
  const agents = useAgentStore(selectAgents);
  const agentOrder = useAgentStore(selectAgentOrder);
  const selectedAgent = useAgentStore(selectSelectedAgent);
  const finalAnswer = useAgentStore(selectFinalAnswer);
  const voteDistribution = useAgentStore(selectVoteDistribution);

  const [activeTab, setActiveTab] = useState<TabType>(initialTab);

  // Update active tab when initialTab changes (e.g., opening from notification)
  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
    }
  }, [isOpen, initialTab]);
  const [filterAgent, setFilterAgent] = useState<string | 'all'>('all');
  const [expandedAnswerId, setExpandedAnswerId] = useState<string | null>(null);

  // Auto-expand final answer when modal opens with answers tab
  useEffect(() => {
    if (isOpen && activeTab === 'answers' && !expandedAnswerId) {
      // Find the final answer (answerNumber === 0) and expand it
      const finalAnswerEntry = answers.find(a => a.answerNumber === 0);
      if (finalAnswerEntry) {
        setExpandedAnswerId(finalAnswerEntry.id);
      }
    }
  }, [isOpen, activeTab, answers, expandedAnswerId]);

  // Workspace state - now fetched from API
  const [workspaces, setWorkspaces] = useState<WorkspacesResponse>({ current: [], historical: [] });
  const [workspaceFiles, setWorkspaceFiles] = useState<FileInfo[]>([]);
  const [isLoadingWorkspaces, setIsLoadingWorkspaces] = useState(false);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);

  // Per-agent workspace selection state
  const [selectedAgentWorkspace, setSelectedAgentWorkspace] = useState<string | null>(null);
  const [selectedHistoricalWorkspace, setSelectedHistoricalWorkspace] = useState<WorkspaceInfo | null>(null);

  // Answer-linked workspace state
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

  // Handle timeline node click - navigate to appropriate tab
  const handleTimelineNodeClick = useCallback((node: TimelineNodeType) => {
    if (node.type === 'answer' || node.type === 'final') {
      // Switch to answers tab and expand the matching answer
      setActiveTab('answers');
      // Find and expand the answer that matches this node's label
      const matchingAnswer = answers.find(a => {
        // Match by agent ID and answer number
        const agentIdx = agentOrder.indexOf(a.agentId) + 1;
        const expectedLabel = a.answerNumber === 0
          ? 'final'
          : `agent${agentIdx}.${a.answerNumber}`;
        return node.label === expectedLabel || node.label === `answer${agentIdx}.${a.answerNumber}`;
      });
      if (matchingAnswer) {
        setExpandedAnswerId(matchingAnswer.id);
      }
    } else if (node.type === 'vote') {
      // Switch to votes tab
      setActiveTab('votes');
    }
  }, [answers, agentOrder]);

  // Fetch available workspaces from API
  const fetchWorkspaces = useCallback(async () => {
    setIsLoadingWorkspaces(true);
    setWorkspaceError(null);
    try {
      const response = await fetch('/api/workspaces');
      if (!response.ok) {
        throw new Error('Failed to fetch workspaces');
      }
      const data: WorkspacesResponse = await response.json();
      setWorkspaces(data);

      // Auto-select first agent's workspace if available
      if (data.current.length > 0 && !selectedAgentWorkspace) {
        const firstWorkspace = data.current[0];
        const agentId = getAgentIdFromWorkspace(firstWorkspace.name, agentOrder);
        if (agentId) {
          setSelectedAgentWorkspace(agentId);
        }
      }
    } catch (err) {
      setWorkspaceError(err instanceof Error ? err.message : 'Failed to load workspaces');
    } finally {
      setIsLoadingWorkspaces(false);
    }
  }, [selectedAgentWorkspace, agentOrder]);

  // Fetch files for selected workspace
  const fetchWorkspaceFiles = useCallback(async (workspace: WorkspaceInfo) => {
    setIsLoadingFiles(true);
    setWorkspaceError(null);
    try {
      const response = await fetch(`/api/workspace/browse?path=${encodeURIComponent(workspace.path)}`);
      if (!response.ok) {
        throw new Error('Failed to fetch workspace files');
      }
      const data = await response.json();
      setWorkspaceFiles(data.files || []);
    } catch (err) {
      setWorkspaceError(err instanceof Error ? err.message : 'Failed to load files');
      setWorkspaceFiles([]);
    } finally {
      setIsLoadingFiles(false);
    }
  }, []);

  // Fetch answer-linked workspaces from API
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

  // Map workspaces to agents
  const workspacesByAgent = useMemo(() => {
    const map: Record<string, { current?: WorkspaceInfo; historical: WorkspaceInfo[] }> = {};

    // Initialize for all agents
    agentOrder.forEach((agentId) => {
      map[agentId] = { historical: [] };
    });

    // Map current workspaces
    workspaces.current.forEach((ws) => {
      const agentId = getAgentIdFromWorkspace(ws.name, agentOrder);
      if (agentId && map[agentId]) {
        map[agentId].current = ws;
      }
    });

    // Map historical workspaces
    workspaces.historical.forEach((ws) => {
      const agentId = getAgentIdFromWorkspace(ws.name, agentOrder);
      if (agentId && map[agentId]) {
        map[agentId].historical.push(ws);
      }
    });

    return map;
  }, [workspaces, agentOrder]);

  // Compute active workspace to display
  const activeWorkspace = useMemo(() => {
    if (!selectedAgentWorkspace) return null;
    if (selectedHistoricalWorkspace) return selectedHistoricalWorkspace;
    return workspacesByAgent[selectedAgentWorkspace]?.current || null;
  }, [selectedAgentWorkspace, selectedHistoricalWorkspace, workspacesByAgent]);

  // Fetch workspaces when modal opens or tab switches to workspace
  useEffect(() => {
    if (isOpen && activeTab === 'workspace') {
      fetchWorkspaces();
      fetchAnswerWorkspaces();
    }
  }, [isOpen, activeTab, fetchWorkspaces, fetchAnswerWorkspaces]);

  // Fetch files when workspace is selected
  useEffect(() => {
    if (activeWorkspace) {
      fetchWorkspaceFiles(activeWorkspace);
    }
  }, [activeWorkspace, fetchWorkspaceFiles]);

  // Filter answers based on selected agent
  const filteredAnswers = useMemo(() => {
    let result = [...answers];

    if (filterAgent !== 'all') {
      result = result.filter((a) => a.agentId === filterAgent);
    }

    return result.sort((a, b) => b.timestamp - a.timestamp);
  }, [answers, filterAgent]);

  // Group answers by agent for summary stats
  const answersByAgent = useMemo(() => {
    const grouped: Record<string, Answer[]> = {};
    answers.forEach((answer) => {
      if (!grouped[answer.agentId]) {
        grouped[answer.agentId] = [];
      }
      grouped[answer.agentId].push(answer);
    });
    return grouped;
  }, [answers]);

  // Collect vote data with answer labels
  const votes = useMemo(() => {
    return agentOrder
      .map((agentId, voterIdx) => {
        const agent = agents[agentId];
        if (!agent?.voteTarget) return null;

        const targetIdx = agentOrder.indexOf(agent.voteTarget);
        const targetAgent = agents[agent.voteTarget];

        // Find the answer that was voted for (most recent answer from target at time of vote)
        // The target's answerCount tells us how many answers they had
        const targetAnswerCount = targetAgent?.answerCount || 1;
        const votedAnswerLabel = `answer${targetIdx + 1}.${targetAnswerCount}`;

        // Find what answers were available to choose from (answers from all agents at vote time)
        const availableAnswers = agentOrder.map((aid, idx) => {
          const a = agents[aid];
          const count = a?.answerCount || 1;
          return `answer${idx + 1}.${count}`;
        });

        return {
          voterId: agentId,
          voterIndex: voterIdx + 1,
          voterModel: agent.modelName,
          targetId: agent.voteTarget,
          targetIndex: targetIdx + 1,
          targetModel: targetAgent?.modelName,
          votedAnswerLabel,
          availableAnswers,
          reason: agent.voteReason || 'No reason provided',
        };
      })
      .filter(Boolean) as Array<{
        voterId: string;
        voterIndex: number;
        voterModel?: string;
        targetId: string;
        targetIndex: number;
        targetModel?: string;
        votedAnswerLabel: string;
        availableAnswers: string[];
        reason: string;
      }>;
  }, [agents, agentOrder]);

  // Sort vote distribution by votes (highest first)
  const sortedDistribution = useMemo(() => {
    return Object.entries(voteDistribution)
      .sort(([, a], [, b]) => b - a)
      .map(([agentId, voteCount]) => {
        const idx = agentOrder.indexOf(agentId);
        return {
          agentId,
          agentIndex: idx + 1,
          modelName: agents[agentId]?.modelName,
          votes: voteCount,
          isWinner: agentId === selectedAgent,
        };
      });
  }, [voteDistribution, agents, agentOrder, selectedAgent]);

  // Build file tree from workspace files
  const fileTree = useMemo(() => buildFileTree(workspaceFiles), [workspaceFiles]);

  // Count total workspaces
  const totalWorkspaces = workspaces.current.length + workspaces.historical.length;

  if (!isOpen) return null;

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
            className="fixed inset-4 md:inset-10 lg:inset-20 bg-gray-800 rounded-xl border border-gray-600 shadow-2xl z-50 flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900/50">
              <div className="flex items-center gap-3">
                <FileText className="w-6 h-6 text-blue-400" />
                <h2 className="text-xl font-semibold text-gray-100">Browser</h2>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-gray-400" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex border-b border-gray-700 bg-gray-800/50">
              <button
                onClick={() => setActiveTab('answers')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors border-b-2 ${
                  activeTab === 'answers'
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                <FileText className="w-4 h-4" />
                Answers
                <span className="px-1.5 py-0.5 bg-gray-700 rounded-full text-xs">
                  {answers.length}
                </span>
              </button>
              <button
                onClick={() => setActiveTab('votes')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors border-b-2 ${
                  activeTab === 'votes'
                    ? 'border-amber-500 text-amber-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                <Vote className="w-4 h-4" />
                Votes
                <span className="px-1.5 py-0.5 bg-gray-700 rounded-full text-xs">
                  {votes.length}
                </span>
              </button>
              <button
                onClick={() => setActiveTab('workspace')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors border-b-2 ${
                  activeTab === 'workspace'
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                <Folder className="w-4 h-4" />
                Workspace
                <span className="px-1.5 py-0.5 bg-gray-700 rounded-full text-xs">
                  {totalWorkspaces}
                </span>
              </button>
              <button
                onClick={() => setActiveTab('timeline')}
                className={`flex items-center gap-2 px-6 py-3 text-sm font-medium transition-colors border-b-2 ${
                  activeTab === 'timeline'
                    ? 'border-green-500 text-green-400'
                    : 'border-transparent text-gray-400 hover:text-gray-200'
                }`}
              >
                <GitBranch className="w-4 h-4" />
                Timeline
              </button>
            </div>

            {/* Tab Content */}
            {activeTab === 'answers' ? (
              <>
                {/* Filter Bar */}
                <div className="px-6 py-3 border-b border-gray-700 bg-gray-800/50 flex items-center gap-4">
                  <span className="text-sm text-gray-400">Filter by agent:</span>
                  <div className="relative">
                    <select
                      value={filterAgent}
                      onChange={(e) => setFilterAgent(e.target.value)}
                      className="appearance-none bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 pr-10 text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="all">All Agents</option>
                      {agentOrder.map((agentId) => (
                        <option key={agentId} value={agentId}>
                          {agentId} ({answersByAgent[agentId]?.length || 0} answers)
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
                  </div>
                </div>

                {/* Answer List */}
                <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
                  {filteredAnswers.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <FileText className="w-12 h-12 mb-4 opacity-50" />
                      <p>No answers yet</p>
                      <p className="text-sm mt-1">Answers will appear here as agents submit them</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {filteredAnswers.map((answer) => {
                        const isExpanded = expandedAnswerId === answer.id;
                        const isWinner = answer.agentId === selectedAgent;

                        return (
                          <motion.div
                            key={answer.id}
                            layout
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className={`
                              bg-gray-700/50 rounded-lg border overflow-hidden cursor-pointer
                              transition-colors hover:bg-gray-700/70
                              ${isWinner ? 'border-yellow-500/50' : 'border-gray-600'}
                            `}
                            onClick={() => setExpandedAnswerId(isExpanded ? null : answer.id)}
                          >
                            {/* Answer Header */}
                            <div className="flex items-center justify-between px-4 py-3">
                              <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg ${isWinner ? 'bg-yellow-900/50' : 'bg-blue-900/50'}`}>
                                  {isWinner ? (
                                    <Trophy className="w-4 h-4 text-yellow-400" />
                                  ) : (
                                    <User className="w-4 h-4 text-blue-400" />
                                  )}
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium text-gray-200">{answer.agentId}</span>
                                    <span className="text-gray-500 text-sm">
                                      {answer.answerNumber === 0 ? 'Final Answer' : `Answer #${answer.answerNumber}`}
                                    </span>
                                    {answer.answerNumber === 0 && (
                                      <span className="px-2 py-0.5 bg-green-900/50 text-green-300 rounded-full text-xs">
                                        Final
                                      </span>
                                    )}
                                    {isWinner && answer.answerNumber !== 0 && (
                                      <span className="px-2 py-0.5 bg-yellow-900/50 text-yellow-300 rounded-full text-xs">
                                        Winner
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-2 text-xs text-gray-500 mt-0.5">
                                    <Clock className="w-3 h-3" />
                                    <span>{formatTimestamp(answer.timestamp)}</span>
                                  </div>
                                </div>
                              </div>
                              <motion.div
                                animate={{ rotate: isExpanded ? 180 : 0 }}
                                className="text-gray-400"
                              >
                                <ChevronDown className="w-5 h-5" />
                              </motion.div>
                            </div>

                            {/* Answer Content (Expandable) */}
                            <AnimatePresence>
                              {isExpanded && (
                                <motion.div
                                  initial={{ height: 0, opacity: 0 }}
                                  animate={{ height: 'auto', opacity: 1 }}
                                  exit={{ height: 0, opacity: 0 }}
                                  transition={{ duration: 0.2 }}
                                  className="border-t border-gray-600"
                                >
                                  <div className="p-4 bg-gray-800/50">
                                    <pre className="whitespace-pre-wrap text-sm text-gray-300 font-mono leading-relaxed max-h-96 overflow-y-auto custom-scrollbar">
                                      {resolveAnswerContent(answer, agents, finalAnswer)}
                                    </pre>
                                  </div>
                                </motion.div>
                              )}
                            </AnimatePresence>
                          </motion.div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </>
            ) : activeTab === 'votes' ? (
              <>
                {/* Votes Tab Content */}
                <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
                  {/* Vote Distribution Summary */}
                  {sortedDistribution.length > 0 && (
                    <div className="mb-6">
                      <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                        <Trophy className="w-4 h-4" />
                        Vote Distribution
                      </h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {sortedDistribution.map(({ agentId, agentIndex, modelName, votes: voteCount, isWinner }) => (
                          <div
                            key={agentId}
                            className={`
                              flex items-center justify-between px-4 py-3 rounded-lg
                              ${isWinner
                                ? 'bg-yellow-500/20 border border-yellow-500/50'
                                : 'bg-gray-700/50 border border-gray-600'
                              }
                            `}
                          >
                            <div className="flex items-center gap-2">
                              <User className={`w-4 h-4 ${isWinner ? 'text-yellow-400' : 'text-gray-400'}`} />
                              <div>
                                <span className={`font-medium ${isWinner ? 'text-yellow-300' : 'text-gray-200'}`}>
                                  Agent {agentIndex}
                                </span>
                                {modelName && (
                                  <span className="text-xs text-gray-500 block">{modelName}</span>
                                )}
                              </div>
                              {isWinner && <span className="text-sm">👑</span>}
                            </div>
                            <span className={`text-lg font-bold ${isWinner ? 'text-yellow-400' : 'text-gray-300'}`}>
                              {voteCount}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Individual Votes */}
                  <div>
                    <h3 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                      <Vote className="w-4 h-4" />
                      Individual Votes
                    </h3>

                    {votes.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <Vote className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>No votes cast yet</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {votes.map((vote) => (
                          <motion.div
                            key={vote.voterId}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="bg-gray-700/50 rounded-lg border border-gray-600 overflow-hidden"
                          >
                            {/* Vote header */}
                            <div className="flex items-center gap-3 px-4 py-3 bg-gray-700/50">
                              <div className="flex items-center gap-2 text-gray-300">
                                <User className="w-4 h-4 text-blue-400" />
                                <span className="font-medium">Agent {vote.voterIndex}</span>
                                {vote.voterModel && (
                                  <span className="text-xs text-gray-500">({vote.voterModel})</span>
                                )}
                              </div>
                              <ArrowRight className="w-4 h-4 text-amber-500" />
                              <div className="flex items-center gap-2">
                                <span className={`font-medium px-2 py-0.5 rounded ${
                                  vote.targetId === selectedAgent
                                    ? 'bg-yellow-500/30 text-yellow-300'
                                    : 'bg-green-500/20 text-green-300'
                                }`}>
                                  {vote.votedAnswerLabel}
                                </span>
                                {vote.targetId === selectedAgent && <span className="text-sm">👑</span>}
                              </div>
                            </div>

                            {/* Vote details */}
                            <div className="px-4 py-3 border-t border-gray-600 space-y-2">
                              {/* Voted for */}
                              <div className="text-sm">
                                <span className="text-gray-500">Voted for: </span>
                                <span className="text-gray-300">
                                  Agent {vote.targetIndex}
                                  {vote.targetModel && ` (${vote.targetModel})`}
                                </span>
                              </div>

                              {/* Available choices */}
                              <div className="text-sm">
                                <span className="text-gray-500">From choices: </span>
                                <span className="text-gray-400">
                                  {vote.availableAnswers.join(', ')}
                                </span>
                              </div>

                              {/* Reason */}
                              <div className="mt-2 pt-2 border-t border-gray-600/50">
                                <p className="text-sm text-gray-400 italic">{vote.reason}</p>
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : activeTab === 'workspace' ? (
              <>
                {/* Per-Agent Workspace Selector Bar */}
                <div className="px-6 py-3 border-b border-gray-700 bg-gray-800/50 flex items-center gap-4 flex-wrap">
                  {/* Agent Buttons */}
                  <div className="flex items-center gap-2">
                    <Folder className="w-4 h-4 text-blue-400" />
                    <span className="text-sm text-gray-400">Agent:</span>
                    <div className="flex gap-1">
                      {agentOrder.map((agentId) => {
                        const agentData = workspacesByAgent[agentId];
                        const hasWorkspace = agentData?.current || agentData?.historical.length > 0;
                        if (!hasWorkspace) return null;

                        return (
                          <button
                            key={agentId}
                            onClick={() => {
                              setSelectedAgentWorkspace(agentId);
                              setSelectedHistoricalWorkspace(null);
                            }}
                            className={`px-3 py-1 text-sm rounded transition-colors ${
                              selectedAgentWorkspace === agentId
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                            }`}
                          >
                            {agentId}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Answer Version Dropdown */}
                  {selectedAgentWorkspace && (
                    <div className="flex items-center gap-2">
                      <History className="w-4 h-4 text-amber-400" />
                      <span className="text-sm text-gray-400">Version:</span>
                      <div className="relative">
                        <select
                          value={selectedAnswerLabel}
                          onChange={(e) => {
                            const label = e.target.value;
                            setSelectedAnswerLabel(label);
                            setSelectedHistoricalWorkspace(null);

                            if (label === 'current') {
                              // Use current workspace for this agent
                              const ws = workspacesByAgent[selectedAgentWorkspace]?.current;
                              if (ws) fetchWorkspaceFiles(ws);
                            } else {
                              // Find answer workspace by label
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
                          className="appearance-none bg-gray-700 border border-gray-600 rounded-lg px-3 py-1 pr-8 text-sm text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                          <option value="current">Current</option>
                          {answerWorkspaces
                            .filter(w => w.agentId === selectedAgentWorkspace)
                            .map((ws) => (
                              <option key={ws.answerId} value={ws.answerLabel}>
                                {ws.answerLabel}
                              </option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" />
                      </div>
                    </div>
                  )}

                  {/* Refresh Button */}
                  <button
                    onClick={() => { fetchWorkspaces(); fetchAnswerWorkspaces(); }}
                    disabled={isLoadingWorkspaces}
                    className="ml-auto p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-gray-200"
                    title="Refresh workspaces"
                  >
                    <RefreshCw className={`w-4 h-4 ${isLoadingWorkspaces ? 'animate-spin' : ''}`} />
                  </button>
                </div>

                {/* Error Display */}
                {workspaceError && (
                  <div className="px-6 py-2 bg-red-900/30 border-b border-red-700 text-red-300 text-sm">
                    {workspaceError}
                  </div>
                )}

                {/* File Tree */}
                <div className="flex-1 overflow-y-auto custom-scrollbar p-4">
                  {isLoadingWorkspaces || isLoadingFiles ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <RefreshCw className="w-8 h-8 mb-4 animate-spin" />
                      <p>Loading...</p>
                    </div>
                  ) : totalWorkspaces === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <Folder className="w-12 h-12 mb-4 opacity-50" />
                      <p>No workspaces found</p>
                      <p className="text-sm mt-1">Workspaces will appear when agents create files</p>
                    </div>
                  ) : !activeWorkspace ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <Folder className="w-12 h-12 mb-4 opacity-50" />
                      <p>Select an agent to browse their workspace</p>
                    </div>
                  ) : workspaceFiles.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500">
                      <Folder className="w-12 h-12 mb-4 opacity-50" />
                      <p>No files in this workspace</p>
                    </div>
                  ) : (
                    <div>
                      <div className="mb-3 text-sm text-gray-400">
                        {selectedAgentWorkspace} • {activeWorkspace.name} • {workspaceFiles.length} files
                        {selectedHistoricalWorkspace && (
                          <span className="ml-2 text-amber-400">(historical)</span>
                        )}
                      </div>
                      {fileTree.map((node) => (
                        <FileNode key={node.path} node={node} depth={0} onFileClick={handleFileClick} />
                      ))}
                    </div>
                  )}
                </div>

                {/* Workspace Summary */}
                {activeWorkspace && workspaceFiles.length > 0 && (
                  <div className="border-t border-gray-700 px-6 py-3 text-sm text-gray-400 flex items-center justify-between">
                    <span>
                      {workspaceFiles.length} files in {activeWorkspace.name}
                    </span>
                    <span className="text-xs text-gray-500">
                      {activeWorkspace.path}
                    </span>
                  </div>
                )}
              </>
            ) : activeTab === 'timeline' ? (
              <div className="flex-1 overflow-hidden">
                <TimelineView onNodeClick={handleTimelineNodeClick} />
              </div>
            ) : null}

            {/* Footer with stats */}
            <div className="px-6 py-3 border-t border-gray-700 bg-gray-900/50 flex items-center justify-between text-sm">
              <div className="flex items-center gap-4 text-gray-400">
                <span>Total: {answers.length} answers</span>
                <span>Agents: {Object.keys(answersByAgent).length}</span>
              </div>
              {selectedAgent && (
                <div className="flex items-center gap-2 text-yellow-400">
                  <Trophy className="w-4 h-4" />
                  <span>Winner: {selectedAgent}</span>
                </div>
              )}
            </div>
          </motion.div>
        </>
      )}

      {/* File Viewer Modal */}
      <FileViewerModal
        isOpen={fileViewerOpen}
        onClose={() => setFileViewerOpen(false)}
        filePath={selectedFilePath}
        workspacePath={activeWorkspace?.path || ''}
      />
    </AnimatePresence>
  );
}

export default AnswerBrowserModal;
