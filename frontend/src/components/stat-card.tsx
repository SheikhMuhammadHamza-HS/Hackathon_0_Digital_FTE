import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle: string;
  icon: LucideIcon;
  variant?: "default" | "purple" | "green" | "orange";
}

export function StatCard({ title, value, subtitle, icon: Icon, variant = "default" }: StatCardProps) {
  return (
    <div className="bg-[#111113] border border-zinc-800/50 rounded-xl p-5 hover:border-zinc-700/50 transition-colors group">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-zinc-400">{title}</p>
          <h3 className="text-3xl font-bold mt-2 tracking-tight group-hover:text-indigo-400 transition-colors">{value}</h3>
          <p className="text-[11px] text-zinc-500 mt-1">{subtitle}</p>
        </div>
        <div className={cn(
          "w-10 h-10 rounded-lg flex items-center justify-center bg-zinc-800/50",
          variant === "purple" && "text-indigo-400",
          variant === "green" && "text-emerald-400",
          variant === "orange" && "text-orange-400"
        )}>
          <Icon className="w-5 h-4" />
        </div>
      </div>
    </div>
  );
}
