"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Panel,
  Handle,
  Position
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { 
  Building2, 
  User, 
  Coins, 
  Globe, 
  Cpu, 
  Code, 
  DollarSign, 
  HelpCircle,
  Expand
} from "lucide-react";

// Custom Node Component
const CustomNode = ({ data }: any) => {
  const labelType = data.labelType || "Company";
  
  // Icon and theme selection based on entity type
  const { icon: Icon, bg, border, text, glow } = useMemo(() => {
    switch (labelType) {
      case "Company":
        return {
          icon: Building2,
          bg: "bg-[#064e3b]/85",
          border: "border-emerald-500",
          text: "text-emerald-400",
          glow: "shadow-[0_0_15px_-3px_rgba(16,185,129,0.3)]"
        };
      case "Founder":
        return {
          icon: User,
          bg: "bg-[#7c2d12]/85",
          border: "border-orange-500",
          text: "text-orange-400",
          glow: "shadow-[0_0_15px_-3px_rgba(249,115,22,0.3)]"
        };
      case "Investor":
        return {
          icon: Coins,
          bg: "bg-[#581c87]/85",
          border: "border-purple-500",
          text: "text-purple-400",
          glow: "shadow-[0_0_15px_-3px_rgba(168,85,247,0.3)]"
        };
      case "Market":
        return {
          icon: Globe,
          bg: "bg-[#1e3a8a]/85",
          border: "border-blue-500",
          text: "text-blue-400",
          glow: "shadow-[0_0_15px_-3px_rgba(59,130,246,0.3)]"
        };
      case "Product":
        return {
          icon: Cpu,
          bg: "bg-[#78350f]/85",
          border: "border-amber-500",
          text: "text-amber-400",
          glow: "shadow-[0_0_15px_-3px_rgba(245,158,11,0.3)]"
        };
      case "Technology":
        return {
          icon: Code,
          bg: "bg-[#134e5e]/85",
          border: "border-cyan-500",
          text: "text-cyan-400",
          glow: "shadow-[0_0_15px_-3px_rgba(6,182,212,0.3)]"
        };
      case "Funding Round":
        return {
          icon: DollarSign,
          bg: "bg-[#14532d]/85",
          border: "border-green-500",
          text: "text-green-400",
          glow: "shadow-[0_0_15px_-3px_rgba(34,197,94,0.3)]"
        };
      default:
        return {
          icon: HelpCircle,
          bg: "bg-zinc-800/85",
          border: "border-zinc-500",
          text: "text-zinc-400",
          glow: "shadow-none"
        };
    }
  }, [labelType]);

  return (
    <div className={`px-4 py-2.5 rounded-lg border-2 ${bg} ${border} ${text} ${glow} min-w-[140px] text-center font-sans relative`}>
      <Handle type="target" position={Position.Top} className="opacity-0 pointer-events-none" />
      <div className="flex items-center gap-2 justify-center">
        <Icon className="w-4 h-4 shrink-0" />
        <div className="flex flex-col text-left">
          <span className="text-[10px] uppercase font-semibold tracking-wider opacity-60">{labelType}</span>
          <span className="text-sm font-bold text-white leading-tight">{data.label}</span>
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="opacity-0 pointer-events-none" />
    </div>
  );
};

// Node Types Registry
const nodeTypes = {
  custom: CustomNode
};

export default function GraphCanvas({ data, onNodeSelect, onExpandNode }: any) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!data || !data.nodes || data.nodes.length === 0) return;

    // Concentric Ring Layout calculation
    const count = data.nodes.length;
    const centerNodeId = data.nodes[0].id;
    const radiusStep = 240;
    
    const layoutedNodes = data.nodes.map((node: any, idx: number) => {
      if (idx === 0) {
        return {
          id: node.id,
          type: "custom",
          data: { label: node.id, labelType: node.label, ...node },
          position: { x: 500, y: 350 }
        };
      }
      
      // Converted concentric math
      const angle = (idx - 1) * ((2 * Math.PI) / Math.min(8, count - 1));
      const ringIndex = Math.floor((idx - 1) / 8);
      const radius = radiusStep * (ringIndex + 1);
      
      // Introduce slight staggering offset to prevent overlap for larger sets
      const staggeredAngle = angle + (ringIndex * 0.25);

      return {
        id: node.id,
        type: "custom",
        data: { label: node.id, labelType: node.label, ...node },
        position: {
          x: 500 + Math.cos(staggeredAngle) * radius,
          y: 350 + Math.sin(staggeredAngle) * radius
        }
      };
    });

    // Format edges for React Flow
    const layoutedEdges = data.edges.map((edge: any, index: number) => {
      // Color edges based on relationship types
      let strokeColor = "rgba(255, 255, 255, 0.2)";
      let labelBgColor = "#1e293b";
      
      if (edge.type === "COMPETES_WITH") strokeColor = "#ef4444"; // Red
      else if (edge.type === "FUNDED_BY") strokeColor = "#a855f7"; // Purple
      else if (edge.type === "PARTNERED_WITH") strokeColor = "#3b82f6"; // Blue
      else if (edge.type === "FOUNDED_BY") strokeColor = "#f97316"; // Orange
      else if (edge.type === "USES_TECH") strokeColor = "#06b6d4"; // Cyan
      else if (edge.type === "ACQUIRED") strokeColor = "#10b981"; // Emerald

      return {
        id: `edge-${edge.source}-${edge.target}-${edge.type}-${index}`,
        source: edge.source,
        target: edge.target,
        label: edge.type.replace("_", " "),
        animated: edge.type === "PARTNERED_WITH" || edge.type === "USES_TECH" || edge.type === "ACQUIRED",
        style: { stroke: strokeColor, strokeWidth: 2 },
        labelStyle: { fill: "#fff", fontSize: 9, fontWeight: 600 },
        labelBgStyle: { fill: labelBgColor, fillOpacity: 0.8 },
        labelBgPadding: [6, 4],
        labelBgBorderRadius: 4
      };
    });

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [data, setNodes, setEdges]);

  const handleNodeClick = (event: any, node: any) => {
    if (onNodeSelect) {
      onNodeSelect(node.data);
    }
  };

  const handleNodeDoubleClick = (event: any, node: any) => {
    if (onExpandNode) {
      onExpandNode(node.id);
    }
  };

  return (
    <div className="w-full h-full relative" style={{ minHeight: "500px" }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        fitView
        className="w-full h-full"
      >
        <Background color="#1f2937" gap={16} size={1} />
        <Controls />
        <MiniMap 
          nodeColor={(n) => {
            if (n.data?.labelType === "Company") return "#10b981";
            if (n.data?.labelType === "Founder") return "#f97316";
            if (n.data?.labelType === "Investor") return "#a855f7";
            return "#6b7280";
          }}
          bgColor="#0c0c0e"
          maskColor="rgba(0,0,0,0.6)"
        />
        
        <Panel position="top-left" className="bg-[#18181b]/95 border border-white/10 p-3 rounded-lg text-xs flex flex-col gap-2 max-w-[220px] backdrop-blur text-gray-300 shadow-xl">
          <div className="font-bold text-white border-b border-white/10 pb-1.5 mb-0.5">Graph Navigation Guide</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-emerald-500 inline-block"></span> Company</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-orange-500 inline-block"></span> Founder</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-purple-500 inline-block"></span> Investor</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-blue-500 inline-block"></span> Market</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-cyan-500 inline-block"></span> Technology</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block"></span> Product</div>
          <div className="mt-1 border-t border-white/10 pt-1 text-[10px] text-gray-400 italic">
            Double-click a node to expand its relationships and explore neighbors.
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}
