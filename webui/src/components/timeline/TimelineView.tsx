/**
 * TimelineView Component
 *
 * Vertical swimlane visualization showing the coordination flow.
 * Each agent has a column, with nodes for answers/votes/final answer
 * and arrows showing context dependencies.
 */

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Loader2, GitBranch, CheckCircle2 } from 'lucide-react';
import { useAgentStore, selectIsComplete } from '../../stores/agentStore';
import type { TimelineNode as TimelineNodeType, TimelineData } from '../../types';
import { TimelineNode } from './TimelineNode';
import { TimelineArrow } from './TimelineArrow';
import { TimelineLegend } from './TimelineLegend';

interface TimelineViewProps {
  onNodeClick?: (node: TimelineNodeType) => void;
}

// Node dimensions for layout calculations
const NODE_SIZE = 40;
const NODE_GAP_Y = 80;
const COLUMN_WIDTH = 150;
const HEADER_HEIGHT = 60;
const PADDING = 40;

export function TimelineView({ onNodeClick }: TimelineViewProps) {
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const sessionId = useAgentStore((state) => state.sessionId);
  const isComplete = useAgentStore(selectIsComplete);

  // Check if timeline has a final node
  const hasFinalNode = useMemo(() => {
    return timelineData?.nodes.some(n => n.type === 'final') ?? false;
  }, [timelineData]);

  // Fetch timeline data
  const fetchTimeline = useCallback(async () => {
    if (!sessionId) {
      setIsLoading(false);
      return;
    }

    // Only show loading on first fetch
    if (!timelineData) {
      setIsLoading(true);
    }
    setError(null);

    try {
      const response = await fetch(`/api/sessions/${sessionId}/timeline`);
      if (!response.ok) {
        throw new Error('Failed to fetch timeline');
      }
      const data: TimelineData = await response.json();
      setTimelineData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timeline');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, timelineData]);

  // Initial fetch and auto-refresh every 3 seconds
  useEffect(() => {
    fetchTimeline();
    const interval = setInterval(fetchTimeline, 3000);
    return () => clearInterval(interval);
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Calculate node positions based on agent and timestamp
  const nodePositions = useMemo(() => {
    if (!timelineData || timelineData.nodes.length === 0) {
      return new Map<string, { x: number; y: number }>();
    }

    const positions = new Map<string, { x: number; y: number }>();
    const { nodes, agents } = timelineData;

    // Group nodes by agent
    const nodesByAgent = new Map<string, TimelineNodeType[]>();
    agents.forEach(agentId => nodesByAgent.set(agentId, []));

    nodes.forEach(node => {
      const agentNodes = nodesByAgent.get(node.agentId);
      if (agentNodes) {
        agentNodes.push(node);
      }
    });

    // Calculate Y position based on order within agent column
    agents.forEach((agentId, agentIndex) => {
      const agentNodes = nodesByAgent.get(agentId) || [];
      // Sort by timestamp
      agentNodes.sort((a, b) => a.timestamp - b.timestamp);

      agentNodes.forEach((node, nodeIndex) => {
        const x = PADDING + agentIndex * COLUMN_WIDTH + COLUMN_WIDTH / 2;
        const y = HEADER_HEIGHT + PADDING + nodeIndex * NODE_GAP_Y;
        positions.set(node.id, { x, y });
      });
    });

    return positions;
  }, [timelineData]);

  // Calculate SVG dimensions
  const svgDimensions = useMemo(() => {
    if (!timelineData) {
      return { width: 600, height: 400 };
    }

    const width = Math.max(600, PADDING * 2 + timelineData.agents.length * COLUMN_WIDTH);

    // Find max Y position
    let maxY = HEADER_HEIGHT + PADDING;
    nodePositions.forEach(pos => {
      maxY = Math.max(maxY, pos.y);
    });

    const height = Math.max(400, maxY + NODE_GAP_Y + PADDING);

    return { width, height };
  }, [timelineData, nodePositions]);

  // Render loading state
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <Loader2 className="w-8 h-8 animate-spin mb-3" />
        <p>Loading timeline...</p>
      </div>
    );
  }

  // Render error state (will auto-retry)
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-red-400">
        <GitBranch className="w-12 h-12 mb-3 opacity-50" />
        <p className="font-medium">Failed to load timeline</p>
        <p className="text-sm text-gray-500 mt-1">{error}</p>
        <p className="text-xs text-gray-600 mt-2">Retrying automatically...</p>
      </div>
    );
  }

  // Render empty state
  if (!sessionId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <GitBranch className="w-12 h-12 mb-3 opacity-50" />
        <p>No active session</p>
        <p className="text-sm text-gray-600 mt-1">
          Start a coordination to see the timeline
        </p>
      </div>
    );
  }

  if (!timelineData || timelineData.nodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-500">
        <GitBranch className="w-12 h-12 mb-3 opacity-50" />
        <p>No timeline data yet</p>
        <p className="text-sm text-gray-600 mt-1">
          Timeline will populate as agents submit answers and votes
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Legend */}
      <TimelineLegend />

      {/* Completion Banner */}
      {(isComplete || hasFinalNode) && (
        <div className="mx-4 mb-2 px-4 py-3 bg-gradient-to-r from-green-900/50 to-emerald-900/50 border border-green-600/50 rounded-lg flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-400 shrink-0" />
          <div>
            <p className="text-green-300 font-medium text-sm">Coordination Complete</p>
            <p className="text-green-400/70 text-xs">Final answer has been selected</p>
          </div>
        </div>
      )}

      {/* Timeline Container */}
      <div className="flex-1 overflow-auto p-4">
        <svg
          width={svgDimensions.width}
          height={svgDimensions.height}
          className="min-w-full"
        >
          {/* Background grid lines for swimlanes */}
          {timelineData.agents.map((_, index) => (
            <line
              key={`grid-${index}`}
              x1={PADDING + index * COLUMN_WIDTH + COLUMN_WIDTH / 2}
              y1={HEADER_HEIGHT}
              x2={PADDING + index * COLUMN_WIDTH + COLUMN_WIDTH / 2}
              y2={svgDimensions.height - PADDING}
              stroke="rgba(75, 85, 99, 0.3)"
              strokeWidth="1"
              strokeDasharray="4 4"
            />
          ))}

          {/* Agent column headers */}
          {timelineData.agents.map((agentId, index) => {
            const x = PADDING + index * COLUMN_WIDTH + COLUMN_WIDTH / 2;
            const agentIndex = index + 1;
            return (
              <g key={`header-${agentId}`}>
                <rect
                  x={x - 50}
                  y={10}
                  width={100}
                  height={36}
                  rx={8}
                  fill="rgba(59, 130, 246, 0.2)"
                  stroke="rgba(59, 130, 246, 0.5)"
                  strokeWidth="1"
                />
                <text
                  x={x}
                  y={32}
                  textAnchor="middle"
                  className="fill-blue-400 text-sm font-medium"
                >
                  Agent {agentIndex}
                </text>
              </g>
            );
          })}

          {/* Draw context arrows (behind nodes) */}
          {/* Context arrows show which ANSWERS provided context to other nodes */}
          {/* Votes never provide context, so we skip arrows FROM vote nodes */}
          {/* We also skip arrows TO vote nodes - votes have contextSources but those */}
          {/* represent "available options", not actual context dependency */}
          {timelineData.nodes
            .filter(node => node.type !== 'vote') // Only draw context arrows TO non-vote nodes
            .map(node => {
              const nodePos = nodePositions.get(node.id);
              if (!nodePos) return null;

              // Draw arrows from context sources
              return node.contextSources.map(sourceLabel => {
                // Find the source node by label
                const sourceNode = timelineData.nodes.find(n => n.label === sourceLabel);
                // Skip if source doesn't exist or is a vote (votes don't provide context)
                if (!sourceNode || sourceNode.type === 'vote') return null;

                const sourcePos = nodePositions.get(sourceNode.id);
                if (!sourcePos) return null;

                return (
                  <TimelineArrow
                    key={`arrow-${sourceNode.id}-${node.id}`}
                    from={sourcePos}
                    to={nodePos}
                    type="context"
                  />
                );
              });
            })}

          {/* Draw vote arrows (showing which answer received the vote) */}
          {timelineData.nodes
            .filter(n => n.type === 'vote' && n.votedFor)
            .map(node => {
              const nodePos = nodePositions.get(node.id);
              if (!nodePos || !node.votedFor) return null;

              // Find the voted-for agent's latest answer node
              const targetAnswer = timelineData.nodes.find(
                n => n.type === 'answer' && n.agentId === node.votedFor
              );

              if (!targetAnswer) {
                // Fallback: point to the agent's column if no answer node found
                const targetAgentIndex = timelineData.agents.indexOf(node.votedFor);
                if (targetAgentIndex === -1) return null;
                const targetX = PADDING + targetAgentIndex * COLUMN_WIDTH + COLUMN_WIDTH / 2;
                return (
                  <TimelineArrow
                    key={`vote-arrow-${node.id}`}
                    from={nodePos}
                    to={{ x: targetX, y: nodePos.y - 40 }}
                    type="vote"
                  />
                );
              }

              const targetPos = nodePositions.get(targetAnswer.id);
              if (!targetPos) return null;

              return (
                <TimelineArrow
                  key={`vote-arrow-${node.id}`}
                  from={nodePos}
                  to={targetPos}
                  type="vote"
                />
              );
            })}

          {/* Draw nodes */}
          {timelineData.nodes.map(node => {
            const pos = nodePositions.get(node.id);
            if (!pos) return null;

            // Final nodes are larger for emphasis
            const nodeSize = node.type === 'final' ? NODE_SIZE * 1.4 : NODE_SIZE;

            return (
              <TimelineNode
                key={node.id}
                node={node}
                x={pos.x}
                y={pos.y}
                size={nodeSize}
                onClick={() => onNodeClick?.(node)}
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
}

export default TimelineView;
