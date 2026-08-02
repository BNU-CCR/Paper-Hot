"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export function SheetContent({ className, children, ...props }) { return <DialogPrimitive.Portal><DialogPrimitive.Overlay className="ui-sheet-overlay" /><DialogPrimitive.Content className={cn("ui-sheet-content", className)} {...props}>{children}<DialogPrimitive.Close className="ui-sheet-close" aria-label="关闭菜单"><X size={19} /></DialogPrimitive.Close></DialogPrimitive.Content></DialogPrimitive.Portal>; }
