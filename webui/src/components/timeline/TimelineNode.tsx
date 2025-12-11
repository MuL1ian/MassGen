/**
 * TimelineNode Component
 *
 * Renders a single node on the timeline (answer, vote, or final).
 * Color-coded by type with hover effects and tooltips.
 */

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import type { TimelineNode as TimelineNodeType } from '../../types';

interface TimelineNodeProps {
  node: TimelineNodeType;
  x: number;
  y: number;
  size: number;
  onClick?: () => void;
}

// Track which nodes have been animated to prevent re-animation
const animatedNodes = new Set<string>();

// Node colors by type
const nodeColors = {
  answer: {
    fill: 'url(#answerGradient)',
    stroke: '#60A5FA',
    glow: 'rgba(59, 130, 246, 0.4)',
  },
  vote: {
    fill: 'url(#voteGradient)',
    stroke: '#FBBF24',
    glow: 'rgba(245, 158, 11, 0.4)',
  },
  final: {
    fill: 'url(#finalGradient)',
    stroke: '#FDE047',
    glow: 'rgba(234, 179, 8, 0.5)',
  },
};

export function TimelineNode({ node, x, y, size, onClick }: TimelineNodeProps) {
  const [isHovered, setIsHovered] = useState(false);
  const colors = nodeColors[node.type];
  const radius = size / 2;

  // Only animate nodes that haven't been seen before
  const shouldAnimate = !animatedNodes.has(node.id);
  useEffect(() => {
    animatedNodes.add(node.id);
  }, [node.id]);

  // Format timestamp for tooltip
  const formatTime = (timestamp: number) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  return (
    <g
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
      style={{ cursor: onClick ? 'pointer' : 'default' }}
    >
      {/* Gradient definitions */}
      <defs>
        <linearGradient id="answerGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#3B82F6" />
          <stop offset="100%" stopColor="#2563EB" />
        </linearGradient>
        <linearGradient id="voteGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#F59E0B" />
          <stop offset="100%" stopColor="#D97706" />
        </linearGradient>
        <linearGradient id="finalGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#EAB308" />
          <stop offset="100%" stopColor="#CA8A04" />
        </linearGradient>
        <filter id={`glow-${node.id}`}>
          <feGaussianBlur stdDeviation="3" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Glow effect on hover */}
      {isHovered && (
        <circle
          cx={x}
          cy={y}
          r={radius + 6}
          fill={colors.glow}
          opacity={0.6}
        />
      )}

      {/* Main node circle */}
      <motion.circle
        cx={x}
        cy={y}
        r={radius}
        fill={colors.fill}
        stroke={colors.stroke}
        strokeWidth={2}
        initial={shouldAnimate ? { scale: 0 } : false}
        animate={{ scale: isHovered ? 1.15 : 1 }}
        transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        filter={node.type === 'final' ? `url(#glow-${node.id})` : undefined}
      />

      {/* Icon inside node */}
      <text
        x={x}
        y={y + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        className="fill-white text-xs font-bold select-none pointer-events-none"
      >
        {node.type === 'answer' && 'A'}
        {node.type === 'vote' && 'V'}
        {node.type === 'final' && '★'}
      </text>

      {/* Label below node */}
      <text
        x={x}
        y={y + radius + 14}
        textAnchor="middle"
        className="fill-gray-400 text-xs font-medium select-none pointer-events-none"
      >
        {node.label}
      </text>

      {/* Tooltip on hover */}
      {isHovered && (
        <g>
          {/* Calculate tooltip dimensions based on content */}
          {(() => {
            const tooltipX = x + radius + 10;
            const tooltipY = y - 40;
            const lineHeight = 14;
            let currentY = tooltipY + 16;

            // Calculate height based on content
            let contentLines = 2; // label + timestamp
            if (node.type === 'vote' && node.votedFor) contentLines += 1;
            if (node.type === 'vote' && node.contextSources.length > 0) {
              contentLines += 1; // "Options:" header
              contentLines += node.contextSources.length; // Each option on its own line
            } else if (node.contextSources.length > 0) {
              contentLines += 1; // "Context:" header
              contentLines += Math.min(node.contextSources.length, 4); // Limit displayed
            }

            const tooltipHeight = 20 + contentLines * lineHeight;
            const tooltipWidth = 150;

            return (
              <>
                <rect
                  x={tooltipX}
                  y={tooltipY}
                  width={tooltipWidth}
                  height={tooltipHeight}
                  rx={6}
                  fill="rgba(31, 41, 55, 0.95)"
                  stroke="rgba(75, 85, 99, 0.5)"
                  strokeWidth={1}
                />
                {/* Label */}
                <text
                  x={tooltipX + 8}
                  y={currentY}
                  className="fill-gray-200 text-xs font-medium"
                >
                  {node.label}
                </text>
                {/* Timestamp */}
                <text
                  x={tooltipX + 8}
                  y={currentY += lineHeight}
                  className="fill-gray-400 text-xs"
                >
                  {formatTime(node.timestamp)}
                </text>
                {/* Vote target (for vote nodes) */}
                {node.type === 'vote' && node.votedFor && (
                  <text
                    x={tooltipX + 8}
                    y={currentY += lineHeight}
                    className="fill-amber-400 text-xs font-medium"
                  >
                    Voted: {node.votedFor}
                  </text>
                )}
                {/* Vote options (context sources for vote nodes) */}
                {node.type === 'vote' && node.contextSources.length > 0 && (
                  <>
                    <text
                      x={tooltipX + 8}
                      y={currentY += lineHeight}
                      className="fill-gray-500 text-xs"
                    >
                      Options:
                    </text>
                    {node.contextSources.map((source) => {
                      const isSelected = source === node.votedFor || source.includes(node.votedFor || '');
                      return (
                        <text
                          key={source}
                          x={tooltipX + 12}
                          y={currentY += lineHeight}
                          className={isSelected ? 'fill-amber-300 text-xs font-medium' : 'fill-gray-400 text-xs'}
                        >
                          {isSelected ? '● ' : '○ '}{source}
                        </text>
                      );
                    })}
                  </>
                )}
                {/* Context sources (for non-vote nodes) */}
                {node.type !== 'vote' && node.contextSources.length > 0 && (
                  <>
                    <text
                      x={tooltipX + 8}
                      y={currentY += lineHeight}
                      className="fill-gray-500 text-xs"
                    >
                      Context:
                    </text>
                    {node.contextSources.slice(0, 4).map((source) => (
                      <text
                        key={source}
                        x={tooltipX + 12}
                        y={currentY += lineHeight}
                        className="fill-blue-400 text-xs"
                      >
                        ← {source}
                      </text>
                    ))}
                    {node.contextSources.length > 4 && (
                      <text
                        x={tooltipX + 12}
                        y={currentY += lineHeight}
                        className="fill-gray-500 text-xs"
                      >
                        +{node.contextSources.length - 4} more...
                      </text>
                    )}
                  </>
                )}
              </>
            );
          })()}
        </g>
      )}
    </g>
  );
}

export default TimelineNode;
