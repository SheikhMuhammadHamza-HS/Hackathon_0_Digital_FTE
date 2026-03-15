"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { 
  LayoutDashboard, 
  Mail, 
  MessageSquare, 
  CheckCircle2, 
  Share2, 
  Calculator, 
  Cloud, 
  ScrollText,
  Settings,
  Circle
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Emails", href: "/emails", icon: Mail },
  { name: "WhatsApp", href: "/whatsapp", icon: MessageSquare },
  { name: "Approvals", href: "/approvals", icon: CheckCircle2 },
  { name: "Social Media", href: "/social", icon: Share2 },
  { name: "Accounting", href: "/accounting", icon: Calculator },
  { name: "Cloud Status", href: "/status", icon: Cloud },
  { name: "Logs", href: "/logs", icon: ScrollText },
];

const systemStatus = [
  { name: "Cloud", status: "ONLINE", color: "bg-green-500" },
  { name: "Local", status: "RUNNING", color: "bg-green-500" },
  { name: "Odoo", status: "PORT 3006", color: "bg-blue-500" },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full w-64 bg-[#09090b] border-r border-zinc-800/50">
      <div className="p-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-indigo-600 rotate-45 flex items-center justify-center rounded-sm glow-purple">
            <div className="w-3 h-3 bg-white -rotate-45" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">VaultOS</h1>
            <p className="text-[10px] text-zinc-500 font-medium uppercase tracking-widest">AI Employee Command Center</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-all duration-200 group",
                isActive 
                  ? "bg-indigo-600/10 text-indigo-400 glow-purple" 
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
              )}
            >
              <item.icon className={cn(
                "w-4 h-4 transition-colors",
                isActive ? "text-indigo-400" : "text-zinc-500 group-hover:text-zinc-300"
              )} />
              {item.name}
            </Link>
          );
        })}
      </nav>

      <div className="p-6 mt-auto border-t border-zinc-800/50">
        <h3 className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-4">System Status</h3>
        <div className="space-y-3">
          {systemStatus.map((s) => (
            <div key={s.name} className="flex items-center justify-between text-[11px]">
              <div className="flex items-center gap-2 text-zinc-400">
                <div className={cn("w-1.5 h-1.5 rounded-full shadow-sm", s.color)} />
                {s.name}:
              </div>
              <span className="font-mono text-zinc-300 uppercase">{s.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
