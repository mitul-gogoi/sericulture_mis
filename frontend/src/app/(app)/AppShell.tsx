"use client";
import { ReactNode, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  House, Users, UsersThree, Calendar, MapTrifold, Gift,
  GraduationCap, Bell, ChartBar, SignOut, UserCircle, Leaf, ListChecks,
  CaretDown, CaretRight, Stack, MapPin, Buildings, Users as UsersIco, Star,
  Butterfly, FlowArrow, Package, TreeStructure, ChartLineUp, Warning,
  ArrowsDownUp, Gauge, Compass, Tag, Wrench,
} from "@phosphor-icons/react";
import type { Role } from "@/lib/types";

type NavItem = { href: string; label: string; icon: React.ElementType; testId?: string };
type NavGroup = { group: string; items: NavItem[]; collapsible?: boolean };

const MASTERS_CHILDREN: NavItem[] = [
  { href: "/masters/directorate", label: "Directorate Office", icon: Buildings },
  { href: "/masters/districts", label: "Districts", icon: MapPin },
  { href: "/masters/subdivision-cdc", label: "Sub-division/CDC", icon: Buildings },
  { href: "/masters/sericulture-circles", label: "Sericulture Circles", icon: Buildings },
  { href: "/masters/caste", label: "Caste", icon: UsersIco },
  { href: "/masters/religion", label: "Religion", icon: Star },
  { href: "/masters/education-levels", label: "Education Level", icon: GraduationCap },
  { href: "/masters/silk-types", label: "Silk Types", icon: Butterfly },
  { href: "/masters/activities", label: "Activities", icon: FlowArrow },
  { href: "/masters/products", label: "Products", icon: Package },
  { href: "/masters/silk-type-activity-products", label: "Map Activity to Product", icon: TreeStructure },
  { href: "/masters/loss-reasons", label: "Loss Reasons", icon: Warning },
  { href: "/masters/input-source-categories", label: "Input Source Categories", icon: Tag },
  { href: "/masters/input-source-types", label: "Input Source Types", icon: Compass },
  { href: "/masters/asset-types", label: "Asset Types", icon: Wrench },
  { href: "/masters/fig-settings", label: "Minimum FIG Members", icon: UsersThree },
];

const SA_MENU: NavGroup[] = [
  { group: "Dashboard", items: [{ href: "/dashboard", label: "Dashboard", icon: House }] },
  { group: "Master Data", collapsible: true, items: MASTERS_CHILDREN },
  { group: "Farmers & FIGs", collapsible: true, items: [
    { href: "/farmers", label: "Farmer Management", icon: Users },
    { href: "/figs", label: "FIG Management", icon: UsersThree },
  ]},
  { group: "Meetings & Yield", collapsible: true, items: [
    { href: "/meetings", label: "Monthly Submission Status", icon: Calendar },
    { href: "/yields", label: "Yield Reports", icon: ListChecks },
  ]},
  { group: "Land & GIS", items: [{ href: "/lands", label: "GPS Verification & Reports", icon: MapTrifold }] },
  { group: "Asset Management", items: [{ href: "/assets", label: "Assets", icon: Wrench }] },
  { group: "Training", items: [{ href: "/trainings", label: "Training Management", icon: GraduationCap }] },
  { group: "Schemes", collapsible: true, items: [
    { href: "/schemes", label: "Scheme Management", icon: Gift },
    { href: "/schemes/allocations", label: "Allocations", icon: Stack },
    { href: "/schemes/beneficiaries", label: "Beneficiaries", icon: UsersIco },
  ]},
  { group: "User Management", collapsible: true, items: [
    { href: "/users/state-admins", label: "State Admins", icon: UserCircle },
    { href: "/users", label: "District Admins", icon: UserCircle },
    { href: "/users/fig-presidents", label: "FIG Presidents", icon: UsersThree },
  ]},
  { group: "Notifications", items: [{ href: "/notifications", label: "Notifications", icon: Bell }] },
  { group: "Reports & Analytics", collapsible: true, items: [
    { href: "/reports", label: "Reports", icon: ChartBar },
    { href: "/reports/scheme-utilization", label: "Scheme Utilization", icon: Gift },
    { href: "/reports/district-comparison", label: "District Comparison", icon: MapTrifold },
    { href: "/reports/onboarding-trend", label: "Onboarding Trend", icon: ChartLineUp },
    { href: "/analytics/input-output-overview", label: "Input & Output Overview", icon: ChartLineUp },
    { href: "/analytics/lands", label: "Lands Drill-down", icon: MapTrifold },
    { href: "/analytics/products", label: "Production Explorer", icon: ChartBar },
    { href: "/analytics/stock", label: "Stock Explorer", icon: Stack },
    { href: "/analytics/inputs", label: "Input Explorer", icon: ArrowsDownUp },
    { href: "/reports/dfl-efficiency", label: "DFL Efficiency", icon: ChartLineUp },
    { href: "/reports/byproduct-ratio", label: "Byproduct Ratio", icon: TreeStructure },
    { href: "/reports/activity-efficiency", label: "Activity Efficiency", icon: Gauge },
  ]},
];

const DA_MENU: NavGroup[] = [
  { group: "Dashboard", items: [{ href: "/dashboard", label: "Dashboard", icon: House }] },
  { group: "Farmers & FIGs", collapsible: true, items: [
    { href: "/farmers", label: "Farmer Management", icon: Users },
    { href: "/figs", label: "FIG Management", icon: UsersThree },
  ]},
  { group: "Meetings & Yield", collapsible: true, items: [
    { href: "/meetings", label: "Monthly Submission Status", icon: Calendar },
    { href: "/yields", label: "Yield View (read-only)", icon: ListChecks },
  ]},
  { group: "Land", items: [{ href: "/lands", label: "GPS Verification", icon: MapTrifold }] },
  { group: "Asset Management", items: [{ href: "/assets", label: "Assets", icon: Wrench }] },
  { group: "Training", items: [{ href: "/trainings", label: "Training Management", icon: GraduationCap }] },
  { group: "Schemes", collapsible: true, items: [
    { href: "/schemes/beneficiaries", label: "Scheme Beneficiaries", icon: Gift },
    { href: "/schemes/allocations", label: "District Allocations", icon: Stack },
  ]},
  { group: "Notifications", items: [{ href: "/notifications", label: "Notifications", icon: Bell }] },
  { group: "Reports & Analytics", collapsible: true, items: [
    { href: "/reports", label: "Reports", icon: ChartBar },
    { href: "/reports/scheme-utilization", label: "Scheme Utilization", icon: Gift },
    { href: "/reports/onboarding-trend", label: "Onboarding Trend", icon: ChartLineUp },
    { href: "/analytics/input-output-overview", label: "Input & Output Overview", icon: ChartLineUp },
    { href: "/analytics/lands", label: "Lands Drill-down", icon: MapTrifold },
    { href: "/analytics/products", label: "Production Explorer", icon: ChartBar },
    { href: "/analytics/stock", label: "Stock Explorer", icon: Stack },
    { href: "/analytics/inputs", label: "Input Explorer", icon: ArrowsDownUp },
    { href: "/reports/dfl-efficiency", label: "DFL Efficiency", icon: ChartLineUp },
    { href: "/reports/byproduct-ratio", label: "Byproduct Ratio", icon: TreeStructure },
    { href: "/reports/activity-efficiency", label: "Activity Efficiency", icon: Gauge },
  ]},
];

const FP_MENU: NavGroup[] = [
  { group: "Dashboard", items: [{ href: "/dashboard", label: "Dashboard", icon: House }] },
  { group: "Monthly Submission", collapsible: true, items: [
    { href: "/submission", label: "Submit Monthly Meeting Data", icon: Calendar },
    { href: "/meetings", label: "Submission History", icon: ListChecks },
  ]},
  { group: "Farmers & FIGs", collapsible: true, items: [
    { href: "/farmers", label: "Farmer Management", icon: Users },
    { href: "/figs", label: "FIG Management", icon: UsersThree },
  ]},
  { group: "Land & GPS", items: [{ href: "/lands", label: "Land & GPS", icon: MapTrifold }] },
  { group: "Asset Management", items: [{ href: "/assets", label: "Assets (read-only)", icon: Wrench }] },
  { group: "Notifications", items: [{ href: "/notifications", label: "My Notifications", icon: Bell }] },
  { group: "Analytics", collapsible: true, items: [
    { href: "/analytics/input-output-overview", label: "Input & Output Overview", icon: ChartLineUp },
    { href: "/analytics/products", label: "Production Explorer", icon: ChartBar },
    { href: "/analytics/stock", label: "Stock Explorer", icon: Stack },
    { href: "/analytics/inputs", label: "Input Explorer", icon: ArrowsDownUp },
  ]},
];

const MENUS: Record<Role, NavGroup[]> = {
  STATE_ADMIN: SA_MENU, DISTRICT_ADMIN: DA_MENU, FIG_PRESIDENT: FP_MENU,
};

const ROLE_LABEL: Record<Role, string> = {
  STATE_ADMIN: "State Admin",
  DISTRICT_ADMIN: "District Admin",
  FIG_PRESIDENT: "FIG President",
};

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!user && typeof window !== "undefined") window.location.replace("/login");
  }, [user]);

  // Auto-expand a collapsible group when the current route matches one of its items
  useEffect(() => {
    if (!user || !pathname) return;
    const groups = MENUS[user.role] || [];
    setOpenGroups((prev) => {
      const next = { ...prev };
      groups.forEach((g) => {
        if (g.collapsible && g.items.some((it) => pathname === it.href || pathname.startsWith(it.href + "/"))) {
          next[g.group] = true;
        }
      });
      return next;
    });
  }, [pathname, user]);

  if (!user) return null;
  const groups = MENUS[user.role] || [];

  // Pick the most specific matching item across the entire menu (longest matching href prefix)
  const activeHref = (() => {
    if (!pathname) return "";
    let best = "";
    groups.forEach((g) => g.items.forEach((it) => {
      if (pathname === it.href || pathname.startsWith(it.href + "/")) {
        if (it.href.length > best.length) best = it.href;
      }
    }));
    return best;
  })();

  return (
    <div className="min-h-screen flex" style={{ background: "var(--bg)" }}>
      <aside className="w-64 flex-shrink-0 flex flex-col" style={{ background: "var(--sidebar)", borderRight: "1px solid var(--border)" }}>
        <div className="px-5 py-5 flex items-center gap-2 border-b" style={{ borderColor: "var(--border)" }}>
          <Leaf size={26} weight="duotone" color="#2D5134" />
          <div>
            <div className="font-heading font-extrabold text-[15px] leading-tight">Sericulture MIS</div>
            <div className="label-tag mt-0.5">Directorate · Assam</div>
          </div>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-3 overflow-y-auto">
          {groups.map((g) => {
            const groupSlug = g.group.toLowerCase().replace(/[^a-z]+/g, "-");
            if (g.collapsible) {
              const isOpen = !!openGroups[g.group];
              return (
                <div key={g.group}>
                  <button
                    type="button"
                    onClick={() => setOpenGroups((s) => ({ ...s, [g.group]: !s[g.group] }))}
                    data-testid={`nav-group-toggle-${groupSlug}`}
                    aria-expanded={isOpen}
                    className="w-full flex items-center justify-between px-3 mb-1 label-tag hover:opacity-80"
                  >
                    <span>{g.group}</span>
                    {isOpen ? <CaretDown size={12} weight="bold" /> : <CaretRight size={12} weight="bold" />}
                  </button>
                  {isOpen && (
                    <div className="space-y-1" data-testid={`nav-group-items-${groupSlug}`}>
                      {g.items.map((it) => (
                        <Link key={it.href} href={it.href}
                          data-testid={`nav-${it.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                          className={`nav-item ${activeHref === it.href ? "active" : ""}`}>
                          <it.icon size={18} weight="bold" />
                          <span>{it.label}</span>
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              );
            }
            return (
              <div key={g.group}>
                <div className="label-tag px-3 mb-1">{g.group}</div>
                <div className="space-y-1">
                  {g.items.map((it) => (
                    <Link key={it.href} href={it.href}
                      data-testid={`nav-${it.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                      className={`nav-item ${activeHref === it.href ? "active" : ""}`}>
                      <it.icon size={18} weight="bold" />
                      <span>{it.label}</span>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </nav>
        <div className="p-3 border-t" style={{ borderColor: "var(--border)" }}>
          <div className="px-2 py-2 mb-2">
            <div className="text-xs label-tag">Signed in as</div>
            <div className="text-sm font-semibold mt-1 truncate">{user.name || user.mobile_no}</div>
            <div className="text-xs" style={{ color: "var(--text-muted)" }}>{ROLE_LABEL[user.role]}</div>
          </div>
          <button onClick={logout} data-testid="logout-btn" className="btn-secondary w-full flex items-center justify-center gap-2">
            <SignOut size={16} weight="bold" /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-x-hidden">
        <div className="px-8 py-6 max-w-[1500px] mx-auto">{children}</div>
      </main>
    </div>
  );
}
