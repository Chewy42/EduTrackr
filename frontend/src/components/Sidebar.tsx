import React, { ReactNode, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  FiHome,
  FiCalendar,
  FiSearch,
  FiSettings,
  FiMenu,
} from "react-icons/fi";

interface NavItem {
  label: string;
  to: string;
  icon: ReactNode;
}

const navItems: NavItem[] = [
  {
    label: "Home",
    to: "/",
    icon: <FiHome className="text-xl" />,
  },
  {
    label: "Generate Schedule",
    to: "/schedule-gen-home",
    icon: <FiCalendar className="text-xl" />,
  },
  {
    label: "Explore my Options",
    to: "/exploration-assistant",
    icon: <FiSearch className="text-xl" />,
  },
  {
    label: "Settings",
    to: "/settings",
    icon: <FiSettings className="text-xl" />,
  },
];

export default function Sidebar() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(() => 
    typeof window !== 'undefined' ? window.innerWidth < 768 : false
  );

  return (
    <aside
      className={[
        "flex h-screen flex-col bg-blue-600 text-white shadow-xl transition-[width] duration-300 ease-out",
        collapsed ? "w-20" : "w-64",
      ].join(" ")}
    >
      <div className="flex h-16 items-center justify-between border-b border-white/10 px-4">
        {!collapsed && (
          <span className="text-lg font-semibold tracking-tight">
            EduTrackr
          </span>
        )}
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className="cursor-pointer hover:scale-110 ml-auto flex h-9 w-9 items-center justify-center rounded-[15px] bg-gray-200 text-blue-600 shadow-sm transition-all ease-linear duration-300 hover:scale-[101.5%] hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          <FiMenu className="text-[20px]" />
        </button>
      </div>
      <nav className="flex flex-1 flex-col gap-1 py-4">
        {navItems.map((item) => {
          const isActive = location.pathname === item.to;

          return (
            <Link
              key={item.to}
              to={item.to}
              className={[
                "group relative flex items-center gap-3 py-3 text-sm font-medium transition-colors duration-200",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/60 focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600",
                collapsed ? "justify-center px-0" : "px-6",
                isActive
                  ? "bg-white/15 text-white"
                  : "text-blue-100 hover:bg-white/10 hover:text-white",
              ].join(" ")}
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/10 text-lg transition-transform duration-200 group-hover:scale-110">
                {item.icon}
              </span>
              {!collapsed && <span className="truncate">{item.label}</span>}
            </Link>
          );
        })}
      </nav>
      <div className="h-4" />
    </aside>
  );
}
