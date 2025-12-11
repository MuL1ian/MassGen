/**
 * TimelineArrow Component
 *
 * Renders curved arrows connecting timeline nodes.
 * Different styles for context dependencies vs vote arrows.
 */

import { useMemo } from 'react';

interface Point {
  x: number;
  y: number;
}

interface TimelineArrowProps {
  from: Point;
  to: Point;
  type: 'context' | 'vote';
}

// Arrow colors
const arrowColors = {
  context: {
    stroke: '#3B82F6',
    fill: '#3B82F6',
  },
  vote: {
    stroke: '#F59E0B',
    fill: '#F59E0B',
  },
};

export function TimelineArrow({ from, to, type }: TimelineArrowProps) {
  const colors = arrowColors[type];

  // Calculate curved path using quadratic bezier
  const path = useMemo(() => {
    // Control point for curve
    const midX = (from.x + to.x) / 2;
    const midY = (from.y + to.y) / 2;

    // Curve direction based on relative positions
    const dx = to.x - from.x;
    const dy = to.y - from.y;

    // Offset control point perpendicular to the line
    const curveOffset = Math.min(50, Math.abs(dx) * 0.3);
    const controlX = midX;
    const controlY = dy > 0 ? midY - curveOffset : midY + curveOffset;

    // If same column, curve to the side
    if (Math.abs(dx) < 10) {
      const sideOffset = 40;
      return `M ${from.x} ${from.y} Q ${from.x + sideOffset} ${midY} ${to.x} ${to.y}`;
    }

    return `M ${from.x} ${from.y} Q ${controlX} ${controlY} ${to.x} ${to.y}`;
  }, [from, to]);

  // Unique ID for this arrow's marker
  const markerId = `arrowhead-${type}-${from.x}-${from.y}-${to.x}-${to.y}`;

  return (
    <g>
      {/* Arrowhead marker definition */}
      <defs>
        <marker
          id={markerId}
          markerWidth="10"
          markerHeight="7"
          refX="9"
          refY="3.5"
          orient="auto"
        >
          <polygon
            points="0 0, 10 3.5, 0 7"
            fill={colors.fill}
          />
        </marker>
      </defs>

      {/* Arrow path */}
      <path
        d={path}
        fill="none"
        stroke={colors.stroke}
        strokeWidth={type === 'vote' ? 2.5 : 2}
        strokeOpacity={0.6}
        strokeDasharray={type === 'context' ? 'none' : '5 3'}
        markerEnd={`url(#${markerId})`}
      />
    </g>
  );
}

export default TimelineArrow;
