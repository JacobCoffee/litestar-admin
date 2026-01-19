/**
 * Auth components barrel export.
 *
 * @example
 * ```tsx
 * import {
 *   ProtectedRoute,
 *   AuthGuard,
 *   UserMenu,
 *   useIsAuthorized,
 * } from '@/components/auth';
 * ```
 */

export { ProtectedRoute } from "./ProtectedRoute";
export type { ProtectedRouteProps } from "./ProtectedRoute";

export { AuthGuard, useIsAuthorized } from "./AuthGuard";
export type { AuthGuardProps } from "./AuthGuard";

export { UserMenu } from "./UserMenu";
export type { UserMenuProps } from "./UserMenu";
