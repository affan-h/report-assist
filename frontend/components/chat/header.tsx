import { useState, useEffect, useRef } from "react";
import { Session } from "@/lib/chat-utils";

export const ChatHeader = ({ session }: { session: Session }) => {
  const [isVisible, setIsVisible] = useState(true);
  const lastScrollY = useRef(0); // Use a ref to track scroll position without triggering re-renders

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      // Logic:
      // 1. If current scroll is greater than last scroll -> we are scrolling DOWN.
      // 2. We add a small buffer (e.g., > 10) to prevent jitter at the very top.
      if (currentScrollY > lastScrollY.current && currentScrollY > 10) {
        setIsVisible(false);
      } else {
        setIsVisible(true);
      }

      lastScrollY.current = currentScrollY;
    };

    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);

  return (
    <div
      className={`
      shrink-0 p-4 border-b border-neutral-200/60 bg-white/50 backdrop-blur-sm sticky top-0 z-10
      transition-transform duration-300 ease-in-out
      ${isVisible ? "translate-y-0" : "-translate-y-full"}
    `}
    >
      <h3 className="text-lg font-semibold text-neutral-800 tracking-tight flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
        {session.title || "New Analysis Session"}
      </h3>
      <p className="text-xs text-neutral-400 pl-4 font-mono">{session.id}</p>
    </div>
  );
};
