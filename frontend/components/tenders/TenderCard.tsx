"use client";
import { useState } from "react";
import { api, type Tender } from "@/lib/api";

const FLAGS: Record<string, string> = {
  US: "🇺🇸", GB: "🇬🇧", DE: "🇩🇪", FR: "🇫🇷", IT: "🇮🇹", ES: "🇪🇸",
  PL: "🇵🇱", NL: "🇳🇱", SE: "🇸🇪", NO: "🇳🇴", FI: "🇫🇮", DK: "🇩🇰",
  AT: "🇦🇹", CA: "🇨🇦", AU: "🇦🇺", JP: "🇯🇵", KR: "🇰🇷", CN: "🇨🇳",
  IN: "🇮🇳", KZ: "🇰🇿", RU: "🇷🇺", UA: "🇺🇦", BY: "🇧🇾", UZ: "🇺🇿",
  TR: "🇹🇷", SA: "🇸🇦", AE: "🇦🇪", BR: "🇧🇷", EU: "🇪🇺", UN: "🇺🇳", WB: "🌍",
};

function daysLeft(deadline: string): number {
  return Math.ceil((new Date(deadline).getTime() - Date.now()) / 86400000);
}

function formatBudget(t: Tender): string | null {
  if (t.budget_usd) return `$${t.budget_usd.toLocaleString("en", { maximumFractionDigits: 0 })}`;
  if (t.budget_original && t.currency_original)
    return `${t.budget_original.toLocaleString("en", { maximumFractionDigits: 0 })} ${t.currency_original}`;
  return null;
}

export default function TenderCard({ tender: t, onSave }: { tender: Tender; onSave?: () => void }) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const days = daysLeft(t.deadline);
  const flag = FLAGS[t.country_code] ?? "🌐";
  const budget = formatBudget(t);
  const isNew = Date.now() - new Date(t.created_at).getTime() < 86400000;
  const urgent = days <= 7;

  const deadlineStr = new Date(t.deadline).toLocaleDateString("ru-RU", {
    day: "numeric", month: "short", year: "numeric",
  });

  async function handleSave() {
    setSaving(true);
    try {
      await api.tenders.save(t.id);
      setSaved(true);
      onSave?.();
    } catch {
      // not logged in or error
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className={`card hover:border-blue-300 transition-colors flex items-start gap-3 ${
        isNew ? "border-l-2 border-l-green-400" : ""
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-2 mb-1.5">
          <span className="text-sm">{flag}</span>
          <span className="text-sm font-medium text-gray-900 line-clamp-2">{t.title}</span>
        </div>

        {t.equipment_summary && (
          <p className="text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded mb-1.5 inline-block">
            📋 {t.equipment_summary}
          </p>
        )}

        <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
          <span>
            {t.country_name}{t.city ? ` · ${t.city}` : ""}
          </span>
          <span className="text-gray-300">·</span>
          <span className="capitalize text-gray-400">{t.source_id.replace(/_/g, " ")}</span>
          {budget && (
            <>
              <span className="text-gray-300">·</span>
              <span className="font-medium text-gray-700">{budget}</span>
            </>
          )}
        </div>
      </div>

      <div className="flex flex-col items-end gap-2 flex-shrink-0">
        <span
          className={`text-xs font-medium px-2 py-1 rounded-full ${
            urgent ? "badge-red" : days <= 30 ? "badge-yellow" : "badge-green"
          }`}
        >
          ⏰ {deadlineStr} · {days} дн.
        </span>

        <div className="flex gap-1.5">
          <button
            onClick={handleSave}
            disabled={saving || saved}
            className={`text-xs px-2 py-1 rounded border transition-colors ${
              saved
                ? "bg-green-50 text-green-600 border-green-200"
                : "bg-white text-gray-500 border-gray-200 hover:border-blue-400 hover:text-blue-600"
            }`}
          >
            {saved ? "★ Сохранено" : "☆ Сохранить"}
          </button>
          <a
            href={t.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs px-2 py-1 rounded border border-transparent bg-blue-600 text-white hover:bg-blue-700 transition-colors"
          >
            ↗ Открыть
          </a>
        </div>
      </div>
    </div>
  );
}
