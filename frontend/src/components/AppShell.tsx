import * as React from "react";
import { Link, NavLink } from "react-router-dom";
import {
  KeyRound,
  LayoutDashboard,
  ListFilter,
  LogOut,
  Menu,
  Moon,
  ShieldAlert,
  ShieldCheck,
  Sun,
  UserCheck,
  X,
} from "lucide-react";

import { getApiBaseUrl } from "@/api/client";
import { useTheme } from "@/components/theme-provider";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/overrides", label: "Emergency Overrides", icon: ShieldAlert },
  { to: "/blocklists", label: "Blocklists", icon: ListFilter },
  { to: "/keys", label: "Security Keys", icon: KeyRound },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);

  const toggleTheme = () => {
    setTheme(theme === "dark" ? "light" : "dark");
  };

  return (
    <div className="bg-muted/30 flex min-h-screen">
      {/* Desktop Sidebar */}
      <aside className="bg-card hidden w-64 shrink-0 border-r md:flex md:flex-col">
        <div className="flex h-14 items-center gap-2.5 px-5">
          <div className="bg-primary text-primary-foreground flex size-8 items-center justify-center rounded-lg">
            <ShieldCheck className="size-4" />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold leading-none">
              ClearGuard
            </p>
            <p className="text-muted-foreground mt-1 truncate text-xs">
              Admin Console
            </p>
          </div>
        </div>
        <Separator />

        <nav className="flex-1 space-y-1 p-3">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                <Icon className="size-4 shrink-0" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        <Separator />
        <div className="space-y-2 p-3">
          <Link
            to="/verify"
            className="text-muted-foreground hover:bg-muted hover:text-foreground flex items-center gap-2 rounded-md px-3 py-2 text-xs font-medium transition-colors"
          >
            <UserCheck className="size-4 shrink-0" />
            <span>Partner Verify Portal</span>
          </Link>
          <div className="bg-muted/60 text-muted-foreground rounded-md px-3 py-2 text-[11px]">
            <p className="text-foreground font-medium">Connected API</p>
            <p className="mt-0.5 truncate font-mono">{getApiBaseUrl()}</p>
          </div>
        </div>
      </aside>

      {/* Mobile Sidebar Overlay */}
      {mobileNavOpen ? (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="fixed inset-0 bg-black/50"
            onClick={() => setMobileNavOpen(false)}
          />
          <aside className="bg-card relative z-10 flex w-64 flex-col border-r">
            <div className="flex h-14 items-center justify-between px-4">
              <div className="flex items-center gap-2">
                <ShieldCheck className="size-5" />
                <span className="text-sm font-semibold">ClearGuard</span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setMobileNavOpen(false)}
              >
                <X className="size-4" />
              </Button>
            </div>
            <Separator />
            <nav className="flex-1 space-y-1 p-3">
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.end}
                    onClick={() => setMobileNavOpen(false)}
                    className={({ isActive }) =>
                      cn(
                        "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium",
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground",
                      )
                    }
                  >
                    <Icon className="size-4" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
          </aside>
        </div>
      ) : null}

      {/* Main Content */}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="bg-background/95 sticky top-0 z-20 flex h-14 items-center justify-between border-b px-4 backdrop-blur sm:px-6">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileNavOpen(true)}
            >
              <Menu className="size-5" />
            </Button>
            <Badge variant="outline" className="hidden sm:inline-flex">
              v0.7.0 Admin
            </Badge>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              title="Toggle theme (or press d)"
            >
              <Sun className="size-4 scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
              <Moon className="absolute size-4 scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
              <span className="sr-only">Toggle theme</span>
            </Button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" className="gap-2">
                  <span className="bg-primary text-primary-foreground flex size-5 items-center justify-center rounded-full text-xs font-semibold uppercase">
                    {user?.username?.slice(0, 1) ?? "A"}
                  </span>
                  <span className="max-w-28 truncate text-xs font-medium">
                    {user?.username ?? "Admin"}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuLabel>
                  <p className="text-xs font-semibold">{user?.username}</p>
                  <p className="text-muted-foreground truncate text-[11px] font-normal">
                    {user?.email ?? "Administrator"}
                  </p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={logout} className="text-destructive">
                  <LogOut className="mr-2 size-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
