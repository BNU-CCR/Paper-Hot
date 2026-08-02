"use client";

import Link from "next/link";
import { GitFork, Menu, Monitor, Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "./ui/button";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";

const GITHUB_URL = "https://github.com/BNU-CCR/Paper-Hot";
const links = [["/", "精选论文"], ["/journals/", "期刊书库"], ["/about/", "关于项目"]];

function Navigation({ activePath, onNavigate }) {
  return <nav className="sidebar-nav" aria-label="主导航">{links.map(([href, label]) => <Link key={href} className={activePath === href ? "active" : ""} href={href} onClick={onNavigate}>{label}</Link>)}</nav>;
}

function ThemeSwitch() {
  const [theme, setTheme] = useState("system");
  useEffect(() => setTheme(window.localStorage.getItem("paper-hot-theme") || "system"), []);
  useEffect(() => { const resolved = theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : theme === "system" ? "light" : theme; document.documentElement.dataset.theme = resolved; window.localStorage.setItem("paper-hot-theme", theme); }, [theme]);
  const options = [["dark", Moon, "深色"], ["system", Monitor, "跟随系统"], ["light", Sun, "浅色"]];
  return <div className="theme-switch" aria-label="主题切换">{options.map(([value, Icon, label]) => <Button key={value} size="icon" variant="ghost" className={theme === value ? "active" : ""} onClick={() => setTheme(value)} aria-label={label}><Icon size={15} /></Button>)}</div>;
}

function Brand() { return <Link className="brand" href="/"><span>Paper</span><i /><span>HOT</span></Link>; }
function GithubLink() { return <a className="github-link" href={GITHUB_URL} target="_blank" rel="noreferrer"><GitFork size={16} /> GitHub</a>; }

export function AppSidebar({ activePath }) {
  const [open, setOpen] = useState(false);
  return <>
    <aside className="sidebar"><Brand /><Navigation activePath={activePath} /><div className="sidebar-footer"><GithubLink /><ThemeSwitch /></div></aside>
    <div className="mobile-header"><Brand /><Sheet open={open} onOpenChange={setOpen}><SheetTrigger asChild><Button variant="outline" size="icon" aria-label="打开导航"><Menu size={19} /></Button></SheetTrigger><SheetContent><Brand /><Navigation activePath={activePath} onNavigate={() => setOpen(false)} /><div className="sidebar-footer"><GithubLink /><ThemeSwitch /></div></SheetContent></Sheet></div>
  </>;
}
