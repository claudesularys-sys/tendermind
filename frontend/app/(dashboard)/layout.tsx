import Sidebar from "@/components/layout/Sidebar";
import AuthGuard from "@/components/AuthGuard";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1 ml-[200px] p-6 max-w-6xl">
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}
