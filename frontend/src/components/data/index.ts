/**
 * Data components for displaying and manipulating model records.
 */

export {
  RecordForm,
  type RecordFormProps,
  type FormMode,
  type FieldConfig,
  type RelatedRecord,
} from "./RecordForm";

export {
  DataTable,
  useDataTable,
  type Column,
  type DataTableProps,
  type UseDataTableOptions,
  type UseDataTableReturn,
} from "./DataTable";

export {
  SearchFilter,
  type SearchFilterProps,
  type FilterableColumn,
  type FilterState,
  type ColumnFilter,
  type FilterOperator,
  type DateRangeValue,
} from "./SearchFilter";

export {
  ExportDialog,
  ExportButton,
  type ExportDialogProps,
  type ExportButtonProps,
  type ExportColumn,
} from "./ExportDialog";

export {
  BulkActions,
  useBulkSelection,
  type BulkActionsProps,
  type BulkAction,
  type BulkActionResult,
  type UseBulkSelectionOptions,
  type UseBulkSelectionReturn,
} from "./BulkActions";

export {
  ColumnVisibility,
  useColumnVisibility,
  type ColumnVisibilityProps,
  type ColumnConfig,
  type UseColumnVisibilityOptions,
  type UseColumnVisibilityReturn,
} from "./ColumnVisibility";
