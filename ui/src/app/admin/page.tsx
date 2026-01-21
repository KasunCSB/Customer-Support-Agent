
"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTheme } from "@/components/providers/ThemeProvider";

const backendUrl =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  process.env.BACKEND_URL ||
  "http://localhost:8000";

type TableName =
  | "users"
  | "services"
  | "subscriptions"
  | "tickets"
  | "actions"
  | "audit_logs"
  | "sessions"
  | "verifications";

type Row = Record<string, unknown>;

type AdminStats = {
  counts: Record<string, number>;
  latest_tickets: Row[];
  latest_actions: Row[];
  latest_audit_logs: Row[];
};

type HealthStatus = "checking" | "ok" | "down";

type CardField = { label: string; key?: string; render?: (row: Row) => string };

const TABLES: TableName[] = [
  "users",
  "services",
  "subscriptions",
  "tickets",
  "actions",
  "audit_logs",
  "sessions",
  "verifications",
];

const TABLE_META: Record<TableName, { label: string; description: string }> = {
  users: { label: "Customers", description: "Profiles, roles, and status" },
  services: { label: "Services", description: "Packages, pricing, and validity" },
  subscriptions: { label: "Subscriptions", description: "Active and pending bundles" },
  tickets: { label: "Tickets", description: "Incidents, priorities, assignments" },
  actions: { label: "Actions", description: "Tool executions and outcomes" },
  audit_logs: { label: "Audit Logs", description: "Compliance activity trail" },
  sessions: { label: "Sessions", description: "Auth sessions and expiry" },
  verifications: { label: "Verifications", description: "OTP and verification history" },
};

const NAV_GROUPS: { title: string; items: TableName[] }[] = [
  { title: "Customer Ops", items: ["users", "subscriptions", "tickets"] },
  { title: "Service Ops", items: ["services", "actions"] },
  { title: "Compliance", items: ["audit_logs", "sessions", "verifications"] },
];
const TABLE_COLUMNS: Record<TableName, string[]> = {
  users: ["display_name", "email", "role", "status", "preferred_channel"],
  services: ["code", "name", "category", "price", "currency", "validity_days"],
  subscriptions: ["status", "activated_at", "expires_at"],
  tickets: ["subject", "priority", "status", "created_at"],
  actions: ["action_name", "status", "requires_confirmation", "created_at"],
  audit_logs: ["action", "actor_role", "severity", "created_at"],
  sessions: ["expires_at", "revoked_at", "user_agent"],
  verifications: ["destination", "purpose", "expires_at", "attempts", "verified_at"],
};

const CARD_FIELDS: Record<TableName, CardField[]> = {
  users: [
    { label: "Role", key: "role" },
    { label: "Status", key: "status" },
    { label: "Channel", key: "preferred_channel" },
  ],
  services: [
    { label: "Category", key: "category" },
    { label: "Price", render: (row) => `${safeFormat(row.price)} ${safeFormat(row.currency)}`.trim() },
    { label: "Validity", render: (row) => `${safeFormat(row.validity_days)} days` },
  ],
  subscriptions: [
    { label: "Status", key: "status" },
    { label: "Active", key: "activated_at" },
    { label: "Expires", key: "expires_at" },
  ],
  tickets: [
    { label: "Priority", key: "priority" },
    { label: "Status", key: "status" },
    { label: "Opened", key: "created_at" },
  ],
  actions: [
    { label: "Status", key: "status" },
    { label: "Requires Confirm", key: "requires_confirmation" },
    { label: "Created", key: "created_at" },
  ],
  audit_logs: [
    { label: "Action", key: "action" },
    { label: "Severity", key: "severity" },
    { label: "Actor", key: "actor_role" },
  ],
  sessions: [
    { label: "Expires", key: "expires_at" },
    { label: "Revoked", key: "revoked_at" },
    { label: "Client", key: "user_agent" },
  ],
  verifications: [
    { label: "Purpose", key: "purpose" },
    { label: "Expires", key: "expires_at" },
    { label: "Attempts", key: "attempts" },
  ],
};

const DETAIL_FIELDS: Record<TableName, string[]> = {
  users: ["display_name", "email", "role", "status", "preferred_channel"],
  services: ["code", "name", "description", "category", "price", "currency", "validity_days"],
  subscriptions: ["status", "activated_at", "expires_at"],
  tickets: ["subject", "description", "priority", "status", "created_at", "closed_at"],
  actions: ["action_name", "status", "requires_confirmation", "error", "created_at", "completed_at"],
  audit_logs: ["action", "actor_role", "severity", "created_at"],
  sessions: ["expires_at", "revoked_at", "user_agent"],
  verifications: ["destination", "purpose", "expires_at", "verified_at", "attempts"],
};

const EDITABLE_FIELDS: Partial<Record<TableName, string[]>> = {
  users: ["display_name", "role", "status", "preferred_channel", "metadata", "email"],
  services: ["name", "description", "category", "price", "currency", "validity_days", "metadata", "code"],
  subscriptions: ["status", "activated_at", "expires_at", "metadata"],
  tickets: ["subject", "description", "priority", "status", "metadata", "closed_at"],
  actions: ["status", "requires_confirmation", "params", "result", "error"],
};

const FILTER_OPTIONS = [
  { value: "all", label: "All records" },
  { value: "openTickets", label: "Open or in progress" },
  { value: "urgent", label: "Urgent priority" },
  { value: "pendingActions", label: "Pending actions" },
  { value: "activeSubs", label: "Active subscriptions" },
  { value: "vipCustomers", label: "VIP customers" },
  { value: "resolved", label: "Resolved or closed" },
];
const safeFormat = (val: unknown) => {
  if (val === null || val === undefined) return "";
  if (typeof val === "object") return JSON.stringify(val, null, 2);
  return String(val);
};

const shortId = (val: unknown) => {
  const text = safeFormat(val);
  if (text.length <= 12) return text;
  return `${text.slice(0, 6)}...${text.slice(-4)}`;
};

const isVip = (row: Row) => {
  const meta = row.metadata;
  if (!meta) return false;
  const text = typeof meta === "string" ? meta : JSON.stringify(meta);
  return text.toLowerCase().includes("vip");
};

const friendlyLabel = (row: Row, table: TableName) => {
  if (table === "users") {
    const name = safeFormat(row.display_name ?? "");
    const email = safeFormat(row.email ?? "");
    return `${name || "Customer"} - ${email}`;
  }
  if (table === "tickets") {
    return `${row.subject ?? "Support ticket"} - ${row.status ?? ""}`;
  }
  if (table === "subscriptions") {
    return `Subscription - ${row.status ?? ""}`;
  }
  if (table === "services") {
    return `${row.code ?? ""} - ${row.name ?? ""}`;
  }
  if (table === "actions") {
    return `${row.action_name ?? "Action"} - ${row.status ?? ""}`;
  }
  return safeFormat(row.action ?? "Record");
};

const formatCell = (key: string, value: unknown) => {
  const text = safeFormat(value);
  if (key.endsWith("_at") && text) {
    return text.replace("T", " ").slice(0, 19);
  }
  if (key.endsWith("id") || key.endsWith("_id")) {
    return shortId(text);
  }
  return text;
};

const badgeTone = (value: string) => {
  const v = value.toLowerCase();
  if (v.includes("urgent") || v.includes("failed")) {
    return "bg-red-100 text-red-700 border-red-200 dark:bg-red-500/20 dark:text-red-300 dark:border-red-500/30";
  }
  if (v.includes("active") || v.includes("completed") || v.includes("resolved")) {
    return "bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-500/30";
  }
  if (v.includes("pending") || v.includes("in_progress")) {
    return "bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-500/20 dark:text-amber-300 dark:border-amber-500/30";
  }
  return "bg-neutral-100 text-neutral-700 border-neutral-200 dark:bg-neutral-800 dark:text-neutral-300 dark:border-neutral-700";
};
export default function AdminPage() {
  const { resolvedTheme, setTheme } = useTheme();
  const [username, setUsername] = useState("ltadmin");
  const [password, setPassword] = useState("");
  const [authed, setAuthed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [selectedTable, setSelectedTable] = useState<TableName>("users");
  const [rows, setRows] = useState<Row[]>([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [health, setHealth] = useState<HealthStatus>("checking");
  const [search, setSearch] = useState("");
  const [selectedRow, setSelectedRow] = useState<Row | null>(null);
  const [editData, setEditData] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [showNav, setShowNav] = useState(false);
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards");
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [quickFilter, setQuickFilter] = useState("all");
  const [statusMessage, setStatusMessage] = useState("Idle");
  const [lastSync, setLastSync] = useState("--");
  const panel = resolvedTheme === "dark" ? "bg-white/5 border-white/10" : "bg-white border-neutral-200";
  const panelSoft =
    resolvedTheme === "dark" ? "bg-neutral-900 border-white/10" : "bg-neutral-100 border-neutral-200";
  const inputClass =
    resolvedTheme === "dark"
      ? "bg-neutral-900 border-white/10 text-neutral-100"
      : "bg-white border-neutral-200 text-neutral-900";
  const hoverPanel = resolvedTheme === "dark" ? "hover:bg-white/10" : "hover:bg-neutral-100";
  const tableHeaderClass = resolvedTheme === "dark" ? "bg-neutral-900/60" : "bg-neutral-100";
  const overlayClass = resolvedTheme === "dark" ? "bg-black/60" : "bg-neutral-200/60";
  const rowClass =
    resolvedTheme === "dark" ? "border-white/10 hover:bg-white/5" : "border-neutral-200 hover:bg-neutral-100";
  const borderClass = resolvedTheme === "dark" ? "border-white/10" : "border-neutral-200";
  const valueText = resolvedTheme === "dark" ? "text-neutral-200" : "text-neutral-700";
  const mutedText = resolvedTheme === "dark" ? "text-neutral-400" : "text-neutral-500";
  const pillBase =
    resolvedTheme === "dark"
      ? "bg-neutral-800 text-neutral-300 border-neutral-700"
      : "bg-neutral-100 text-neutral-700 border-neutral-200";
  const hoverText = resolvedTheme === "dark" ? "hover:text-neutral-200" : "hover:text-neutral-700";

  const loadHealth = useCallback(async () => {
    setHealth("checking");
    try {
      const resp = await fetch(`${backendUrl}/api/health`);
      if (resp.ok) {
        setHealth("ok");
      } else {
        setHealth("down");
      }
    } catch {
      setHealth("down");
    }
  }, []);

  const loadStats = useCallback(async () => {
    try {
      const resp = await fetch(`${backendUrl}/api/admin/stats`, {
        credentials: "include",
      });
      if (resp.status === 401) {
        setAuthed(false);
        return;
      }
      const data = (await resp.json()) as AdminStats;
      setStats(data);
      setAuthed(true);
      setStatusMessage("Overview synced");
      setLastSync(new Date().toLocaleTimeString());
    } catch (err) {
      console.error(err);
      setError("Failed to load stats");
    }
  }, []);

  const loadTable = useCallback(async (table: TableName) => {
    try {
      const resp = await fetch(`${backendUrl}/api/admin/table/${table}`, {
        credentials: "include",
      });
      if (resp.status === 401) {
        setAuthed(false);
        return;
      }
      const data = await resp.json();
      setRows((data.rows as Row[]) || []);
      setStatusMessage(`Loaded ${TABLE_META[table].label}`);
      setLastSync(new Date().toLocaleTimeString());
    } catch (err) {
      console.error(err);
      setError(`Failed to load ${table}`);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadHealth();
  }, [loadStats, loadHealth, refreshKey]);

  useEffect(() => {
    if (authed) {
      loadTable(selectedTable);
    }
  }, [authed, selectedTable, refreshKey, loadTable]);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${backendUrl}/api/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Invalid credentials");
      }
      setAuthed(true);
      setRefreshKey((k) => k + 1);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      setAuthed(false);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    await fetch(`${backendUrl}/api/admin/logout`, {
      method: "POST",
      credentials: "include",
    });
    setAuthed(false);
    setRows([]);
    setStats(null);
    setSelectedRow(null);
  };
  const filteredRows = useMemo(() => {
    let base = rows;
    if (quickFilter !== "all") {
      base = rows.filter((row) => {
        const status = String(row.status ?? "").toLowerCase();
        const priority = String(row.priority ?? "").toLowerCase();
        if (quickFilter === "openTickets") return status === "open" || status === "in_progress";
        if (quickFilter === "pendingActions") return status === "pending";
        if (quickFilter === "vipCustomers") return isVip(row);
        if (quickFilter === "activeSubs") return status === "active";
        if (quickFilter === "resolved") return status === "resolved" || status === "closed";
        if (quickFilter === "urgent") return priority === "urgent";
        return true;
      });
    }
    if (!search.trim()) return base;
    const needle = search.toLowerCase();
    return base.filter((row) =>
      Object.values(row)
        .map((v) => safeFormat(v).toLowerCase())
        .some((txt) => txt.includes(needle)),
    );
  }, [rows, search, quickFilter]);

  const pagedRows = useMemo(
    () => filteredRows.slice(0, rowsPerPage),
    [filteredRows, rowsPerPage],
  );

  const visibleColumns = useMemo(() => TABLE_COLUMNS[selectedTable] || [], [selectedTable]);

  const tableHeader = useMemo(() => {
    if (visibleColumns.length) return visibleColumns;
    if (!rows.length) return [];
    return Object.keys(rows[0]);
  }, [rows, visibleColumns]);

  const onSelectRow = (row: Row) => {
    setSelectedRow(row);
    const fields = EDITABLE_FIELDS[selectedTable] || [];
    const next: Record<string, string> = {};
    fields.forEach((key) => {
      const val = row[key];
      if (key.toLowerCase().includes("metadata") || key === "params" || key === "result") {
        next[key] = val ? JSON.stringify(val, null, 2) : "{}";
      } else {
        next[key] = safeFormat(val);
      }
    });
    setEditData(next);
  };

  const handleEditChange = (field: string, value: string) => {
    setEditData((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    if (!selectedRow || !selectedRow.id) return;
    const fields = EDITABLE_FIELDS[selectedTable] || [];
    const payload: Record<string, unknown> = {};
    try {
      fields.forEach((key) => {
        if (!(key in editData)) return;
        const raw = editData[key];
        if (key.toLowerCase().includes("metadata") || key === "params" || key === "result") {
          payload[key] = raw ? JSON.parse(raw) : {};
        } else if (raw === "") {
          payload[key] = null;
        } else if (!Number.isNaN(Number(raw)) && raw.trim() !== "") {
          payload[key] = Number(raw);
        } else if (raw === "true" || raw === "false") {
          payload[key] = raw === "true";
        } else {
          payload[key] = raw;
        }
      });
    } catch {
      setError("Invalid JSON in one of the fields");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const resp = await fetch(
        `${backendUrl}/api/admin/table/${selectedTable}/${selectedRow.id as string}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ data: payload }),
        },
      );
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || "Save failed");
      }
      await loadTable(selectedTable);
      setRefreshKey((k) => k + 1);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Save failed";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const exportCsv = () => {
    if (!filteredRows.length) return;
    const headers = tableHeader.length ? tableHeader : Object.keys(filteredRows[0] || {});
    const lines = [
      headers.join(","),
      ...filteredRows.map((row) =>
        headers
          .map((h) => {
            const value = safeFormat(row[h]).replace(/\"/g, '""');
            return `"${value}"`;
          })
          .join(","),
      ),
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `${selectedTable}-export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  const HealthPill = ({ status }: { status: HealthStatus }) => {
    const label = status === "ok" ? "Healthy" : status === "down" ? "Degraded" : "Checking...";
    const color =
      status === "ok" ? "bg-emerald-500" : status === "down" ? "bg-red-500" : "bg-amber-500";
    return (
      <span
        className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm ${panel}`}
      >
        <span className={`h-2 w-2 rounded-full ${color}`} />
        {label}
      </span>
    );
  };

  const ActivityList = () => {
    if (!stats) return null;
    const items: { label: string; when?: string; detail?: string }[] = [];
    stats.latest_tickets.forEach((t) =>
      items.push({
        label: `${safeFormat(t.subject) || "Ticket"} - ${safeFormat(t.status)}`,
        when: safeFormat(t.created_at),
        detail: safeFormat(t.priority),
      }),
    );
    stats.latest_actions.forEach((a) =>
      items.push({
        label: `Action ${safeFormat(a.action_name)} - ${safeFormat(a.status)}`,
        when: safeFormat(a.created_at),
        detail: safeFormat(a.error || ""),
      }),
    );
    stats.latest_audit_logs.forEach((a) =>
      items.push({
        label: `Audit ${safeFormat(a.action)} - ${safeFormat(a.severity)}`,
        when: safeFormat(a.created_at),
        detail: safeFormat(a.target_type),
      }),
    );
    return (
      <div className={`rounded-xl border p-5 space-y-3 ${panel}`}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Activity</h3>
          <button
            onClick={() => setRefreshKey((k) => k + 1)}
            className={`text-sm ${mutedText} ${hoverText}`}
          >
            Refresh
          </button>
        </div>
        {items.slice(0, 10).map((item, idx) => (
          <div
            key={`${item.label}-${idx}`}
            className={`flex justify-between border-b pb-2 last:border-b-0 last:pb-0 ${borderClass}`}
          >
            <div>
              <p className="text-sm font-medium">{item.label}</p>
              {item.detail ? <p className={`text-xs ${mutedText}`}>{item.detail}</p> : null}
            </div>
            <p className="text-xs text-neutral-500">{item.when}</p>
          </div>
        ))}
      </div>
    );
  };

  const OverviewCards = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      {TABLES.slice(0, 6).map((name) => (
        <div key={name} className={`p-4 rounded-xl border space-y-1 ${panel}`}>
          <p className={`text-sm uppercase ${mutedText}`}>{TABLE_META[name].label}</p>
          <p className="text-2xl font-semibold">{stats?.counts?.[name] ?? "-"}</p>
        </div>
      ))}
    </div>
  );

  const SettingsPanel = () => (
    <div className={`rounded-xl border p-5 space-y-3 ${panel}`}>
      <h3 className="text-lg font-semibold">Settings</h3>
      <p className={`text-sm ${mutedText}`}>Read-only (set via environment variables).</p>
      <div className="space-y-2 text-sm">
        <div className={`px-3 py-2 rounded-md border ${panelSoft}`}>
          <p className="text-xs uppercase text-neutral-500">Cookie TTL (hrs)</p>
          <p className={valueText}>
            {process.env.NEXT_PUBLIC_ADMIN_COOKIE_TTL_HOURS ||
              process.env.ADMIN_COOKIE_TTL_HOURS ||
              "ADMIN_COOKIE_TTL_HOURS"}
          </p>
        </div>
        <div className={`px-3 py-2 rounded-md border ${panelSoft}`}>
          <p className="text-xs uppercase text-neutral-500">Backend</p>
          <p className={`${valueText} break-all`}>{backendUrl}</p>
        </div>
        <div className={`px-3 py-2 rounded-md border ${panelSoft}`}>
          <p className="text-xs uppercase text-neutral-500">Environment</p>
          <p className={valueText}>{process.env.NODE_ENV}</p>
        </div>
      </div>
    </div>
  );

  const DetailDrawer = () => {
    if (!selectedRow) return null;
    const editable = EDITABLE_FIELDS[selectedTable] || [];
    return (
      <div className={`w-full sm:w-[420px] lg:w-[480px] h-full border-l p-6 space-y-5 overflow-y-auto ${panelSoft}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className={`text-sm uppercase ${mutedText}`}>Details</p>
            <h3 className="text-lg font-semibold">{friendlyLabel(selectedRow, selectedTable)}</h3>
          </div>
          <button
            className={`text-sm ${mutedText} ${hoverText}`}
            onClick={() => setSelectedRow(null)}
          >
            Close
          </button>
        </div>
        <div className="space-y-2">
          {(DETAIL_FIELDS[selectedTable] || []).map((key) => (
            <div key={key} className="text-sm">
              <p className={`text-xs uppercase ${mutedText}`}>{key}</p>
              <pre className={`whitespace-pre-wrap break-words ${valueText}`}>
                {safeFormat(selectedRow[key]) || "--"}
              </pre>
            </div>
          ))}
        </div>
        {editable.length ? (
          <div className="space-y-2">
            <h4 className="text-sm font-semibold">Edit</h4>
            {editable.map((field) => (
              <div key={field} className="space-y-1">
                <label className={`text-xs uppercase ${mutedText}`}>{field}</label>
                {field.toLowerCase().includes("metadata") || field === "params" || field === "result" ? (
                  <textarea
                    value={editData[field] ?? ""}
                    onChange={(e) => handleEditChange(field, e.target.value)}
                    className={`w-full min-h-[80px] px-3 py-2 rounded-md border text-sm ${inputClass}`}
                  />
                ) : (
                  <input
                    value={editData[field] ?? ""}
                    onChange={(e) => handleEditChange(field, e.target.value)}
                    className={`w-full px-3 py-2 rounded-md border text-sm ${inputClass}`}
                  />
                )}
              </div>
            ))}
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm text-white"
            >
              {saving ? "Saving..." : "Save changes"}
            </button>
            {error ? <p className="text-red-400 text-sm">{error}</p> : null}
          </div>
        ) : (
          <p className="text-xs text-neutral-500">This table is read-only.</p>
        )}
      </div>
    );
  };

  const TableView = () => (
    <div className={`rounded-xl border overflow-hidden ${panel}`}>
      <div className={`flex items-center justify-between px-4 py-3 border-b ${borderClass}`}>
        <div className="flex items-center gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search records..."
            className={`px-3 py-2 rounded-md border text-sm w-64 ${inputClass}`}
          />
          <button
            onClick={() => setRefreshKey((k) => k + 1)}
            className={`px-3 py-2 rounded-md border text-sm ${panelSoft} ${hoverPanel}`}
          >
            Refresh
          </button>
        </div>
        <p className={`text-sm ${mutedText}`}>
          {filteredRows.length} rows - {TABLE_META[selectedTable].label}
        </p>
      </div>
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead className={tableHeaderClass}>
            <tr>
              <th className="text-left px-3 py-2 font-medium">Row</th>
              {tableHeader.map((h) => (
                <th key={h} className="text-left px-3 py-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pagedRows.map((row, index) => (
              <tr
                key={String(row.id ?? row.external_id ?? index)}
                className={`border-b cursor-pointer ${rowClass}`}
                onClick={() => onSelectRow(row)}
              >
                <td className="px-3 py-2">
                  <div className="text-sm font-semibold">{friendlyLabel(row, selectedTable)}</div>
                </td>
                {tableHeader.map((h) => (
                  <td key={h} className="align-top px-3 py-2">
                    <span className="text-xs">{formatCell(h, row[h])}</span>
                  </td>
                ))}
              </tr>
            ))}
            {!pagedRows.length ? (
              <tr>
                <td
                  colSpan={tableHeader.length + 1}
                  className="px-3 py-4 text-neutral-500 text-center"
                >
                  No rows
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );

  const CardsView = () => (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {pagedRows.map((row, index) => (
        <button
          type="button"
          key={String(row.id ?? row.external_id ?? index)}
          onClick={() => onSelectRow(row)}
          className={`text-left p-4 rounded-xl border ${panel} ${hoverPanel}`}
        >
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold">{friendlyLabel(row, selectedTable)}</p>
            </div>
            {isVip(row) ? (
              <span className="px-2 py-1 text-xs rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                VIP
              </span>
            ) : null}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(CARD_FIELDS[selectedTable] || []).map((field) => {
              const value = field.render ? field.render(row) : safeFormat(row[field.key || ""]);
              const tone =
                field.key === "status" || field.key === "priority"
                  ? badgeTone(value || "unknown")
                  : pillBase;
              return (
                <span
                  key={field.label}
                  className={`px-2 py-1 text-xs rounded-full border ${tone}`}
                >
                  {field.label}: {value || "--"}
                </span>
              );
            })}
          </div>
        </button>
      ))}
      {!pagedRows.length ? (
        <div className="text-sm text-neutral-500">No records found.</div>
      ) : null}
    </div>
  );

  const MenuButton = () => (
    <details className="relative">
      <summary className={`list-none cursor-pointer px-3 py-2 rounded-md border text-sm ${panel}`}>
        Menu
      </summary>
      <div className={`absolute right-0 mt-2 w-48 rounded-md border shadow-lg p-2 z-10 ${panelSoft}`}>
        <button
          onClick={() => setRefreshKey((k) => k + 1)}
          className={`w-full text-left px-3 py-2 text-sm rounded ${hoverPanel}`}
        >
          Refresh all
        </button>
        <button
          onClick={exportCsv}
          className={`w-full text-left px-3 py-2 text-sm rounded ${hoverPanel}`}
        >
          Export CSV
        </button>
      </div>
    </details>
  );

  return (
    <div
      className={`min-h-screen ${
        resolvedTheme === "dark" ? "bg-neutral-950 text-neutral-100" : "bg-neutral-50 text-neutral-900"
      }`}
    >
      <div className="max-w-7xl mx-auto py-6 px-4 space-y-6">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              className={`px-3 py-2 rounded-md border text-sm lg:hidden ${panel}`}
              onClick={() => setShowNav((s) => !s)}
            >
              Menu
            </button>
            <div>
              <p className="text-xs uppercase text-neutral-500">Admin Console</p>
              <p className="text-lg font-semibold">{TABLE_META[selectedTable].label}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap justify-end">
            <HealthPill status={health} />
            <span className={`px-3 py-1 rounded-md border text-xs ${panel}`}>
              {statusMessage} - {lastSync}
            </span>
            <button
              onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
              className={`px-3 py-2 rounded-md border text-sm ${panel}`}
            >
              Theme: {resolvedTheme === "dark" ? "Dark" : "Light"}
            </button>
            <MenuButton />
            {authed ? (
              <button
                onClick={handleLogout}
                className="px-3 py-2 rounded-md bg-red-600 hover:bg-red-500 text-sm text-white"
              >
                Logout
              </button>
            ) : null}
          </div>
        </div>

        {!authed ? (
          <div className={`max-w-md p-6 rounded-xl border ${panel}`}>
            <h2 className="text-xl font-semibold mb-4">Admin Login</h2>
            <div className="space-y-4">
              <div>
                <label className={`block text-sm mb-1 ${mutedText}`}>Username</label>
                <input
                  className={`w-full px-3 py-2 rounded-md border ${inputClass}`}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
              <div>
                <label className={`block text-sm mb-1 ${mutedText}`}>Password</label>
                <input
                  type="password"
                  className={`w-full px-3 py-2 rounded-md border ${inputClass}`}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
              {error ? <p className="text-red-400 text-sm">{error}</p> : null}
              <button
                onClick={handleLogin}
                disabled={loading}
                className="w-full px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white"
              >
                {loading ? "Signing in..." : "Sign in"}
              </button>
              <p className="text-xs text-neutral-500">
                Access is restricted. Use the configured admin credentials.
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr_320px] gap-6">
            <aside
              className={`rounded-xl border p-4 space-y-4 ${panel} ${showNav ? "block" : "hidden"} lg:block`}
            >
              {NAV_GROUPS.map((group) => (
                <div key={group.title} className="space-y-2">
                  <p className={`text-xs uppercase ${mutedText}`}>{group.title}</p>
                  {group.items.map((item) => (
                    <button
                      key={item}
                      onClick={() => {
                        setSelectedTable(item);
                        setShowNav(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-md border text-sm ${
                        selectedTable === item
                          ? "bg-blue-600 border-blue-500 text-white"
                          : `${panel} ${hoverPanel}`
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span>{TABLE_META[item].label}</span>
                        <span className={`text-xs ${selectedTable === item ? "text-white" : valueText}`}>
                          {stats?.counts?.[item] ?? "-"}
                        </span>
                      </div>
                      <p
                        className={`text-sm leading-snug ${
                          selectedTable === item ? "text-white/80" : mutedText
                        }`}
                      >
                        {TABLE_META[item].description}
                      </p>
                    </button>
                  ))}
                </div>
              ))}
            </aside>

            <div className="space-y-6">
              <div className="space-y-1">
                <p className="text-xs uppercase text-neutral-500">Operations Dashboard</p>
                <h1 className="text-2xl font-semibold">Operations Dashboard</h1>
                <p className={`text-sm ${mutedText}`}>
                  Monitor customer operations, services, and escalations in real time.
                </p>
              </div>
              <OverviewCards />

              <div className="flex flex-wrap gap-2 items-center">
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search records..."
                  className={`px-3 py-2 rounded-md border text-sm w-60 ${inputClass}`}
                />
                <select
                  value={viewMode}
                  onChange={(e) => setViewMode(e.target.value as "cards" | "table")}
                  className={`px-3 py-2 rounded-md border text-sm ${inputClass}`}
                >
                  <option value="cards">Card view</option>
                  <option value="table">Table view</option>
                </select>
                <select
                  value={quickFilter}
                  onChange={(e) => setQuickFilter(e.target.value)}
                  className={`px-3 py-2 rounded-md border text-sm ${inputClass}`}
                >
                  {FILTER_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                <select
                  value={rowsPerPage}
                  onChange={(e) => setRowsPerPage(Number(e.target.value))}
                  className={`px-3 py-2 rounded-md border text-sm ${inputClass}`}
                >
                  {[10, 25, 50, 100].map((n) => (
                    <option key={n} value={n}>
                      {n} rows
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => setRefreshKey((k) => k + 1)}
                  className={`px-3 py-2 rounded-md border text-sm ${panelSoft} ${hoverPanel}`}
                >
                  Refresh
                </button>
              </div>

              {viewMode === "cards" ? <CardsView /> : <TableView />}
            </div>

            <div className="space-y-5">
              <SettingsPanel />
              <ActivityList />
            </div>
          </div>
        )}
      </div>
      {authed && selectedRow ? (
        <div
          className={`fixed inset-0 z-30 flex justify-end backdrop-blur-sm ${overlayClass}`}
          onClick={() => setSelectedRow(null)}
        >
          <div onClick={(e) => e.stopPropagation()}>
            <DetailDrawer />
          </div>
        </div>
      ) : null}
    </div>
  );
}
