import { Sidebar, MobileNav } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { RequireAuth } from "@/components/require-auth";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Topbar />
          <MobileNav />
          <main className="flex-1 p-5 lg:p-8">{children}</main>
        </div>
      </div>
    </RequireAuth>
  );
}
