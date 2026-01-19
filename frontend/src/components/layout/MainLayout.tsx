"use client";

import { useMemo, type ReactNode, type ComponentType } from "react";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSidebar } from "@/contexts/LayoutContext";
import { useAuthContext } from "@/contexts/AuthContext";
import {
  useModels,
  useCustomViews,
  useActions,
  usePages,
  useLinks,
  useEmbeds,
} from "@/hooks/useApi";
import { Sidebar, type SidebarProps } from "./Sidebar";
import { Header, type HeaderProps } from "./Header";
import { Breadcrumb, generateBreadcrumbsFromPath } from "./Breadcrumb";
import type { NavCategory, NavItem } from "@/types";

export interface MainLayoutProps {
  /** Main content */
  children: ReactNode;
  /** Sidebar configuration */
  sidebar?: Omit<SidebarProps, "className">;
  /** Header configuration */
  header?: Omit<HeaderProps, "breadcrumb" | "className">;
  /** Whether to show breadcrumbs in header */
  showBreadcrumbs?: boolean;
  /** Base path for breadcrumb generation */
  basePath?: string;
  /** Additional CSS classes for the main content area */
  contentClassName?: string;
  /** Additional CSS classes for the layout wrapper */
  className?: string;
}

// Icon components for sidebar navigation
const TableIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M3 3a1 1 0 011-1h12a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V3zm2 0v4h10V3H5zm10 6H5v8h10V9z"
      clipRule="evenodd"
    />
  </svg>
);

const GridIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
  </svg>
);

const ZapIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z"
      clipRule="evenodd"
    />
  </svg>
);

const FileTextIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path
      fillRule="evenodd"
      d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
      clipRule="evenodd"
    />
  </svg>
);

const ExternalLinkIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z" />
    <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z" />
  </svg>
);

const LayoutIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor">
    <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
  </svg>
);

// Icon map for dynamic icon selection
const iconMap: Record<string, ComponentType<{ className?: string }>> = {
  table: TableIcon,
  grid: GridIcon,
  zap: ZapIcon,
  file: FileTextIcon,
  "external-link": ExternalLinkIcon,
  layout: LayoutIcon,
};

export function MainLayout({
  children,
  sidebar,
  header,
  showBreadcrumbs = true,
  basePath = "/",
  contentClassName,
  className,
}: MainLayoutProps) {
  const { isCollapsed, isMobile } = useSidebar();
  const { user, logout } = useAuthContext();
  const pathname = usePathname();
  const router = useRouter();

  // Fetch all view types for sidebar
  const { data: models } = useModels();
  const { data: customViews } = useCustomViews();
  const { data: actions } = useActions();
  const { data: pages } = usePages();
  const { data: links } = useLinks();
  const { data: embeds } = useEmbeds();

  // Helper to get icon component from icon string
  const getIcon = (iconName: string): ComponentType<{ className?: string }> => {
    return iconMap[iconName] ?? TableIcon;
  };

  // Build sidebar categories from all view types
  const sidebarCategories = useMemo<NavCategory[]>(() => {
    const categories: NavCategory[] = [];
    const categoryMap = new Map<string, NavItem[]>();

    // Helper to add items to category
    const addToCategory = (categoryName: string, item: NavItem) => {
      if (!categoryMap.has(categoryName)) {
        categoryMap.set(categoryName, []);
      }
      categoryMap.get(categoryName)!.push(item);
    };

    // Add models
    if (models && models.length > 0) {
      for (const model of models) {
        const category = model.category ?? "Models";
        addToCategory(category, {
          id: `model-${model.model_name}`,
          label: model.name,
          href: `/models/${model.model_name}`,
          icon: TableIcon,
        });
      }
    }

    // Add custom views
    if (customViews && customViews.length > 0) {
      for (const view of customViews) {
        const category = view.category ?? "Custom Views";
        addToCategory(category, {
          id: `custom-${view.identity}`,
          label: view.name,
          href: `/custom/${view.identity}`,
          icon: getIcon(view.icon) ?? GridIcon,
        });
      }
    }

    // Add actions
    if (actions && actions.length > 0) {
      for (const action of actions) {
        const category = action.category ?? "Actions";
        addToCategory(category, {
          id: `action-${action.identity}`,
          label: action.name,
          href: `/actions/${action.identity}`,
          icon: getIcon(action.icon) ?? ZapIcon,
        });
      }
    }

    // Add pages
    if (pages && pages.length > 0) {
      for (const page of pages) {
        const category = page.category ?? "Pages";
        addToCategory(category, {
          id: `page-${page.identity}`,
          label: page.name,
          href: `/pages/${page.identity}`,
          icon: getIcon(page.icon) ?? FileTextIcon,
        });
      }
    }

    // Add links (external navigation)
    if (links && links.length > 0) {
      for (const link of links) {
        const category = link.category ?? "Links";
        addToCategory(category, {
          id: `link-${link.identity}`,
          label: link.name,
          href: link.url,
          icon: getIcon(link.icon) ?? ExternalLinkIcon,
          target: link.target,
        });
      }
    }

    // Add embeds
    if (embeds && embeds.length > 0) {
      for (const embed of embeds) {
        const category = embed.category ?? "Embeds";
        addToCategory(category, {
          id: `embed-${embed.identity}`,
          label: embed.name,
          href: `/embeds/${embed.identity}`,
          icon: getIcon(embed.icon) ?? LayoutIcon,
        });
      }
    }

    // Convert map to array with consistent ordering
    // Priority: Models first, then custom views, actions, pages, links, embeds
    const priorityOrder = ["Models", "Custom Views", "Actions", "Pages", "Links", "Embeds"];
    const sortedKeys = Array.from(categoryMap.keys()).sort((a, b) => {
      const aIndex = priorityOrder.indexOf(a);
      const bIndex = priorityOrder.indexOf(b);
      if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
      if (aIndex !== -1) return -1;
      if (bIndex !== -1) return 1;
      return a.localeCompare(b);
    });

    for (const categoryName of sortedKeys) {
      const items = categoryMap.get(categoryName)!;
      categories.push({
        id: categoryName.toLowerCase().replace(/\s+/g, "-"),
        label: categoryName,
        items,
      });
    }

    // Return empty Models category if nothing else
    if (categories.length === 0) {
      return [
        {
          id: "models",
          label: "Models",
          items: [],
        },
      ];
    }

    return categories;
  }, [models, customViews, actions, pages, links, embeds]);

  // Generate breadcrumbs from current path
  const breadcrumbItems = showBreadcrumbs ? generateBreadcrumbsFromPath(pathname, basePath) : [];

  const breadcrumb =
    showBreadcrumbs && breadcrumbItems.length > 0 ? (
      <Breadcrumb items={breadcrumbItems} homeHref={basePath} />
    ) : undefined;

  // User info for sidebar and header
  // AdminUser doesn't have name field, derive from email
  const userName = user?.email?.split("@")[0] ?? "User";
  const userEmail = user?.email ?? "";

  const handleLogout = async () => {
    await logout();
  };

  const handleProfileClick = () => {
    router.push("/profile");
  };

  const handleSettingsClick = () => {
    router.push("/settings");
  };

  return (
    <div className={cn("min-h-screen bg-[var(--color-background)]", className)}>
      {/* Skip to main content link - visible only on focus for keyboard users */}
      <a
        href="#main-content"
        className={cn(
          "sr-only focus:not-sr-only",
          "fixed top-4 left-4 z-[100]",
          "px-4 py-2 rounded-[var(--radius-md)]",
          "bg-[var(--color-primary)] text-[var(--color-primary-foreground)]",
          "font-medium text-sm",
          "focus:outline-none focus-visible:ring-2",
          "focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2",
          "focus-visible:ring-offset-[var(--color-background)]",
        )}
      >
        Skip to main content
      </a>

      {/* Sidebar */}
      <Sidebar
        {...sidebar}
        categories={sidebar?.categories ?? sidebarCategories}
        userName={userName}
        userEmail={userEmail}
      />

      {/* Main content wrapper */}
      <div
        className={cn(
          "flex min-h-screen flex-col transition-all duration-300",
          // Offset for sidebar width on desktop
          !isMobile && (isCollapsed ? "ml-16" : "ml-64"),
        )}
      >
        {/* Header */}
        <Header
          {...header}
          breadcrumb={breadcrumb}
          userName={userName}
          userEmail={userEmail}
          onLogoutClick={handleLogout}
          onProfileClick={handleProfileClick}
          onSettingsClick={handleSettingsClick}
        />

        {/* Main content area */}
        <main
          id="main-content"
          tabIndex={-1}
          className={cn(
            "flex-1 overflow-y-auto p-4 md:p-6",
            "focus:outline-none",
            contentClassName,
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
