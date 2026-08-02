"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Flame, GitFork, House, Info, Library, Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "./ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
} from "./ui/sidebar";

const GITHUB_URL = "https://github.com/BNU-CCR/Paper-Hot";
const links: Array<[string, string, LucideIcon]> = [["/", "精选论文", House], ["/hotspots/", "当期热点", Flame], ["/journals/", "期刊书库", Library], ["/about/", "关于项目", Info]];

function ThemeSwitch() {
  const [theme, setTheme] = useState("system");
  useEffect(() => setTheme(window.localStorage.getItem("paper-hot-theme") || "system"), []);
  useEffect(() => { const resolved = theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : theme === "system" ? "light" : theme; document.documentElement.dataset.theme = resolved; window.localStorage.setItem("paper-hot-theme", theme); }, [theme]);
  const options: Array<[string, LucideIcon, string]> = [["dark", Moon, "深色"], ["system", Monitor, "跟随系统"], ["light", Sun, "浅色"]];
  return <div className="grid grid-cols-3 gap-[3px] rounded-(--radius) border border-border bg-muted p-[3px] group-data-[collapsible=icon]:grid-cols-1" aria-label="主题切换">{options.map(([value, Icon, label]) => <Button key={value} size="icon" variant="ghost" data-active={theme === value || undefined} className="size-7 min-h-0 w-full data-[active]:bg-background data-[active]:text-foreground data-[active]:shadow-sm" onClick={() => setTheme(value)} aria-label={label} title={label}><Icon size={15} /></Button>)}</div>;
}

export function MobileBar() {
  return (
    <header className="sticky top-0 z-20 flex items-center gap-2 border-b border-border bg-background px-3 py-2 md:hidden">
      <SidebarTrigger />
      <Link className="flex items-center gap-2 text-sm font-bold tracking-tight" href="/">
        <span>Paper HOT</span>
      </Link>
    </header>
  );
}

export function AppSidebar() {
  const pathname = usePathname();
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-1 px-1">
          <SidebarTrigger className="-ml-1" />
          <Link className="flex min-w-0 items-center gap-2 text-sm font-bold tracking-tight group-data-[collapsible=icon]:hidden" href="/">
            <span className="truncate">Paper HOT</span>
          </Link>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {links.map(([href, label, Icon]) => (
                <SidebarMenuItem key={href}>
                  <SidebarMenuButton asChild isActive={href === "/" ? pathname === "/" : pathname.startsWith(href)} tooltip={label}>
                    <Link href={href}><Icon aria-hidden="true" /><span>{label}</span></Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip="GitHub">
              <a href={GITHUB_URL} target="_blank" rel="noreferrer"><GitFork aria-hidden="true" /><span>GitHub</span></a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
        <ThemeSwitch />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
