"use client";

import { useEffect, useCallback, useRef } from "react";

/**
 * Key modifier types for keyboard shortcuts.
 */
export type KeyModifier = "meta" | "ctrl" | "alt" | "shift";

/**
 * Configuration for a keyboard shortcut.
 */
export interface KeyboardShortcut {
  /** Unique identifier for the shortcut */
  id: string;
  /** Human-readable label for the shortcut */
  label: string;
  /** The key to trigger the shortcut (lowercase) */
  key: string;
  /** Required modifiers (meta = Cmd on Mac, Ctrl on Windows) */
  modifiers: KeyModifier[];
  /** Callback to execute when the shortcut is triggered */
  handler: () => void;
  /** Whether the shortcut should work when an input is focused */
  allowInInput?: boolean;
  /** Description shown in command palette */
  description?: string;
  /** Category for grouping shortcuts */
  category?: string;
  /** Whether the shortcut is currently enabled */
  enabled?: boolean;
}

/**
 * Options for the useKeyboardShortcuts hook.
 */
export interface UseKeyboardShortcutsOptions {
  /** Whether to enable all shortcuts */
  enabled?: boolean;
  /** Callback when any shortcut is triggered */
  onShortcutTriggered?: (shortcut: KeyboardShortcut) => void;
}

/**
 * Return type for the useKeyboardShortcuts hook.
 */
export interface UseKeyboardShortcutsReturn {
  /** Register a new shortcut */
  registerShortcut: (shortcut: KeyboardShortcut) => void;
  /** Unregister a shortcut by ID */
  unregisterShortcut: (id: string) => void;
  /** Get all registered shortcuts */
  getShortcuts: () => KeyboardShortcut[];
  /** Get shortcuts by category */
  getShortcutsByCategory: () => Map<string, KeyboardShortcut[]>;
  /** Format shortcut for display (e.g., "Cmd + K") */
  formatShortcut: (shortcut: KeyboardShortcut) => string;
}

/**
 * Check if a modifier key is pressed based on the event.
 */
function isModifierPressed(e: KeyboardEvent, modifier: KeyModifier): boolean {
  switch (modifier) {
    case "meta":
      return e.metaKey || e.ctrlKey; // Support both Cmd (Mac) and Ctrl (Windows/Linux)
    case "ctrl":
      return e.ctrlKey;
    case "alt":
      return e.altKey;
    case "shift":
      return e.shiftKey;
    default:
      return false;
  }
}

/**
 * Check if the event target is an input element.
 */
function isInputElement(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) return false;

  const tagName = target.tagName.toLowerCase();
  const isInput = tagName === "input" || tagName === "textarea" || tagName === "select";
  const isEditable = target.isContentEditable;

  return isInput || isEditable;
}

/**
 * Detect the user's platform for displaying appropriate modifier keys.
 */
function isMacOS(): boolean {
  if (typeof window === "undefined") return false;
  return navigator.platform.toLowerCase().includes("mac");
}

/**
 * Format a modifier key for display.
 */
function formatModifier(modifier: KeyModifier): string {
  const mac = isMacOS();

  switch (modifier) {
    case "meta":
      return mac ? "\u2318" : "Ctrl"; // Command symbol or Ctrl
    case "ctrl":
      return mac ? "\u2303" : "Ctrl"; // Control symbol or Ctrl
    case "alt":
      return mac ? "\u2325" : "Alt"; // Option symbol or Alt
    case "shift":
      return mac ? "\u21E7" : "Shift"; // Shift symbol
    default:
      return modifier;
  }
}

/**
 * Format a key for display.
 */
function formatKey(key: string): string {
  const specialKeys: Record<string, string> = {
    escape: "Esc",
    enter: "\u23CE",
    arrowup: "\u2191",
    arrowdown: "\u2193",
    arrowleft: "\u2190",
    arrowright: "\u2192",
    backspace: "\u232B",
    delete: "\u2326",
    tab: "\u21E5",
    space: "Space",
  };

  return specialKeys[key.toLowerCase()] || key.toUpperCase();
}

/**
 * Hook for managing global keyboard shortcuts.
 *
 * @example
 * ```tsx
 * const { registerShortcut, formatShortcut } = useKeyboardShortcuts();
 *
 * useEffect(() => {
 *   registerShortcut({
 *     id: 'search',
 *     label: 'Search',
 *     key: 'k',
 *     modifiers: ['meta'],
 *     handler: () => setSearchOpen(true),
 *   });
 * }, [registerShortcut]);
 * ```
 */
export function useKeyboardShortcuts(
  options: UseKeyboardShortcutsOptions = {},
): UseKeyboardShortcutsReturn {
  const { enabled = true, onShortcutTriggered } = options;
  const shortcutsRef = useRef<Map<string, KeyboardShortcut>>(new Map());

  const registerShortcut = useCallback((shortcut: KeyboardShortcut) => {
    shortcutsRef.current.set(shortcut.id, {
      enabled: true,
      allowInInput: false,
      category: "General",
      ...shortcut,
    });
  }, []);

  const unregisterShortcut = useCallback((id: string) => {
    shortcutsRef.current.delete(id);
  }, []);

  const getShortcuts = useCallback((): KeyboardShortcut[] => {
    return Array.from(shortcutsRef.current.values());
  }, []);

  const getShortcutsByCategory = useCallback((): Map<string, KeyboardShortcut[]> => {
    const categories = new Map<string, KeyboardShortcut[]>();

    for (const shortcut of shortcutsRef.current.values()) {
      const category = shortcut.category || "General";
      const existing = categories.get(category) || [];
      existing.push(shortcut);
      categories.set(category, existing);
    }

    return categories;
  }, []);

  const formatShortcut = useCallback((shortcut: KeyboardShortcut): string => {
    const modifierParts = shortcut.modifiers.map(formatModifier);
    const keyPart = formatKey(shortcut.key);

    if (isMacOS()) {
      return [...modifierParts, keyPart].join("");
    }

    return [...modifierParts, keyPart].join(" + ");
  }, []);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return;

      const key = e.key.toLowerCase();

      for (const shortcut of shortcutsRef.current.values()) {
        // Skip disabled shortcuts
        if (shortcut.enabled === false) continue;

        // Check if in input and shortcut doesn't allow it
        if (!shortcut.allowInInput && isInputElement(e.target)) continue;

        // Check if the key matches
        if (shortcut.key.toLowerCase() !== key) continue;

        // Check if all required modifiers are pressed
        const allModifiersPressed = shortcut.modifiers.every((mod) =>
          isModifierPressed(e, mod),
        );

        if (!allModifiersPressed) continue;

        // Check that no extra modifiers are pressed
        const hasExtraMeta =
          (e.metaKey || e.ctrlKey) && !shortcut.modifiers.includes("meta");
        const hasExtraAlt = e.altKey && !shortcut.modifiers.includes("alt");
        const hasExtraShift = e.shiftKey && !shortcut.modifiers.includes("shift");

        // Allow meta modifier to satisfy "ctrl" requirement on Mac
        if (hasExtraMeta || hasExtraAlt || hasExtraShift) continue;

        // Prevent default browser behavior
        e.preventDefault();
        e.stopPropagation();

        // Execute the handler
        shortcut.handler();

        // Notify callback if provided
        onShortcutTriggered?.(shortcut);

        // Only trigger one shortcut per keypress
        break;
      }
    },
    [enabled, onShortcutTriggered],
  );

  useEffect(() => {
    if (!enabled) return;

    document.addEventListener("keydown", handleKeyDown, { capture: true });

    return () => {
      document.removeEventListener("keydown", handleKeyDown, { capture: true });
    };
  }, [enabled, handleKeyDown]);

  return {
    registerShortcut,
    unregisterShortcut,
    getShortcuts,
    getShortcutsByCategory,
    formatShortcut,
  };
}

/**
 * Hook to register a single keyboard shortcut.
 * Automatically cleans up when the component unmounts.
 *
 * @example
 * ```tsx
 * useShortcut({
 *   id: 'save',
 *   label: 'Save',
 *   key: 's',
 *   modifiers: ['meta'],
 *   handler: handleSave,
 * });
 * ```
 */
export function useShortcut(
  shortcut: KeyboardShortcut,
  deps: React.DependencyList = [],
): void {
  const handlerRef = useRef(shortcut.handler);

  // Keep handler up to date
  useEffect(() => {
    handlerRef.current = shortcut.handler;
  }, [shortcut.handler]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();

      // Check if the key matches
      if (shortcut.key.toLowerCase() !== key) return;

      // Skip if in input and shortcut doesn't allow it
      if (!shortcut.allowInInput && isInputElement(e.target)) return;

      // Check if all required modifiers are pressed
      const allModifiersPressed = shortcut.modifiers.every((mod) =>
        isModifierPressed(e, mod),
      );

      if (!allModifiersPressed) return;

      // Prevent default browser behavior
      e.preventDefault();
      e.stopPropagation();

      // Execute the handler
      handlerRef.current();
    };

    document.addEventListener("keydown", handleKeyDown, { capture: true });

    return () => {
      document.removeEventListener("keydown", handleKeyDown, { capture: true });
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shortcut.key, shortcut.modifiers.join(","), shortcut.allowInInput, ...deps]);
}

/**
 * Default shortcuts that can be used across the application.
 */
export const DEFAULT_SHORTCUTS = {
  SEARCH: {
    id: "global-search",
    label: "Search",
    key: "k",
    modifiers: ["meta"] as KeyModifier[],
    description: "Open global search",
    category: "Navigation",
  },
  ESCAPE: {
    id: "escape",
    label: "Close",
    key: "Escape",
    modifiers: [] as KeyModifier[],
    description: "Close modal or cancel",
    category: "General",
    allowInInput: true,
  },
  SAVE: {
    id: "save",
    label: "Save",
    key: "s",
    modifiers: ["meta"] as KeyModifier[],
    description: "Save current item",
    category: "Actions",
  },
  NEW: {
    id: "new",
    label: "New",
    key: "n",
    modifiers: ["meta"] as KeyModifier[],
    description: "Create new item",
    category: "Actions",
  },
  GO_HOME: {
    id: "go-home",
    label: "Go to Dashboard",
    key: "h",
    modifiers: ["meta", "shift"] as KeyModifier[],
    description: "Navigate to dashboard",
    category: "Navigation",
  },
} as const;
