"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";

const NAV = [
  { href: "/dashboard", icon: "🔥", label: "Активные" },
  { href: "/favorites", icon: "⭐", label: "Избранное" },
  { href: "/sources", icon: "📡", label: "Источники" },
  { href: "/settings/profile", icon: "⚙️", label: "Профиль" },
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="w-[200px] min-h-screen bg-white border-r border-gray-200 flex flex-col px-3 py-4 fixed top-0 left-0">
      <div className="px-3 mb-6">
        <span className="text-base font-bold text-gray-900">
          Tender<span className="text-blue-600">Mind</span>
        </span>
      </div>

      <nav className="flex flex-col gap-1 flex-1">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors",
              path.startsWith(item.href)
                ? "bg-blue-50 text-blue-700 font-medium"
                : "text-gray-600 hover:bg-gray-100"
            )}
          >
            <span>{item.icon}</span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="border-t border-gray-100 pt-3 px-3 space-y-1">
        <p className="text-xs text-gray-400">Telegram подключён ✓</p>
        <p className="text-xs text-gray-400">40+ источников</p>
      </div>
    </aside>
  );
}
