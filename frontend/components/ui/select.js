"use client";

import * as SelectPrimitive from "@radix-ui/react-select";
import { Check, ChevronDown } from "lucide-react";
import { cn } from "../../lib/utils";

export const Select = SelectPrimitive.Root;
export const SelectValue = SelectPrimitive.Value;
export function SelectTrigger({ className, children, ...props }) { return <SelectPrimitive.Trigger className={cn("ui-select-trigger", className)} {...props}>{children}<SelectPrimitive.Icon><ChevronDown size={15} /></SelectPrimitive.Icon></SelectPrimitive.Trigger>; }
export function SelectContent({ className, children, ...props }) { return <SelectPrimitive.Portal><SelectPrimitive.Content className={cn("ui-select-content", className)} position="popper" {...props}><SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport></SelectPrimitive.Content></SelectPrimitive.Portal>; }
export function SelectItem({ className, children, ...props }) { return <SelectPrimitive.Item className={cn("ui-select-item", className)} {...props}><SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText><SelectPrimitive.ItemIndicator><Check size={14} /></SelectPrimitive.ItemIndicator></SelectPrimitive.Item>; }
