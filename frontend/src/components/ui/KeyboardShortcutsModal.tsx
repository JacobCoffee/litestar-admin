"use client";

import { useEffect, useMemo } from "react";
import { Modal, ModalHeader, ModalBody } from "@/components/ui/Modal";
import { useShortcut, DEFAULT_SHORTCUTS } from "@/hooks/useKeyboardShortcuts";
import { getTableNavigationHints } from "@/hooks/useTableKeyboardNavigation";
import { cn } from "@/lib/utils";

/**
 * Props for KeyboardShortcutsModal component.
 */
export interface KeyboardShortcutsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Shortcut category with items for display.
 */
interface ShortcutCategory {
  name: string;
  icon: React.ReactNode;
  shortcuts: Array<{
    keys: string;
    description: string;
  }>;
}

/**
 * Detect if running on macOS.
 */
function isMacOS(): boolean {
  if (typeof window === "undefined") return false;
  return navigator.platform.toLowerCase().includes("mac");
}

/**
 * Format modifier key for display.
 */
function formatModifier(isMac: boolean): string {
  return isMac ? "\u2318" : "Ctrl";
}

// Icons
const CommandIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M18 3a3 3 0 0 0-3 3v12a3 3 0 0 0 3 3 3 3 0 0 0 3-3 3 3 0 0 0-3-3H6a3 3 0 0 0-3 3 3 3 0 0 0 3 3 3 3 0 0 0 3-3V6a3 3 0 0 0-3-3 3 3 0 0 0-3 3 3 3 0 0 0 3 3h12a3 3 0 0 0 3-3 3 3 0 0 0-3-3z" />
  </svg>
);

const NavigationIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="3 11 22 2 13 21 11 13 3 11" />
  </svg>
);

const TableIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="3" y1="9" x2="21" y2="9" />
    <line x1="3" y1="15" x2="21" y2="15" />
    <line x1="9" y1="3" x2="9" y2="21" />
    <line x1="15" y1="3" x2="15" y2="21" />
  </svg>
);

const EditIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
);

const GeneralIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);

/**
 * Keyboard badge component for displaying key combinations.
 */
function KeyBadge({ children }: { children: React.ReactNode }) {
  return (
    <kbd
      className={cn(
        "inline-flex items-center justify-center",
        "min-w-[24px] h-6 px-1.5",
        "text-xs font-mono font-medium",
        "bg-[var(--color-card)]",
        "border border-[var(--color-border)]",
        "rounded-[var(--radius-sm)]",
        "shadow-sm",
      )}
    >
      {children}
    </kbd>
  );
}

/**
 * Shortcut row component.
 */
function ShortcutRow({ keys, description }: { keys: string; description: string }) {
  // Split keys by space to render individual badges
  const keyParts = keys.split(" ");

  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-[var(--color-foreground)]">{description}</span>
      <div className="flex items-center gap-1">
        {keyParts.map((key, index) => (
          <KeyBadge key={index}>{key}</KeyBadge>
        ))}
      </div>
    </div>
  );
}

/**
 * Category section component.
 */
function CategorySection({ category }: { category: ShortcutCategory }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 pb-2 border-b border-[var(--color-border)]">
        <span className="text-[var(--color-accent)]">{category.icon}</span>
        <h3 className="text-sm font-semibold text-[var(--color-foreground)]">{category.name}</h3>
      </div>
      <div className="divide-y divide-[var(--color-border)]/50">
        {category.shortcuts.map((shortcut, index) => (
          <ShortcutRow key={index} keys={shortcut.keys} description={shortcut.description} />
        ))}
      </div>
    </div>
  );
}

/**
 * Modal component displaying all available keyboard shortcuts.
 * Organized by category with platform-specific key display.
 *
 * @example
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false);
 *
 * <KeyboardShortcutsModal
 *   isOpen={isOpen}
 *   onClose={() => setIsOpen(false)}
 * />
 * ```
 */
export function KeyboardShortcutsModal({ isOpen, onClose }: KeyboardShortcutsModalProps) {
  const isMac = useMemo(() => isMacOS(), []);
  const mod = formatModifier(isMac);

  // Get table navigation hints
  const tableHints = useMemo(() => getTableNavigationHints(), []);

  // Build categories
  const categories: ShortcutCategory[] = useMemo(
    () => [
      {
        name: "Command Palette",
        icon: <CommandIcon className="h-4 w-4" />,
        shortcuts: [
          { keys: `${mod} K`, description: "Open command palette" },
          { keys: "\u2191 \u2193", description: "Navigate items" },
          { keys: "\u23CE", description: "Select item" },
          { keys: "Esc", description: "Close palette" },
        ],
      },
      {
        name: "Navigation",
        icon: <NavigationIcon className="h-4 w-4" />,
        shortcuts: [
          { keys: `${mod} \u21E7 H`, description: "Go to Dashboard" },
        ],
      },
      {
        name: "Actions",
        icon: <EditIcon className="h-4 w-4" />,
        shortcuts: [
          { keys: `${mod} S`, description: "Save current item" },
          { keys: `${mod} N`, description: "Create new item" },
        ],
      },
      {
        name: "Table Navigation",
        icon: <TableIcon className="h-4 w-4" />,
        shortcuts: tableHints,
      },
      {
        name: "General",
        icon: <GeneralIcon className="h-4 w-4" />,
        shortcuts: [
          { keys: "?", description: "Show keyboard shortcuts" },
          { keys: "Esc", description: "Close modal or cancel" },
        ],
      },
    ],
    [mod, tableHints],
  );

  // Register ? shortcut to show this modal
  useShortcut(
    {
      id: "show-shortcuts",
      label: "Show Keyboard Shortcuts",
      key: "/",
      modifiers: ["shift"],
      handler: () => {
        // This is handled by the parent component
      },
      allowInInput: false,
      description: "Show keyboard shortcuts help",
      category: "General",
    },
    [isOpen],
  );

  return (
    <Modal isOpen={isOpen} onClose={onClose} aria-label="Keyboard Shortcuts">
      <ModalHeader onClose={onClose}>Keyboard Shortcuts</ModalHeader>
      <ModalBody>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {categories.map((category) => (
            <CategorySection key={category.name} category={category} />
          ))}
        </div>

        {/* Footer hint */}
        <div className="mt-6 pt-4 border-t border-[var(--color-border)]">
          <p className="text-xs text-[var(--color-muted)] text-center">
            Press <KeyBadge>?</KeyBadge> anywhere to show this help.
            {isMac ? " Use \u2318 for Cmd." : " Use Ctrl for modifier key."}
          </p>
        </div>
      </ModalBody>
    </Modal>
  );
}

KeyboardShortcutsModal.displayName = "KeyboardShortcutsModal";
