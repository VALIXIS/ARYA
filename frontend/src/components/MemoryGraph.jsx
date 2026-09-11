import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import {
  Network,
  Search,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Copy,
  Check,
  X,
  ArrowUpRight,
  Trash2,
  CheckCircle2,
  MessageSquare,
  Power,
  Lock,
  Wifi,
  Smartphone,
  Laptop,
  Tv,
  Sparkles,
  RefreshCw,
} from 'lucide-react';

const CATEGORY_STYLES = {
  Core: { color: '#00f2fe', bg: 'rgba(0, 242, 254, 0.15)', border: '#00f2fe', glow: 'rgba(0, 242, 254, 0.6)' },
  Projects: { color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.15)', border: '#38bdf8', glow: 'rgba(56, 189, 248, 0.5)' },
  'Technical Identity': { color: '#818cf8', bg: 'rgba(129, 140, 248, 0.15)', border: '#818cf8', glow: 'rgba(129, 140, 248, 0.5)' },
  Ecosystem: { color: '#c084fc', bg: 'rgba(192, 132, 252, 0.15)', border: '#c084fc', glow: 'rgba(192, 132, 252, 0.5)' },
  Goals: { color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)', border: '#f59e0b', glow: 'rgba(245, 158, 11, 0.5)' },
  Tasks: { color: '#fb923c', bg: 'rgba(251, 146, 60, 0.15)', border: '#fb923c', glow: 'rgba(251, 146, 60, 0.5)' },
  Devices: { color: '#2dd4bf', bg: 'rgba(45, 212, 191, 0.15)', border: '#2dd4bf', glow: 'rgba(45, 212, 191, 0.5)' },
  Identity: { color: '#fbbf24', bg: 'rgba(251, 191, 36, 0.15)', border: '#fbbf24', glow: 'rgba(251, 191, 36, 0.5)' },
  Education: { color: '#34d399', bg: 'rgba(52, 211, 153, 0.15)', border: '#34d399', glow: 'rgba(52, 211, 153, 0.5)' },
  Preferences: { color: '#f472b6', bg: 'rgba(244, 114, 182, 0.15)', border: '#f472b6', glow: 'rgba(244, 114, 182, 0.5)' },
  Interests: { color: '#fb7185', bg: 'rgba(251, 113, 133, 0.15)', border: '#fb7185', glow: 'rgba(251, 113, 133, 0.5)' },
  default: { color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)', border: '#94a3b8', glow: 'rgba(148, 163, 184, 0.4)' },
};

function getCategoryStyle(category) {
  return CATEGORY_STYLES[category] || CATEGORY_STYLES.default;
}

export default function MemoryGraph({ onSelectTab, onSendMessage }) {
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], total_memories: 0, total_goals: 0, total_tasks: 0, total_devices: 0 });
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  const containerRef = useRef(null);
  const canvasRef = useRef(null);

  // Fetch memory graph data from backend API
  const fetchGraphData = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/memories/graph');
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
      }
    } catch (err) {
      console.error('Failed to fetch memory graph data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGraphData();
  }, [fetchGraphData]);

  // Compute categories and node counts dynamically
  const { categories, categoryCounts } = useMemo(() => {
    const counts = { ALL: (graphData.nodes || []).filter((n) => n.type !== 'core' && n.type !== 'category').length };
    const catSet = new Set(['ALL']);

    (graphData.nodes || []).forEach((n) => {
      if (n.type === 'category') {
        catSet.add(n.label);
      } else if (n.category) {
        counts[n.category] = (counts[n.category] || 0) + 1;
        catSet.add(n.category);
      }
    });

    return {
      categories: Array.from(catSet),
      categoryCounts: counts,
    };
  }, [graphData.nodes]);

  // Camera Transform (Pan & Zoom)
  const transformRef = useRef({ x: 0, y: 0, k: 1 });
  const isDraggingCanvasRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  // Node Dragging state
  const draggedNodeRef = useRef(null);

  // Physics Nodes Ref
  const nodesRef = useRef([]);
  const edgesRef = useRef([]);
  const animFrameRef = useRef(null);
  const pulsesRef = useRef([]);

  // Initial radial constellation layout generator
  const initConstellation = useCallback((rawNodes, rawEdges, width, height) => {
    const centerX = width / 2;
    const centerY = height / 2;

    const coreNode = rawNodes.find((n) => n.type === 'core') || { id: 'root_arya', label: 'ARYA Brain', type: 'core', category: 'Core' };
    const categoryNodes = rawNodes.filter((n) => n.type === 'category');
    const leafNodes = rawNodes.filter((n) => n.type !== 'core' && n.type !== 'category');

    const childrenByCat = {};
    categoryNodes.forEach((c) => {
      childrenByCat[c.label] = [];
    });
    leafNodes.forEach((leaf) => {
      if (!childrenByCat[leaf.category]) {
        childrenByCat[leaf.category] = [];
      }
      childrenByCat[leaf.category].push(leaf);
    });

    const simNodes = [];

    // 1. Core Node in Center
    simNodes.push({
      ...coreNode,
      x: centerX,
      y: centerY,
      vx: 0,
      vy: 0,
      radius: 24,
      isCore: true,
      color: '#00f2fe',
    });

    // 2. Distribute Category Nodes radially with wide separation
    const catCount = categoryNodes.length || 1;
    const catRadius = Math.min(width, height) * 0.32;

    categoryNodes.forEach((cat, i) => {
      const catAngle = (i / catCount) * Math.PI * 2 - Math.PI / 2;
      const catX = centerX + Math.cos(catAngle) * catRadius;
      const catY = centerY + Math.sin(catAngle) * catRadius;
      const style = getCategoryStyle(cat.label);

      simNodes.push({
        ...cat,
        x: catX,
        y: catY,
        baseX: catX,
        baseY: catY,
        angle: catAngle,
        vx: 0,
        vy: 0,
        radius: 14,
        isCategory: true,
        color: style.color,
        bg: style.bg,
        glow: style.glow,
      });

      // 3. Position leaf children in an outward fan/arc around their category parent
      const children = childrenByCat[cat.label] || [];
      const numChildren = children.length;

      children.forEach((child, j) => {
        let childAngle = catAngle;
        let childDist = 70;

        if (numChildren === 1) {
          childAngle = catAngle;
          childDist = 74;
        } else {
          const spread = Math.min(Math.PI * 0.7, 0.35 * numChildren);
          const step = numChildren > 1 ? spread / (numChildren - 1) : 0;
          childAngle = catAngle - spread / 2 + j * step;
          childDist = 65 + (j % 3) * 22;
        }

        const childX = catX + Math.cos(childAngle) * childDist;
        const childY = catY + Math.sin(childAngle) * childDist;
        const childStyle = getCategoryStyle(child.category);

        let radius = 7;
        if (child.type === 'goal' || child.type === 'device') radius = 8;

        simNodes.push({
          ...child,
          x: childX,
          y: childY,
          baseX: childX,
          baseY: childY,
          vx: 0,
          vy: 0,
          radius,
          parentCat: cat.label,
          color: childStyle.color,
          bg: childStyle.bg,
          glow: childStyle.glow,
        });
      });
    });

    pulsesRef.current = rawEdges.slice(0, 16).map((edge, i) => ({
      edgeId: edge.id,
      source: edge.source,
      target: edge.target,
      progress: (i / 16),
      speed: 0.005 + (i % 3) * 0.003,
    }));

    return simNodes;
  }, []);

  // Initialize Canvas & Physics Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || graphData.nodes.length === 0) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.parentElement.getBoundingClientRect();
    const width = rect.width || 800;
    const height = rect.height || 520;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    nodesRef.current = initConstellation(graphData.nodes, graphData.edges, width, height);
    edgesRef.current = graphData.edges;
    transformRef.current = { x: 0, y: 0, k: 1 };

    let simStep = 0;

    const loop = () => {
      simStep++;
      const currentNodes = nodesRef.current;
      const currentEdges = edgesRef.current;
      const nodesMap = new Map(currentNodes.map((n) => [n.id, n]));

      // Physics Relaxation
      if (simStep < 180 || draggedNodeRef.current) {
        for (let i = 0; i < currentNodes.length; i++) {
          const a = currentNodes[i];
          for (let j = i + 1; j < currentNodes.length; j++) {
            const b = currentNodes[j];
            const dx = b.x - a.x;
            const dy = b.y - a.y;
            const dist = Math.hypot(dx, dy) || 1;
            const minDist = (a.radius + b.radius) + (a.isCategory || b.isCategory ? 34 : 22);

            if (dist < minDist) {
              const overlap = (minDist - dist) * 0.08;
              const fx = (dx / dist) * overlap;
              const fy = (dy / dist) * overlap;

              if (a !== draggedNodeRef.current && !a.isCore) {
                a.x -= fx;
                a.y -= fy;
              }
              if (b !== draggedNodeRef.current && !b.isCore) {
                b.x += fx;
                b.y += fy;
              }
            }
          }
        }

        currentEdges.forEach((edge) => {
          const src = nodesMap.get(edge.source);
          const tgt = nodesMap.get(edge.target);
          if (src && tgt) {
            const dx = tgt.x - src.x;
            const dy = tgt.y - src.y;
            const dist = Math.hypot(dx, dy) || 1;
            let targetDist = 70;
            if (src.isCore || tgt.isCore) targetDist = 180;

            const diff = dist - targetDist;
            const force = diff * 0.008;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            if (tgt !== draggedNodeRef.current && !tgt.isCore) {
              tgt.x -= fx;
              tgt.y -= fy;
            }
            if (src !== draggedNodeRef.current && !src.isCore) {
              src.x += fx;
              src.y += fy;
            }
          }
        });
      }

      // Gentle Ambient Breathing
      const t = simStep * 0.02;
      currentNodes.forEach((node, i) => {
        if (!node.isCore && node !== draggedNodeRef.current) {
          node.x += Math.sin(t + i * 0.6) * 0.08;
          node.y += Math.cos(t + i * 0.6) * 0.08;
        }
      });

      // Clear Screen
      ctx.save();
      ctx.clearRect(0, 0, width, height);

      const { x: panX, y: panY, k: scale } = transformRef.current;
      ctx.translate(panX, panY);
      ctx.scale(scale, scale);

      const activeCat = activeCategory.toUpperCase();
      const hasSearch = searchQuery.trim().length > 0;
      const searchLower = searchQuery.toLowerCase().trim();

      const isNodeHighlighted = (n) => {
        if (hasSearch) {
          return (
            n.label.toLowerCase().includes(searchLower) ||
            n.category.toLowerCase().includes(searchLower) ||
            (n.detail && n.detail.toLowerCase().includes(searchLower))
          );
        }
        if (activeCat !== 'ALL') {
          return n.isCore || n.category.toUpperCase() === activeCat;
        }
        return true;
      };

      const hoveredNeighborIds = new Set();
      if (hoveredNode) {
        hoveredNeighborIds.add(hoveredNode.id);
        currentEdges.forEach((e) => {
          if (e.source === hoveredNode.id) hoveredNeighborIds.add(e.target);
          if (e.target === hoveredNode.id) hoveredNeighborIds.add(e.source);
        });
      }

      // Draw Edges
      currentEdges.forEach((edge) => {
        const src = nodesMap.get(edge.source);
        const tgt = nodesMap.get(edge.target);
        if (!src || !tgt) return;

        const isHoverPath = hoveredNode && (hoveredNeighborIds.has(src.id) && hoveredNeighborIds.has(tgt.id));
        const isCatMatch = activeCat === 'ALL' || (src.category.toUpperCase() === activeCat || tgt.category.toUpperCase() === activeCat);

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);

        if (isHoverPath) {
          ctx.strokeStyle = '#00f2fe';
          ctx.lineWidth = 2.2;
          ctx.globalAlpha = 0.9;
        } else if (hasSearch) {
          const matchA = isNodeHighlighted(src);
          const matchB = isNodeHighlighted(tgt);
          ctx.strokeStyle = matchA && matchB ? '#f59e0b' : 'rgba(148, 163, 184, 0.06)';
          ctx.lineWidth = matchA && matchB ? 1.8 : 0.8;
          ctx.globalAlpha = matchA && matchB ? 0.7 : 0.15;
        } else if (!isCatMatch) {
          ctx.strokeStyle = 'rgba(148, 163, 184, 0.05)';
          ctx.lineWidth = 0.8;
          ctx.globalAlpha = 0.15;
        } else {
          ctx.strokeStyle = src.isCore ? 'rgba(0, 242, 254, 0.22)' : 'rgba(148, 163, 184, 0.18)';
          ctx.lineWidth = src.isCore ? 1.4 : 1.0;
          ctx.globalAlpha = 0.6;
        }

        ctx.stroke();
      });

      // Draw Pulses
      pulsesRef.current.forEach((pulse) => {
        pulse.progress = (pulse.progress + pulse.speed) % 1;
        const src = nodesMap.get(pulse.source);
        const tgt = nodesMap.get(pulse.target);
        if (!src || !tgt) return;

        const px = src.x + (tgt.x - src.x) * pulse.progress;
        const py = src.y + (tgt.y - src.y) * pulse.progress;

        ctx.beginPath();
        ctx.arc(px, py, 2.2, 0, Math.PI * 2);
        ctx.fillStyle = '#00f2fe';
        ctx.globalAlpha = 0.85;
        ctx.shadowColor = '#00f2fe';
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // Draw Nodes
      currentNodes.forEach((node) => {
        const isHovered = hoveredNode && hoveredNode.id === node.id;
        const isNeighbor = hoveredNeighborIds.has(node.id);
        const isSelected = selectedNode && selectedNode.id === node.id;
        const highlighted = isNodeHighlighted(node);

        let alpha = 0.85;
        if (hoveredNode) {
          alpha = isHovered ? 1.0 : isNeighbor ? 0.9 : 0.2;
        } else if (!highlighted) {
          alpha = 0.15;
        }

        ctx.save();
        ctx.globalAlpha = alpha;

        const glowRadius = node.radius + (isHovered || isSelected ? 8 : node.isCore ? 6 : 3);
        const grad = ctx.createRadialGradient(node.x, node.y, node.radius * 0.6, node.x, node.y, glowRadius);
        grad.addColorStop(0, node.color);
        grad.addColorStop(1, 'transparent');

        ctx.beginPath();
        ctx.arc(node.x, node.y, glowRadius, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.isCore ? '#00f2fe' : node.color;
        ctx.fill();

        ctx.strokeStyle = isHovered || isSelected ? '#ffffff' : 'rgba(255, 255, 255, 0.4)';
        ctx.lineWidth = isHovered || isSelected ? 2.5 : 1;
        ctx.stroke();

        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 6, 0, Math.PI * 2);
          ctx.strokeStyle = node.color;
          ctx.lineWidth = 1.5;
          ctx.setLineDash([3, 3]);
          ctx.stroke();
          ctx.setLineDash([]);
        }

        ctx.restore();

        // Node Labels (Crisp, High-Contrast Pill)
        const shouldShowLabel =
          node.isCore ||
          node.isCategory ||
          isHovered ||
          isSelected ||
          (hasSearch && highlighted) ||
          (activeCat !== 'ALL' && highlighted);

        if (shouldShowLabel) {
          ctx.save();
          ctx.globalAlpha = alpha;

          const labelText = node.label;
          ctx.font = node.isCore
            ? 'bold 12px "JetBrains Mono", monospace'
            : node.isCategory
            ? 'bold 11px "JetBrains Mono", monospace'
            : '10px "JetBrains Mono", monospace';

          const textWidth = ctx.measureText(labelText).width;
          const pillPaddingX = 6;
          const pillHeight = 16;
          const pillX = node.x - textWidth / 2 - pillPaddingX;
          const pillY = node.y + node.radius + 5;

          ctx.fillStyle = 'rgba(15, 23, 42, 0.88)';
          ctx.beginPath();
          if (typeof ctx.roundRect === 'function') {
            ctx.roundRect(pillX, pillY, textWidth + pillPaddingX * 2, pillHeight, 4);
          } else {
            ctx.rect(pillX, pillY, textWidth + pillPaddingX * 2, pillHeight);
          }
          ctx.fill();

          ctx.strokeStyle = node.isCategory || node.isCore ? node.color : 'rgba(148, 163, 184, 0.3)';
          ctx.lineWidth = 0.8;
          ctx.stroke();

          ctx.fillStyle = node.isCore ? '#00f2fe' : node.isCategory ? '#ffffff' : '#cbd5e1';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(labelText, node.x, pillY + pillHeight / 2);

          ctx.restore();
        }
      });

      ctx.restore();
      animFrameRef.current = requestAnimationFrame(loop);
    };

    loop();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [graphData, initConstellation, searchQuery, activeCategory, hoveredNode, selectedNode]);

  // Screen to World
  const screenToWorld = useCallback((screenX, screenY) => {
    const { x: panX, y: panY, k: scale } = transformRef.current;
    return {
      x: (screenX - panX) / scale,
      y: (screenY - panY) / scale,
    };
  }, []);

  // Mouse Move
  const handleMouseMove = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    setMousePos({ x: e.clientX, y: e.clientY });

    if (draggedNodeRef.current) {
      const world = screenToWorld(mouseX, mouseY);
      draggedNodeRef.current.x = world.x;
      draggedNodeRef.current.y = world.y;
      return;
    }

    if (isDraggingCanvasRef.current) {
      const dx = mouseX - dragStartRef.current.x;
      const dy = mouseY - dragStartRef.current.y;
      transformRef.current.x += dx;
      transformRef.current.y += dy;
      dragStartRef.current = { x: mouseX, y: mouseY };
      return;
    }

    const world = screenToWorld(mouseX, mouseY);
    const hit = nodesRef.current.find((n) => {
      const dist = Math.hypot(n.x - world.x, n.y - world.y);
      return dist <= n.radius + 8;
    });

    if (hit !== hoveredNode) {
      setHoveredNode(hit || null);
      canvas.style.cursor = hit ? 'pointer' : 'grab';
    }
  };

  // Mouse Down
  const handleMouseDown = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    const world = screenToWorld(mouseX, mouseY);

    const hit = nodesRef.current.find((n) => {
      const dist = Math.hypot(n.x - world.x, n.y - world.y);
      return dist <= n.radius + 8;
    });

    if (hit) {
      draggedNodeRef.current = hit;
      setSelectedNode(hit);
      canvas.style.cursor = 'grabbing';

      const rect = canvas.getBoundingClientRect();
      const cx = rect.width / 2;
      const cy = rect.height / 2;
      transformRef.current = {
        x: cx - hit.x * 1.2,
        y: cy - hit.y * 1.2,
        k: 1.2,
      };
    } else {
      isDraggingCanvasRef.current = true;
      dragStartRef.current = { x: mouseX, y: mouseY };
      canvas.style.cursor = 'grabbing';
    }
  };

  // Mouse Up
  const handleMouseUp = () => {
    const canvas = canvasRef.current;
    if (canvas) {
      canvas.style.cursor = hoveredNode ? 'pointer' : 'grab';
    }
    draggedNodeRef.current = null;
    isDraggingCanvasRef.current = false;
  };

  // Wheel Zoom
  const handleWheel = (e) => {
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.88;
    const oldK = transformRef.current.k;
    const newK = Math.max(0.35, Math.min(3.5, oldK * zoomFactor));

    transformRef.current.x = mouseX - (mouseX - transformRef.current.x) * (newK / oldK);
    transformRef.current.y = mouseY - (mouseY - transformRef.current.y) * (newK / oldK);
    transformRef.current.k = newK;
  };

  const handleResetView = () => {
    transformRef.current = { x: 0, y: 0, k: 1 };
    setSelectedNode(null);
    setHoveredNode(null);
  };

  const handleZoomIn = () => {
    const canvas = canvasRef.current;
    const cx = (canvas?.width || 800) / 2;
    const cy = (canvas?.height || 520) / 2;
    const oldK = transformRef.current.k;
    const newK = Math.min(3.5, oldK * 1.25);
    transformRef.current.x = cx - (cx - transformRef.current.x) * (newK / oldK);
    transformRef.current.y = cy - (cy - transformRef.current.y) * (newK / oldK);
    transformRef.current.k = newK;
  };

  const handleZoomOut = () => {
    const canvas = canvasRef.current;
    const cx = (canvas?.width || 800) / 2;
    const cy = (canvas?.height || 520) / 2;
    const oldK = transformRef.current.k;
    const newK = Math.max(0.35, oldK * 0.8);
    transformRef.current.x = cx - (cx - transformRef.current.x) * (newK / oldK);
    transformRef.current.y = cy - (cy - transformRef.current.y) * (newK / oldK);
    transformRef.current.k = newK;
  };

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFocusCategory = (cat) => {
    setActiveCategory(cat);
    const catNode = nodesRef.current.find((n) => n.isCategory && n.label.toUpperCase() === cat.toUpperCase());
    if (catNode && canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const cx = rect.width / 2;
      const cy = rect.height / 2;
      transformRef.current = {
        x: cx - catNode.x * 1.3,
        y: cy - catNode.y * 1.3,
        k: 1.3,
      };
      setSelectedNode(catNode);
    }
  };

  return (
    <div
      ref={containerRef}
      className="relative flex flex-col h-full bg-slate-950/95 rounded-2xl border border-slate-800 shadow-2xl backdrop-blur-2xl overflow-hidden select-none"
    >
      {/* Top Cyber Filter HUD */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 bg-slate-900/90 border-b border-slate-800/90 z-10 backdrop-blur-xl">
        {/* Title & Real-Time Stats */}
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-cyan-950/80 border border-amber-500/40 text-amber-500 shadow-md shadow-cyan-500/20">
            <Network className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-white font-mono">
                Memory Knowledge Graph
              </h2>
              <span className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-300 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                {graphData.nodes.length} Nodes
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono tracking-tight">
              {graphData.total_memories} memories · {graphData.total_goals} goals · {graphData.total_tasks} tasks · {graphData.total_devices} devices
            </p>
          </div>
        </div>

        {/* Live Search Input */}
        <div className="flex items-center gap-2 flex-1 max-w-xs sm:max-w-sm">
          <div className="relative w-full">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search memories, projects, entities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-8 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 font-mono transition-colors"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Category Filter Pills with Item Badges */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 max-w-full custom-scrollbar">
          {categories.map((cat) => {
            const count = categoryCounts[cat] || 0;
            const isActive = activeCategory === cat;
            const style = getCategoryStyle(cat);

            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`flex items-center gap-1.5 text-[10px] font-mono uppercase px-2.5 py-1 rounded-full transition-all shrink-0 ${
                  isActive
                    ? 'font-bold shadow-lg'
                    : 'bg-slate-900 border border-slate-800 text-slate-400 hover:text-white hover:border-slate-700'
                }`}
                style={
                  isActive
                    ? {
                        backgroundColor: style.bg,
                        color: style.color,
                        borderColor: style.border,
                        borderWidth: 1,
                        boxShadow: `0 0 12px ${style.glow}`,
                      }
                    : {}
                }
              >
                <span>{cat}</span>
                <span
                  className={`text-[9px] px-1 py-0.2 rounded font-bold ${
                    isActive ? 'bg-white/20 text-white' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Graph Canvas Area */}
      <div className="relative flex-1 w-full h-full min-h-[420px] bg-grid-pattern overflow-hidden">
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onWheel={handleWheel}
          className="w-full h-full cursor-grab active:cursor-grabbing"
        />

        {/* Floating HUD Zoom & View Controls */}
        <div className="absolute bottom-4 left-4 flex items-center gap-1 p-1 bg-slate-900/90 border border-slate-800 rounded-xl shadow-xl backdrop-blur-xl z-10 font-mono">
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            className="p-1.5 text-slate-400 hover:text-amber-500 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            className="p-1.5 text-slate-400 hover:text-amber-500 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <div className="w-[1px] h-4 bg-slate-800 mx-1" />
          <button
            onClick={handleResetView}
            title="Reset View / Recenter"
            className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="text-[10px]">Recenter</span>
          </button>
        </div>

        {/* Floating Tooltip Near Cursor on Hover */}
        {hoveredNode && !selectedNode && (
          <div
            className="fixed pointer-events-none z-50 p-3 rounded-xl bg-slate-900/95 border border-slate-700 shadow-2xl backdrop-blur-2xl max-w-sm transition-all"
            style={{
              left: Math.min(window.innerWidth - 340, mousePos.x + 16),
              top: Math.min(window.innerHeight - 200, mousePos.y + 16),
            }}
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span
                className="text-[10px] uppercase font-mono px-2 py-0.5 rounded font-bold"
                style={{
                  backgroundColor: getCategoryStyle(hoveredNode.category).bg,
                  color: getCategoryStyle(hoveredNode.category).color,
                  border: `1px solid ${getCategoryStyle(hoveredNode.category).border}`,
                }}
              >
                {hoveredNode.category}
              </span>
              <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                {hoveredNode.type}
              </span>
            </div>
            <h4 className="text-xs font-bold text-white mb-1 font-mono">{hoveredNode.label}</h4>
            {hoveredNode.detail && (
              <p className="text-[11px] text-slate-300 font-sans line-clamp-3 leading-relaxed">
                {hoveredNode.detail}
              </p>
            )}
            <p className="text-[9px] text-slate-500 font-mono mt-1.5">Click to inspect complete details</p>
          </div>
        )}

        {/* Selected Node Inspector Drawer Overlay */}
        {selectedNode && (
          <div className="absolute top-4 right-4 max-w-sm w-full bg-slate-900/95 border border-slate-700 p-5 rounded-2xl shadow-2xl backdrop-blur-2xl z-20 animate-in fade-in slide-in-from-right-4">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2.5">
              <div className="flex items-center gap-2">
                <span
                  className="text-[10px] uppercase font-mono px-2.5 py-0.5 rounded-full font-bold"
                  style={{
                    backgroundColor: getCategoryStyle(selectedNode.category).bg,
                    color: getCategoryStyle(selectedNode.category).color,
                    border: `1px solid ${getCategoryStyle(selectedNode.category).border}`,
                  }}
                >
                  {selectedNode.category}
                </span>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  {selectedNode.type}
                </span>
                {selectedNode.status && (
                  <span
                    className={`text-[9px] uppercase font-mono px-2 py-0.5 rounded font-semibold ${
                      selectedNode.status === 'online' || selectedNode.status === 'completed'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-amber-950 text-amber-300 border border-amber-800'
                    }`}
                  >
                    {selectedNode.status}
                  </span>
                )}
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <h3 className="font-bold text-white text-sm mb-2 font-mono">{selectedNode.label}</h3>

            <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3 mb-3 max-h-48 overflow-y-auto custom-scrollbar">
              <p className="text-xs text-slate-200 leading-relaxed font-sans">
                {selectedNode.detail || selectedNode.label}
              </p>
            </div>

            {selectedNode.created_at && (
              <p className="text-[10px] text-slate-500 font-mono mb-3">
                Timestamp: {new Date(selectedNode.created_at).toLocaleString()}
              </p>
            )}

            {/* Contextual Action Buttons tailored for each Node Type */}
            <div className="flex flex-col gap-2 pt-2 border-t border-slate-800/80">
              {/* Common Actions: Copy */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleCopy(selectedNode.detail || selectedNode.label)}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-colors"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copied ? 'Copied' : 'Copy Text'}</span>
                </button>

                {/* Memory Node Actions: Ask ARYA or Delete Memory */}
                {selectedNode.type === 'memory' && (
                  <>
                    <button
                      onClick={() => {
                        if (onSendMessage) {
                          onSendMessage(`Tell me more about ${selectedNode.label}`);
                          if (onSelectTab) onSelectTab('cockpit');
                        }
                      }}
                      className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 hover:bg-cyan-900 text-xs font-mono transition-colors"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span>Ask ARYA</span>
                    </button>
                    {selectedNode.raw_id && (
                      <button
                        onClick={async () => {
                          if (confirm(`Delete memory: "${selectedNode.label}"?`)) {
                            try {
                              const res = await fetch(`/api/memories/${selectedNode.raw_id}`, { method: 'DELETE' });
                              if (res.ok) {
                                setSelectedNode(null);
                                fetchGraphData();
                              }
                            } catch (e) {
                              console.error(e);
                            }
                          }
                        }}
                        className="px-2.5 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-900/50 text-xs font-mono transition-colors"
                        title="Delete Memory"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </>
                )}
              </div>

              {/* Goal Node Actions: Toggle Goal Status */}
              {selectedNode.type === 'goal' && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={async () => {
                      if (selectedNode.raw_id) {
                        try {
                          const res = await fetch(`/api/goals/${selectedNode.raw_id}/complete`, { method: 'POST' });
                          if (res.ok) {
                            fetchGraphData();
                          }
                        } catch (e) {
                          console.error(e);
                        }
                      }
                    }}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-950/60 border border-amber-800/60 text-amber-300 hover:bg-amber-900 text-xs font-mono font-semibold transition-colors"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{selectedNode.status === 'completed' ? 'Re-open Goal' : 'Complete Goal'}</span>
                  </button>
                  <button
                    onClick={() => {
                      if (onSendMessage) {
                        onSendMessage(`Provide an action plan to achieve my goal: ${selectedNode.label}`);
                        if (onSelectTab) onSelectTab('cockpit');
                      }
                    }}
                    className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono transition-colors"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    <span>Action Plan</span>
                  </button>
                </div>
              )}

              {/* Task Node Actions: Complete Task */}
              {selectedNode.type === 'task' && (
                <button
                  onClick={async () => {
                    if (selectedNode.raw_id) {
                      try {
                        const res = await fetch(`/tasks/${selectedNode.raw_id}/complete`, { method: 'POST' });
                        if (res.ok) {
                          fetchGraphData();
                        }
                      } catch (e) {
                        console.error(e);
                      }
                    }
                  }}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 hover:bg-emerald-900 text-xs font-mono font-semibold transition-colors"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Mark Task Completed</span>
                </button>
              )}

              {/* Device Node Actions: Open Device Manager */}
              {selectedNode.type === 'device' && (
                <button
                  onClick={() => {
                    if (onSelectTab) onSelectTab('devices');
                  }}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-teal-950/60 border border-teal-800/60 text-teal-300 hover:bg-teal-900 text-xs font-mono font-semibold transition-colors"
                >
                  <Wifi className="w-3.5 h-3.5" />
                  <span>Manage Devices in Portal</span>
                </button>
              )}

              {/* Category Node Actions: Focus Cluster */}
              {selectedNode.isCategory && (
                <button
                  onClick={() => handleFocusCategory(selectedNode.label)}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950 border border-cyan-800 text-cyan-300 hover:bg-cyan-900 text-xs font-mono font-semibold transition-colors"
                >
                  <ArrowUpRight className="w-3.5 h-3.5" />
                  <span>Focus {selectedNode.label} Cluster</span>
                </button>
              )}

              {/* ARYA Core Node Actions */}
              {selectedNode.type === 'core' && (
                <button
                  onClick={() => {
                    if (onSendMessage) {
                      onSendMessage('Generate a full system and user telemetry report');
                      if (onSelectTab) onSelectTab('cockpit');
                    }
                  }}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950/80 border border-amber-500/50 text-cyan-300 hover:bg-cyan-900 text-xs font-mono font-bold transition-colors shadow-lg shadow-cyan-500/10"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                  <span>Run System Diagnostics</span>
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
