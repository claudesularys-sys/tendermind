"use client";
import { useEffect, useState } from "react";
import { api, type FavoriteOut } from "@/lib/api";
import TenderCard from "@/components/tenders/TenderCard";

export default function FavoritesPage() {
  const [favs, setFavs] = useState<FavoriteOut[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () =>
    api.tenders.favorites().then((f) => {
      setFavs(f);
      setLoading(false);
    });

  useEffect(() => { load(); }, []);

  if (loading) return <div className="text-gray-400 text-sm">Загрузка...</div>;

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-5">
        Избранное {favs.length > 0 && <span className="text-gray-400 font-normal text-base">({favs.length})</span>}
      </h1>
      {favs.length === 0 ? (
        <div className="card text-center py-16 text-gray-400">
          <p className="text-4xl mb-3">⭐</p>
          <p className="font-medium text-gray-600">Нет сохранённых тендеров</p>
          <p className="text-sm mt-1">Нажмите «Сохранить» на карточке тендера</p>
        </div>
      ) : (
        <div className="space-y-2">
          {favs.map((f) => (
            <TenderCard key={f.id} tender={f.tender} onSave={load} />
          ))}
        </div>
      )}
    </div>
  );
}
