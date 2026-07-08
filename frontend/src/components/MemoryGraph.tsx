import { useEffect, useState, useRef, useMemo } from 'react';
import { fetchMemoryGraph } from '../api/memory';
import type { MemoryGraphData, FactNode } from '../api/memory';
import { Maximize, Search, X } from 'lucide-react';

const CATEGORY_COLORS: Record<string, string> = {
  preference: '#c084fc',    // Purple
  habit: '#4ade80',         // Green
  relationship: '#f472b6',  // Pink
  project: '#facc15',       // Yellow
  other: '#a1a1aa',         // Zinc Gray
};

const RELATION_COLORS: Record<string, string> = {
  related_to: '#475569',    // Slate Gray
  contradicts: '#ef4444',   // Red
  clarifies: '#0284c7',     // Sky Blue
  causes: '#f97316',        // Orange
};

interface MemoryGraphProps {
  refreshTrigger: number;
}

export default function MemoryGraph({ refreshTrigger }: MemoryGraphProps) {
  const [graphData, setGraphData] = useState<MemoryGraphData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<FactNode | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<any>(null);
  
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [ForceGraph2D, setForceGraph2D] = useState<any>(null);

  // Dynamic import of react-force-graph-2d to handle ESM/CommonJS interop cleanly
  useEffect(() => {
    import('react-force-graph-2d')
      .then((module) => {
        setForceGraph2D(() => module.default);
      })
      .catch((err) => {
        console.error('Failed to dynamically import react-force-graph-2d:', err);
        setError('Failed to initialize graph visualization engine');
      });
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await fetchMemoryGraph();
        setGraphData(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load graph data');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [refreshTrigger]);

  // Update canvas dimensions on container resize
  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({
          width: Math.max(width, 400),
          height: Math.max(height, 400),
        });
        if (graphRef.current) {
          graphRef.current.d3ReheatSimulation();
        }
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, [ForceGraph2D]);

  const hasAutoFitRun = useRef(false);

  useEffect(() => {
    hasAutoFitRun.current = false;
  }, [graphData]);

  // Adjust D3 force simulation settings for spacious spacing (Obsidian style)
  useEffect(() => {
    if (graphRef.current) {
      // 1. Stronger node repulsion force to prevent clustering & label overlapping
      const charge = graphRef.current.d3Force('charge');
      if (charge) {
        charge.strength(-350);
      }
      
      // 2. Longer default distance between connected nodes
      const link = graphRef.current.d3Force('link');
      if (link) {
        link.distance(120);
      }
      
      // Reheat the physics engine to settle nodes in new spaced coordinates
      graphRef.current.d3ReheatSimulation();
    }
  }, [ForceGraph2D, graphData]);

  const handleEngineStop = () => {
    if (!hasAutoFitRun.current) {
      console.log('onEngineStop: Auto-fitting graph to view');
      if (graphRef.current) {
        graphRef.current.zoomToFit(300);
      }
      hasAutoFitRun.current = true;
    }
  };

  // Compute node degrees (number of connected edges)
  const nodeDegrees = useMemo(() => {
    const degrees: Record<number, number> = {};
    if (graphData) {
      graphData.nodes.forEach((n) => {
        degrees[n.id] = 0;
      });
      (graphData.edges || []).forEach((edge) => {
        const sId = typeof edge.source === 'object' ? (edge.source as any).id : edge.source;
        const tId = typeof edge.target === 'object' ? (edge.target as any).id : edge.target;
        if (degrees[sId] !== undefined) degrees[sId]++;
        if (degrees[tId] !== undefined) degrees[tId]++;
      });
    }
    return degrees;
  }, [graphData]);

  // Compute matching status for node queries
  const isMatched = (node: FactNode) => {
    if (!searchQuery) return true;
    return (node.content || '').toLowerCase().includes(searchQuery.toLowerCase());
  };

  // Find related nodes for the detail side panel
  const relatedFacts = useMemo(() => {
    if (!selectedNode || !graphData) return [];
    const list: { node: FactNode; relation: string }[] = [];
    (graphData.edges || []).forEach((edge) => {
      const sId = typeof edge.source === 'object' ? (edge.source as any).id : edge.source;
      const tId = typeof edge.target === 'object' ? (edge.target as any).id : edge.target;

      if (sId === selectedNode.id) {
        const targetNode = graphData.nodes.find((n) => n.id === tId);
        if (targetNode) {
          list.push({ node: targetNode, relation: edge.relation_type });
        }
      } else if (tId === selectedNode.id) {
        const sourceNode = graphData.nodes.find((n) => n.id === sId);
        if (sourceNode) {
          list.push({ node: sourceNode, relation: edge.relation_type });
        }
      }
    });
    return list;
  }, [selectedNode, graphData]);

  const handleFitView = () => {
    console.log('handleFitView (zoomToFit) triggered');
    if (graphRef.current) {
      graphRef.current.zoomToFit(400);
    }
  };

  if (loading || !ForceGraph2D) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-zinc-950 text-zinc-200">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-purple-500 border-t-transparent"></div>
          <span className="text-sm font-medium">Загрузка карты памяти...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-zinc-950 text-red-400">
        <div className="rounded-lg border border-red-950 bg-red-950/20 p-6 text-center max-w-md">
          <p className="font-semibold mb-2">Ошибка при загрузке данных</p>
          <p className="text-xs text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  const nodesCount = graphData?.nodes.length || 0;
  if (nodesCount === 0) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-zinc-950 text-zinc-400">
        <div className="text-center p-6 border border-dashed border-zinc-800 rounded-lg max-w-sm">
          <svg
            className="mx-auto h-12 w-12 text-zinc-600 mb-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <p className="font-medium text-zinc-300">Пока нет утвержденных фактов</p>
          <p className="text-xs text-zinc-500 mt-1">
            Факты появляются здесь после подтверждения на бэкенде.
          </p>
        </div>
      </div>
    );
  }

  const GraphComponent = ForceGraph2D;

  const formattedData = graphData
    ? {
        nodes: graphData.nodes,
        links: (graphData.edges || []).map((edge) => ({
          source: edge.source,
          target: edge.target,
          relation_type: edge.relation_type,
        })),
      }
    : { nodes: [], links: [] };

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full bg-[#141423] overflow-hidden select-none"
      style={{
        backgroundImage: 'radial-gradient(circle, #252538 1px, transparent 1px)',
        backgroundSize: '18px 18px',
      }}
    >
      {/* Floating Controls (Top-Left) */}
      <div className="absolute top-6 left-6 z-10 flex flex-col gap-2 pointer-events-auto">
        <button
          onClick={handleFitView}
          className="p-2 bg-zinc-900/90 border border-zinc-800/80 rounded-xl text-zinc-300 hover:text-zinc-100 hover:bg-zinc-800 transition-all font-semibold text-[10px] shadow-lg backdrop-blur-md flex items-center gap-1.5 cursor-pointer"
          title="Вписать в экран"
        >
          <Maximize className="h-3.5 w-3.5" /> Вписать в экран
        </button>
      </div>

      {/* Floating Search Bar (Top-Center) */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2 z-10 w-80 pointer-events-auto">
        <div className="relative">
          <input
            type="text"
            placeholder="Поиск по фактам..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-zinc-900/90 border border-zinc-800/80 rounded-xl px-4 py-2 pl-10 text-xs text-zinc-100 focus:outline-none focus:border-purple-500/80 shadow-lg backdrop-blur-md transition-all font-sans"
          />
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-200 text-[10px] font-semibold cursor-pointer"
            >
              Очистить
            </button>
          )}
        </div>
      </div>

      {/* 2D Canvas Graph */}
      <GraphComponent
        ref={graphRef}
        graphData={formattedData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="transparent"
        
        // Node physics parameters
        nodeRelSize={6}
        nodeVal={(node: any) => 4 + (nodeDegrees[node.id] || 0) * 2}
        
        // Custom rendering for Obsidian style
        nodeCanvasObject={(node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
          const degree = nodeDegrees[node.id] || 0;
          const size = 4 + degree * 1.5;
          const category = node.category || 'other';
          const color = CATEGORY_COLORS[category] || '#a1a1aa';
          
          const x = typeof node.x === 'number' ? node.x : 0;
          const y = typeof node.y === 'number' ? node.y : 0;
          
          const matched = isMatched(node);

          // Render with transparency if doesn't match search
          ctx.save();
          if (!matched) {
            ctx.globalAlpha = 0.15;
          }

          // 1. Draw outer glow (only for matched nodes)
          if (matched) {
            ctx.beginPath();
            ctx.arc(x, y, size + 2, 0, 2 * Math.PI, false);
            ctx.fillStyle = `${color}25`; // Faint category color glow
            ctx.fill();
          }

          // 2. Draw node circle
          ctx.beginPath();
          ctx.arc(x, y, size, 0, 2 * Math.PI, false);
          ctx.fillStyle = color;
          ctx.fill();

          // 3. Draw outline border
          if (matched && searchQuery && (node.content || '').toLowerCase().includes(searchQuery.toLowerCase())) {
            // White highlight outline for matched queries
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1.8;
          } else {
            ctx.strokeStyle = '#0e0e1a';
            ctx.lineWidth = 1.2;
          }
          ctx.stroke();

          // 4. Draw labels (always on Obsidian style, but smaller when zoomed out)
          const content = node.content || '';
          if (globalScale > 0.4 && content) {
            const maxLen = 22;
            const label = content.length > maxLen ? content.substring(0, maxLen - 3) + '...' : content;
            const fontSize = Math.max(8.5 / globalScale, 5);
            ctx.font = `${fontSize}px system-ui, -apple-system, sans-serif`;
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillStyle = '#e4e4e7'; // zinc-200
            
            // Text shadow
            ctx.shadowColor = '#0e0e1a';
            ctx.shadowBlur = 4;
            
            ctx.fillText(label, x, y + size + 4.5);
          }
          
          ctx.restore();
        }}
        nodeCanvasObjectMode={() => 'replace'}

        // Built-in Link Customization
        linkColor={(link: any) => {
          const sId = typeof link.source === 'object' ? link.source.id : link.source;
          const tId = typeof link.target === 'object' ? link.target.id : link.target;
          
          const sNode = graphData?.nodes.find(n => n.id === sId);
          const tNode = graphData?.nodes.find(n => n.id === tId);
          
          const matched = (!sNode || isMatched(sNode)) && (!tNode || isMatched(tNode));
          
          const baseColor = RELATION_COLORS[link.relation_type] || '#475569';
          return matched ? baseColor : `${baseColor}15`; // Faded if not matched
        }}
        linkWidth={(link: any) => link.relation_type === 'clarifies' ? 1 : 2}
        linkLineDash={(link: any) => link.relation_type === 'contradicts' ? [4, 4] : undefined}
        
        // Directional arrows for causes
        linkDirectionalArrowLength={(link: any) => link.relation_type === 'causes' ? 6 : 0}
        linkDirectionalArrowRelPos={1}
        linkDirectionalArrowColor={(link: any) => RELATION_COLORS[link.relation_type] || '#475569'}

        // Event Handlers
        onNodeClick={(node: any) => {
          setSelectedNode(node);
        }}
        onEngineStop={handleEngineStop}
      />

      {/* Obsidian Detail Side Panel (Right side slide-out) */}
      {selectedNode && (
        <div className="absolute top-0 right-0 h-full w-80 bg-zinc-950/90 border-l border-zinc-900 p-6 shadow-2xl backdrop-blur-md z-20 flex flex-col gap-6 animate-in slide-in-from-right duration-300 font-sans pointer-events-auto">
          {/* Close Button & Badge */}
          <div className="flex items-center justify-between">
            <span
              className="inline-flex items-center rounded-md px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider border"
              style={{
                backgroundColor: `${CATEGORY_COLORS[selectedNode.category || 'other']}20`,
                color: CATEGORY_COLORS[selectedNode.category || 'other'],
                borderColor: `${CATEGORY_COLORS[selectedNode.category || 'other']}40`,
              }}
            >
              {selectedNode.category || 'other'}
            </span>
            <button
              onClick={() => setSelectedNode(null)}
              className="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-900 hover:text-zinc-300 transition-colors cursor-pointer"
            >
              <X className="h-4.5 w-4.5" />
            </button>
          </div>

          {/* Fact Content */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] text-zinc-500 font-semibold tracking-wider font-mono">СОДЕРЖАНИЕ ФАКТА</span>
            <h3 className="text-sm font-bold text-zinc-200 leading-relaxed">
              {selectedNode.content}
            </h3>
          </div>

          {/* AI Confidence Meter */}
          <div className="flex flex-col gap-2">
            <span className="text-[10px] text-zinc-500 font-semibold tracking-wider font-mono">ДОСТОВЕРНОСТЬ ИИ</span>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-zinc-900 rounded-full h-1.5 overflow-hidden border border-zinc-800/80">
                <div
                  className="h-1.5 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-500"
                  style={{ width: `${Math.round((selectedNode.confidence || 0.8) * 100)}%` }}
                ></div>
              </div>
              <span className="text-xs font-semibold text-purple-400 font-mono">
                {Math.round((selectedNode.confidence || 0.8) * 100)}%
              </span>
            </div>
          </div>

          {/* Related Facts List */}
          <div className="flex-1 flex flex-col gap-3 overflow-hidden">
            <span className="text-[10px] text-zinc-500 font-semibold tracking-wider font-mono">
              СВЯЗАННЫЕ ФАКТЫ ({relatedFacts.length})
            </span>
            <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-3">
              {relatedFacts.length === 0 ? (
                <div className="text-xs text-zinc-600 italic py-2">Связи отсутствуют</div>
              ) : (
                relatedFacts.map((rf) => (
                  <div
                    key={rf.node.id}
                    onClick={() => {
                      setSelectedNode(rf.node);
                      // Center view on node
                      if (graphRef.current && typeof rf.node.x === 'number' && typeof rf.node.y === 'number') {
                        graphRef.current.centerAt(rf.node.x, rf.node.y, 300);
                      }
                    }}
                    className="p-3 bg-zinc-900/40 border border-zinc-900 hover:border-zinc-800/80 hover:bg-zinc-900/80 rounded-xl flex flex-col gap-2 cursor-pointer transition-all"
                  >
                    <div className="flex items-center justify-between text-[9px]">
                      <span className="font-semibold text-zinc-500 uppercase tracking-wider font-mono">
                        {rf.relation === 'related_to' ? 'связан с' : rf.relation}
                      </span>
                      <span
                        className="px-1.5 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider"
                        style={{
                          backgroundColor: `${CATEGORY_COLORS[rf.node.category || 'other']}20`,
                          color: CATEGORY_COLORS[rf.node.category || 'other'],
                        }}
                      >
                        {rf.node.category}
                      </span>
                    </div>
                    <p className="text-xs font-semibold text-zinc-300 leading-snug line-clamp-2">
                      {rf.node.content}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>
          
          <div className="text-[9px] text-zinc-600 font-mono border-t border-zinc-900 pt-3">
            ID: {selectedNode.id}
          </div>
        </div>
      )}
    </div>
  );
}
