"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Bot, Footprints, LayoutDashboard, Plus, Settings, ShieldCheck } from "lucide-react";
import { Logo } from "@/components/logo";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/traces", label: "Traces", icon: Footprints },
  { href: "/monitoring", label: "Monitoring", icon: Activity },
  { href: "/settings", label: "Settings", icon: Settings },
];

function isActive(pathname: string, href: string) {
  return pathname === href || pathname.startsWith(href + "/");
}

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r bg-card/40 lg:flex">
      <div className="flex h-16 items-center border-b px-6">
        <Link href="/dashboard"><Logo /></Link>
      </div>
      <div className="p-4">
        <Link href="/new" className="flex items-center justify-center gap-2 rounded-lg accent-bg px-3 py-2 text-sm font-medium text-white shadow-sm transition-opacity hover:opacity-90">
          <Plus className="size-4" /> New Evaluation
        </Link>
      </div>
      <nav className="flex-1 space-y-1 px-4">
        {NAV.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link key={item.href} href={item.href}
              className={cn("flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-secondary text-foreground" : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground")}>
              <item.icon className="size-4" />{item.label}
            </Link>
          );
        })}
      </nav>
      <div className="m-4 rounded-xl border bg-gradient-to-b from-accent/10 to-transparent p-4">
        <div className="flex items-center gap-2 text-sm font-medium"><ShieldCheck className="size-4 text-accent" /> Free plan</div>
        <p className="mt-1 text-xs text-muted-foreground">3 agents · upgrade for monitoring & auto-fix.</p>
        <Link href="/settings" className="mt-3 block rounded-md border bg-background px-3 py-1.5 text-center text-xs font-medium transition-colors hover:bg-secondary">Upgrade plan</Link>
      </div>
    </aside>
  );
}

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="flex items-center gap-1 overflow-x-auto border-b bg-card/60 px-2 py-2 scroll-thin lg:hidden">
      <Link href="/dashboard" className="mr-1 shrink-0 px-2"><Logo showWord={false} /></Link>
      {NAV.map((item) => {
        const active = isActive(pathname, item.href);
        return (
          <Link key={item.href} href={item.href} className={cn("flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium", active ? "bg-secondary text-foreground" : "text-muted-foreground")}>
            <item.icon className="size-3.5" />{item.label}
          </Link>
        );
      })}
    </nav>
  );
}
