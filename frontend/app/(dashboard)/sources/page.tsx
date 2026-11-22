"use client";
import { useEffect, useState } from "react";
import { api, type SourceStatus } from "@/lib/api";

const REGION_LABELS: Record<string, string> = {
  americas:      "🌎 Америка",
  europe:        "🌍 Европа",
  asia:          "🌏 Азия / Тихоокеан",
  cis:           "🇷🇺 СНГ / Турция",
  mena:          "🌙 MENA / Африка",
  international: "🌐 Международные",
};

function timeAgo(iso: string): string {
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff} сек. назад`;
  if (diff < 3600) return `${Math.floor(diff / 60)} мин. назад`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} ч. назад`;
  return `${Math.floor(diff / 86400)} д. назад`;
}

export default function SourcesPage() {
  const [sources, setSources] = useState<SourceStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState<string | null>(null);

  useEffect(() => {
    api.sources.list().then((s) => {
      setSources(s);
      setLoading(false);
    });
    const t = setInterval(() => api.sources.list().then(setSources), 30_000);
    return () => clearInterval(t);
  }, []);

  async function handleTrigger(sourceId: string) {
    setTriggering(sourceId);
    try {
      await api.sources.trigger(sourceId);
    } finally {
      setTimeout(() => setTriggering(null), 3000);
    }
  }

  const grouped = sources.reduce<Record<string, SourceStatus[]>>((acc, s) => {
    acc[s.region] = [...(acc[s.region] ?? []), s];
    return acc;
  }, {});

  const ok      = sources.filter((s) => s.last_status === "ok").length;
  const errored = sources.filter((s) => s.last_status === "error").length;
  const pending = sources.filter((s) => !s.last_status).length;

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="card h-12 animate-pulse bg-gray-100" />
        ))}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-900">Источники</h1>
        <div className="flex gap-4 text-sm">
          <span className="text-green-600">● {ok} активны</span>
          {errored > 0 && <span className="text-red-500">● {errored} ошибка</span>}
          {pending > 0 && <span className="text-gray-400">● {pending} ожидают</span>}
          <span className="text-gray-400">Всего: {sources.length}</span>
        </div>
      </div>

      <div className="space-y-6">
        {Object.entries(REGION_LABELS).map(([region, label]) => {
          const items = grouped[region] ?? [];
          if (!items.length) return null;
          return (
            <div key={region}>
              <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2 px-1">
                {label}
              </h2>
              <div className="card p-0 overflow-hidden divide-y divide-gray-100">
                {items.map((s) => (
                  <div
                    key={s.source_id}
                    className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors"
                  >
                    <span
                      className={`w-2 h-2 rounded-full flex-shrink-0 ${
                        s.last_status === "ok"
                          ? "bg-green-400"
                          : s.last_status === "error"
                          ? "bg-red-400 animate-pulse"
                          : "bg-gray-300"
                      }`}
                    />

                    <div className="flex-1 min-w-0">
                      <span className="text-sm font-medium text-gray-900">
                        {s.source_id.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs text-gray-400 ml-2">{s.country_name}</span>
                    </div>

                    <div className="text-xs text-right text-gray-400 min-w-[100px]">
                      {s.last_run_at ? (
                        <>
                          <div>{timeAgo(s.last_run_at)}</div>
                          {s.last_new != null && s.last_new > 0 && (
                            <div className="text-green-600">+{s.last_new} новых</div>
                          )}
                          {s.last_status === "error" && (
                            <div className="text-red-500">Ошибка</div>
                          )}
                        </>
                      ) : (
                        <span className="text-gray-300">Не запускался</span>
                      )}
                    </div>

                    <span
                      className={`text-xs px-2 py-0.5 rounded border flex-shrink-0 ${
                        s.schedule.includes("*/30")
                          ? "badge-blue"
                          : "bg-gray-50 text-gray-400 border-gray-200"
                      }`}
                    >
                      {s.schedule.includes("*/30") ? "30 мин" : "2 ч"}
                    </span>

                    <button
                      onClick={() => handleTrigger(s.source_id)}
                      disabled={triggering === s.source_id}
                      className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-500 hover:border-blue-400 hover:text-blue-600 transition-colors disabled:opacity-50 flex-shrink-0"
                      title="Запустить вручную"
                    >
                      {triggering === s.source_id ? "⏳" : "▶"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
