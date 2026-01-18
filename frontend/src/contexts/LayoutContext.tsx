'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

interface SidebarState {
  /** Whether the sidebar is open (mobile drawer) */
  isOpen: boolean;
  /** Whether the sidebar is collapsed to icon-only mode */
  isCollapsed: boolean;
  /** Whether we're in mobile viewport */
  isMobile: boolean;
}

interface SidebarContextValue extends SidebarState {
  /** Open the sidebar (mobile) */
  open: () => void;
  /** Close the sidebar (mobile) */
  close: () => void;
  /** Toggle sidebar open/close state */
  toggle: () => void;
  /** Expand sidebar to full width */
  expand: () => void;
  /** Collapse sidebar to icon-only mode */
  collapse: () => void;
  /** Toggle collapsed state */
  toggleCollapse: () => void;
}

const SidebarContext = createContext<SidebarContextValue | null>(null);

const MOBILE_BREAKPOINT = 768;
const STORAGE_KEY = 'litestar-admin-sidebar-collapsed';

interface LayoutProviderProps {
  readonly children: ReactNode;
}

export function LayoutProvider({ children }: LayoutProviderProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Initialize collapsed state from localStorage and detect mobile
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored !== null) {
      setIsCollapsed(stored === 'true');
    }

    const checkMobile = () => {
      const mobile = window.innerWidth < MOBILE_BREAKPOINT;
      setIsMobile(mobile);
      // Auto-close sidebar on mobile when viewport changes
      if (mobile) {
        setIsOpen(false);
      }
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Persist collapsed state
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(isCollapsed));
  }, [isCollapsed]);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);
  const expand = useCallback(() => setIsCollapsed(false), []);
  const collapse = useCallback(() => setIsCollapsed(true), []);
  const toggleCollapse = useCallback(() => setIsCollapsed((prev) => !prev), []);

  const value = useMemo<SidebarContextValue>(
    () => ({
      isOpen,
      isCollapsed,
      isMobile,
      open,
      close,
      toggle,
      expand,
      collapse,
      toggleCollapse,
    }),
    [isOpen, isCollapsed, isMobile, open, close, toggle, expand, collapse, toggleCollapse]
  );

  return <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>;
}

export function useSidebar(): SidebarContextValue {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a LayoutProvider');
  }
  return context;
}
