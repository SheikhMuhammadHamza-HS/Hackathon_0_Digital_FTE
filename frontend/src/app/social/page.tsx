"use client";

import { 
  Twitter, 
  Linkedin, 
  Facebook, 
  Instagram, 
  Plus, 
  Calendar,
  BarChart3,
  History
} from "lucide-react";
import { motion } from "framer-motion";

const socials = [
  { platform: "𝕏 (Twitter)", icon: Twitter, status: "Connected", color: "text-white" },
  { platform: "LinkedIn", icon: Linkedin, status: "Connected", color: "text-blue-500" },
  { platform: "Facebook", icon: Facebook, status: "Drafting", color: "text-blue-600" },
];

const posts = [
  { id: 1, platform: "𝕏", content: "Excited to announce our new partnership! 🚀 #Tech #AI", status: "Posted", time: "2h ago" },
  { id: 2, platform: "LinkedIn", content: "The future of autonomous work is here. Here's how we're building it.", status: "Scheduled", time: "In 4h" },
  { id: 3, platform: "𝕏", content: "Don't miss our live demo today at 5 PM PST!", status: "Failed", time: "1h ago" },
];

export default function SocialMediaPage() {
  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Social Media</h1>
          <p className="text-zinc-500 mt-1">Multi-channel presence orchestration</p>
        </div>
        <button className="flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 rounded-xl text-sm font-bold transition-all glow-purple">
          <Plus className="w-4 h-4" /> Create Post
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {socials.map((s) => (
          <div key={s.platform} className="bg-[#111113] border border-zinc-800/50 rounded-2xl p-6 glass">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-zinc-800 flex items-center justify-center">
                <s.icon className={`w-6 h-6 ${s.color}`} />
              </div>
              <div>
                <h3 className="font-bold text-white">{s.platform}</h3>
                <span className="text-xs text-emerald-400 font-medium">{s.status}</span>
              </div>
            </div>
            <div className="mt-6 flex items-center gap-4 text-xs text-zinc-500 font-medium">
              <div className="flex items-center gap-1.5"><BarChart3 className="w-3 h-3" /> 1.2k reach</div>
              <div className="flex items-center gap-1.5"><History className="w-3 h-3" /> 4 posts</div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-[#111113] border border-zinc-800/50 rounded-2xl overflow-hidden glass">
        <div className="p-6 border-b border-zinc-800/50 flex items-center justify-between">
          <h3 className="font-bold text-white flex items-center gap-2">
            <Calendar className="w-4 h-4 text-indigo-400" /> Recent Activity
          </h3>
        </div>
        <div className="divide-y divide-zinc-800/50">
          {posts.map((post) => (
            <div key={post.id} className="p-6 flex items-center gap-6 hover:bg-zinc-800/20 transition-colors">
              <div className="w-10 h-10 rounded-lg bg-zinc-900 border border-zinc-800 flex items-center justify-center font-bold text-zinc-400 shrink-0">
                {post.platform}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{post.content}</p>
                <span className="text-[11px] text-zinc-500 mt-1 block">{post.time}</span>
              </div>
              <div className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                post.status === "Posted" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                post.status === "Failed" ? "bg-red-500/10 text-red-500 border border-red-500/20" :
                "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20"
              }`}>
                {post.status}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
