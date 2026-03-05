"use client";

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useCrmLeads } from "./hooks/useCrmApi";
import { useCrmWebSocket } from "./hooks/useCrmWebSocket";
import { searchCrmLeads, updateCrmLead, deleteCrmLead, fetchLeadScore } from "@/lib/gateway";
import type { CrmLead, CrmLeadCreate } from "@/types/crm";

type SortKey = keyof Pick<
  CrmLead,
  "name" | "email" | "company" | "trust" | "interaction_count" | "source_channel" | "created_at"
>;

function LeadTrustRing({ trust, leadId, interactionCount }: { trust: number, leadId: string, interactionCount: number }) {
  const [scoreInfo, setScoreInfo] = useState<any>(null);
  const [hover, setHover] = useState(false);

  useEffect(() => {
    if (hover && !scoreInfo) {
      fetchLeadScore(leadId).then(setScoreInfo).catch(() => { });
    }
  }, [hover, leadId, scoreInfo]);

  const color = trust >= 0.7 ? "var(--color-success)" : trust >= 0.3 ? "var(--color-warning)" : "var(--color-error)";
  const dashArray = `${trust * 100} 100`;

  // Mock trend based on UX
  const trend = (interactionCount % 3 === 0) ? 'up' : (interactionCount % 2 === 0) ? 'down' : 'flat';

  return (
    <div
      className="relative inline-flex items-center justify-center w-8 h-8 group"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <svg viewBox="0 0 36 36" className="w-8 h-8 -rotate-90">
        <path
          className="stroke-[var(--color-surface)]"
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          strokeWidth="3"
        />
        <path
          stroke={color}
          strokeDasharray={dashArray}
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          strokeWidth="3"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-[9px] font-mono" style={{ color }}>
        {trust.toFixed(2)}
      </div>
      {trend === 'up' && <span className="absolute -top-1 -right-1 text-[10px] text-[var(--color-success)] font-bold">↑</span>}
      {trend === 'down' && <span className="absolute -top-1 -right-1 text-[10px] text-[var(--color-error)] font-bold">↓</span>}

      <AnimatePresence>
        {hover && scoreInfo && (
          <motion.div
            initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="absolute z-50 bottom-full mb-2 left-1/2 -translate-x-1/2 bg-[var(--color-surface-alt)] p-2 rounded-lg shadow-xl border border-[var(--color-border)] text-[10px] w-48 font-mono text-[var(--color-text)]"
          >
            <div className="mb-1 text-[var(--color-text-muted)] border-b border-[var(--color-border)] pb-1">Trust Breakdown</div>
            <div className="flex justify-between py-0.5"><span>Interaction:</span> <span className="text-[var(--color-accent)]">{scoreInfo.interaction_score?.toFixed(2) ?? 0}</span></div>
            <div className="flex justify-between py-0.5"><span>Recency:</span> <span className="text-[var(--color-accent)]">{scoreInfo.recency_score?.toFixed(2) ?? 0}</span></div>
            <div className="flex justify-between py-0.5"><span>Flows:</span> <span className="text-[var(--color-accent)]">{scoreInfo.flow_score?.toFixed(2) ?? 0}</span></div>
            <div className="mt-1 border-t border-[var(--color-border)] pt-1 font-bold flex justify-between">
              <span>Total:</span> <span style={{ color }}>{trust.toFixed(2)}</span>
            </div>
            {/* Pointer triangle */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-[var(--color-border)]" />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function LeadTable() {
  const { leads, loading, refresh, create } = useCrmLeads();
  const { events } = useCrmWebSocket();
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortAsc, setSortAsc] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<CrmLead[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<Partial<CrmLead>>({});
  const searchInputRef = useRef<HTMLInputElement>(null);

  const [newLead, setNewLead] = useState<CrmLeadCreate>({
    name: "",
    email: "",
    company: "",
    source_channel: "manual",
    tags: [],
  });

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (events.length > 0) refresh();
  }, [events.length, refresh]);

  // Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
      if (e.key === 'Escape') {
        setShowCreate(false);
        setEditingId(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Debounced search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setIsSearching(false);
      return;
    }
    setIsSearching(true);
    const timer = setTimeout(async () => {
      try {
        const results = await searchCrmLeads(searchQuery);
        setSearchResults(results);
      } catch (err) {
        console.error("Search error:", err);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const displayLeads = searchQuery.trim() ? searchResults : leads;

  const sorted = [...displayLeads].sort((a, b) => {
    const va = a[sortKey] ?? "";
    const vb = b[sortKey] ?? "";
    if (typeof va === "number" && typeof vb === "number") {
      return sortAsc ? va - vb : vb - va;
    }
    return sortAsc
      ? String(va).localeCompare(String(vb))
      : String(vb).localeCompare(String(va));
  });

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const handleCreate = async () => {
    if (!newLead.name.trim()) return;
    await create(newLead);
    setNewLead({ name: "", email: "", company: "", source_channel: "manual", tags: [] });
    setShowCreate(false);
  };

  const handleEdit = (lead: CrmLead) => {
    setEditingId(lead.id);
    setEditForm(lead);
  };

  const handleSaveEdit = async (leadId: string) => {
    try {
      await updateCrmLead(leadId, {
        name: editForm.name,
        email: editForm.email,
        company: editForm.company,
        tags: editForm.tags,
      });
      setEditingId(null);
      setEditForm({});
      refresh();
    } catch (err) {
      console.error("Update error:", err);
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditForm({});
  };

  const handleDelete = async (leadId: string) => {
    if (!confirm("Are you sure you want to delete this lead?")) return;
    try {
      await deleteCrmLead(leadId);
      refresh();
    } catch (err) {
      console.error("Delete error:", err);
    }
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: "name", label: "Name" },
    { key: "email", label: "Email" },
    { key: "company", label: "Company" },
    { key: "trust", label: "Trust" },
    { key: "interaction_count", label: "Interactions" },
    { key: "source_channel", label: "Source" },
    { key: "created_at", label: "Created" },
  ];

  return (
    <div>
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row gap-2 mb-4">
        <div className="relative flex-1">
          <input
            ref={searchInputRef}
            className="w-full pl-3 pr-10 py-2 rounded-lg text-sm font-mono transition-colors focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
            style={{
              background: "var(--color-bg)",
              color: "var(--color-text)",
              border: "1px solid var(--color-border)",
            }}
            placeholder="Search leads..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <div className="absolute right-3 top-2 text-[10px] font-mono text-[var(--color-text-muted)] pointer-events-none hidden sm:block border border-[var(--color-border)] px-1.5 rounded bg-[var(--color-surface)]">
            Ctrl+K
          </div>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="text-sm px-4 py-2 rounded-lg font-medium transition-colors hover:bg-[var(--color-accent)] hover:text-white whitespace-nowrap"
            style={{
              background: "var(--color-accent)22",
              color: "var(--color-accent)",
              border: "1px solid var(--color-accent)44",
            }}
          >
            + Add Lead
          </button>
          <button
            onClick={refresh}
            className="text-sm px-4 py-2 rounded-lg font-medium transition-colors"
            style={{
              background: "var(--color-surface)",
              color: "var(--color-text-secondary)",
              border: "1px solid var(--color-border)",
            }}
          >
            Refresh
          </button>
        </div>
      </div>

      <AnimatePresence>
        {showCreate && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-4 p-4 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] flex flex-wrap gap-3 items-end overflow-hidden"
          >
            {/* Create inputs ... */}
            <div className="flex-1 min-w-[150px]">
              <label className="block text-[10px] uppercase text-[var(--color-text-muted)] mb-1">Name *</label>
              <input className="w-full px-3 py-1.5 rounded text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none"
                value={newLead.name} onChange={e => setNewLead({ ...newLead, name: e.target.value })} />
            </div>
            <div className="flex-1 min-w-[150px]">
              <label className="block text-[10px] uppercase text-[var(--color-text-muted)] mb-1">Email</label>
              <input className="w-full px-3 py-1.5 rounded text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none"
                value={newLead.email ?? ""} onChange={e => setNewLead({ ...newLead, email: e.target.value })} />
            </div>
            <div className="flex-1 min-w-[120px]">
              <label className="block text-[10px] uppercase text-[var(--color-text-muted)] mb-1">Company</label>
              <input className="w-full px-3 py-1.5 rounded text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none"
                value={newLead.company ?? ""} onChange={e => setNewLead({ ...newLead, company: e.target.value })} />
            </div>
            <div className="flex-1 min-w-[120px]">
              <label className="block text-[10px] uppercase text-[var(--color-text-muted)] mb-1">Source</label>
              <select className="w-full px-3 py-1.5 rounded text-sm bg-[var(--color-surface)] border border-[var(--color-border)] text-[var(--color-text)] focus:outline-none"
                value={newLead.source_channel} onChange={e => setNewLead({ ...newLead, source_channel: e.target.value })}>
                <option value="manual">manual</option>
                <option value="telegram">telegram</option>
                <option value="email">email</option>
                <option value="n8n">n8n</option>
                <option value="webhook">webhook</option>
              </select>
            </div>
            <button onClick={handleCreate} className="px-4 py-1.5 rounded text-sm text-[var(--color-bg)] font-medium h-full mt-auto mb-0.5 whitespace-nowrap transition-colors hover:brightness-110" style={{ background: "var(--color-success)" }}>
              Create
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Mobile Card View (hidden on large displays) */}
      <div className="md:hidden flex flex-col gap-3">
        {loading && <div className="text-center py-4 text-[var(--color-text-muted)] text-sm">Loading...</div>}
        {!loading && sorted.length === 0 && <div className="text-center py-4 text-[var(--color-text-muted)] text-sm">No leads found.</div>}

        {sorted.map((lead, i) => (
          <motion.div
            key={lead.id}
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
            className="p-4 rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)] flex flex-col gap-3 shadow-md"
          >
            <div className="flex justify-between items-start">
              <div>
                <div className="font-medium text-[var(--color-text)] text-sm">{lead.name}</div>
                <div className="text-xs text-[var(--color-text-muted)] mt-0.5">{lead.email || "-"} • {lead.company || "-"}</div>
              </div>
              <LeadTrustRing trust={lead.trust} leadId={lead.id} interactionCount={lead.interaction_count} />
            </div>

            <div className="flex justify-between items-end">
              <div className="flex flex-wrap gap-2 text-[10px] text-[var(--color-text-secondary)] font-mono">
                <span className="bg-[var(--color-surface)] border border-[var(--color-border)] px-1.5 py-0.5 rounded flex items-center gap-1"><span className="text-[8px]">💬</span> {lead.interaction_count}</span>
                <span className="bg-[var(--color-surface)] border border-[var(--color-border)] px-1.5 py-0.5 rounded capitalize flex items-center gap-1"><span className="text-[8px]">📍</span> {lead.source_channel}</span>
              </div>

              <div className="flex gap-2">
                <button onClick={() => handleEdit(lead)} className="text-[10px] text-[var(--color-accent)] font-medium">Edit</button>
                <button onClick={() => handleDelete(lead.id)} className="text-[10px] text-[var(--color-error)] font-medium">Delete</button>
              </div>
            </div>

            {editingId === lead.id && (
              <div className="mt-2 pt-2 border-t border-[var(--color-border)] flex flex-col gap-2">
                <input className="w-full px-2 py-1 bg-[var(--color-surface-alt)] border border-[var(--color-border)] rounded text-xs text-[var(--color-text)]" placeholder="Name" value={editForm.name ?? ""} onChange={e => setEditForm({ ...editForm, name: e.target.value })} />
                <input className="w-full px-2 py-1 bg-[var(--color-surface-alt)] border border-[var(--color-border)] rounded text-xs text-[var(--color-text)]" placeholder="Email" value={editForm.email ?? ""} onChange={e => setEditForm({ ...editForm, email: e.target.value })} />
                <input className="w-full px-2 py-1 bg-[var(--color-surface-alt)] border border-[var(--color-border)] rounded text-xs text-[var(--color-text)]" placeholder="Company" value={editForm.company ?? ""} onChange={e => setEditForm({ ...editForm, company: e.target.value })} />
                <div className="flex gap-2 mt-1">
                  <button onClick={() => handleSaveEdit(lead.id)} className="text-xs px-3 py-1 bg-[var(--color-success)22] text-[var(--color-success)] border border-[var(--color-success)44] rounded">Save</button>
                  <button onClick={handleCancelEdit} className="text-xs px-3 py-1 bg-[var(--color-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)] rounded">Cancel</button>
                </div>
              </div>
            )}
          </motion.div>
        ))}
      </div>

      {/* Desktop Table View */}
      <div className="hidden md:block overflow-x-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)]">
        <table className="w-full text-sm text-left">
          <thead className="bg-[var(--color-surface-alt)] text-[var(--color-text-secondary)] font-mono text-xs uppercase tracking-wider">
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 cursor-pointer select-none font-medium hover:bg-[var(--color-surface)] transition-colors"
                  style={{ color: sortKey === col.key ? "var(--color-accent)" : "inherit" }}
                  onClick={() => toggleSort(col.key)}
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {sortKey === col.key && (
                      <span className="text-[10px]">{sortAsc ? "▲" : "▼"}</span>
                    )}
                  </div>
                </th>
              ))}
              <th className="px-4 py-3 font-medium">Tags</th>
              <th className="px-4 py-3 font-medium text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-border)]">
            {loading && (
              <tr><td colSpan={9} className="text-center py-8 text-[var(--color-text-muted)]">Loading...</td></tr>
            )}
            {!loading && sorted.length === 0 && (
              <tr><td colSpan={9} className="text-center py-8 text-[var(--color-text-muted)]">No leads found.</td></tr>
            )}
            {sorted.map((lead, i) => (
              <motion.tr
                key={lead.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="hover:bg-[var(--color-surface)] transition-colors group"
              >
                {editingId === lead.id ? (
                  <>
                    <td className="px-4 py-2"><input className="w-full px-2 py-1 bg-black/20 border border-[var(--color-border)] rounded text-xs text-[var(--color-text)]" value={editForm.name ?? ""} onChange={e => setEditForm({ ...editForm, name: e.target.value })} autoFocus /></td>
                    <td className="px-4 py-2"><input className="w-full px-2 py-1 bg-black/20 border border-[var(--color-border)] rounded text-xs text-[var(--color-text)]" value={editForm.email ?? ""} onChange={e => setEditForm({ ...editForm, email: e.target.value })} /></td>
                    <td className="px-4 py-2"><input className="w-full px-2 py-1 bg-black/20 border border-[var(--color-border)] rounded text-xs text-[var(--color-text)]" value={editForm.company ?? ""} onChange={e => setEditForm({ ...editForm, company: e.target.value })} /></td>
                    <td className="px-4 py-2"><LeadTrustRing trust={lead.trust} leadId={lead.id} interactionCount={lead.interaction_count} /></td>
                    <td className="px-4 py-2 font-mono text-xs text-[var(--color-text-muted)]">{lead.interaction_count}</td>
                    <td className="px-4 py-2 text-xs text-[var(--color-text-muted)] capitalize">{lead.source_channel}</td>
                    <td className="px-4 py-2 font-mono text-xs text-[var(--color-text-muted)]">{lead.created_at?.slice(0, 10)}</td>
                    <td className="px-4 py-2"></td>
                    <td className="px-4 py-2 text-right">
                      <button onClick={() => handleSaveEdit(lead.id)} className="text-xs px-2 py-1 text-[var(--color-success)] hover:underline mr-2 font-medium">Save</button>
                      <button onClick={handleCancelEdit} className="text-xs px-2 py-1 text-[var(--color-text-muted)] hover:underline">Cancel</button>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="px-4 py-3 text-[var(--color-text)] font-medium text-sm">{lead.name}</td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)] text-sm">{lead.email || "-"}</td>
                    <td className="px-4 py-3 text-[var(--color-text-secondary)] text-sm">{lead.company || "-"}</td>
                    <td className="px-4 py-3"><LeadTrustRing trust={lead.trust} leadId={lead.id} interactionCount={lead.interaction_count} /></td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)] font-mono text-xs">{lead.interaction_count}</td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)] text-xs capitalize">{lead.source_channel}</td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)] font-mono text-xs">{lead.created_at?.slice(0, 10)}</td>
                    <td className="px-4 py-3">
                      <div className="flex gap-1 flex-wrap">
                        {(lead.tags ?? []).map((tag) => (
                          <span key={tag} className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--color-surface-alt)] border border-[var(--color-border)] text-[var(--color-text-muted)] font-mono">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                      <button onClick={() => handleEdit(lead)} className="text-xs text-[var(--color-accent)] hover:underline px-2 font-medium">Edit</button>
                      <button onClick={() => handleDelete(lead.id)} className="text-xs text-[var(--color-error)] hover:underline px-2 font-medium">Delete</button>
                    </td>
                  </>
                )}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
