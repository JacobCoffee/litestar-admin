"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { CommandPalette, type CommandItem } from "@/components/ui/CommandPalette";
import { KeyboardShortcutsModal } from "@/components/ui/KeyboardShortcutsModal";
import { useShortcut, type KeyModifier } from "@/hooks/useKeyboardShortcuts";
import {
  HomeIcon,
  UsersIcon,
  TableIcon,
  CogIcon,
  ClipboardListIcon,
  PlusIcon,
  SearchIcon,
  ZapIcon,
  FileTextIcon,
  LayoutIcon,
  ExternalLinkIcon,
  KeyboardIcon,
} from "@/lib/icons";
import { useModels, useActions, usePages, useEmbeds, useLinks, useCustomViews } from "@/hooks";

/**
 * Context value for the command palette.
 */
interface CommandPaletteContextValue {
  /** Whether the command palette is open */
  isOpen: boolean;
  /** Open the command palette */
  open: () => void;
  /** Close the command palette */
  close: () => void;
  /** Toggle the command palette */
  toggle: () => void;
  /** Register additional command items */
  registerItems: (items: CommandItem[]) => void;
  /** Unregister command items by their IDs */
  unregisterItems: (ids: string[]) => void;
}

const CommandPaletteContext = createContext<CommandPaletteContextValue | null>(null);

/**
 * Props for the CommandPaletteProvider.
 */
export interface CommandPaletteProviderProps {
  children: ReactNode;
}

/**
 * Detect if running on macOS.
 */
function isMacOS(): boolean {
  if (typeof window === "undefined") return false;
  return navigator.platform.toLowerCase().includes("mac");
}

/**
 * Format a shortcut for display.
 */
function formatShortcutDisplay(key: string, modifiers: KeyModifier[]): string {
  const mac = isMacOS();

  const modifierSymbols = modifiers.map((mod) => {
    switch (mod) {
      case "meta":
        return mac ? "\u2318" : "Ctrl";
      case "alt":
        return mac ? "\u2325" : "Alt";
      case "shift":
        return mac ? "\u21E7" : "Shift";
      default:
        return mod;
    }
  });

  const keySymbol = key.length === 1 ? key.toUpperCase() : key;

  if (mac) {
    return [...modifierSymbols, keySymbol].join("");
  }

  return [...modifierSymbols, keySymbol].join(" + ");
}

/**
 * Provider that enables the command palette and global keyboard shortcuts.
 *
 * This provider:
 * - Opens the command palette with Cmd/Ctrl + K
 * - Provides navigation commands for all admin routes
 * - Integrates with models, actions, pages, and other admin features
 * - Allows registering custom commands from child components
 *
 * @example
 * ```tsx
 * // In providers.tsx
 * <CommandPaletteProvider>
 *   {children}
 * </CommandPaletteProvider>
 *
 * // In a component
 * const { open } = useCommandPalette();
 * <button onClick={open}>Search</button>
 * ```
 */
export function CommandPaletteProvider({ children }: CommandPaletteProviderProps) {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [customItems, setCustomItems] = useState<CommandItem[]>([]);

  // Fetch data for dynamic command items
  const { data: models = [] } = useModels({ enabled: true });
  const { data: actions = [] } = useActions({ enabled: true });
  const { data: pages = [] } = usePages({ enabled: true });
  const { data: embeds = [] } = useEmbeds({ enabled: true });
  const { data: links = [] } = useLinks({ enabled: true });
  const { data: customViews = [] } = useCustomViews({ enabled: true });

  // Open/close handlers
  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  // Register the Cmd+K shortcut
  useShortcut(
    {
      id: "global-search",
      label: "Open Command Palette",
      key: "k",
      modifiers: ["meta"],
      handler: toggle,
      allowInInput: false,
    },
    [toggle],
  );

  // Register the ? shortcut for keyboard shortcuts help
  const openShortcuts = useCallback(() => setIsShortcutsOpen(true), []);
  const closeShortcuts = useCallback(() => setIsShortcutsOpen(false), []);

  useShortcut(
    {
      id: "show-keyboard-shortcuts",
      label: "Show Keyboard Shortcuts",
      key: "/",
      modifiers: ["shift"],
      handler: openShortcuts,
      allowInInput: false,
      description: "Display all available keyboard shortcuts",
      category: "General",
    },
    [openShortcuts],
  );

  // Custom item registration
  const registerItems = useCallback((items: CommandItem[]) => {
    setCustomItems((prev) => {
      const existingIds = new Set(prev.map((p) => p.id));
      const newItems = items.filter((item) => !existingIds.has(item.id));
      return [...prev, ...newItems];
    });
  }, []);

  const unregisterItems = useCallback((ids: string[]) => {
    const idSet = new Set(ids);
    setCustomItems((prev) => prev.filter((item) => !idSet.has(item.id)));
  }, []);

  // Build command items
  const commandItems = useMemo<CommandItem[]>(() => {
    const items: CommandItem[] = [];

    // Navigation commands
    items.push({
      id: "nav-dashboard",
      label: "Go to Dashboard",
      description: "View the admin dashboard",
      category: "Navigation",
      icon: <HomeIcon className="h-4 w-4" />,
      shortcut: formatShortcutDisplay("H", ["meta", "shift"]),
      onSelect: () => router.push("/"),
    });

    items.push({
      id: "nav-models",
      label: "Go to Models",
      description: "View all data models",
      category: "Navigation",
      icon: <TableIcon className="h-4 w-4" />,
      onSelect: () => router.push("/models"),
    });

    items.push({
      id: "nav-users",
      label: "Go to Users",
      description: "Manage admin users",
      category: "Navigation",
      icon: <UsersIcon className="h-4 w-4" />,
      onSelect: () => router.push("/users"),
    });

    items.push({
      id: "nav-audit",
      label: "Go to Audit Log",
      description: "View activity history",
      category: "Navigation",
      icon: <ClipboardListIcon className="h-4 w-4" />,
      onSelect: () => router.push("/audit"),
    });

    items.push({
      id: "nav-settings",
      label: "Go to Settings",
      description: "Admin settings and preferences",
      category: "Navigation",
      icon: <CogIcon className="h-4 w-4" />,
      onSelect: () => router.push("/settings"),
    });

    // Model-specific commands
    for (const model of models) {
      const modelId = model.model_name;
      items.push({
        id: `model-${modelId}`,
        label: `View ${model.name}`,
        description: `Browse ${model.name} records`,
        category: "Models",
        icon: <TableIcon className="h-4 w-4" />,
        keywords: [modelId, model.name, "model", "table"],
        onSelect: () => router.push(`/models/${modelId}`),
      });

      if (model.can_create) {
        items.push({
          id: `model-${modelId}-new`,
          label: `Create ${model.name}`,
          description: `Add a new ${model.name} record`,
          category: "Actions",
          icon: <PlusIcon className="h-4 w-4" />,
          keywords: [modelId, model.name, "create", "new", "add"],
          onSelect: () => router.push(`/models/${modelId}/new`),
        });
      }
    }

    // Action commands
    for (const action of actions) {
      items.push({
        id: `action-${action.identity}`,
        label: action.name,
        description: `Run ${action.name} action`,
        category: "Actions",
        icon: <ZapIcon className="h-4 w-4" />,
        keywords: [action.identity, "action", "run"],
        onSelect: () => router.push(`/actions/${action.identity}`),
      });
    }

    // Page commands
    for (const page of pages) {
      items.push({
        id: `page-${page.identity}`,
        label: page.name,
        description: `View ${page.name} page`,
        category: "Pages",
        icon: <FileTextIcon className="h-4 w-4" />,
        keywords: [page.identity, "page"],
        onSelect: () => router.push(`/pages/${page.identity}`),
      });
    }

    // Embed commands
    for (const embed of embeds) {
      items.push({
        id: `embed-${embed.identity}`,
        label: embed.name,
        description: `View ${embed.name} embed`,
        category: "Embeds",
        icon: <LayoutIcon className="h-4 w-4" />,
        keywords: [embed.identity, "embed"],
        onSelect: () => router.push(`/embeds/${embed.identity}`),
      });
    }

    // Custom view commands
    for (const view of customViews) {
      items.push({
        id: `custom-${view.identity}`,
        label: view.name,
        description: `View ${view.name}`,
        category: "Custom Views",
        icon: <TableIcon className="h-4 w-4" />,
        keywords: [view.identity, "custom", "view"],
        onSelect: () => router.push(`/custom/${view.identity}`),
      });
    }

    // External link commands
    for (const link of links) {
      items.push({
        id: `link-${link.identity}`,
        label: link.name,
        description: `Open ${link.name}`,
        category: "Links",
        icon: <ExternalLinkIcon className="h-4 w-4" />,
        keywords: [link.identity, "link", "external"],
        onSelect: () => {
          if (link.target === "_blank") {
            window.open(link.url, "_blank", "noopener,noreferrer");
          } else {
            window.location.href = link.url;
          }
        },
      });
    }

    // Add quick actions
    items.push({
      id: "action-search",
      label: "Search Records",
      description: "Search across all models (coming soon)",
      category: "Quick Actions",
      icon: <SearchIcon className="h-4 w-4" />,
      shortcut: formatShortcutDisplay("/", []),
      onSelect: () => {
        // Global search is not yet implemented
        // For now, navigate to the first model's list page
        const firstModel = models[0];
        if (firstModel) {
          router.push(`/models/${firstModel.model_name}`);
        }
      },
    });

    // Add keyboard shortcuts command
    items.push({
      id: "show-shortcuts",
      label: "Keyboard Shortcuts",
      description: "View all available keyboard shortcuts",
      category: "Quick Actions",
      icon: <KeyboardIcon className="h-4 w-4" />,
      shortcut: "?",
      onSelect: openShortcuts,
    });

    // Add custom items
    items.push(...customItems);

    return items;
  }, [models, actions, pages, embeds, links, customViews, customItems, router, openShortcuts]);

  const contextValue = useMemo<CommandPaletteContextValue>(
    () => ({
      isOpen,
      open,
      close,
      toggle,
      registerItems,
      unregisterItems,
    }),
    [isOpen, open, close, toggle, registerItems, unregisterItems],
  );

  return (
    <CommandPaletteContext.Provider value={contextValue}>
      {children}
      <CommandPalette
        isOpen={isOpen}
        onClose={close}
        items={commandItems}
        placeholder="Type a command or search..."
        emptyMessage="No commands found. Try a different search."
      />
      <KeyboardShortcutsModal isOpen={isShortcutsOpen} onClose={closeShortcuts} />
    </CommandPaletteContext.Provider>
  );
}

/**
 * Hook to access the command palette context.
 *
 * @example
 * ```tsx
 * const { open, isOpen, registerItems } = useCommandPalette();
 *
 * // Open the palette programmatically
 * open();
 *
 * // Register custom commands
 * useEffect(() => {
 *   const items = [
 *     { id: 'custom-1', label: 'Custom Action', onSelect: doSomething },
 *   ];
 *   registerItems(items);
 *   return () => unregisterItems(items.map(i => i.id));
 * }, [registerItems, unregisterItems]);
 * ```
 */
export function useCommandPalette(): CommandPaletteContextValue {
  const context = useContext(CommandPaletteContext);

  if (!context) {
    throw new Error("useCommandPalette must be used within a CommandPaletteProvider");
  }

  return context;
}
