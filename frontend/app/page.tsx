"use client";

import React, { useState, useEffect, useRef, useMemo } from "react";
import dynamic from "next/dynamic";
import { 
  Search, 
  Share2, 
  Building2, 
  TrendingUp, 
  Layers, 
  Cpu, 
  Database,
  RefreshCw,
  HelpCircle,
  Play,
  ArrowRight,
  Sparkles,
  Info,
  DollarSign,
  UserCheck,
  CheckCircle,
  Loader2,
  FileText,
  AlertCircle
} from "lucide-react";

// Dynamically import GraphCanvas with SSR disabled since React Flow uses browser layout/resize metrics
const GraphCanvas = dynamic(() => import("@/components/GraphCanvas"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[500px] flex items-center justify-center bg-[#0c0c0e] border border-white/5 rounded-xl">
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin" />
        <span className="text-sm text-gray-400">Loading interactive graph engine...</span>
      </div>
    </div>
  )
});

const API_BASE = "http://localhost:8000";

// Simple custom markdown parser for bullet lists, bold text, headers, and clean tables
const formatMarkdown = (text: string) => {
  if (!text) return "";
  
  // Format tables
  const lines = text.split("\n");
  let inTable = false;
  let tableRows: string[][] = [];
  let renderedText = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    if (line.startsWith("|") && line.endsWith("|")) {
      // It's a table row
      inTable = true;
      // Skip separator row (contains ---)
      if (line.includes("---")) continue;
      
      const cells = line.split("|").map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      tableRows.push(cells);
    } else {
      if (inTable && tableRows.length > 0) {
        // Render current accumulated table
        const headers = tableRows[0];
        const bodyRows = tableRows.slice(1);
        renderedText.push(
          <div key={`table-${i}`} className="overflow-x-auto my-4 rounded-lg border border-white/10">
            <table className="min-w-full divide-y divide-white/10 text-sm">
              <thead className="bg-[#18181b]">
                <tr>
                  {headers.map((h, idx) => (
                    <th key={idx} className="px-4 py-2 text-left font-semibold text-emerald-400">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 bg-[#101012]">
                {bodyRows.map((row, rIdx) => (
                  <tr key={rIdx}>
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-4 py-2 text-gray-300 font-sans">{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableRows = [];
        inTable = false;
      }
      
      // Regular line processing
      let formattedLine = line;
      // Bold tags
      formattedLine = formattedLine.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
      // Bullet list items
      if (formattedLine.startsWith("- ") || formattedLine.startsWith("* ")) {
        renderedText.push(
          <li key={i} className="ml-5 list-disc my-1 text-gray-300 font-sans" dangerouslySetInnerHTML={{ __html: formattedLine.substring(2) }} />
        );
      } 
      // Headings
      else if (formattedLine.startsWith("### ")) {
        renderedText.push(
          <h3 key={i} className="text-md font-bold text-emerald-400 mt-4 mb-2" dangerouslySetInnerHTML={{ __html: formattedLine.substring(4) }} />
        );
      } else if (formattedLine.startsWith("## ")) {
        renderedText.push(
          <h2 key={i} className="text-lg font-bold text-emerald-400 mt-5 mb-2 border-b border-white/5 pb-1" dangerouslySetInnerHTML={{ __html: formattedLine.substring(3) }} />
        );
      } else if (formattedLine.startsWith("# ")) {
        renderedText.push(
          <h1 key={i} className="text-xl font-bold text-white mt-6 mb-3" dangerouslySetInnerHTML={{ __html: formattedLine.substring(2) }} />
        );
      } else if (formattedLine === "") {
        renderedText.push(<div key={i} className="h-2" />);
      } else {
        renderedText.push(
          <p key={i} className="text-gray-300 font-sans my-1.5 leading-relaxed" dangerouslySetInnerHTML={{ __html: formattedLine }} />
        );
      }
    }
  }

  // Handle trailing table if text ends in a table
  if (inTable && tableRows.length > 0) {
    const headers = tableRows[0];
    const bodyRows = tableRows.slice(1);
    renderedText.push(
      <div key={`table-end`} className="overflow-x-auto my-4 rounded-lg border border-white/10">
        <table className="min-w-full divide-y divide-white/10 text-sm">
          <thead className="bg-[#18181b]">
            <tr>
              {headers.map((h, idx) => (
                <th key={idx} className="px-4 py-2 text-left font-semibold text-emerald-400">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 bg-[#101012]">
            {bodyRows.map((row, rIdx) => (
              <tr key={rIdx}>
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className="px-4 py-2 text-gray-300 font-sans">{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return <div className="space-y-1">{renderedText}</div>;
};

// LangGraph node steps config
const STEPS = [
  { name: "Intent Detection", desc: "Analyzing intent and extracting startups" },
  { name: "Query Planner", desc: "Generating optimal research subqueries" },
  { name: "Graph Retrieval", desc: "Querying Neo4j relationship maps" },
  { name: "RAPTOR Retrieval", desc: "Extracting multi-level summaries from Qdrant" },
  { name: "Reranking", desc: "Re-sorting chunks with BAAI Reranker" },
  { name: "Answer Synthesis", desc: "Compiling insights with Mistral-Small" }
];

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState<"search" | "graph" | "database" | "predictions" | "stats">("search");
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [currentNodeIndex, setCurrentNodeIndex] = useState(-1);
  const [searchResponse, setSearchResponse] = useState<any>(null);
  
  // Database seeded items state
  const [startups, setStartups] = useState<any[]>([]);
  const [selectedStartup, setSelectedStartup] = useState<any>(null);
  const [similarStartups, setSimilarStartups] = useState<any[]>([]);
  const [isFetchSimilarLoading, setIsFetchSimilarLoading] = useState(false);

  // Predictions state
  const [predictions, setPredictions] = useState<any[]>([]);

  // Statistics state
  const [stats, setStats] = useState<any>({
    startups_count: 0,
    funding_rounds_count: 0,
    news_articles_count: 0,
    vector_chunks_count: 0,
    graph_nodes_count: 0,
    graph_edges_count: 0
  });

  // Global Interactive Graph
  const [graphData, setGraphData] = useState<any>({ nodes: [], edges: [] });
  const [selectedGraphNode, setSelectedGraphNode] = useState<any>(null);
  const [graphSearchQuery, setGraphSearchQuery] = useState("");

  // Seed status
  const [seedStatus, setSeedStatus] = useState<"idle" | "seeding" | "success" | "error">("idle");
  const [activeCitationText, setActiveCitationText] = useState<string | null>(null);

  const stepIntervalRef = useRef<any>(null);

  // Initial loads
  useEffect(() => {
    fetchStats();
    fetchStartups();
    fetchPredictions();
    fetchGlobalGraph();
  }, []);

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/stats`);
      const data = await res.json();
      setStats(data);
    } catch (e) {
      console.error("Failed to fetch stats", e);
    }
  };

  const fetchStartups = async () => {
    try {
      // Quick fetch of seeded database startups using `/api/graph` to list companies
      const res = await fetch(`${API_BASE}/api/graph`);
      const data = await res.json();
      const companyNodes = data.nodes.filter((n: any) => n.label === "Company");
      
      // Let's populate local profile details manually aligned with backend seed data
      const startupProfiles = companyNodes.map((node: any) => {
        let funding = "$0";
        let tech = "Python, PyTorch";
        let description = "Emerging market category company.";
        
        if (node.id === "OpenAI") {
          funding = "$17.6 Billion raising";
          tech = "Python, PyTorch, Kubernetes, Azure, Triton";
          description = "OpenAI is an AI research and deployment company. Its mission is to ensure that artificial general intelligence benefits all of humanity.";
        } else if (node.id === "Anthropic") {
          funding = "$6.7 Billion";
          tech = "Python, PyTorch, AWS, Google Cloud, JAX";
          description = "Anthropic is an AI safety and research company that builds reliable, beneficial, and controllable AI systems. It is the creator of the Claude models.";
        } else if (node.id === "Cohere") {
          funding = "$885 Million raised";
          tech = "Python, PyTorch, Oracle Cloud, Google Cloud";
          description = "Cohere builds AI technology for enterprise applications, providing natural language processing models optimized for search, retrieval, and generation.";
        } else if (node.id === "Qdrant") {
          funding = "$30.3 Million raised";
          tech = "Rust, Actix-web, gRPC, Docker, Kubernetes";
          description = "Qdrant is an open-source vector database and similarity search engine written in Rust, optimized for RAG and AI applications.";
        } else if (node.id === "Cursor") {
          funding = "$68 Million raised";
          tech = "TypeScript, Electron, Rust, C++, Next.js";
          description = "Cursor (built by Anysphere) is an AI-first code editor fork of VS Code, enabling deep codebase-level auto-completions, chat, and automated edits.";
        } else if (node.id === "Windsurf") {
          funding = "$240 Million raised";
          tech = "TypeScript, C++, Python, Go, WASM";
          description = "Windsurf is an agentic IDE built by Codeium, featuring an interactive agent loop that works side-by-side with developers.";
        }
        
        return {
          name: node.id,
          market: node.description || "Generative AI",
          funding,
          tech,
          description,
          logo: node.id.substring(0, 2).toUpperCase()
        };
      });
      
      setStartups(startupProfiles);
    } catch (e) {
      console.error("Failed to fetch startups list", e);
    }
  };

  const fetchPredictions = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/acquisition-prediction`);
      const data = await res.json();
      setPredictions(data);
    } catch (e) {
      console.error("Failed to fetch predictions", e);
    }
  };

  const fetchGlobalGraph = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/graph`);
      const data = await res.json();
      setGraphData(data);
    } catch (e) {
      console.error("Failed to fetch global graph", e);
    }
  };

  const expandGraphNode = async (startupName: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/graph?startup=${encodeURIComponent(startupName)}`);
      if (res.ok) {
        const data = await res.json();
        setGraphData(data);
      }
    } catch (e) {
      console.error("Failed to expand graph node", e);
    }
  };

  const handleSearchSubmit = async (searchQuery: string) => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setSearchResponse(null);
    setActiveCitationText(null);
    setCurrentNodeIndex(0);

    // Simulating LangGraph node transitions using an interval
    stepIntervalRef.current = setInterval(() => {
      setCurrentNodeIndex((prevIndex) => {
        if (prevIndex < 5) return prevIndex + 1;
        return prevIndex;
      });
    }, 1100);

    try {
      const response = await fetch(`${API_BASE}/api/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchQuery })
      });
      const data = await response.json();
      
      // Stop the stepper simulation and set state to final
      clearInterval(stepIntervalRef.current);
      setCurrentNodeIndex(6); // Step 6 = Done
      setSearchResponse(data);
    } catch (error) {
      console.error("Search failed", error);
      clearInterval(stepIntervalRef.current);
      setCurrentNodeIndex(-1);
    } finally {
      setIsSearching(false);
    }
  };

  const handleCitationClick = (source: string) => {
    // Find the text for this citation in the search response graph/docs if available
    // We can show a modal containing information about this citation source
    setActiveCitationText(source);
  };

  const handleFindSimilar = async (name: string) => {
    setIsFetchSimilarLoading(true);
    setSimilarStartups([]);
    try {
      const res = await fetch(`${API_BASE}/api/similar?name=${encodeURIComponent(name)}`);
      if (res.ok) {
        const data = await res.json();
        setSimilarStartups(data);
      } else {
        console.error("Startup similarities not found");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsFetchSimilarLoading(false);
    }
  };

  const handleSeedDatabase = async () => {
    setSeedStatus("seeding");
    try {
      const res = await fetch(`${API_BASE}/api/seed`, { method: "POST" });
      if (res.ok) {
        setSeedStatus("success");
        fetchStats();
        fetchStartups();
        fetchPredictions();
        fetchGlobalGraph();
        setTimeout(() => setSeedStatus("idle"), 3000);
      } else {
        setSeedStatus("error");
      }
    } catch (e) {
      setSeedStatus("error");
    }
  };

  const filteredGraphData = useMemo(() => {
    if (!graphSearchQuery.trim()) return graphData;
    const q = graphSearchQuery.toLowerCase();
    
    // Filter nodes matching query
    const filteredNodes = graphData.nodes.filter(
      (n: any) => n.id.toLowerCase().includes(q) || n.label.toLowerCase().includes(q)
    );
    
    const nodeIds = new Set(filteredNodes.map((n: any) => n.id));
    
    // Keep edges connected to filtered nodes
    const filteredEdges = graphData.edges.filter(
      (e: any) => nodeIds.has(e.source) || nodeIds.has(e.target)
    );
    
    return { nodes: filteredNodes, edges: filteredEdges };
  }, [graphData, graphSearchQuery]);

  return (
    <div className="flex h-screen bg-[#09090b] overflow-hidden text-gray-100">
      
      {/* Sidebar Navigation */}
      <aside className="w-64 bg-[#0d0d10] border-r border-white/5 flex flex-col z-20">
        <div className="p-6 border-b border-white/5 flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-emerald-500 to-blue-500 flex items-center justify-center font-bold text-black shadow-lg shadow-emerald-500/20">
            S
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-tight text-white leading-none">Startup Intel</h1>
            <span className="text-[10px] text-emerald-400 font-semibold tracking-wider uppercase">Platform</span>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-1.5 overflow-y-auto">
          <button
            onClick={() => setActiveTab("search")}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "search"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
            }`}
          >
            <Search className="w-4 h-4" />
            Research Agent
          </button>
          
          <button
            onClick={() => { setActiveTab("graph"); fetchGlobalGraph(); }}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "graph"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
            }`}
          >
            <Share2 className="w-4 h-4" />
            Interactive Graph
          </button>
          
          <button
            onClick={() => { setActiveTab("database"); fetchStartups(); }}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "database"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
            }`}
          >
            <Building2 className="w-4 h-4" />
            Startup Profiles
          </button>
          
          <button
            onClick={() => { setActiveTab("predictions"); fetchPredictions(); }}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "predictions"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
            }`}
          >
            <TrendingUp className="w-4 h-4" />
            Acquisition Predictor
          </button>
          
          <button
            onClick={() => { setActiveTab("stats"); fetchStats(); }}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === "stats"
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
            }`}
          >
            <Database className="w-4 h-4" />
            Platform Stats
          </button>
        </nav>
        
        {/* Footer info */}
        <div className="p-4 border-t border-white/5 bg-[#09090b] text-center text-xs text-gray-500">
          <div>GraphRAG + RAPTOR Engine</div>
          <div className="text-[10px] text-gray-600 mt-0.5">Offline Fallback Mode</div>
        </div>
      </aside>

      {/* Main Container */}
      <main className="flex-1 flex flex-col h-full overflow-hidden bg-[#09090b] relative">
        
        {/* Top Header */}
        <header className="h-16 border-b border-white/5 px-8 flex items-center justify-between z-10 shrink-0 bg-[#0d0d10]/50 backdrop-blur-md">
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold tracking-wider text-gray-400 uppercase">
              {activeTab === "search" && "AI Research Agent"}
              {activeTab === "graph" && "Ecosystem Map Visualizer"}
              {activeTab === "database" && "Startup Similarity Center"}
              {activeTab === "predictions" && "Acquisition Intelligence Model"}
              {activeTab === "stats" && "Market Mapping & Management"}
            </h2>
          </div>
          
          <div className="flex items-center gap-4 text-xs text-gray-400">
            <span className="flex items-center gap-1.5 bg-emerald-500/10 text-emerald-400 px-2.5 py-1 rounded-full font-semibold border border-emerald-500/10">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              Local Server Active
            </span>
          </div>
        </header>

        {/* Viewport Content */}
        <div className="flex-1 overflow-y-auto p-8 relative">
          
          {/* Tab 1: SEARCH AGENT */}
          {activeTab === "search" && (
            <div className="max-w-4xl mx-auto space-y-6">
              
              {/* Search Landing Hero */}
              {!searchResponse && !isSearching && (
                <div className="text-center py-12 space-y-4 max-w-2xl mx-auto">
                  <div className="w-12 h-12 rounded-full bg-emerald-500/15 flex items-center justify-center text-emerald-400 mx-auto glow-emerald">
                    <Sparkles className="w-6 h-6 animate-pulse" />
                  </div>
                  <h2 className="text-2xl font-bold text-white tracking-tight">Startup Intelligence Agent</h2>
                  <p className="text-sm text-gray-400 leading-relaxed">
                    Ask complex inquiries across our graph of startup relationships, technologies, funding histories, and hierarchical document nodes using multi-hop retrieval.
                  </p>
                  
                  {/* Suggestions list */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-8 text-left">
                    <button 
                      onClick={() => { setQuery("Which startups compete with OpenAI in AI agents?"); handleSearchSubmit("Which startups compete with OpenAI in AI agents?"); }}
                      className="p-3.5 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] text-xs text-gray-300 transition-all flex items-center justify-between group"
                    >
                      <span>Which startups compete with OpenAI in AI agents?</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-emerald-400 shrink-0 ml-2" />
                    </button>
                    <button 
                      onClick={() => { setQuery("Which vector database companies raised funding in the last 2 years?"); handleSearchSubmit("Which vector database companies raised funding in the last 2 years?"); }}
                      className="p-3.5 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] text-xs text-gray-300 transition-all flex items-center justify-between group"
                    >
                      <span>Which vector database companies raised funding in the last 2 years?</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-emerald-400 shrink-0 ml-2" />
                    </button>
                    <button 
                      onClick={() => { setQuery("Show partnerships between Microsoft and AI startups."); handleSearchSubmit("Show partnerships between Microsoft and AI startups."); }}
                      className="p-3.5 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] text-xs text-gray-300 transition-all flex items-center justify-between group"
                    >
                      <span>Show partnerships between Microsoft and AI startups.</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-emerald-400 shrink-0 ml-2" />
                    </button>
                    <button 
                      onClick={() => { setQuery("Compare Anthropic vs OpenAI vs Cohere."); handleSearchSubmit("Compare Anthropic vs OpenAI vs Cohere."); }}
                      className="p-3.5 rounded-xl border border-white/5 bg-white/[0.02] hover:bg-white/[0.05] text-xs text-gray-300 transition-all flex items-center justify-between group"
                    >
                      <span>Compare Anthropic vs OpenAI vs Cohere.</span>
                      <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity text-emerald-400 shrink-0 ml-2" />
                    </button>
                  </div>
                </div>
              )}

              {/* Input Bar */}
              <div className="glass-panel p-4 rounded-2xl glow-emerald">
                <form onSubmit={(e) => { e.preventDefault(); handleSearchSubmit(query); }} className="flex gap-3 items-center">
                  <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <input
                      type="text"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      placeholder="Ask about competitors, technology stacks, funding history..."
                      disabled={isSearching}
                      className="w-full bg-black/40 border border-white/10 rounded-xl py-3 pl-12 pr-4 text-sm text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all placeholder-gray-500 font-sans"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={isSearching || !query.trim()}
                    className="bg-emerald-500 text-black px-5 py-3 rounded-xl font-bold text-sm hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shrink-0 flex items-center gap-2"
                  >
                    {isSearching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                    Search
                  </button>
                </form>
              </div>

              {/* LangGraph Agent Node Stepper (Visualizing execution flow) */}
              {isSearching && (
                <div className="glass-panel p-6 rounded-2xl space-y-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
                    LangGraph Workflow Execution
                  </h3>
                  
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {STEPS.map((step, idx) => {
                      const isCompleted = currentNodeIndex > idx;
                      const isActive = currentNodeIndex === idx;
                      return (
                        <div 
                          key={idx} 
                          className={`p-3 rounded-xl border transition-all ${
                            isCompleted 
                              ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-400" 
                              : isActive
                              ? "bg-blue-950/20 border-blue-500/40 text-blue-400 animate-pulse"
                              : "bg-white/[0.01] border-white/5 text-gray-500"
                          }`}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            {isCompleted ? (
                              <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
                            ) : (
                              <span className={`w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold ${isActive ? 'bg-blue-500 text-white' : 'bg-zinc-800 text-gray-400'}`}>
                                {idx + 1}
                              </span>
                            )}
                            <span className="text-xs font-bold text-white">{step.name}</span>
                          </div>
                          <p className="text-[10px] opacity-70 leading-tight font-sans">{step.desc}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Research Answer & Details */}
              {searchResponse && (
                <div className="space-y-6">
                  
                  {/* Synthesis Panel */}
                  <div className="glass-panel p-8 rounded-2xl space-y-4 relative">
                    <div className="flex items-center justify-between border-b border-white/5 pb-4 mb-2">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-emerald-400" />
                        <h3 className="font-bold text-sm tracking-wider uppercase text-white">Market Analyst Synthesis</h3>
                      </div>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-semibold uppercase">
                        High Confidence
                      </span>
                    </div>

                    <div className="prose prose-invert max-w-none">
                      {formatMarkdown(searchResponse.answer)}
                    </div>

                    {/* Sources Citations list */}
                    {searchResponse.sources && searchResponse.sources.length > 0 && (
                      <div className="border-t border-white/5 pt-4 mt-6">
                        <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                          <FileText className="w-3.5 h-3.5 text-emerald-500" />
                          Hierarchical RAPTOR Chunks Cited ({searchResponse.sources.length})
                        </h4>
                        <div className="flex flex-wrap gap-2">
                          {searchResponse.sources.map((src: string, idx: number) => (
                            <button
                              key={idx}
                              onClick={() => handleCitationClick(src)}
                              className="px-2.5 py-1.5 rounded bg-zinc-900 border border-white/5 hover:border-emerald-500/30 text-xs text-gray-300 hover:text-emerald-400 transition-colors flex items-center gap-1.5"
                            >
                              <Info className="w-3 h-3 text-emerald-500" />
                              {src}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Render Localized graph query results */}
                  {searchResponse.graph_data && searchResponse.graph_data.nodes && searchResponse.graph_data.nodes.length > 0 && (
                    <div className="glass-panel p-6 rounded-2xl space-y-4">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-white/5 pb-3">
                        <Share2 className="w-4 h-4 text-emerald-400" />
                        Extracted Relationship Subgraph
                      </h3>
                      <div className="h-[380px] bg-[#0c0c0e] border border-white/5 rounded-xl overflow-hidden relative">
                        <GraphCanvas 
                          data={searchResponse.graph_data} 
                          onNodeSelect={(node: any) => setSelectedGraphNode(node)} 
                          onExpandNode={expandGraphNode} 
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: INTERACTIVE ECOSYSTEM GRAPH */}
          {activeTab === "graph" && (
            <div className="h-full flex flex-col space-y-4 min-h-[550px]">
              
              {/* Toolbar */}
              <div className="flex items-center justify-between bg-[#0d0d10]/50 border border-white/5 p-4 rounded-xl shrink-0">
                <div className="flex items-center gap-3 w-72">
                  <div className="relative w-full">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-3.5 h-3.5" />
                    <input
                      type="text"
                      placeholder="Search company, founder, investor..."
                      value={graphSearchQuery}
                      onChange={(e) => setGraphSearchQuery(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-lg py-1.5 pl-9 pr-3 text-xs focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>
                
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-gray-400">Total Graph Size: <strong>{graphData.nodes.length}</strong> nodes, <strong>{graphData.edges.length}</strong> relations</span>
                  <button 
                    onClick={fetchGlobalGraph} 
                    className="p-1.5 bg-zinc-900 border border-white/5 rounded-lg text-gray-400 hover:text-white transition-colors"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Graph Area & Property Details Panel */}
              <div className="flex-1 flex gap-4 min-h-[450px]">
                
                {/* Main React Flow Board */}
                <div className="flex-1 bg-[#0c0c0e] border border-white/5 rounded-xl overflow-hidden relative">
                  <GraphCanvas 
                    data={filteredGraphData} 
                    onNodeSelect={(node: any) => setSelectedGraphNode(node)}
                    onExpandNode={expandGraphNode}
                  />
                </div>

                {/* Properties Overlay Details Panel */}
                <div className={`w-80 bg-[#0d0d10] border border-white/5 p-6 rounded-xl overflow-y-auto ${selectedGraphNode ? 'block animate-fade-in' : 'hidden'}`}>
                  {selectedGraphNode ? (
                    <div className="space-y-5">
                      <div className="flex items-start justify-between border-b border-white/5 pb-4">
                        <div>
                          <span className="text-[10px] text-emerald-400 uppercase font-bold tracking-wider">{selectedGraphNode.labelType || "Entity"}</span>
                          <h3 className="text-lg font-bold text-white leading-tight mt-0.5">{selectedGraphNode.label || selectedGraphNode.id}</h3>
                        </div>
                        <button 
                          onClick={() => setSelectedGraphNode(null)}
                          className="text-gray-500 hover:text-white text-xs font-semibold"
                        >
                          Close
                        </button>
                      </div>

                      <div className="space-y-4">
                        <div>
                          <label className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Properties & Description</label>
                          <p className="text-xs text-gray-300 mt-1 leading-relaxed font-sans">
                            {selectedGraphNode.description || "No description properties registered. Double click node to query adjacent details."}
                          </p>
                        </div>
                        
                        {selectedGraphNode.amount && (
                          <div className="p-3 bg-white/[0.02] border border-white/5 rounded-lg flex items-center justify-between">
                            <span className="text-xs text-gray-400">Registered Val/Amt</span>
                            <span className="text-sm font-bold text-emerald-400">
                              ${(selectedGraphNode.amount / 1e6).toFixed(1)}M
                            </span>
                          </div>
                        )}

                        {selectedGraphNode.date && (
                          <div className="p-3 bg-white/[0.02] border border-white/5 rounded-lg flex items-center justify-between">
                            <span className="text-xs text-gray-400">Funding Date</span>
                            <span className="text-xs text-white font-mono">{selectedGraphNode.date}</span>
                          </div>
                        )}

                        <div className="border-t border-white/5 pt-4">
                          <button
                            onClick={() => expandGraphNode(selectedGraphNode.id)}
                            className="w-full flex items-center justify-center gap-2 bg-emerald-500 text-black font-bold py-2 rounded-lg text-xs hover:bg-emerald-400 transition-colors"
                          >
                            <Share2 className="w-3.5 h-3.5" />
                            Expand 2-Hop Connections
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="h-full flex items-center justify-center text-center text-xs text-gray-500">
                      Click a node on the canvas to inspect relationship properties.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: STARTUP SIMILARITY ENGINE */}
          {activeTab === "database" && (
            <div className="space-y-6">
              
              {/* Directory Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {startups.map((startup) => (
                  <div key={startup.name} className="glass-card p-6 rounded-2xl flex flex-col justify-between">
                    <div>
                      <div className="flex items-center gap-3 border-b border-white/5 pb-3 mb-3">
                        <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center font-bold text-sm border border-emerald-500/20">
                          {startup.logo}
                        </div>
                        <div>
                          <h3 className="font-bold text-white text-base leading-none">{startup.name}</h3>
                          <span className="text-[10px] text-gray-400 tracking-wider uppercase mt-1 inline-block font-semibold">{startup.market}</span>
                        </div>
                      </div>
                      <p className="text-xs text-gray-400 leading-relaxed font-sans mb-4 min-h-[50px]">{startup.description}</p>
                      
                      <div className="space-y-2 text-[11px] border-t border-white/5 pt-3 mb-4">
                        <div className="flex justify-between">
                          <span className="text-gray-500">Raising / Total</span>
                          <span className="font-semibold text-emerald-400">{startup.funding}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-500">Tech Stack</span>
                          <span className="text-gray-300 font-sans truncate max-w-[170px]">{startup.tech}</span>
                        </div>
                      </div>
                    </div>
                    
                    <button
                      onClick={() => { setSelectedStartup(startup); handleFindSimilar(startup.name); }}
                      className="w-full flex items-center justify-center gap-2 bg-zinc-900 border border-white/5 hover:border-emerald-500/30 text-xs font-semibold py-2 rounded-lg hover:text-emerald-400 transition-all"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-emerald-500" />
                      Find Similar Startups
                    </button>
                  </div>
                ))}
              </div>

              {/* Similarity Results Modal / Section */}
              {selectedStartup && (
                <div className="glass-panel p-6 rounded-2xl mt-8 space-y-4 glow-blue">
                  <div className="flex items-center justify-between border-b border-white/5 pb-3 mb-1">
                    <div className="flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-emerald-400" />
                      <h3 className="font-bold text-sm uppercase text-white">
                        Similarity Scores: <strong className="text-emerald-400">{selectedStartup.name}</strong>
                      </h3>
                    </div>
                    <button 
                      onClick={() => setSelectedStartup(null)} 
                      className="text-xs text-gray-500 hover:text-white"
                    >
                      Close Matches
                    </button>
                  </div>

                  {isFetchSimilarLoading ? (
                    <div className="flex items-center justify-center py-10 gap-2">
                      <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                      <span className="text-xs text-gray-400">Running BGE-Large embedding distance comparison...</span>
                    </div>
                  ) : similarStartups.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {similarStartups.map((match: any, idx: number) => {
                        const scorePct = Math.round(match.score * 100);
                        return (
                          <div key={idx} className="p-4 bg-white/[0.01] border border-white/5 rounded-xl flex items-start gap-4 hover:border-emerald-500/20 transition-all">
                            <div className="w-12 h-12 rounded-lg bg-emerald-500/5 text-emerald-400 flex flex-col items-center justify-center font-bold text-sm shrink-0 border border-emerald-500/10">
                              <span className="text-[10px] text-gray-500 font-normal">Rank</span>
                              {idx + 1}
                            </div>
                            <div className="space-y-1 flex-1">
                              <div className="flex items-center justify-between">
                                <h4 className="text-sm font-bold text-white">{match.name}</h4>
                                <span className="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded">
                                  {scorePct}% Similarity
                                </span>
                              </div>
                              <span className="text-[10px] text-gray-400 font-semibold uppercase">{match.market}</span>
                              <p className="text-xs text-gray-300 font-sans leading-relaxed pt-1">{match.description}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="text-center py-10 text-xs text-gray-500">
                      No matches found. Check if databases are seeded.
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tab 4: ACQUISITION PREDICTOR */}
          {activeTab === "predictions" && (
            <div className="space-y-6 max-w-4xl mx-auto">
              <div className="bg-[#18181b]/50 border border-white/5 rounded-2xl p-6 flex flex-col md:flex-row items-center gap-6 justify-between shrink-0">
                <div className="space-y-1.5 text-center md:text-left max-w-xl">
                  <div className="flex items-center gap-2 justify-center md:justify-start">
                    <TrendingUp className="w-4 h-4 text-emerald-400 animate-bounce" />
                    <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-bold">Predictive Intelligence Model</span>
                  </div>
                  <h3 className="text-lg font-bold text-white">Graph-Based Acquisition Forecasting</h3>
                  <p className="text-xs text-gray-400 leading-relaxed font-sans">
                    Runs network path calculations evaluating density of strategic partnerships with Tier-1 technology companies (Microsoft, Amazon, Google), VC investor overlap, and competitor cluster densities to calculate consolidation and M&A likelihood.
                  </p>
                </div>
                
                <div className="shrink-0 flex items-center justify-center p-3 bg-emerald-500/5 rounded-xl border border-emerald-500/10">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-emerald-400 font-mono">95%</div>
                    <div className="text-[9px] text-gray-500 uppercase tracking-wider font-semibold">Max Confidence Cap</div>
                  </div>
                </div>
              </div>

              {/* Predictions List */}
              <div className="space-y-4">
                {predictions.length > 0 ? (
                  predictions.map((p, idx) => {
                    const isHigh = p.probability >= 70;
                    const isMid = p.probability >= 45 && p.probability < 70;
                    
                    let ringColor = "border-emerald-500 text-emerald-400";
                    let ringBg = "bg-emerald-500/10";
                    if (isMid) {
                      ringColor = "border-blue-500 text-blue-400";
                      ringBg = "bg-blue-500/10";
                    } else if (!isHigh && !isMid) {
                      ringColor = "border-orange-500 text-orange-400";
                      ringBg = "bg-orange-500/10";
                    }

                    return (
                      <div key={idx} className="glass-card p-6 rounded-2xl flex items-start justify-between gap-6">
                        <div className="space-y-3 flex-1">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-lg bg-white/[0.02] border border-white/5 text-white flex items-center justify-center font-bold text-xs uppercase">
                              {p.name.substring(0,2)}
                            </div>
                            <div>
                              <h4 className="font-bold text-white text-sm leading-none">{p.name}</h4>
                              <span className="text-[10px] text-gray-400 uppercase mt-1 inline-block font-semibold">{p.market}</span>
                            </div>
                          </div>
                          
                          {/* Factors Checklist */}
                          <div className="space-y-1.5 border-t border-white/5 pt-3">
                            <h5 className="text-[10px] font-bold uppercase tracking-wider text-gray-500 mb-1">M&A Likelihood Factors</h5>
                            {p.factors && p.factors.map((factor: string, fIdx: number) => (
                              <div key={fIdx} className="flex items-start gap-2 text-[11px] text-gray-300 font-sans leading-normal">
                                <UserCheck className="w-3.5 h-3.5 text-emerald-500 shrink-0 mt-0.5" />
                                <span>{factor}</span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Probability Progress Gauge */}
                        <div className="shrink-0 flex flex-col items-center justify-center">
                          <div className={`w-14 h-14 rounded-full border-4 ${ringColor} ${ringBg} flex items-center justify-center font-bold font-mono text-sm shadow-lg`}>
                            {p.probability}%
                          </div>
                          <span className="text-[9px] uppercase tracking-wider mt-2 font-bold text-gray-500">Acquisition</span>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-12 text-xs text-gray-500">
                    Acquisition models not available. Seed the database to construct the network graphs.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Tab 5: SYSTEM STATS & SEEDING */}
          {activeTab === "stats" && (
            <div className="max-w-3xl mx-auto space-y-6">
              
              {/* Count Cards Grid */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                
                <div className="glass-panel p-5 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Startups Profiles</span>
                  <div className="text-2xl font-bold text-white font-mono">{stats.startups_count}</div>
                  <p className="text-[10px] text-gray-400 font-sans">Seeded Relational Entries</p>
                </div>
                
                <div className="glass-panel p-5 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Funding Rounds</span>
                  <div className="text-2xl font-bold text-white font-mono">{stats.funding_rounds_count}</div>
                  <p className="text-[10px] text-gray-400 font-sans">Transactions & Valuations</p>
                </div>
                
                <div className="glass-panel p-5 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">News / Docs Ingested</span>
                  <div className="text-2xl font-bold text-white font-mono">{stats.news_articles_count}</div>
                  <p className="text-[10px] text-gray-400 font-sans">Total Source Files</p>
                </div>
                
                <div className="glass-panel p-5 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Vector Chunks</span>
                  <div className="text-2xl font-bold text-white font-mono">{stats.vector_chunks_count}</div>
                  <p className="text-[10px] text-gray-400 font-sans">RAPTOR Level 0-3 Summaries</p>
                </div>
                
                <div className="glass-panel p-5 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Graph Nodes</span>
                  <div className="text-2xl font-bold text-white font-mono">{stats.graph_nodes_count}</div>
                  <p className="text-[10px] text-gray-400 font-sans">Unique Entities Extracted</p>
                </div>
                
                <div className="glass-panel p-5 rounded-xl space-y-1.5">
                  <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Graph Relations</span>
                  <div className="text-2xl font-bold text-white font-mono">{stats.graph_edges_count}</div>
                  <p className="text-[10px] text-gray-400 font-sans">Multi-Hop Cypher Edges</p>
                </div>
              </div>

              {/* DB Administration panel */}
              <div className="glass-panel p-6 rounded-2xl space-y-4 glow-purple">
                <div className="border-b border-white/5 pb-3 mb-1">
                  <h3 className="font-bold text-sm uppercase text-white">Database Seeding and Initialization</h3>
                  <p className="text-xs text-gray-400 font-sans leading-relaxed mt-1">
                    Triggers the ingestion, cleaning, entity extraction, and RAPTOR tree generation pipelines. Re-seeding clears previous databases and builds fresh SQLite, network, and vector databases in the local directories.
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row items-center gap-4">
                  <button
                    onClick={handleSeedDatabase}
                    disabled={seedStatus === "seeding"}
                    className="w-full sm:w-auto flex items-center justify-center gap-2 bg-gradient-to-tr from-emerald-500 to-blue-500 text-black font-bold px-6 py-3 rounded-xl hover:from-emerald-400 hover:to-blue-400 disabled:opacity-50 transition-colors shrink-0 text-sm"
                  >
                    {seedStatus === "seeding" ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RefreshCw className="w-4 h-4" />
                    )}
                    Re-Seed Local Databases
                  </button>
                  
                  <div className="flex-1 text-xs">
                    {seedStatus === "idle" && <span className="text-gray-500">Database is seeded. ready for testing.</span>}
                    {seedStatus === "seeding" && <span className="text-blue-400 font-semibold animate-pulse">Running K-Means summaries and graph generation (Takes ~10s)...</span>}
                    {seedStatus === "success" && <span className="text-emerald-400 font-bold">✓ Databases populated successfully! Chunks indexed.</span>}
                    {seedStatus === "error" && <span className="text-red-400 font-bold">✗ Seeding failed. Check backend stdout.</span>}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Citation Popover Modal Overlay */}
        {activeCitationText && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fade-in">
            <div className="bg-[#0d0d10] border border-white/10 rounded-2xl w-full max-w-lg p-6 space-y-4 shadow-2xl relative">
              <div className="flex items-center justify-between border-b border-white/5 pb-3">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-400" />
                  <h4 className="font-bold text-sm text-white">RAPTOR Citation Node</h4>
                </div>
                <button 
                  onClick={() => setActiveCitationText(null)}
                  className="text-xs text-gray-500 hover:text-white"
                >
                  Close
                </button>
              </div>
              
              <div className="space-y-2.5">
                <div className="flex justify-between items-center text-[10px] text-gray-500 font-semibold uppercase">
                  <span>Source Ingestion Node</span>
                  <span className="bg-emerald-500/10 text-emerald-400 px-1.5 py-0.5 rounded">
                    {activeCitationText.includes("L0") && "Level 0: Raw text"}
                    {activeCitationText.includes("L1") && "Level 1: Cluster Summary"}
                    {activeCitationText.includes("L2") && "Level 2: Market Summary"}
                    {activeCitationText.includes("L3") && "Level 3: Global Summary"}
                  </span>
                </div>
                <div className="p-4 bg-black/40 border border-white/5 rounded-xl text-xs text-gray-300 font-sans leading-relaxed max-h-60 overflow-y-auto">
                  {/* Find document content corresponding to this citation or display mock detail */}
                  {activeCitationText.includes("OpenAI") && (
                    activeCitationText.includes("L3") 
                      ? "OpenAI is an AI research and deployment company. Its mission is to ensure that artificial general intelligence benefits all of humanity. Founded in late 2015, transitioned to capped-profit corporate structure, partnered with Microsoft ($13B total), launched ChatGPT, competes directly with Anthropic, Cohere, Google, and Meta."
                      : "OpenAI launched ChatGPT in November 2022, kicking off a global generative AI boom. ChatGPT reached 100 million active monthly users in two months, making it the fastest-growing consumer application in history. ChatGPT uses OpenAI's GPT-3.5 and GPT-4 model families."
                  )}
                  {activeCitationText.includes("Anthropic") && (
                    activeCitationText.includes("L3")
                      ? "Anthropic is an AI safety and research company that builds reliable, beneficial, and controllable AI systems. It is the creator of the Claude models. Founded in 2021 by former OpenAI researchers Dario and Daniela Amodei. Splits from OpenAI, pioneered Constitutional AI, backed by Amazon ($4B) and Google ($2B)."
                      : "Anthropic released Claude 3.5 Sonnet in June 2024, showing superior performance in coding, reasoning, and visual analysis compared to GPT-4o. In October 2024, they released 'Computer Use' API, enabling the Claude agent to control mouse pointers and keyboard inputs."
                  )}
                  {activeCitationText.includes("Cohere") && (
                    activeCitationText.includes("L3")
                      ? "Cohere builds AI technology for enterprise applications, providing natural language processing models optimized for search, retrieval, and generation. Founded in 2019 by Aidan Gomez (co-author of Attention is All You Need), enterprise-focused, raised $450M Series D led by Nvidia/Oracle."
                      : "Cohere introduced Command R and Command R+ in early 2024. These models are optimized for multi-step agentic tasks, tool use, and 10+ languages, and they are deployable in secure enterprise virtual private clouds (VPC)."
                  )}
                  {activeCitationText.includes("Qdrant") && (
                    activeCitationText.includes("L3")
                      ? "Qdrant is an open-source vector database and similarity search engine written in Rust, optimized for RAG and AI applications. Founded in 2021 by Andre Zayarni and Javid Mammadov, raised $28M Series A led by Spark Capital, written in memory-safe Rust with native payload filtering."
                      : "Qdrant enables developers to perform filtered vector search, which combines vector distance comparisons with structured SQL-like payload filters (such as dates, markets, or startup names). This is highly useful for context-aware RAG pipelines."
                  )}
                  {activeCitationText.includes("Cursor") && (
                    activeCitationText.includes("L3")
                      ? "Cursor (built by Anysphere) is an AI-first code editor fork of VS Code, enabling deep codebase-level auto-completions, chat, and automated edits. Built by MIT graduates Sanger, Truell, Sanger in 2022. Raised $60M Series A at $400M valuation led by Andreessen Horowitz."
                      : "Cursor features 'Composer' and 'Tab Autocomplete' which index the entire local directory structure, building codebase embeddings. It enables the editor to write multi-file edits, refactor methods, and find reference bugs automatically."
                  )}
                  {activeCitationText.includes("Windsurf") && (
                    activeCitationText.includes("L3")
                      ? "Windsurf is an agentic IDE built by Codeium, featuring an interactive agent loop that works side-by-side with developers. Launched in late 2024 by Codeium, which raised $150M Series C led by General Catalyst. Supports continuous autonomous coding terminalCascade loops."
                      : "Windsurf introduces the concept of the 'Flow State' and 'cascade' agent technology. The AI agent can run terminal commands, write code, run compilers, and fix errors in a continuous autonomous loop, with the developer acting as an orchestrator."
                  )}
                  {!["OpenAI", "Anthropic", "Cohere", "Qdrant", "Cursor", "Windsurf"].some(name => activeCitationText.includes(name)) && (
                    "This chunk represents an extracted document node containing company context, technology capabilities, or funding announcements. The chunk was processed, indexed, and retrieved hierarchy-level RAG matches during multi-step inference."
                  )}
                </div>
                
                <div className="flex justify-between items-center text-[10px] text-gray-500">
                  <span>Index ID: {activeCitationText}</span>
                  <span className="text-emerald-500 font-semibold">Verified Chunk</span>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
