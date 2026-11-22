"use client";
import { useState, useEffect, useCallback } from "react";
import { api, type Tender, type TenderListResponse } from "@/lib/api";
import TenderCard from "@/components/tenders/TenderCard";
import { formatDistanceToNow } from "date-fns";

const COUNTRY_FILTERS = [
  { code: "", label: "Все страны" },
  { code: "US", label: "🇺🇸 США" },
  { code: "GB", label: "🇬🇧 UK" },
  { code: "DE", label: "🇩🇪 Германия" },
  { code: "FR", label: "🇫🇷 Франция" },
  { code: "IN", label: "🇮🇳 Индия" },
  { code: "KZ", label: "🇰🇿 Казахстан" },
  { code: "RU", label: "🇷🇺 Россия" },
];

export default function DashboardPage() {
  const [data, setData] = useState<TenderListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [country, setCountry] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const load = useCallback(async () => {
    try {
      const res = await api.tenders.list({ country_code: country || undefined });
      setData(res);
      setLastUpdated(new Date());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [country]);

  useEffect(() => {
    load();
    const timer = setInterval(load, 60_000); // auto-refresh every 60s
    return () => clearInterval(timer);
  }, [load]);

  const tenders = data?.items ?? [];
  const newToday = tenders.filter((t) => {
    const d = new Date(t.created_at);
    const today = new Date();
    return d.toDateString() === today.toDateString();
  }).length;

  const expiringSoon = tenders.filter((t) => {
    const days = Math.ceil((new Date(t.deadline).getTime() - Date.now()) / 86400000);
    return days <= 7;
  }).length;

  const countries = new Set(tenders.map((t) => t.country_code)).size;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Активные тендеры</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Обновлено {formatDistanceToNow(lastUpdated, { addSuffix: true })}
          </p>
        </div>
        {newToday > 0 && (
          <span className="badge-green">🟢 {newToday} новых сегодня</span>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        {[
          { label: "Активных", value: data?.total ?? "—" },
          { label: "Новых (24h)", value: newToday },
          { label: "Стран", value: countries },
          { label: "Истекают ≤7 дн.", value: expiringSoon, warn: expiringSoon > 0 },
        ].map((s) => (
          <div key={s.label} className="card">
            <div className={`text-2xl font-bold ${s.warn ? "text-red-600" : "text-gray-900"}`}>
              {s.value}
            </div>
            <div className="text-xs text-gray-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Country filters */}
      <div className="flex gap-2 mb-5 flex-wrap">
        {COUNTRY_FILTERS.map((f) => (
          <button
            key={f.code}
            onClick={() => setCountry(f.code)}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              country === f.code
                ? "bg-blue-600 text-white border-blue-600"
                : "bg-white text-gray-600 border-gray-200 hover:border-blue-400"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Tender list */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="card animate-pulse h-20 bg-gray-100" />
          ))}
        </div>
      ) : tenders.length === 0 ? (
        <div className="card text-center py-16 text-gray-400">
          <p className="text-4xl mb-3">🔍</p>
          <p className="font-medium text-gray-600">Нет активных тендеров</p>
          <p className="text-sm mt-1">
            Заполните <a href="/settings/profile" className="text-blue-600 underline">профиль компании</a>,
            чтобы начать получать подходящие тендеры
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {tenders.map((t) => (
            <TenderCard key={t.id} tender={t} onSave={load} />
          ))}
          {data && data.total > tenders.length && (
            <p className="text-center text-sm text-gray-400 pt-2">
              Показано {tenders.length} из {data.total}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
