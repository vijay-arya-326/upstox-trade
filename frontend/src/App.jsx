import { useCallback, useEffect, useState } from "react";
import { get, postEngine } from "./api.js";

function usePoll(fn, ms, deps = []) {
  useEffect(() => {
    let live = true;
    const tick = () => fn().catch(() => {});
    tick();
    const t = setInterval(() => live && tick(), ms);
    return () => {
      live = false;
      clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}

function Card({ title, children, wide }) {
  return (
    <section className={`rounded-xl border border-slate-800 bg-slate-900 p-4 ${wide ? "md:col-span-2" : ""}`}>
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h2>
      {children}
    </section>
  );
}

function DataTable({ columns, rows }) {
  if (!rows?.length) return <p className="text-sm text-slate-500">No rows yet.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-800 text-slate-400">
            {columns.map((c) => (
              <th key={c.key} className="px-2 py-1 font-medium">{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 50).map((r, i) => (
            <tr key={i} className="border-b border-slate-800/50">
              {columns.map((c) => (
                <td key={c.key} className="px-2 py-1 font-mono text-xs">{String(r[c.key] ?? "")}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InstrumentPicker({ value, onChange }) {
  const [q, setQ] = useState("");
  const [segment, setSegment] = useState("");
  const [segments, setSegments] = useState([]);
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    get("/api/instruments/segments").then((d) => setSegments(d.segments || [])).catch(() => {});
  }, []);

  useEffect(() => {
    const t = setTimeout(async () => {
      if (!open) return;
      try {
        const d = await get(`/api/instruments?q=${encodeURIComponent(q)}&segment=${encodeURIComponent(segment)}&limit=20`);
        setResults(d.data || []);
        setTotal(d.total || 0);
      } catch { /* offline */ }
    }, 300);
    return () => clearTimeout(t);
  }, [q, segment, open]);

  return (
    <div className="relative">
      <button onClick={() => setOpen((o) => !o)}
        className="max-w-64 truncate rounded-md border border-slate-700 bg-slate-900 px-2 py-1 font-mono text-xs hover:border-slate-500">
        {value?.trading_symbol || value?.instrument_key || "Select instrument…"}
      </button>
      {open && (
        <div className="absolute z-20 mt-1 w-96 rounded-lg border border-slate-700 bg-slate-900 p-2 shadow-xl">
          <div className="flex gap-2">
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search symbol / name…"
              autoFocus
              className="w-full rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-sm outline-none focus:border-blue-500" />
            <select value={segment} onChange={(e) => setSegment(e.target.value)}
              className="rounded-md border border-slate-700 bg-slate-950 px-1 py-1 text-xs">
              <option value="">all segments</option>
              {segments.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <p className="px-1 py-1 text-xs text-slate-500">{total} matches (76k master)</p>
          <ul className="max-h-64 overflow-y-auto">
            {results.map((r) => (
              <li key={r.instrument_key}>
                <button
                  onClick={() => { onChange(r); setOpen(false); }}
                  className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-xs hover:bg-slate-800">
                  <span className="font-mono font-semibold">{r.trading_symbol}</span>
                  <span className="truncate text-slate-400">{r.name}</span>
                  <span className="ml-auto shrink-0 rounded bg-slate-800 px-1 font-mono text-[10px]">{r.segment}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [status, setStatus] = useState(null);
  const [ltp, setLtp] = useState(null);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [signals, setSignals] = useState([]);
  const [strategy, setStrategy] = useState("");
  const [instrument, setInstrument] = useState(() => {
    try { return JSON.parse(localStorage.getItem("ut.instrument")) || null; }
    catch { return null; }
  });

  const pickInstrument = (r) => {
    setInstrument(r);
    try { localStorage.setItem("ut.instrument", JSON.stringify(r)); } catch { /* ignore */ }
  };

  const refreshStatus = useCallback(async () => {
    const s = await get("/api/status");
    setStatus(s);
    if (!strategy && s.strategies?.length) setStrategy(s.strategies[0]);
  }, [strategy]);

  const refreshTables = useCallback(async () => {
    const [p, o, sg] = await Promise.all([get("/api/positions"), get("/api/orders"), get("/api/signals")]);
    setPositions(p.data || []);
    setOrders(o.data || []);
    setSignals(sg.data || []);
  }, []);

  const refreshLtp = useCallback(async () => {
    const key = instrument?.instrument_key;
    const d = await get(key ? `/api/ltp?instrument_key=${encodeURIComponent(key)}` : "/api/ltp");
    setLtp(d);
  }, [instrument?.instrument_key]);

  usePoll(refreshStatus, 10000);
  usePoll(refreshTables, 5000);
  usePoll(refreshLtp, 2000, [instrument?.instrument_key]);

  const engine = async (action) => {
    const d = await postEngine(action, strategy, instrument?.instrument_key);
    setStatus((s) => ({ ...s, engine: d.engine }));
  };

  const running = status?.engine?.running;

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 flex flex-wrap items-center gap-3 border-b border-slate-800 bg-slate-950/90 px-4 py-2 backdrop-blur">
        <span className="font-bold">upstox-trade</span>
        <InstrumentPicker value={instrument} onChange={pickInstrument} />
        <span className="font-mono text-xs text-slate-400">{ltp?.instrument_key || status?.instrument_key || "—"}</span>
        <span className="text-xl font-semibold">{ltp?.ltp ?? "—"}</span>
        <span className={`inline-block h-2.5 w-2.5 rounded-full ${ltp?.live ? "bg-green-500" : "bg-slate-600"}`} />
        <span className="rounded bg-slate-800 px-2 py-0.5 text-xs">{status?.env}</span>
        <div className="ml-auto flex items-center gap-2">
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)}
            className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-sm">
            {(status?.strategies || []).map((n) => <option key={n} value={n}>{n}</option>)}
          </select>
          <button onClick={() => engine("start")}
            className="rounded-md bg-green-600 px-3 py-1 text-sm font-medium hover:bg-green-500">Start</button>
          <button onClick={() => engine("stop")}
            className="rounded-md bg-slate-700 px-3 py-1 text-sm font-medium hover:bg-slate-600">Stop</button>
          <span className={`text-xs ${running ? "text-green-400" : "text-slate-500"}`}>
            {running ? "running" : "stopped"}
          </span>
        </div>
      </header>

      <main className="grid gap-3 p-3 md:grid-cols-2">
        <Card title="Strategies">
          <div className="flex flex-wrap gap-2">
            {(status?.strategies || []).map((n) => (
              <span key={n} className="rounded-full border border-slate-700 px-3 py-1 text-sm">{n}</span>
            ))}
          </div>
        </Card>
        <Card title="Status">
          <pre className="whitespace-pre-wrap text-xs text-slate-400">
            {status ? JSON.stringify(status, null, 2) : "loading…"}
          </pre>
        </Card>
        <Card title="Positions" wide>
          <DataTable rows={positions} columns={[
            { key: "id", label: "id" }, { key: "trading_symbol", label: "symbol" },
            { key: "qty_bought", label: "bought" }, { key: "qty_sold", label: "sold" },
            { key: "buy_price", label: "buy price" }, { key: "trigger_price", label: "trigger" },
          ]} />
        </Card>
        <Card title="Orders" wide>
          <DataTable rows={orders} columns={[
            { key: "order_id", label: "order id" }, { key: "instrument_token", label: "token" },
            { key: "transaction_type", label: "type" }, { key: "quantity", label: "qty" },
            { key: "filled_qty", label: "filled" }, { key: "price", label: "price" },
            { key: "tag", label: "tag" },
          ]} />
        </Card>
        <Card title="Signals" wide>
          <DataTable rows={signals} columns={[{ key: "id", label: "id" }, { key: "signal", label: "payload" }]} />
        </Card>
      </main>
    </div>
  );
}
