"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Loader2 } from "lucide-react";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const isLoginPage = pathname === "/login";
    const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

    if (!token && !isLoginPage) {
      router.push("/login");
    } else if (token && isLoginPage) {
      router.push("/");
    } else {
      setLoading(false);
    }
  }, [pathname, router]);

  if (loading && pathname !== "/login") {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#09090b]">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}
