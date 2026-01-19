"use client";

import { useMemo, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  getModelIcon,
  getCustomViewIcon,
  getActionIcon,
  getPageIcon,
  getLinkIcon,
  getEmbedIcon,
  UsersIcon,
} from "@/lib/icons";
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
          icon: getModelIcon(model.icon),
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
          icon: getCustomViewIcon(view.icon),
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
          icon: getActionIcon(action.icon),
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
          icon: getPageIcon(page.icon),
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
          icon: getLinkIcon(link.icon),
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
          icon: getEmbedIcon(embed.icon),
        });
      }
    }

    // Add Users to Administration category (always present)
    addToCategory("Administration", {
      id: "users",
      label: "Users",
      href: "/users",
      icon: UsersIcon,
    });

    // Convert map to array with consistent ordering
    // Priority: Models first, then custom views, actions, pages, links, embeds, Administration last
    const priorityOrder = ["Models", "Custom Views", "Actions", "Pages", "Links", "Embeds", "Administration"];
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

    // Return empty Models category if nothing else (except System)
    if (categories.length === 1) {
      const systemCategory = categories[0];
      if (systemCategory) {
        return [
          {
            id: "models",
            label: "Models",
            items: [],
          },
          systemCategory,
        ];
      }
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
