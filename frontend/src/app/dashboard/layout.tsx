"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { motion, AnimatePresence, useMotionValue, useTransform, animate } from "framer-motion";
import { swrFetcher } from "@/lib/gateway";

const TABS = [
  { href: "/dashboard/neural-link", label: "Neural Link", icon: "🔗" },
  { href: "/dashboard/jornadas", label: "Jornadas", icon: "🗺️" },
  { href: "/dashboard/bunker-ops", label: "Bunker Ops", icon: "🛡️" },
  { href: "/dashboard/agent-lab", label: "Agent Lab", icon: "🧪" },
  { href: "/dashboard/chat", label: "Chat", icon: "💬" },
  { href: "/dashboard/kpi", label: "KPI", icon: "📊" },
];

function NumberTicker({ value, prefix = "", suffix = "", decimals = 0 }: { value: number, prefix?: string, suffix?: string, decimals?: number }) {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) => prefix + latest.toFixed(decimals) + suffix);

  useEffect(() => {
    const controls = animate(count, value, { duration: 0.5 });
    return controls.stop;
  }, [value, count]);

  return <motion.span>{rounded}</motion.span>;
}

function useLiveMetrics() {
  const { data: crmStats } = useSWR<{ total_leads?: number }>(
    "/api/v1/crm/stats",
    swrFetcher,
    { refreshInterval: 30000, dedupingInterval: 5000 }
  );
  const { data: clusterHealth } = useSWR<{
    tests?: number;
    agents?: number;
    costPerReq?: number;
    cacheRate?: number;
    summary?: { total?: number };
    services?: Record<string, unknown>;
  }>(
    "/api/v1/cluster/health",
    swrFetcher,
    { refreshInterval: 30000, dedupingInterval: 5000 }
  );
  const { data: pipelineStats } = useSWR<{
    avg_cost?: number;
    cache_hit_rate?: number;
  }>(
    "/api/v1/pipeline/stats",
    swrFetcher,
    { refreshInterval: 30000, dedupingInterval: 5000 }
  );

  const tests = clusterHealth?.tests ?? clusterHealth?.summary?.total ?? 0;
  const agents =
    clusterHealth?.agents ??
    (clusterHealth?.services ? Object.keys(clusterHealth.services).length : 0);
  const leads = crmStats?.total_leads ?? 0;
  const costPerReq =
    pipelineStats?.avg_cost ?? clusterHealth?.costPerReq ?? 0;
  const cacheRate =
    typeof pipelineStats?.cache_hit_rate === "number"
      ? pipelineStats.cache_hit_rate * 100
      : clusterHealth?.cacheRate ?? 0;

  return { tests, agents, leads, costPerReq, cacheRate };
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const metrics = useLiveMetrics();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close menu on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Global Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && !e.altKey && !e.metaKey && !e.shiftKey) {
        const idx = parseInt(e.key, 10) - 1;
        if (idx >= 0 && idx < TABS.length) {
          e.preventDefault();
          router.push(TABS[idx].href);
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [router]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header
        className="sticky top-0 z-10 px-6 py-4 border-b border-[var(--color-border)] animate-gradient"
        style={{
          background: "linear-gradient(135deg, var(--color-bg) 0%, var(--color-surface) 100%)",
          backgroundSize: "200% 200%",
          borderColor: "var(--color-border)",
        }}
      >
        <div className="max-w-7xl mx-auto flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <Link href="/dashboard" className="flex items-center gap-2">
              <span className="text-xl font-bold text-[var(--color-text)]">
                Sovereign Hub
              </span>
              <span className="text-xs font-mono text-[var(--color-text-muted)] hidden sm:inline-block">
                Neural Link
              </span>
            </Link>

            {/* Desktop Nav */}
            <nav className="hidden md:flex gap-1">
              {TABS.map(({ href, label, icon }) => {
                const active = pathname.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    title={`Ctrl+${TABS.indexOf({ href, label, icon }) + 1}`}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors relative group ${active
                      ? "bg-[var(--color-surface-alt)] text-[var(--color-text)]"
                      : "text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-alt)]"
                      }`}
                  >
                    <span className="mr-1.5">{icon}</span>
                    {label}
                    <span className="absolute -top-8 left-1/2 -translate-x-1/2 px-2 py-1 bg-[var(--color-surface)] border border-[var(--color-border)] text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
                      Ctrl+{TABS.indexOf({ href, label, icon }) + 1}
                    </span>
                  </Link>
                );
              })}
            </nav>

            {/* Mobile Nav Toggle */}
            <button
              className="md:hidden p-2 text-[var(--color-text)]"
              onClick={() => setMenuOpen(!menuOpen)}
            >
              {menuOpen ? (
                <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
              ) : (
                <svg width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" /></svg>
              )}
            </button>
          </div>

          {/* Mobile Nav Dropdown */}
          <AnimatePresence>
            {menuOpen && (
              <motion.nav
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="flex flex-col gap-1 md:hidden overflow-hidden"
              >
                {TABS.map(({ href, label, icon }) => {
                  const active = pathname.startsWith(href);
                  return (
                    <Link
                      key={href}
                      href={href}
                      className={`px-4 py-3 rounded-lg text-sm font-medium transition-colors ${active
                        ? "bg-[var(--color-surface-alt)] text-[var(--color-text)]"
                        : "text-[var(--color-text-muted)]"
                        }`}
                    >
                      <span className="mr-2">{icon}</span>
                      {label}
                    </Link>
                  );
                })}
              </motion.nav>
            )}
          </AnimatePresence>

          {/* Live metrics row */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs font-mono text-[var(--color-text-secondary)]">
            <span><NumberTicker value={metrics.tests} /> tests</span>
            <span className="text-[var(--color-border)]">|</span>
            <span><NumberTicker value={metrics.agents} /> agents</span>
            <span className="text-[var(--color-border)]">|</span>
            <span><NumberTicker value={metrics.leads} /> leads</span>
            <span className="text-[var(--color-border)] hidden sm:inline">|</span>
            <span className="hidden sm:inline"><NumberTicker value={metrics.costPerReq} prefix="$" decimals={3} /> avg/req</span>
            <span className="text-[var(--color-border)] hidden sm:inline">|</span>
            <span className="hidden sm:inline">Cache: <NumberTicker value={metrics.cacheRate} suffix="%" /></span>
          </div>
        </div>
      </header>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={pathname}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full"
          >
            {children}
          </motion.div>
        </AnimatePresence>
      </main>
      <GlobalToasts />
    </div>
  );
}

import { useCrmWebSocket } from "@/modules/crm/hooks/useCrmWebSocket";
import { useRef } from "react";

function GlobalToasts() {
  const { events } = useCrmWebSocket();
  const [toasts, setToasts] = useState<{ id: string, type: string }[]>([]);
  const lastEventRef = useRef<any>(null);

  useEffect(() => {
    if (events.length > 0 && events[0] !== lastEventRef.current) {
      lastEventRef.current = events[0];
      const newToast = { id: Math.random().toString(), type: String(events[0].type || "UPDATE") };
      setToasts((p) => [newToast, ...p].slice(0, 3));
      setTimeout(() => {
        setToasts((p) => p.filter((t) => t.id !== newToast.id));
      }, 4000);
    }
  }, [events]);

  return (
    <div className="fixed top-20 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, x: 50, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, x: 20 }}
            className="pointer-events-auto bg-[var(--color-surface)] border-l-[3px] border-[var(--color-accent)] p-3 rounded-lg shadow-2xl text-xs min-w-[200px]"
          >
            <div className="font-bold text-[var(--color-text)] mb-0.5 tracking-wider uppercase text-[9px] opacity-80">Notification</div>
            <div className="text-[var(--color-text-secondary)] font-mono text-[10px] break-all">{t.type}</div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
