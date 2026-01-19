'use client';

import { useEffect, useState, useCallback } from 'react';
import { MainLayout } from '@/components/layout/MainLayout';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { useTheme, type Theme } from '@/contexts/ThemeContext';
import { cn } from '@/lib/utils';

const ACCENT_COLOR_KEY = 'admin_accent_color';

/**
 * Adjust the brightness of a hex color.
 * @param hex - The hex color (e.g., '#f6821f')
 * @param percent - Positive to lighten, negative to darken
 */
function adjustBrightness(hex: string, percent: number): string {
  // Remove # if present
  const color = hex.replace('#', '');

  // Parse RGB values
  const r = parseInt(color.substring(0, 2), 16);
  const g = parseInt(color.substring(2, 4), 16);
  const b = parseInt(color.substring(4, 6), 16);

  // Adjust brightness
  const adjust = (value: number) => {
    const adjusted = Math.round(value + (value * percent) / 100);
    return Math.max(0, Math.min(255, adjusted));
  };

  // Convert back to hex
  const toHex = (value: number) => value.toString(16).padStart(2, '0');

  return `#${toHex(adjust(r))}${toHex(adjust(g))}${toHex(adjust(b))}`;
}

interface AccentColor {
  name: string;
  value: string;
  lightValue: string;
}

const DEFAULT_ACCENT_COLOR = '#f6821f';

const accentColors: AccentColor[] = [
  { name: 'Orange', value: '#f6821f', lightValue: '#d4690e' },
  { name: 'Blue', value: '#58a6ff', lightValue: '#0969da' },
  { name: 'Green', value: '#3fb950', lightValue: '#1a7f37' },
  { name: 'Purple', value: '#a371f7', lightValue: '#8250df' },
  { name: 'Pink', value: '#f778ba', lightValue: '#bf3989' },
  { name: 'Red', value: '#f85149', lightValue: '#cf222e' },
  { name: 'Teal', value: '#2dd4bf', lightValue: '#14b8a6' },
  { name: 'Yellow', value: '#e3b341', lightValue: '#9a6700' },
];

const themeOptions: { value: Theme; label: string; description: string }[] = [
  { value: 'dark', label: 'Dark', description: 'Dark theme optimized for low-light environments' },
  { value: 'light', label: 'Light', description: 'Light theme for bright environments' },
  { value: 'system', label: 'System', description: 'Automatically match your system preferences' },
];

// Icons
const PaletteIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="13.5" cy="6.5" r="0.5" fill="currentColor" />
    <circle cx="17.5" cy="10.5" r="0.5" fill="currentColor" />
    <circle cx="8.5" cy="7.5" r="0.5" fill="currentColor" />
    <circle cx="6.5" cy="12.5" r="0.5" fill="currentColor" />
    <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.555C21.965 6.012 17.461 2 12 2z" />
  </svg>
);

const SunIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
  </svg>
);

const MoonIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
  </svg>
);

const MonitorIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="2" y="3" width="20" height="14" rx="2" />
    <line x1="8" y1="21" x2="16" y2="21" />
    <line x1="12" y1="17" x2="12" y2="21" />
  </svg>
);

const CheckIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="3"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

function getThemeIcon(theme: Theme, className?: string) {
  const iconClass = className ?? '';
  switch (theme) {
    case 'light':
      return <SunIcon className={iconClass} />;
    case 'dark':
      return <MoonIcon className={iconClass} />;
    case 'system':
      return <MonitorIcon className={iconClass} />;
  }
}

export default function SettingsPage() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [accentColor, setAccentColorState] = useState<string>(DEFAULT_ACCENT_COLOR);
  const [mounted, setMounted] = useState(false);

  // Load accent color from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(ACCENT_COLOR_KEY);
      if (stored) {
        setAccentColorState(stored);
      }
    } catch {
      // localStorage not available
    }
    setMounted(true);
  }, []);

  // Apply accent color to CSS variables
  useEffect(() => {
    if (!mounted || typeof document === 'undefined') return;

    const selectedColor = accentColors.find((c) => c.value === accentColor);
    if (!selectedColor) return;

    const root = document.documentElement;

    // Get the appropriate color value based on theme
    const colorValue = resolvedTheme === 'light' ? selectedColor.lightValue : selectedColor.value;

    // Calculate a slightly darker hover color
    const hoverColor = adjustBrightness(colorValue, -15);

    // Apply to all primary/accent CSS variables for site-wide effect
    root.style.setProperty('--color-primary', colorValue);
    root.style.setProperty('--color-primary-hover', hoverColor);
    root.style.setProperty('--color-accent', colorValue);
  }, [accentColor, resolvedTheme, mounted]);

  const setAccentColor = useCallback((color: string) => {
    setAccentColorState(color);
    try {
      localStorage.setItem(ACCENT_COLOR_KEY, color);
    } catch {
      // localStorage not available
    }
  }, []);

  const resetToDefaults = useCallback(() => {
    setTheme('dark');
    setAccentColor(DEFAULT_ACCENT_COLOR);
    // Reset CSS variables to defaults (defined in globals.css)
    if (typeof document !== 'undefined') {
      const root = document.documentElement;
      root.style.removeProperty('--color-primary');
      root.style.removeProperty('--color-primary-hover');
      root.style.removeProperty('--color-accent');
    }
  }, [setTheme, setAccentColor]);

  if (!mounted) {
    return null; // Avoid hydration mismatch
  }

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title="Settings"
            subtitle="Configure your admin panel preferences"
            breadcrumbs={[
              { label: 'Dashboard', href: '/' },
              { label: 'Settings' },
            ]}
          />

          {/* Theme Selection */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                {getThemeIcon(theme, 'h-5 w-5 text-[var(--color-accent)]')}
                <div>
                  <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                    Appearance
                  </h2>
                  <p className="text-sm text-[var(--color-muted)]">
                    Choose your preferred theme
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {themeOptions.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setTheme(option.value)}
                    className={cn(
                      'relative flex flex-col items-center gap-3 p-4 rounded-lg border-2 transition-all',
                      'hover:border-[var(--color-accent)] hover:bg-[var(--color-card-hover)]',
                      theme === option.value
                        ? 'border-[var(--color-accent)] bg-[var(--color-card-hover)]'
                        : 'border-[var(--color-border)] bg-[var(--color-card)]'
                    )}
                  >
                    <div
                      className={cn(
                        'flex h-12 w-12 items-center justify-center rounded-full',
                        theme === option.value
                          ? 'bg-[var(--color-accent)] text-white'
                          : 'bg-[var(--color-card-hover)] text-[var(--color-muted)]'
                      )}
                    >
                      {getThemeIcon(option.value, 'h-6 w-6')}
                    </div>
                    <div className="text-center">
                      <p
                        className={cn(
                          'font-medium',
                          theme === option.value
                            ? 'text-[var(--color-accent)]'
                            : 'text-[var(--color-foreground)]'
                        )}
                      >
                        {option.label}
                      </p>
                      <p className="text-xs text-[var(--color-muted)] mt-1">
                        {option.description}
                      </p>
                    </div>
                    {theme === option.value && (
                      <div className="absolute top-2 right-2 h-5 w-5 rounded-full bg-[var(--color-accent)] flex items-center justify-center">
                        <CheckIcon className="h-3 w-3 text-white" />
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </CardBody>
          </Card>

          {/* Accent Color Selection */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-3">
                <PaletteIcon className="h-5 w-5 text-[var(--color-accent)]" />
                <div>
                  <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                    Accent Color
                  </h2>
                  <p className="text-sm text-[var(--color-muted)]">
                    Customize the accent color used throughout the interface
                  </p>
                </div>
              </div>
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-4 sm:grid-cols-8 gap-3">
                {accentColors.map((color) => (
                  <button
                    key={color.name}
                    onClick={() => setAccentColor(color.value)}
                    title={color.name}
                    className={cn(
                      'group relative flex flex-col items-center gap-2',
                      'focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--color-background)] rounded-lg'
                    )}
                  >
                    <div
                      className={cn(
                        'h-10 w-10 rounded-full border-2 transition-all',
                        'group-hover:scale-110 group-hover:shadow-lg',
                        accentColor === color.value
                          ? 'border-[var(--color-foreground)] ring-2 ring-offset-2 ring-offset-[var(--color-background)]'
                          : 'border-transparent'
                      )}
                      style={{
                        backgroundColor: resolvedTheme === 'dark' ? color.value : color.lightValue,
                        boxShadow: accentColor === color.value ? `0 0 0 2px ${color.value}` : undefined,
                      }}
                    >
                      {accentColor === color.value && (
                        <div className="h-full w-full flex items-center justify-center">
                          <CheckIcon className="h-5 w-5 text-white drop-shadow-md" />
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-[var(--color-muted)]">{color.name}</span>
                  </button>
                ))}
              </div>

              {/* Preview */}
              <div className="mt-6 p-4 rounded-lg bg-[var(--color-card-hover)] border border-[var(--color-border)]">
                <p className="text-sm text-[var(--color-muted)] mb-3">Preview</p>
                <div className="flex flex-wrap items-center gap-3">
                  <Button variant="primary" size="sm">
                    Primary Button
                  </Button>
                  <span
                    className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
                    style={{
                      backgroundColor: `color-mix(in srgb, var(--color-accent) 20%, transparent)`,
                      color: 'var(--color-accent)',
                    }}
                  >
                    Accent Badge
                  </span>
                  <a
                    href="#"
                    onClick={(e) => e.preventDefault()}
                    className="text-sm text-[var(--color-accent)] hover:underline"
                  >
                    Accent Link
                  </a>
                </div>
              </div>
            </CardBody>
          </Card>

          {/* Reset Section */}
          <Card>
            <CardBody>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-medium text-[var(--color-foreground)]">
                    Reset to Defaults
                  </h3>
                  <p className="text-sm text-[var(--color-muted)]">
                    Restore all settings to their default values
                  </p>
                </div>
                <Button variant="ghost" onClick={resetToDefaults}>
                  Reset
                </Button>
              </div>
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
