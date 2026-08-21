"use client";
import { ReactNode, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { DistrictSwitcher } from "@/components/DistrictSwitcher";
import {
  House, Users, UsersThree, Calendar, MapTrifold, Gift,
  GraduationCap, Bell, SignOut, UserCircle, Leaf, ListChecks,
  CaretDown, CaretRight, Stack, MapPin, Buildings, Users as UsersIco, Star,
  Butterfly, FlowArrow, Package, TreeStructure, Warning,
  ArrowsDownUp, Compass, Tag, Wrench, List, X, Key,
} from "@phosphor-icons/react";
import type { Role } from "@/lib/types";
import { ChangePasswordModal } from "@/components/ChangePasswordModal";

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
  { href: "/masters/conversion-standards", label: "Conversion Standards", icon: ArrowsDownUp },
  { href: "/masters/loss-reasons", label: "Loss Reasons", icon: Warning },
  { href: "/masters/input-source-categories", label: "Input Source Categories", icon: Tag },
  { href: "/masters/input-source-types", label: "Input Source Types", icon: Compass },
  { href: "/masters/asset-types", label: "Asset Types", icon: Wrench },
  { href: "/masters/fig-settings", label: "Minimum FIG Members", icon: UsersThree },
];

const SA_MENU: NavGroup[] = [
  { group: "Dashboard", items: [{ href: "/dashboard", label: "Dashboard", icon: House }] },
  { group: "Farmers & FIGs", collapsible: true, items: [
    { href: "/farmers", label: "Farmer Management", icon: Users },
    { href: "/figs", label: "FIG Management", icon: UsersThree },
  ]},
  { group: "Meetings & Yield", collapsible: true, items: [
    { href: "/meetings", label: "Monthly Submission Status", icon: Calendar },
    { href: "/farmer-submissions", label: "Individual Farmer Submissions", icon: ListChecks },
    { href: "/yields", label: "Yield Reports", icon: ListChecks },
  ]},
  { group: "Master Data", collapsible: true, items: MASTERS_CHILDREN },
  { group: "Land & GIS", collapsible: true, items: [{ href: "/lands", label: "GPS Verification & Reports", icon: MapTrifold }] },
  { group: "Assets", collapsible: true, items: [{ href: "/assets", label: "Asset Management", icon: Wrench }] },
  { group: "Trainings", collapsible: true, items: [{ href: "/trainings", label: "Training Management", icon: GraduationCap }] },
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
  { group: "Notifications", collapsible: true, items: [{ href: "/notifications", label: "Notifications", icon: Bell }] },
];

const DA_MENU: NavGroup[] = [
  { group: "Dashboard", items: [{ href: "/dashboard", label: "Dashboard", icon: House }] },
  { group: "Farmers & FIGs", collapsible: true, items: [
    { href: "/farmers", label: "Farmer Management", icon: Users },
    { href: "/figs", label: "FIG Management", icon: UsersThree },
  ]},
  { group: "Meetings & Yield", collapsible: true, items: [
    { href: "/meetings", label: "Monthly Submission Status", icon: Calendar },
    { href: "/farmer-submissions", label: "Individual Farmer Submissions", icon: ListChecks },
    { href: "/yields", label: "Yield View (read-only)", icon: ListChecks },
  ]},
  { group: "Land & GIS", collapsible: true, items: [{ href: "/lands", label: "GPS Verification", icon: MapTrifold }] },
  { group: "Assets", collapsible: true, items: [{ href: "/assets", label: "Asset Management", icon: Wrench }] },
  { group: "Trainings", collapsible: true, items: [{ href: "/trainings", label: "Training Management", icon: GraduationCap }] },
  { group: "Schemes", collapsible: true, items: [
    { href: "/schemes/beneficiaries", label: "Scheme Beneficiaries", icon: Gift },
    { href: "/schemes/allocations", label: "District Allocations", icon: Stack },
  ]},
  { group: "Notifications", collapsible: true, items: [{ href: "/notifications", label: "Notifications", icon: Bell }] },
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
  { group: "Land & GIS", collapsible: true, items: [{ href: "/lands", label: "Land & GPS", icon: MapTrifold }] },
  { group: "Assets", collapsible: true, items: [{ href: "/assets", label: "Asset Management", icon: Wrench }] },
  { group: "Notifications", collapsible: true, items: [{ href: "/notifications", label: "My Notifications", icon: Bell }] },
];

// FARMER's "Submission" group items depend on whether the farmer currently belongs to an
// active FIG — a FIG member stages private drafts (consumed by their FIG President's meeting
// submission), while a solo farmer submits directly and can request a resubmission. See
// resolveFarmerMenu(), called from the component with a live fig-membership check.
const FARMER_MENU_SOLO: NavItem[] = [
  { href: "/farmer/submit", label: "Submit This Month", icon: Calendar },
  { href: "/farmer/submissions", label: "My Submissions", icon: ListChecks },
];
const FARMER_MENU_FIG_MEMBER: NavItem[] = [
  { href: "/farmer/draft", label: "My Draft", icon: Calendar },
  { href: "/farmer/meetings", label: "Submission History", icon: ListChecks },
];

const FARMER_MENU: NavGroup[] = [
  { group: "Dashboard", items: [{ href: "/dashboard", label: "Dashboard", icon: House }] },
  { group: "My Profile", collapsible: true, items: [{ href: "/farmer/profile", label: "My Profile", icon: UserCircle }] },
  { group: "Submission", collapsible: true, items: FARMER_MENU_SOLO },
  { group: "Land & GIS", collapsible: true, items: [{ href: "/lands", label: "My Land & GPS", icon: MapTrifold }] },
  { group: "Assets", collapsible: true, items: [{ href: "/assets", label: "My Assets", icon: Wrench }] },
  { group: "Notifications", collapsible: true, items: [{ href: "/notifications", label: "My Notifications", icon: Bell }] },
];

function resolveFarmerMenu(hasFig: boolean): NavGroup[] {
  return FARMER_MENU.map((g) => g.group === "Submission"
    ? { ...g, items: hasFig ? FARMER_MENU_FIG_MEMBER : FARMER_MENU_SOLO }
    : g);
}

const MENUS: Record<Role, NavGroup[]> = {
  STATE_ADMIN: SA_MENU, DISTRICT_ADMIN: DA_MENU, FIG_PRESIDENT: FP_MENU, FARMER: FARMER_MENU,
};

const ROLE_LABEL: Record<Role, string> = {
  STATE_ADMIN: "State Admin",
  DISTRICT_ADMIN: "District Admin",
  FIG_PRESIDENT: "FIG President",
  FARMER: "Farmer",
};

export default function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const pathname = usePathname();
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);

  // Only a FARMER's menu depends on live data (whether they currently belong to an active
  // FIG) — every other role's menu is static by role alone.
  const { data: farmerSummary } = useQuery<{ fig_id: string | null }>({
    queryKey: ["farmer-me-summary-nav"],
    queryFn: async () => (await api.get("/farmers/me/summary")).data,
    enabled: user?.role === "FARMER",
  });
  const hasFig = !!farmerSummary?.fig_id;
  const resolvedMenus = useMemo<Record<Role, NavGroup[]>>(
    () => ({ ...MENUS, FARMER: resolveFarmerMenu(hasFig) }),
    [hasFig]
  );

  useEffect(() => {
    if (!user && typeof window !== "undefined") window.location.replace("/login");
  }, [user]);

  // Close the mobile drawer whenever the route changes (covers back/forward + programmatic nav)
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  // Auto-expand a collapsible group when the current route matches one of its items
  useEffect(() => {
    if (!user || !pathname) return;
    const groups = resolvedMenus[user.role] || [];
    setOpenGroups((prev) => {
      let changed = false;
      const next = { ...prev };
      groups.forEach((g) => {
        if (g.collapsible && g.items.some((it) => pathname === it.href || pathname.startsWith(it.href + "/")) && !next[g.group]) {
          next[g.group] = true;
          changed = true;
        }
      });
      return changed ? next : prev;
    });
  }, [pathname, user, resolvedMenus]);

  if (!user) return null;
  const groups = resolvedMenus[user.role] || [];

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
      {/* Mobile-only top bar — the drawer's own header (logo) is off-canvas by default below md:,
          so this persistent bar is what gives a phone user something to tap to open the menu. */}
      <div className="md:hidden fixed top-0 inset-x-0 z-40 flex items-center justify-between px-4 py-3"
           style={{ background: "var(--primary)", borderBottom: "1px solid var(--primary-hover)" }}>
        <div className="flex items-center gap-2">
          <Leaf size={22} weight="duotone" color="#fff" />
          <span className="font-heading font-extrabold text-[14px] text-white">Sericulture MIS</span>
        </div>
        <button type="button" onClick={() => setSidebarOpen(true)} data-testid="mobile-menu-toggle"
                aria-label="Open menu" className="p-2">
          <List size={24} weight="bold" color="#fff" />
        </button>
      </div>

      {/* Backdrop overlay — mobile only, shown while the drawer is open */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-30 md:hidden" style={{ background: "rgba(26,29,26,0.45)" }}
             onClick={() => setSidebarOpen(false)} data-testid="sidebar-overlay" />
      )}

      <aside
        className={`fixed md:static inset-y-0 left-0 z-40 w-64 flex-shrink-0 flex flex-col
                    transform transition-transform duration-200 ease-in-out
                    ${sidebarOpen ? "translate-x-0" : "-translate-x-full"} md:translate-x-0`}
        style={{ background: "var(--sidebar)", borderRight: "1px solid var(--border)" }}>
        <div className="px-5 py-5 flex items-center justify-between gap-2" style={{ background: "var(--primary)", borderBottom: "1px solid var(--primary-hover)" }}>
          <div className="flex items-center gap-2">
            <Leaf size={26} weight="duotone" color="#fff" />
            <div>
              <div className="font-heading font-extrabold text-[15px] leading-tight text-white">Sericulture MIS</div>
              <div className="label-tag mt-0.5" style={{ color: "rgba(255,255,255,0.75)" }}>Directorate · Assam</div>
            </div>
          </div>
          <button type="button" onClick={() => setSidebarOpen(false)} data-testid="sidebar-close"
                  aria-label="Close menu" className="md:hidden p-1">
            <X size={20} weight="bold" color="#fff" />
          </button>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-2.5 overflow-y-auto">
          {groups.map((g) => {
            const groupSlug = g.group.toLowerCase().replace(/[^a-z]+/g, "-");

            // Standalone single-item groups don't need a section label above them — the
            // item's own label already says more than the generic group name would, so a
            // header here is pure redundant chrome (e.g. "DASHBOARD" above "Dashboard").
            if (!g.collapsible && g.items.length === 1) {
              const it = g.items[0];
              return (
                <Link key={g.group} href={it.href} onClick={() => setSidebarOpen(false)}
                  data-testid={`nav-${it.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                  className={`nav-item ${activeHref === it.href ? "active" : ""}`}>
                  <span className="nav-icon-chip"><it.icon size={16} weight="bold" /></span>
                  <span>{it.label}</span>
                </Link>
              );
            }

            const isOpen = !!openGroups[g.group];
            return (
              <div key={g.group} className="nav-section-card">
                <button
                  type="button"
                  onClick={() => setOpenGroups((s) => ({ ...s, [g.group]: !s[g.group] }))}
                  data-testid={`nav-group-toggle-${groupSlug}`}
                  aria-expanded={isOpen}
                  className="nav-section-header"
                >
                  <span className="nav-section-label">{g.group}</span>
                  {isOpen ? <CaretDown size={12} weight="bold" className="nav-section-caret" />
                          : <CaretRight size={12} weight="bold" className="nav-section-caret" />}
                </button>
                {isOpen && (
                  <div className="space-y-0.5 mt-1" data-testid={`nav-group-items-${groupSlug}`}>
                    {g.items.map((it) => (
                      <Link key={it.href} href={it.href} onClick={() => setSidebarOpen(false)}
                        data-testid={`nav-${it.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                        className={`nav-item ${activeHref === it.href ? "active" : ""}`}>
                        <span className="nav-icon-chip"><it.icon size={16} weight="bold" /></span>
                        <span>{it.label}</span>
                      </Link>
                    ))}
                  </div>
                )}
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
          {/* Only rendered for a District Admin holding more than one district. */}
          <DistrictSwitcher />
          {/* Hidden for the permanent super admin: its password cannot be changed, and
              the backend 403s the attempt. Better to not offer it than to fail on click. */}
          {user?.is_protected !== true && <button onClick={() => setChangePasswordOpen(true)} data-testid="change-password-btn"
                  className="btn-secondary w-full flex items-center justify-center gap-2 mb-2">
            <Key size={16} weight="bold" /> Change Password
          </button>}
          <button onClick={logout} data-testid="logout-btn" className="btn-secondary w-full flex items-center justify-center gap-2">
            <SignOut size={16} weight="bold" /> Sign out
          </button>
        </div>
      </aside>
      <main className="flex-1 min-w-0 overflow-x-hidden pt-[60px] md:pt-0">
        <div className="px-4 py-4 md:px-8 md:py-6 max-w-[1500px] mx-auto">{children}</div>
      </main>
      {changePasswordOpen && <ChangePasswordModal onClose={() => setChangePasswordOpen(false)} />}
    </div>
  );
}
