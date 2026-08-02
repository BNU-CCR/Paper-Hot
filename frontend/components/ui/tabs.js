"use client";

import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../../lib/utils";

export const Tabs = TabsPrimitive.Root;
export function TabsList({ className, ...props }) { return <TabsPrimitive.List className={cn("ui-tabs-list", className)} {...props} />; }
export function TabsTrigger({ className, ...props }) { return <TabsPrimitive.Trigger className={cn("ui-tabs-trigger", className)} {...props} />; }
