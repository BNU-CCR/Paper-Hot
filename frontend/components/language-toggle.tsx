"use client";

import { Tabs, TabsList, TabsTrigger } from "./ui/tabs";

export type PaperLanguage = "original" | "zh";

export function LanguageToggle({ value, onValueChange }: { value: PaperLanguage; onValueChange: (value: PaperLanguage) => void }) {
  return <Tabs value={value} onValueChange={(next) => onValueChange(next as PaperLanguage)}><TabsList aria-label="论文语言" className="language-tabs"><TabsTrigger value="original" aria-label="显示原文" title="显示原文">A</TabsTrigger><TabsTrigger value="zh" aria-label="显示中文翻译" title="显示中文翻译">文</TabsTrigger></TabsList></Tabs>;
}
