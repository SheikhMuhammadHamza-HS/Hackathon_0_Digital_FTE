"use client";

import { 
  Mail, 
  Search, 
  MoreVertical, 
  CheckCircle2, 
  XCircle,
  Clock,
  User,
  Star,
  Archive,
  Trash2,
  Reply
} from "lucide-react";
import { motion } from "framer-motion";

const emails = [
  { 
    id: 1, 
    from: "John Doe", 
    email: "john@example.com", 
    subject: "New Invoice #1234 Detail Request", 
    preview: "Hey team, I noticed a discrepancy in the latest invoice for the Global Tech project. Can you double check...", 
    date: "2h ago", 
    status: "Needs Action",
    priority: "High" 
  },
  { 
    id: 2, 
    from: "Vendor Payments", 
    email: "billing@vendor.com", 
    subject: "Annual Subscription Renewal Notice", 
    preview: "Your Platinum Cloud subscription is set to renew automatically on April 1st. No action required unless...", 
    date: "5h ago", 
    status: "Draft Sent",
    priority: "Medium" 
  },
  { 
    id: 3, 
    from: "Odoo ERP System", 
    email: "notifications@odoo.com", 
    subject: "Weekly Financial Summary Export", 
    preview: "The weekly financial report has been successfully generated and is ready for your review in the Vault...", 
    date: "Yesterday", 
    status: "Done",
    priority: "Low" 
  },
];

export default function EmailsPage() {
  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Email Queue</h1>
          <p className="text-zinc-500 mt-1">Manage automated drafts and incoming communication</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-1 flex gap-1">
            <button className="px-3 py-1.5 text-xs font-bold bg-zinc-800 text-white rounded">Queue</button>
            <button className="px-3 py-1.5 text-xs font-bold text-zinc-500 hover:text-zinc-300">Sent</button>
            <button className="px-3 py-1.5 text-xs font-bold text-zinc-500 hover:text-zinc-300">Archive</button>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        {emails.map((email) => (
          <motion.div 
            key={email.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="group bg-[#111113] border border-zinc-800/50 rounded-2xl overflow-hidden hover:border-indigo-500/30 transition-all glass hover:shadow-2xl hover:shadow-indigo-500/5"
          >
            <div className="p-6 flex items-start gap-6">
              <div className="w-12 h-12 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-400 shrink-0 group-hover:bg-indigo-500/10 group-hover:text-indigo-400 transition-colors">
                <User className="w-6 h-6" />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <h4 className="font-bold text-white tracking-tight">{email.from}</h4>
                    <span className="text-[11px] text-zinc-500 hidden sm:block">{email.email}</span>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] font-medium text-zinc-500">
                    <Clock className="w-3 h-3" /> {email.date}
                  </div>
                </div>
                
                <h5 className="text-sm font-semibold text-zinc-200 mb-1">{email.subject}</h5>
                <p className="text-sm text-zinc-400 line-clamp-2 leading-relaxed">{email.preview}</p>
                
                <div className="flex items-center gap-4 mt-6">
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-sm uppercase tracking-widest ${
                    email.status === "Needs Action" ? "bg-amber-500/10 text-amber-500 border border-amber-500/20" :
                    email.status === "Done" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                    "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
                  }`}>
                    {email.status}
                  </span>
                  
                  {email.status === "Needs Action" && (
                    <div className="flex items-center gap-3">
                      <button className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-400 hover:text-emerald-300 transition-colors uppercase tracking-wider">
                        <CheckCircle2 className="w-4 h-4" /> Approve & Send
                      </button>
                      <span className="text-zinc-800 text-xs">|</span>
                      <button className="flex items-center gap-1.5 text-[11px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-wider">
                        <Reply className="w-4 h-4" /> Edit Draft
                      </button>
                    </div>
                  )}
                </div>
              </div>

              <div className="flex flex-col gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="p-2 text-zinc-600 hover:text-amber-400 transition-colors"><Star className="w-4 h-4" /></button>
                <button className="p-2 text-zinc-600 hover:text-white transition-colors"><Archive className="w-4 h-4" /></button>
                <button className="p-2 text-zinc-600 hover:text-red-400 transition-colors"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
