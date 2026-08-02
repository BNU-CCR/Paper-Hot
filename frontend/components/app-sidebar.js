"use client";

import Link from "next/link";
import { BookOpen, Flame, GitFork, House, Info, Library, Menu, Monitor, Moon, PanelLeftClose, PanelLeftOpen, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";

const GITHUB_URL = "https://github.com/BNU-CCR/Paper-Hot";
const links = [["/", "精选论文", House], ["/hotspots/", "当期热点", Flame], ["/journals/", "期刊书库", Library], ["/about/", "关于项目", Info]];

function Navigation({ activePath, collapsed = false, onNavigate }) {
  return <nav className="sidebar-nav" aria-label="主导航">{links.map(([href, label, Icon]) => <Link key={href} className={activePath === href ? "active" : ""} href={href} onClick={onNavigate} title={collapsed ? label : undefined}><Icon size={17} strokeWidth={1.8} /><span className="sidebar-label">{label}</span></Link>)}</nav>;
}

function ThemeSwitch() {
  const [theme, setTheme] = useState("system");
  useEffect(() => setTheme(window.localStorage.getItem("paper-hot-theme") || "system"), []);
  useEffect(() => { const resolved = theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : theme === "system" ? "light" : theme; document.documentElement.dataset.theme = resolved; window.localStorage.setItem("paper-hot-theme", theme); }, [theme]);
  const options = [["dark", Moon, "深色"], ["system", Monitor, "跟随系统"], ["light", Sun, "浅色"]];
  return <div className="theme-switch" aria-label="主题切换">{options.map(([value, Icon, label]) => <Button key={value} size="icon" variant="ghost" className={theme === value ? "active" : ""} onClick={() => setTheme(value)} aria-label={label} title={label}><Icon size={15} /></Button>)}</div>;
}

function Brand({ collapsed = false }) { return <Link className="brand" href="/" title={collapsed ? "Paper HOT" : undefined}><BookOpen size={18} strokeWidth={1.8} /><span className="brand-label">Paper HOT</span></Link>; }
function GithubLink({ collapsed = false }) { return <a className="github-link" href={GITHUB_URL} target="_blank" rel="noreferrer" title={collapsed ? "GitHub" : undefined}><GitFork size={16} /><span className="sidebar-label">GitHub</span></a>; }

export function AppSidebar({ activePath }) {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  useEffect(() => setCollapsed(window.localStorage.getItem("paper-hot-sidebar") === "collapsed"), []);
  useEffect(() => { document.documentElement.dataset.sidebarState = collapsed ? "collapsed" : "expanded"; window.localStorage.setItem("paper-hot-sidebar", collapsed ? "collapsed" : "expanded"); }, [collapsed]);
  return <>
    <aside className="sidebar" data-collapsed={collapsed}><div className="sidebar-header"><Brand collapsed={collapsed} /><Button className="sidebar-toggle" variant="ghost" size="icon" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"} title={collapsed ? "展开侧边栏" : "收起侧边栏"}>{collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}</Button></div><Navigation activePath={activePath} collapsed={collapsed} /><div className="sidebar-footer"><GithubLink collapsed={collapsed} /><ThemeSwitch /></div></aside>
    <div className="mobile-header"><Brand /><Sheet open={open} onOpenChange={setOpen}><SheetTrigger asChild><Button variant="outline" size="icon" aria-label="打开导航"><Menu size={19} /></Button></SheetTrigger><SheetContent><Brand /><Navigation activePath={activePath} onNavigate={() => setOpen(false)} /><div className="sidebar-footer"><GithubLink /><ThemeSwitch /></div></SheetContent></Sheet></div>
  </>;
}
