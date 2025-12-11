/**
 * TimelineLegend Component
 *
 * Displays a legend explaining the different node and arrow types
 * used in the timeline visualization.
 */

export function TimelineLegend() {
  return (
    <div className="flex items-center gap-6 px-4 py-2 bg-gray-800/50 border-b border-gray-700">
      {/* Node types */}
      <div className="flex items-center gap-4">
        <span className="text-xs text-gray-500 uppercase tracking-wider">Nodes:</span>

        {/* Answer node */}
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-4 rounded-full bg-gradient-to-br from-blue-500 to-blue-600 border border-blue-400" />
          <span className="text-xs text-gray-400">Answer</span>
        </div>

        {/* Vote node */}
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-4 rounded-full bg-gradient-to-br from-amber-500 to-amber-600 border border-amber-400" />
          <span className="text-xs text-gray-400">Vote</span>
        </div>

        {/* Final node */}
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-4 rounded-full bg-gradient-to-br from-yellow-500 to-yellow-600 border border-yellow-400 shadow-[0_0_8px_rgba(234,179,8,0.4)]" />
          <span className="text-xs text-gray-400">Final</span>
        </div>
      </div>

      {/* Divider */}
      <div className="h-4 w-px bg-gray-600" />

      {/* Arrow types */}
      <div className="flex items-center gap-4">
        <span className="text-xs text-gray-500 uppercase tracking-wider">Arrows:</span>

        {/* Context arrow */}
        <div className="flex items-center gap-1.5">
          <svg width="24" height="12" className="overflow-visible">
            <defs>
              <marker
                id="legend-context-arrow"
                markerWidth="6"
                markerHeight="5"
                refX="5"
                refY="2.5"
                orient="auto"
              >
                <polygon points="0 0, 6 2.5, 0 5" fill="#3B82F6" />
              </marker>
            </defs>
            <line
              x1="0"
              y1="6"
              x2="18"
              y2="6"
              stroke="#3B82F6"
              strokeWidth="2"
              markerEnd="url(#legend-context-arrow)"
            />
          </svg>
          <span className="text-xs text-gray-400">Context</span>
        </div>

        {/* Vote arrow */}
        <div className="flex items-center gap-1.5">
          <svg width="24" height="12" className="overflow-visible">
            <defs>
              <marker
                id="legend-vote-arrow"
                markerWidth="6"
                markerHeight="5"
                refX="5"
                refY="2.5"
                orient="auto"
              >
                <polygon points="0 0, 6 2.5, 0 5" fill="#F59E0B" />
              </marker>
            </defs>
            <line
              x1="0"
              y1="6"
              x2="18"
              y2="6"
              stroke="#F59E0B"
              strokeWidth="2.5"
              strokeDasharray="4 2"
              markerEnd="url(#legend-vote-arrow)"
            />
          </svg>
          <span className="text-xs text-gray-400">Vote</span>
        </div>
      </div>
    </div>
  );
}

export default TimelineLegend;
