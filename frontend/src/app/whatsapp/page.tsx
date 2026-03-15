"use client";

import { 
  MessageSquare, 
  Search, 
  MoreVertical, 
  CheckCheck,
  Clock,
  Send,
  User
} from "lucide-react";
import { useState } from "react";

const chats = [
  { id: 1, user: "+92 321 4567890", lastMsg: "Please send the invoice.", time: "10:15 AM", unread: 2, status: "pending" },
  { id: 2, user: "+44 789 0123456", lastMsg: "Meeting confirmed for Monday.", time: "9:45 AM", unread: 0, status: "active" },
  { id: 3, user: "+1 555 0101", lastMsg: "Thanks for the update!", time: "Yesterday", unread: 0, status: "done" },
];

export default function WhatsAppPage() {
  const [activeChat, setActiveChat] = useState(chats[0]);

  return (
    <div className="flex h-[calc(100vh-2rem)] m-4 bg-[#111113] border border-zinc-800/50 rounded-2xl overflow-hidden glass">
      {/* Sidebar - Chat List */}
      <div className="w-80 border-r border-zinc-800/50 flex flex-col">
        <div className="p-4 border-b border-zinc-800/50">
          <h2 className="text-xl font-bold mb-4">WhatsApp</h2>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
            <input 
              type="text" 
              placeholder="Search chats..." 
              className="w-full bg-zinc-900 border border-zinc-800 rounded-lg py-2 pl-10 pr-4 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            />
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto divide-y divide-zinc-800/30">
          {chats.map((chat) => (
            <button 
              key={chat.id}
              onClick={() => setActiveChat(chat)}
              className={`w-full p-4 flex items-start gap-3 hover:bg-zinc-800/30 transition-colors text-left ${
                activeChat.id === chat.id ? "bg-indigo-600/5 border-l-2 border-indigo-500" : ""
              }`}
            >
              <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-500 shrink-0 border border-zinc-700">
                <User className="w-5 h-5" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-sm font-bold text-zinc-200 truncate">{chat.user}</span>
                  <span className="text-[10px] text-zinc-500">{chat.time}</span>
                </div>
                <p className="text-xs text-zinc-500 truncate">{chat.lastMsg}</p>
              </div>
              {chat.unread > 0 && (
                <span className="w-4 h-4 rounded-full bg-indigo-600 text-[10px] font-bold flex items-center justify-center text-white mt-1">
                  {chat.unread}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Main Chat Window */}
      <div className="flex-1 flex flex-col bg-zinc-900/20">
        {/* Chat Header */}
        <div className="p-4 border-b border-zinc-800/50 bg-[#111113] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-500 border border-zinc-700">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">{activeChat.user}</h3>
              <p className="text-[10px] text-emerald-400 font-medium uppercase tracking-wider">Online</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button className="p-2 text-zinc-500 hover:text-white transition-colors">
              <MoreVertical className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Message Area */}
        <div className="flex-1 p-6 space-y-4 overflow-y-auto bg-[url('https://web.whatsapp.com/img/bg-chat-tile-dark_a4be512e71a7a31391991d0e9447419b.png')] bg-repeat opacity-40">
          <div className="flex justify-start">
            <div className="bg-zinc-800 rounded-2xl p-3 max-w-[70%] text-sm text-zinc-300 rounded-tl-none">
              Hello! This is an automated message regarding your inquiry.
              <span className="text-[10px] text-zinc-500 block mt-1 text-right">10:15 AM</span>
            </div>
          </div>
          <div className="flex justify-end">
            <div className="bg-indigo-600/90 rounded-2xl p-3 max-w-[70%] text-sm text-white rounded-tr-none glow-purple">
              {activeChat.lastMsg}
              <div className="flex items-center justify-end gap-1 mt-1">
                <span className="text-[10px] text-indigo-200">10:16 AM</span>
                <CheckCheck className="w-3 h-3 text-indigo-200" />
              </div>
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="p-4 bg-[#111113] border-t border-zinc-800/50">
          <div className="flex items-center gap-3">
            <input 
              type="text" 
              placeholder="Type a message..." 
              className="flex-1 bg-zinc-900 border border-zinc-800 rounded-xl py-3 px-4 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
            />
            <button className="w-12 h-12 bg-indigo-600 hover:bg-indigo-500 rounded-xl flex items-center justify-center text-white transition-all active:scale-95 glow-purple">
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
