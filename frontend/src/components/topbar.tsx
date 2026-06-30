"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, Check, LogOut, ScanSearch, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";
import { useAuth } from "@/components/auth-provider";

export function Topbar() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [query, setQuery] = useState("");
  const [bellOpen, setBellOpen] = useState(false);
  const [acctOpen, setAcctOpen] = useState(false);

  const initials = (user?.email ?? "?").slice(0, 2).toUpperCase();

  function onSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    router.push(q ? `/agents?q=${encodeURIComponent(q)}` : "/agents");
  }

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center justify-between gap-4 border-b glass px-5 lg:px-8">
      <form onSubmit={onSearch} className="flex flex-1 items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm text-muted-foreground sm:max-w-xs">
        <Search className="size-4" />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search agents…"
          className="w-full bg-transparent text-foreground outline-none placeholder:text-muted-foreground"
        />
      </form>
      <div className="flex items-center gap-2">
        <Link href="/new" className="hidden sm:block">
          <Button size="sm" variant="accent"><ScanSearch /> Run evaluation</Button>
        </Link>
        <ThemeToggle />
        <div className="relative">
          <Button size="icon" variant="ghost" aria-label="Notifications" onClick={() => setBellOpen((o) => !o)}>
            <Bell className="size-4" />
          </Button>
          {bellOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setBellOpen(false)} />
              <div className="absolute right-0 z-50 mt-2 w-64 rounded-xl border bg-card p-2 shadow-lg">
                <p className="px-2 py-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">Notifications</p>
                <div className="flex items-center gap-2 rounded-lg px-2 py-3 text-sm text-muted-foreground">
                  <Check className="size-4 text-[hsl(var(--success))]" /> You&apos;re all caught up.
                </div>
              </div>
            </>
          )}
        </div>
        <div className="relative">
          <button
            onClick={() => setAcctOpen((o) => !o)}
            className="flex items-center gap-2 rounded-full border bg-card py-1 pl-1 pr-3 transition-colors hover:bg-secondary/60"
          >
            <span className="grid size-7 place-items-center rounded-full accent-bg text-xs font-semibold text-white">{initials}</span>
            <span className="hidden max-w-[120px] truncate text-sm font-medium sm:inline">{user?.email ?? "Account"}</span>
          </button>
          {acctOpen && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setAcctOpen(false)} />
              <div className="absolute right-0 z-50 mt-2 w-56 rounded-xl border bg-card p-2 shadow-lg">
                <div className="border-b px-2 pb-2">
                  <p className="truncate text-sm font-medium">{user?.email}</p>
                  <p className="text-xs text-muted-foreground">Signed in</p>
                </div>
                <button
                  onClick={() => { setAcctOpen(false); logout(); }}
                  className="mt-1 flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-[hsl(var(--danger))] transition-colors hover:bg-secondary/60"
                >
                  <LogOut className="size-4" /> Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
