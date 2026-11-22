"use client";
import { useState, useEffect } from "react";
import { api, type CompanyProfile } from "@/lib/api";

const TRANSFORMER_TYPES = [
  "Силовые", "Распределительные", "Масляные", "Сухие", "Автотрансформаторы",
  "Измерительные", "Oil-cooled", "Dry-type", "Step-up", "Step-down",
];

const VOLTAGE_OPTIONS = ["6 kV", "10 kV", "20 kV", "35 kV", "110 kV", "220 kV", "500 kV", "750 kV"];

export default function ProfilePage() {
  const [form, setForm] = useState<Partial<CompanyProfile>>({
    company_name: "",
    transformer_types: [],
    power_kva_min: undefined,
    power_kva_max: undefined,
    voltage_kv: [],
    certifications: [],
    max_delivery_days: undefined,
    target_countries: [],
    min_budget_usd: undefined,
    keywords_extra: [],
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [extraKw, setExtraKw] = useState("");

  useEffect(() => {
    api.profile.get().then((p) => {
      if (p) setForm(p);
      setLoading(false);
    });
  }, []);

  function toggleArray(field: keyof CompanyProfile, value: string) {
    const arr = (form[field] as string[]) ?? [];
    const next = arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
    setForm({ ...form, [field]: next });
  }

  function addKeyword() {
    const kw = extraKw.trim();
    if (!kw) return;
    const arr = form.keywords_extra ?? [];
    if (!arr.includes(kw)) setForm({ ...form, keywords_extra: [...arr, kw] });
    setExtraKw("");
  }

  async function handleSave() {
    setSaving(true);
    try {
      await api.profile.update(form);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      alert("Ошибка сохранения: " + e);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="text-gray-400 text-sm">Загрузка...</div>;

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-gray-900 mb-1">Профиль компании</h1>
      <p className="text-sm text-gray-500 mb-6">
        AI использует эти данные для поиска подходящих тендеров по всему миру.
      </p>

      <div className="space-y-5">
        {/* Company name */}
        <div className="card">
          <label className="label">Название компании</label>
          <input
            className="input"
            value={form.company_name ?? ""}
            onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            placeholder="ООО «ТрансЭнерго»"
          />
        </div>

        {/* Transformer types */}
        <div className="card">
          <label className="label">Типы трансформаторов (что вы производите/поставляете)</label>
          <div className="flex flex-wrap gap-2">
            {TRANSFORMER_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => toggleArray("transformer_types", t)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                  (form.transformer_types ?? []).includes(t)
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-200 hover:border-blue-400"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Power range */}
        <div className="card">
          <label className="label">Мощность (kVA)</label>
          <div className="flex gap-3 items-center">
            <input
              className="input"
              type="number"
              placeholder="от 100"
              value={form.power_kva_min ?? ""}
              onChange={(e) => setForm({ ...form, power_kva_min: Number(e.target.value) || undefined })}
            />
            <span className="text-gray-400 text-sm">—</span>
            <input
              className="input"
              type="number"
              placeholder="до 10 000"
              value={form.power_kva_max ?? ""}
              onChange={(e) => setForm({ ...form, power_kva_max: Number(e.target.value) || undefined })}
            />
          </div>
        </div>

        {/* Voltage */}
        <div className="card">
          <label className="label">Напряжение (кВ)</label>
          <div className="flex flex-wrap gap-2">
            {VOLTAGE_OPTIONS.map((v) => (
              <button
                key={v}
                onClick={() => toggleArray("voltage_kv", v)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                  (form.voltage_kv ?? []).includes(v)
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-200 hover:border-blue-400"
                }`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>

        {/* Min budget & max delivery */}
        <div className="card">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Минимальная сумма тендера (USD)</label>
              <input
                className="input"
                type="number"
                placeholder="100000"
                value={form.min_budget_usd ?? ""}
                onChange={(e) => setForm({ ...form, min_budget_usd: Number(e.target.value) || undefined })}
              />
            </div>
            <div>
              <label className="label">Макс. срок поставки (дней)</label>
              <input
                className="input"
                type="number"
                placeholder="180"
                value={form.max_delivery_days ?? ""}
                onChange={(e) => setForm({ ...form, max_delivery_days: Number(e.target.value) || undefined })}
              />
            </div>
          </div>
        </div>

        {/* Extra keywords */}
        <div className="card">
          <label className="label">Дополнительные ключевые слова для поиска</label>
          <div className="flex gap-2 mb-2">
            <input
              className="input"
              value={extraKw}
              onChange={(e) => setExtraKw(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addKeyword()}
              placeholder="напр. «isolation transformer» или «трансформатор тока»"
            />
            <button onClick={addKeyword} className="btn-ghost whitespace-nowrap">+ Добавить</button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(form.keywords_extra ?? []).map((kw) => (
              <span
                key={kw}
                className="badge-blue flex items-center gap-1 cursor-pointer"
                onClick={() => setForm({ ...form, keywords_extra: form.keywords_extra?.filter((k) => k !== kw) })}
              >
                {kw} ✕
              </span>
            ))}
          </div>
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className={`btn-primary w-full py-3 text-base ${saved ? "bg-green-600 hover:bg-green-600" : ""}`}
        >
          {saving ? "Сохранение..." : saved ? "✓ Сохранено" : "Сохранить профиль"}
        </button>
        <p className="text-xs text-gray-400 text-center">
          После сохранения AI пересчитает соответствие для всех активных тендеров.
        </p>
      </div>
    </div>
  );
}
