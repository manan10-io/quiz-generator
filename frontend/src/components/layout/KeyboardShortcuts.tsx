"use client";

import { useUiStore } from "@/store/uiStore";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { KEYBOARD_SHORTCUTS } from "@/lib/constants";

export function KeyboardShortcutsDialog() {
  const { isKeyboardShortcutsOpen, toggleKeyboardShortcuts } = useUiStore();

  return (
    <Dialog open={isKeyboardShortcutsOpen} onOpenChange={toggleKeyboardShortcuts}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Keyboard shortcuts</DialogTitle>
        </DialogHeader>
        <div className="space-y-1 py-2">
          {KEYBOARD_SHORTCUTS.map(({ keys, description }) => (
            <div
              key={description}
              className="flex items-center justify-between py-1.5 px-1"
            >
              <span className="text-sm text-muted-foreground">{description}</span>
              <div className="flex items-center gap-1">
                {keys.map((k) => (
                  <kbd
                    key={k}
                    className="inline-flex items-center rounded border border-border bg-muted px-1.5 py-0.5 text-[11px] font-mono text-foreground"
                  >
                    {k}
                  </kbd>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
