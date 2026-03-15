"use client";

import { 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ExternalLink,
  ShieldCheck,
  AlertCircle
} from "lucide-react";
import { motion } from "framer-motion";

const approvals = [
  { 
    id: "APR-2026-001", 
    type: "Financial", 
    title: "Approve Invoice #INV-882", 
    description: "New invoice generated for Client 'Global Tech' - $1,250.00", 
    priority: "High", 
    time: "15 mins ago" 
  },
  { 
    id: "APR-2026-002", 
    type: "Communication", 
    title: "Draft Email to HR", 
    description: "Response to candidate 'Sarah Jawad' regarding technical interview feedback.", 
    priority: "Medium", 
    time: "45 mins ago" 
  },
  { 
    id: "APR-2026-003", 
    type: "Social Media", 
    title: "X Post: Project Milestone", 
    description: "Scheduled post about reaching 1,000 active cloud instances.", 
    priority: "Low", 
    time: "2 hours ago" 
  },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1 }
  }
};

const item = {
  hidden: { y: 20, opacity: 0 },
  show: { y: 0, opacity: 1 }
};

export default function ApprovalsPage() {
  return (
    <motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="p-8 space-y-8 max-w-7xl mx-auto"
    >
      <motion.div variants={item}>
        <h1 className="text-3xl font-bold tracking-tight">Pending Approvals</h1>
        <p className="text-zinc-500 mt-1">Human-in-the-loop: Review and authorize AI actions</p>
      </motion.div>

      <motion.div variants={item} className="grid grid-cols-1 gap-6">
        {approvals.map((app) => (
          <div key={app.id} className="bg-[#111113] border border-zinc-800/50 rounded-2xl p-6 hover:border-indigo-500/30 transition-all group glass">
            <div className="flex flex-col md:flex-row md:items-center gap-6">
              <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500/10 text-indigo-400 shrink-0 glow-purple border border-indigo-500/20">
                <ShieldCheck className="w-7 h-7" />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-widest text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                    {app.type}
                  </span>
                  <span className={cn(
                    "text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded border",
                    app.priority === "High" ? "bg-red-500/10 text-red-500 border-red-500/20" :
                    app.priority === "Medium" ? "bg-amber-500/10 text-amber-500 border-amber-500/20" :
                    "bg-zinc-500/10 text-zinc-400 border-zinc-500/20"
                  )}>
                    {app.priority} Priority
                  </span>
                </div>
                <h3 className="text-lg font-bold text-white group-hover:text-indigo-400 transition-colors">
                  {app.title}
                </h3>
                <p className="text-sm text-zinc-400 mt-1 mb-4">{app.description}</p>
                <div className="flex items-center gap-4 text-[11px] text-zinc-500 font-medium">
                  <div className="flex items-center gap-1.5"><Clock className="w-3 h-3" /> {app.time}</div>
                  <div className="flex items-center gap-1.5"><AlertCircle className="w-3 h-3" /> ID: {app.id}</div>
                </div>
              </div>

              <div className="flex flex-row md:flex-col gap-3 shrink-0">
                <button className="flex items-center justify-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-semibold transition-all hover:scale-[1.02] active:scale-95 glow-purple">
                  <CheckCircle2 className="w-4 h-4" /> Approve
                </button>
                <button className="flex items-center justify-center gap-2 px-6 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-sm font-semibold transition-all hover:scale-[1.02] active:scale-95 border border-zinc-700/50">
                  <XCircle className="w-4 h-4" /> Reject
                </button>
              </div>
            </div>
          </div>
        ))}
      </motion.div>
    </motion.div>
  );
}

function cn(...inputs: any[]) {
  return inputs.filter(Boolean).join(" ");
}
