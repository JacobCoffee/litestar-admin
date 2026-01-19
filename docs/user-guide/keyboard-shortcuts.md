# Keyboard Shortcuts

litestar-admin includes a comprehensive keyboard shortcut system and command palette for power users who prefer keyboard-driven navigation. The system provides quick access to navigation, actions, and model operations without reaching for the mouse.

## Command Palette

The command palette is a spotlight-style search interface that provides instant access to any page, model, or action in your admin panel.

### Opening the Command Palette

Press the keyboard shortcut to open the command palette:

| Platform | Shortcut |
|----------|----------|
| macOS | `Cmd + K` |
| Windows/Linux | `Ctrl + K` |

The palette appears as a modal overlay with a search input at the top.

### Navigating the Palette

Once open, use these keys to navigate:

| Key | Action |
|-----|--------|
| `Arrow Up` / `Arrow Down` | Move selection up/down |
| `Tab` / `Shift + Tab` | Move selection down/up |
| `Enter` | Execute selected command |
| `Escape` | Close the palette |

### Search and Filtering

Type in the search input to filter commands. The palette searches across:

- Command labels (e.g., "Go to Users")
- Descriptions (e.g., "Manage admin users")
- Categories (e.g., "Navigation", "Models")
- Keywords (e.g., model names, identities)

Results are grouped by category and update in real-time as you type.

### Command Categories

The command palette includes commands from several categories:

| Category | Contents |
|----------|----------|
| Navigation | Dashboard, Models, Users, Audit Log, Settings |
| Models | View and create commands for each registered model |
| Actions | Registered admin actions |
| Pages | Custom content pages |
| Embeds | Embedded views and dashboards |
| Custom Views | Non-model data views |
| Links | External link shortcuts |
| Quick Actions | Common operations like search |

## Default Keyboard Shortcuts

litestar-admin provides several built-in keyboard shortcuts:

| Shortcut | Action | Category |
|----------|--------|----------|
| `Cmd/Ctrl + K` | Open command palette | Navigation |
| `Cmd/Ctrl + Shift + H` | Go to dashboard | Navigation |
| `Cmd/Ctrl + S` | Save current item | Actions |
| `Cmd/Ctrl + N` | Create new item | Actions |
| `?` | Show keyboard shortcuts help | General |
| `Escape` | Close modal or cancel | General |

## Keyboard Shortcuts Help Modal

Press `?` (Shift + /) anywhere in the admin panel to open the keyboard shortcuts help modal. This displays all available shortcuts organized by category:

- **Command Palette**: Shortcuts for opening and navigating the command palette
- **Navigation**: Page navigation shortcuts
- **Actions**: Common action shortcuts (save, create new)
- **Table Navigation**: Keyboard navigation for data tables
- **General**: Modal and general shortcuts

You can also access this from the command palette by typing "Keyboard Shortcuts".

## Configuring Keyboard Features

Keyboard navigation features can be configured in **Settings > Table Settings**:

### Keyboard Navigation Toggle

Enable or disable keyboard navigation for data tables. When enabled:
- Arrow keys navigate between rows
- Home/End jump to first/last row
- Page Up/Down change pages
- Enter/Space activate rows

### Show Keyboard Hints

Display a footer bar at the bottom of tables showing available keyboard shortcuts. This helps users discover keyboard navigation features.

Settings are persisted in localStorage and apply to all tables in the admin panel.

## Table Keyboard Navigation

Data tables in litestar-admin support comprehensive keyboard navigation for efficient data browsing without using a mouse.

### Table Navigation Keys

| Key | Action |
|-----|--------|
| `Arrow Up` / `Arrow Down` | Navigate between rows |
| `Home` | Go to first row |
| `End` | Go to last row |
| `Page Up` | Go to previous page |
| `Page Down` | Go to next page |
| `Cmd/Ctrl + Home` | Go to first row on first page |
| `Cmd/Ctrl + End` | Go to last row on last page |
| `Cmd/Ctrl + A` | Select all rows (when selection enabled) |
| `Enter` / `Space` | Activate row (click) or toggle selection |
| `Escape` | Clear row focus |

### Visual Focus Indicator

When navigating with the keyboard, the focused row is highlighted with:
- An accent-colored ring around the row
- A subtle background tint
- Screen reader announcements for accessibility

### Enabling Table Navigation

Table keyboard navigation is enabled by default. To customize:

```tsx
<DataTable
  columns={columns}
  data={data}
  enableKeyboardNavigation={true}  // Enabled by default
  showKeyboardHints={true}         // Show keyboard hints footer
/>
```

### Keyboard Hints Footer

Set `showKeyboardHints={true}` to display a footer bar with keyboard navigation hints:

```tsx
<DataTable
  columns={columns}
  data={data}
  showKeyboardHints={true}
/>
```

This displays a row of keyboard hints showing available shortcuts for table navigation.

### Using the Table Navigation Hook

For custom table implementations, use the `useTableKeyboardNavigation` hook:

```tsx
import { useTableKeyboardNavigation } from "@/hooks";

function CustomTable({ data }) {
  const {
    focusedRowIndex,
    handleTableKeyDown,
    getRowProps,
    tableRef,
    isTableFocused,
  } = useTableKeyboardNavigation({
    rowCount: data.length,
    selectable: true,
    onSelectAll: () => handleSelectAll(),
    onActivateRow: (index) => handleRowClick(data[index]),
    onToggleRow: (index) => toggleSelection(data[index]),
    page: currentPage,
    totalPages: totalPages,
    onPageChange: setPage,
  });

  return (
    <div
      ref={tableRef}
      onKeyDown={handleTableKeyDown}
      tabIndex={0}
      role="grid"
    >
      <table>
        <tbody>
          {data.map((row, index) => {
            const rowProps = getRowProps(index);
            return (
              <tr
                key={row.id}
                tabIndex={rowProps.tabIndex}
                data-focused={rowProps["data-focused"]}
                onKeyDown={rowProps.onKeyDown}
                onFocus={rowProps.onFocus}
              >
                {/* cells */}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
```

### TableKeyboardNavigationOptions

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `rowCount` | `number` | Yes | Total number of rows |
| `selectable` | `boolean` | No | Enable row selection |
| `onSelectAll` | `() => void` | No | Select all callback |
| `onActivateRow` | `(index: number) => void` | No | Row activation callback |
| `onToggleRow` | `(index: number) => void` | No | Row toggle callback |
| `page` | `number` | No | Current page (1-indexed) |
| `totalPages` | `number` | No | Total pages |
| `onPageChange` | `(page: number) => void` | No | Page change callback |
| `enabled` | `boolean` | No | Enable navigation |

### Accessibility Features

Table keyboard navigation follows WAI-ARIA best practices:

- Proper `role="grid"` and `role="row"` attributes
- `aria-rowindex` for screen reader row position
- `aria-selected` for selection state
- Focus management with `tabIndex`
- Screen reader announcements via live regions

### Platform-Specific Display

Shortcuts are displayed with platform-appropriate symbols:

**macOS:**
- Command: `Cmd` (displayed as a special symbol)
- Option: `Opt` (displayed as a special symbol)
- Shift: displayed as an arrow symbol

**Windows/Linux:**
- `Ctrl + K`
- `Alt + ...`
- `Shift + ...`

## Using the Command Palette Programmatically

### Opening the Palette from Code

Access the command palette from any component using the `useCommandPalette` hook:

```tsx
import { useCommandPalette } from "@/contexts/CommandPaletteContext";

function MyComponent() {
  const { open, isOpen, toggle } = useCommandPalette();

  return (
    <button onClick={open}>
      Open Command Palette
    </button>
  );
}
```

### Registering Custom Commands

Add custom commands to the palette by registering items:

```tsx
import { useEffect } from "react";
import { useCommandPalette } from "@/contexts/CommandPaletteContext";

function MyFeature() {
  const { registerItems, unregisterItems } = useCommandPalette();

  useEffect(() => {
    const customItems = [
      {
        id: "my-custom-action",
        label: "Run My Action",
        description: "Execute a custom operation",
        category: "Custom",
        icon: <MyIcon className="h-4 w-4" />,
        keywords: ["custom", "action", "run"],
        onSelect: () => {
          // Your action logic
          console.log("Custom action executed!");
        },
      },
      {
        id: "another-action",
        label: "Another Action",
        description: "Do something else",
        category: "Custom",
        shortcut: "Cmd + Shift + A",  // Display hint only
        onSelect: () => doSomethingElse(),
      },
    ];

    registerItems(customItems);

    // Cleanup on unmount
    return () => {
      unregisterItems(customItems.map(item => item.id));
    };
  }, [registerItems, unregisterItems]);

  return <div>My Feature</div>;
}
```

### CommandItem Properties

Each command item supports these properties:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `string` | Yes | Unique identifier |
| `label` | `string` | Yes | Display label |
| `onSelect` | `() => void` | Yes | Handler when selected |
| `description` | `string` | No | Secondary description text |
| `category` | `string` | No | Grouping category |
| `icon` | `ReactNode` | No | Icon component |
| `shortcut` | `string` | No | Shortcut display hint |
| `keywords` | `string[]` | No | Additional search terms |
| `disabled` | `boolean` | No | Disable the item |

## Registering Custom Shortcuts

### Using the useShortcut Hook

Register a single keyboard shortcut with automatic cleanup:

```tsx
import { useShortcut } from "@/hooks/useKeyboardShortcuts";

function SaveableForm() {
  const handleSave = () => {
    console.log("Saving...");
  };

  useShortcut({
    id: "save-form",
    label: "Save",
    key: "s",
    modifiers: ["meta"],  // Cmd on Mac, Ctrl on Windows
    handler: handleSave,
    description: "Save the current form",
    category: "Actions",
  });

  return <form>...</form>;
}
```

### Using the useKeyboardShortcuts Hook

For managing multiple shortcuts:

```tsx
import { useEffect } from "react";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";

function MyComponent() {
  const {
    registerShortcut,
    unregisterShortcut,
    getShortcuts,
    formatShortcut,
  } = useKeyboardShortcuts();

  useEffect(() => {
    registerShortcut({
      id: "my-shortcut",
      label: "My Action",
      key: "m",
      modifiers: ["meta", "shift"],
      handler: () => console.log("Triggered!"),
      category: "Custom",
    });

    return () => unregisterShortcut("my-shortcut");
  }, [registerShortcut, unregisterShortcut]);

  // Display all shortcuts
  const shortcuts = getShortcuts();
  return (
    <ul>
      {shortcuts.map(shortcut => (
        <li key={shortcut.id}>
          {shortcut.label}: {formatShortcut(shortcut)}
        </li>
      ))}
    </ul>
  );
}
```

### KeyboardShortcut Configuration

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `id` | `string` | Yes | Unique identifier |
| `label` | `string` | Yes | Human-readable name |
| `key` | `string` | Yes | Key to trigger (lowercase) |
| `modifiers` | `KeyModifier[]` | Yes | Required modifier keys |
| `handler` | `() => void` | Yes | Callback function |
| `description` | `string` | No | Description for command palette |
| `category` | `string` | No | Grouping category |
| `allowInInput` | `boolean` | No | Work when input is focused |
| `enabled` | `boolean` | No | Whether shortcut is active |

### Modifier Keys

Available modifiers:

| Modifier | macOS | Windows/Linux |
|----------|-------|---------------|
| `meta` | Command | Ctrl |
| `ctrl` | Control | Ctrl |
| `alt` | Option | Alt |
| `shift` | Shift | Shift |

The `meta` modifier automatically maps to the platform-appropriate key (Command on macOS, Ctrl on Windows/Linux).

## Input Field Behavior

By default, keyboard shortcuts are disabled when the user is focused on an input element (text inputs, textareas, selects, or contenteditable elements). This prevents shortcuts from interfering with typing.

To allow a shortcut to work even when an input is focused:

```tsx
useShortcut({
  id: "escape-input",
  label: "Cancel",
  key: "Escape",
  modifiers: [],
  handler: () => cancelEdit(),
  allowInInput: true,  // Works even in inputs
});
```

## Displaying Shortcuts in the UI

### Formatting Shortcuts for Display

Use the `formatShortcut` function to display shortcuts with platform-appropriate symbols:

```tsx
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";

function ShortcutHint({ shortcut }) {
  const { formatShortcut } = useKeyboardShortcuts();

  return (
    <kbd className="px-2 py-1 bg-gray-100 rounded text-sm">
      {formatShortcut(shortcut)}
    </kbd>
  );
}
```

**Example output:**
- macOS: `Cmd K` (with symbols)
- Windows: `Ctrl + K`

### Showing Shortcuts by Category

Group and display shortcuts by category:

```tsx
function ShortcutReference() {
  const { getShortcutsByCategory, formatShortcut } = useKeyboardShortcuts();

  const categories = getShortcutsByCategory();

  return (
    <div>
      {Array.from(categories.entries()).map(([category, shortcuts]) => (
        <section key={category}>
          <h3>{category}</h3>
          <ul>
            {shortcuts.map(shortcut => (
              <li key={shortcut.id}>
                <span>{shortcut.label}</span>
                <kbd>{formatShortcut(shortcut)}</kbd>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
```

## Command Palette Integration

The command palette automatically includes registered keyboard shortcuts. When you register a shortcut with a matching command item, the palette displays the shortcut hint next to the command.

To show a shortcut in the command palette:

1. Register the keyboard shortcut with `useShortcut` or `useKeyboardShortcuts`
2. Register a command item with a matching `shortcut` display string

```tsx
// The shortcut
useShortcut({
  id: "go-home",
  label: "Go to Dashboard",
  key: "h",
  modifiers: ["meta", "shift"],
  handler: () => router.push("/"),
});

// The command (with shortcut hint)
registerItems([{
  id: "nav-dashboard",
  label: "Go to Dashboard",
  shortcut: formatShortcutDisplay("H", ["meta", "shift"]),  // Shows "Cmd Shift H" on Mac
  onSelect: () => router.push("/"),
}]);
```

## Best Practices

1. **Use Standard Shortcuts**: Stick to common conventions (Cmd+S for save, Cmd+N for new, etc.)

2. **Avoid Conflicts**: Check for browser and OS shortcut conflicts before registering

3. **Provide Feedback**: Show visual feedback when shortcuts are triggered

4. **Document Shortcuts**: Make shortcuts discoverable through the command palette or a help page

5. **Keep It Simple**: Avoid complex multi-key combinations that are hard to remember

6. **Platform Awareness**: Use `meta` for cross-platform compatibility instead of hardcoding `ctrl` or `cmd`

## Accessibility

The keyboard shortcut system is built with accessibility in mind:

- Command palette is fully keyboard navigable
- ARIA attributes for screen reader support
- Focus management when opening/closing the palette
- Clear visual indicators for selected items
- Escape key always closes the palette

## Troubleshooting

### Shortcut Not Working

1. Check if an input element has focus (shortcuts are disabled in inputs by default)
2. Verify the shortcut ID is unique
3. Ensure the shortcut is enabled (`enabled: true`)
4. Check for conflicts with browser shortcuts

### Command Not Appearing in Palette

1. Verify the command has a unique `id`
2. Check that `registerItems` was called
3. Ensure the component is mounted within `CommandPaletteProvider`

### Platform Detection Issues

The system uses `navigator.platform` for platform detection. In rare cases (older browsers, unusual environments), this may not work correctly. The fallback is Windows/Linux behavior.

## See Also

- [Custom Views](custom-views.md) - Building custom admin views
- [User Management](user-management.md) - Managing admin users
