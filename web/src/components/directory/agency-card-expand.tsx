"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/cn";

/**
 * Expand-in-place (accordion) wrapper (DESIGN.md D11). The header is always visible;
 * the server-rendered rank grid / pending notice is passed as children and revealed in
 * place. No page jump, no back button.
 */
export function AgencyCardExpand({
  header,
  children,
}: {
  header: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = React.useState(false);
  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex w-full items-center justify-between gap-3 p-5 text-left">
        {header}
        <ChevronDown
          aria-hidden
          className={cn(
            "h-5 w-5 shrink-0 text-ink-3 transition-transform",
            open && "rotate-180",
          )}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="px-5 pb-5">{children}</CollapsibleContent>
    </Collapsible>
  );
}
