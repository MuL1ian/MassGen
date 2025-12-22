/**
 * FileWorkspaceBrowser Component
 *
 * Displays per-agent file tree with real-time updates.
 * Shows file operations (create, modify, delete).
 */

import { motion, AnimatePresence } from 'framer-motion';
import { Folder, File, Plus, Edit, Trash2, ChevronDown, ChevronRight } from 'lucide-react';
import { useState, useMemo } from 'react';
import { useAgentStore, selectAgents, selectAgentOrder } from '../stores/agentStore';
import type { FileInfo } from '../types';

interface FileTreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children: FileTreeNode[];
  operation?: 'create' | 'modify' | 'delete';
  contentPreview?: string;
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
          operation: isLast ? file.operation : undefined,
          contentPreview: isLast ? file.contentPreview : undefined,
        };
        current.push(node);
      }

      if (!isLast) {
        node.isDirectory = true;
        current = node.children;
      }
    });
  });

  return root;
}

interface FileNodeProps {
  node: FileTreeNode;
  depth: number;
}

function FileNode({ node, depth }: FileNodeProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const operationIcon = {
    create: <Plus className="w-3 h-3 text-green-500" />,
    modify: <Edit className="w-3 h-3 text-amber-500" />,
    delete: <Trash2 className="w-3 h-3 text-red-500" />,
  };

  const operationBadge = {
    create: 'bg-green-900/50 text-green-300 border-green-700',
    modify: 'bg-amber-900/50 text-amber-300 border-amber-700',
    delete: 'bg-red-900/50 text-red-300 border-red-700',
  };

  return (
    <div>
      <motion.div
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        className={`
          flex items-center gap-1 py-1 px-2 hover:bg-gray-700/30 rounded cursor-pointer
          text-sm text-gray-300
        `}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
        onClick={() => node.isDirectory && setIsExpanded(!isExpanded)}
      >
        {/* Expand/Collapse Icon */}
        {node.isDirectory ? (
          isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )
        ) : (
          <span className="w-4" />
        )}

        {/* File/Folder Icon */}
        {node.isDirectory ? (
          <Folder className="w-4 h-4 text-blue-400" />
        ) : (
          <File className="w-4 h-4 text-gray-400" />
        )}

        {/* Name */}
        <span className={node.operation === 'delete' ? 'line-through opacity-50' : ''}>
          {node.name}
        </span>

        {/* Operation Badge */}
        {node.operation && (
          <span
            className={`
              ml-2 px-1.5 py-0.5 text-xs rounded border flex items-center gap-1
              ${operationBadge[node.operation]}
            `}
          >
            {operationIcon[node.operation]}
            {node.operation}
          </span>
        )}
      </motion.div>

      {/* Children */}
      <AnimatePresence>
        {node.isDirectory && isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {node.children.map((child) => (
              <FileNode key={child.path} node={child} depth={depth + 1} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

interface FileWorkspaceBrowserProps {
  agentId?: string;
}

export function FileWorkspaceBrowser({ agentId }: FileWorkspaceBrowserProps) {
  const agents = useAgentStore(selectAgents);
  const agentOrder = useAgentStore(selectAgentOrder);

  const [selectedAgentId, setSelectedAgentId] = useState<string | undefined>(agentId);

  // Get files for selected agent
  const agent = selectedAgentId ? agents[selectedAgentId] : undefined;
  const files = agent?.files || [];

  // Build file tree
  const fileTree = useMemo(() => buildFileTree(files), [files]);

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header with Agent Selector */}
      <div className="flex items-center justify-between p-3 bg-gray-900/50 border-b border-gray-700">
        <div className="flex items-center gap-2">
          <Folder className="w-5 h-5 text-blue-400" />
          <h3 className="font-medium text-gray-200">Workspace Files</h3>
        </div>

        {!agentId && agentOrder.length > 0 && (
          <select
            value={selectedAgentId || ''}
            onChange={(e) => setSelectedAgentId(e.target.value || undefined)}
            className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm text-gray-200"
          >
            <option value="">Select Agent</option>
            {agentOrder.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* File Tree */}
      <div className="max-h-[300px] overflow-y-auto custom-scrollbar p-2">
        {files.length === 0 ? (
          <div className="text-gray-500 text-sm text-center py-4">
            {selectedAgentId ? 'No files created yet' : 'Select an agent to view files'}
          </div>
        ) : (
          <div>
            {fileTree.map((node) => (
              <FileNode key={node.path} node={node} depth={0} />
            ))}
          </div>
        )}
      </div>

      {/* Summary */}
      {files.length > 0 && (
        <div className="border-t border-gray-700 px-3 py-2 text-xs text-gray-500">
          {files.filter((f) => f.operation === 'create').length} created,{' '}
          {files.filter((f) => f.operation === 'modify').length} modified,{' '}
          {files.filter((f) => f.operation === 'delete').length} deleted
        </div>
      )}
    </div>
  );
}

export default FileWorkspaceBrowser;
