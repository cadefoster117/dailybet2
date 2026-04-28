
"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Trophy, Flame, Target, BarChart3, Sparkles, TrendingUp,
  ChevronRight, RefreshCw, Clock, Shield, Zap, Loader2
} from "lucide-react";

// ── Types ──
interface Pick {
  match_id: number;
  home_team: string;
  away_team: string;
  league: string;
  kickoff: string;
  market: string;
  selection: string;
  odds: number;
  confidence: number;
  ml_prob: number;
  value_score: number;
  reasoning: string;
  home_logo: string;
  away_logo: string;
  league_logo: string;
}

interface Acca {
  name: string;
  icon: string;
  picks: Pick[];
  total_odds: number;
  combined_confidence: number;
  description: string;
}

interface AccaData {
  date: string;
  accas: Acca[];
  total_matches_analyzed: number;
  generated_at: string;
}

interface MatchResult {
  home_team: string;
  away_team: string;
  league: string;
  score: string;
  date: string;
  btts: boolean;
  over25: boolean;
  home_win: boolean;
  away_win: boolean;
  draw: boolean;
}

interface StatsData {
  period_days: number;
  total_matches: number;
  btts_rate: number;
  over25_rate: number;
  home_win_rate: number;
  away_win_rate: number;
  draw_rate: number;
  avg_goals: number;
  recent_results: MatchResult[];
}

// ── Icon map ──
const iconMap: Record<string, React.ReactNode> = {
  trophy: <Trophy className="w-5 h-5" />,
  flame: <Flame className="w-5 h-5" />,
  target: <Target className="w-5 h-5" />,
  "bar-chart": <BarChart3 className="w-5 h-5" />,
  sparkles: <Sparkles className="w-5 h-5" />,
};

// ── Tab config ──
const tabs = [
  { id: 0, label: "ACCA", shortLabel: "Acca", icon: <Trophy className="w-4 h-4" /> },
  { id: 1, label: "BTTS+O2.5", shortLabel: "BTTS", icon: <Flame className="w-4 h-4" /> },
  { id: 2, label: "WIN+BTTS", shortLabel: "Win", icon: <Target className="w-4 h-4" /> },
  { id: 3, label: "O2.5", shortLabel: "O2.5", icon: <BarChart3 className="w-4 h-4" /> },
  { id: 4, label: "LUCKY 6", shortLabel: "L6", icon: <Sparkles className="w-4 h-4" /> },
  { id: 5, label: "STATS", shortLabel: "Stats", icon: <TrendingUp className="w-4 h-4" /> },
];

// ── PickCard ──
function PickCard({ pick, index }: { pick: Pick; index: number }) {
  const kickoffTime = new Date(pick.kickoff).toLocaleTimeString("en-GB", {
    hour: "2-digit", minute: "2-digit",
  });
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.4 }}
      className="ticket-border rounded-lg p-3 bg-[var(--bg-card)] hover:bg-[var(--bg-card-hover)] transition-all duration-300 cursor-pointer"
    >
      {/* League + Time */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          {pick.league_logo && (
            <img src={pick.league_logo} alt="" className="w-4 h-4 rounded-sm" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          )}
          <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-medium">{pick.league}</span>
        </div>
        <div className="flex items-center gap-1 text-[10px] text-[var(--text-muted)]">
          <Clock className="w-3 h-3" />
          {kickoffTime}
        </div>
      </div>
      
      {/* Teams */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          {pick.home_logo && (
            <img src={pick.home_logo} alt="" className="w-5 h-5 rounded-sm flex-shrink-0" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          )}
          <span className="text-xs font-semibold truncate">{pick.home_team}</span>
        </div>
        <span className="text-[10px] text-[var(--text-muted)] mx-2 flex-shrink-0">vs</span>
        <div className="flex items-center gap-2 flex-1 min-w-0 justify-end">
          <span className="text-xs font-semibold truncate text-right">{pick.away_team}</span>
          {pick.away_logo && (
            <img src={pick.away_logo} alt="" className="w-5 h-5 rounded-sm flex-shrink-0" onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
          )}
        </div>
      </div>
      
      {/* Selection + Odds */}
      <div className="flex items-center justify-between">
        <div className="flex-1 min-w-0">
          <div className="text-[11px] text-[var(--green-text)] font-bold truncate">{pick.selection}</div>
          <div className="text-[9px] text-[var(--text-muted)] mt-0.5 truncate">{pick.reasoning}</div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          <div className="text-[9px] text-[var(--text-muted)] flex items-center gap-1">
            <Shield className="w-3 h-3" />
            {pick.confidence.toFixed(0)}%
          </div>
          <div className="odds-badge px-2 py-0.5 rounded text-xs">
            {pick.odds.toFixed(2)}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

// ── AccaView ──
function AccaView({ acca }: { acca: Acca }) {
  return (
    <motion.div
      key={acca.name}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="px-4 pb-28"
    >
      {/* Header card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="card-glow rounded-xl p-4 bg-gradient-to-br from-[#0a1610] to-[#0f251a] border border-[var(--border-main)] mb-4"
      >
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-[var(--green-dim)] flex items-center justify-center text-[var(--green-neon)]">
            {iconMap[acca.icon] || <Zap className="w-5 h-5" />}
          </div>
          <div>
            <h2 className="font-[var(--font-heading)] text-lg font-bold text-[var(--green-neon)] glow-green" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              {acca.name}
            </h2>
            <p className="text-[10px] text-[var(--text-muted)]">{acca.description}</p>
          </div>
        </div>
        <div className="flex items-center gap-4 mt-3">
          <div className="flex-1 bg-[var(--bg-deep)] rounded-lg p-2 text-center">
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Total Odds</div>
            <div className="text-lg font-bold text-[var(--green-neon)] glow-green" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              {acca.total_odds.toFixed(2)}
            </div>
          </div>
          <div className="flex-1 bg-[var(--bg-deep)] rounded-lg p-2 text-center">
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Confidence</div>
            <div className="text-lg font-bold text-[var(--green-text)]" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              {acca.combined_confidence.toFixed(0)}%
            </div>
          </div>
          <div className="flex-1 bg-[var(--bg-deep)] rounded-lg p-2 text-center">
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-wider">Picks</div>
            <div className="text-lg font-bold text-[var(--text-primary)]" style={{ fontFamily: "'Orbitron', sans-serif" }}>
              {acca.picks.length}
            </div>
          </div>
        </div>
      </motion.div>
      
      {/* Picks */}
      <div className="space-y-2">
        {acca.picks.map((pick, i) => (
          <PickCard key={pick.match_id + pick.selection} pick={pick} index={i} />
        ))}
      </div>
      
      {acca.picks.length === 0 && (
        <div className="text-center py-12 text-[var(--text-muted)]">
          <Zap className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No picks available for this acca type today</p>
        </div>
      )}
    </motion.div>
  );
}

// ── StatsView ──
function StatsView({ stats }: { stats: StatsData | null; }) {
  if (!stats) return (
    <div className="flex items-center justify-center py-20">
      <Loader2 className="w-6 h-6 animate-spin text-[var(--green-neon)]" />
    </div>
  );
  
  const statCards = [
    { label: "BTTS Rate", value: `${stats.btts_rate}%`, color: "var(--green-neon)" },
    { label: "Over 2.5 Rate", value: `${stats.over25_rate}%`, color: "var(--green-text)" },
    { label: "Home Win", value: `${stats.home_win_rate}%`, color: "var(--blue-accent)" },
    { label: "Away Win", value: `${stats.away_win_rate}%`, color: "var(--orange-accent)" },
    { label: "Draw Rate", value: `${stats.draw_rate}%`, color: "var(--text-muted)" },
    { label: "Avg Goals", value: stats.avg_goals.toFixed(1), color: "var(--green-neon)" },
  ];
  
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="px-4 pb-28"
    >
      <div className="mb-4">
        <h2 className="text-lg font-bold text-[var(--green-neon)] glow-green mb-1" style={{ fontFamily: "'Orbitron', sans-serif" }}>
          Statistics
        </h2>
        <p className="text-[10px] text-[var(--text-muted)]">
          Last {stats.period_days} days — {stats.total_matches} matches analyzed
        </p>
      </div>
      
      {/* Stat Grid */}
      <div className="grid grid-cols-3 gap-2 mb-4">
        {statCards.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className="bg-[var(--bg-card)] border border-[var(--border-main)] rounded-lg p-3 text-center"
          >
            <div className="text-[8px] text-[var(--text-muted)] uppercase tracking-wider mb-1">{s.label}</div>
            <div className="text-lg font-bold" style={{ color: s.color, fontFamily: "'Orbitron', sans-serif" }}>
              {s.value}
            </div>
          </motion.div>
        ))}
      </div>
      
      {/* Recent Results */}
      <h3 className="text-xs font-bold text-[var(--text-secondary)] mb-2 uppercase tracking-wider">Recent Results</h3>
      <div className="space-y-1.5">
        {stats.recent_results.slice(0, 15).map((r, i) => (
          <motion.div
            key={`${r.home_team}-${r.away_team}-${i}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className="flex items-center justify-between bg-[var(--bg-card)] border border-[var(--border-main)] rounded-md px-3 py-2"
          >
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-medium truncate">
                {r.home_team} <span className="text-[var(--green-neon)] font-bold mx-1">{r.score}</span> {r.away_team}
              </div>
              <div className="text-[8px] text-[var(--text-muted)]">{r.league} — {r.date}</div>
            </div>
            <div className="flex gap-1 flex-shrink-0 ml-2">
              {r.btts && <span className="text-[8px] bg-[var(--green-dim)] text-[var(--green-neon)] px-1.5 py-0.5 rounded">BTTS</span>}
              {r.over25 && <span className="text-[8px] bg-[rgba(59,130,246,0.15)] text-[var(--blue-accent)] px-1.5 py-0.5 rounded">O2.5</span>}
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

// ── Loading Skeleton ──
function LoadingSkeleton() {
  return (
    <div className="px-4 pb-28">
      <div className="shimmer-bg rounded-xl h-36 mb-4 bg-[var(--bg-card)]" />
      {[0, 1, 2].map((i) => (
        <div key={i} className="shimmer-bg rounded-lg h-24 mb-2 bg-[var(--bg-card)]" style={{ animationDelay: `${i * 0.2}s` }} />
      ))}
    </div>
  );
}

// ── Main Page ──
export default function Home() {
  const [activeTab, setActiveTab] = useState(0);
  const [accaData, setAccaData] = useState<AccaData | null>(null);
  const [statsData, setStatsData] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const loadAccas = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/accas", { method: "POST" });
      if (!res.ok) throw new Error("Failed to load accas");
      const data = await res.json();
      setAccaData(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  };
  
  const loadStats = async () => {
    try {
      const res = await fetch("/api/stats", { method: "POST" });
      if (!res.ok) throw new Error("Failed to load stats");
      const data = await res.json();
      setStatsData(data);
    } catch {
      // Stats are secondary
    }
  };
  
  useEffect(() => {
    loadAccas();
  }, []);
  
  useEffect(() => {
    if (activeTab === 5) loadStats();
  }, [activeTab]);
  
  const currentAcca = accaData?.accas?.[activeTab] ?? null;
  
  return (
    <main className="max-w-lg mx-auto relative min-h-screen">
      {/* Header */}
      <div className="sticky top-0 z-30 bg-[var(--bg-deep)] border-b border-[var(--border-main)] px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--green-neon)] to-[var(--green-mid)] flex items-center justify-center">
              <Zap className="w-4 h-4 text-[var(--bg-deep)]" />
            </div>
            <div>
              <h1 className="text-sm font-black tracking-wider text-[var(--green-neon)] glow-green" style={{ fontFamily: "'Orbitron', sans-serif" }}>
                DailyBET
              </h1>
              <p className="text-[8px] text-[var(--text-muted)] uppercase tracking-widest">AI Accumulators</p>
            </div>
          </div>
          <button
            onClick={loadAccas}
            disabled={loading}
            className="w-8 h-8 rounded-lg bg-[var(--bg-card)] border border-[var(--border-main)] flex items-center justify-center text-[var(--text-muted)] hover:text-[var(--green-neon)] hover:border-[var(--green-neon)] transition-all cursor-pointer active:scale-95"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
        
        {/* Date + Matches */}
        {accaData && (
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[9px] text-[var(--text-muted)]">
              {new Date(accaData.date).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" })}
            </span>
            <span className="text-[9px] text-[var(--green-dim)]">|</span>
            <span className="text-[9px] text-[var(--green-text)]">{accaData.total_matches_analyzed} matches analyzed</span>
          </div>
        )}
      </div>
      
      {/* Content */}
      <div className="pt-3">
        {error && (
          <div className="mx-4 p-3 rounded-lg bg-[rgba(239,68,68,0.1)] border border-[rgba(239,68,68,0.3)] text-[var(--red-accent)] text-xs mb-3">
            {error}
            <button onClick={loadAccas} className="ml-2 underline cursor-pointer">Retry</button>
          </div>
        )}
        
        <AnimatePresence mode="wait">
          {loading ? (
            <LoadingSkeleton key="loading" />
          ) : activeTab === 5 ? (
            <StatsView key="stats" stats={statsData} />
          ) : currentAcca ? (
            <AccaView key={currentAcca.name} acca={currentAcca} />
          ) : (
            <div key="empty" className="text-center py-20 text-[var(--text-muted)]">
              <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-sm">No data available</p>
            </div>
          )}
        </AnimatePresence>
      </div>
      
      {/* Bottom Tab Bar */}
      <div className="fixed bottom-0 left-0 right-0 z-40 bg-[var(--bg-deep)] border-t border-[var(--border-main)] safe-bottom">
        <div className="max-w-lg mx-auto flex">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex flex-col items-center gap-0.5 py-2 transition-all cursor-pointer active:scale-95 ${
                activeTab === tab.id
                  ? "text-[var(--green-neon)]"
                  : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              }`}
            >
              {tab.icon}
              <span className="text-[8px] font-medium tracking-wider uppercase">{tab.shortLabel}</span>
              {activeTab === tab.id && (
                <motion.div
                  layoutId="tab-indicator"
                  className="w-4 h-0.5 bg-[var(--green-neon)] rounded-full"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}

