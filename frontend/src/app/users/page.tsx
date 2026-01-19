"use client";

import { Suspense } from "react";
import { usePathname } from "next/navigation";
import { Spinner } from "@/components/ui/Loading";
import { MainLayout } from "@/components/layout/MainLayout";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { UserListPage } from "@/components/pages/UserListPage";
import { UserDetailPage } from "@/components/pages/UserDetailPage";
import { UserCreatePage } from "@/components/pages/UserCreatePage";

/**
 * Users page - handles all user routes client-side.
 *
 * Routes:
 * - /users - User list
 * - /users/new - Create new user
 * - /users/{id} - Edit user
 */
export default function UsersPage() {
  return (
    <ProtectedRoute>
      <MainLayout>
        <Suspense fallback={<LoadingFallback />}>
          <UsersContent />
        </Suspense>
      </MainLayout>
    </ProtectedRoute>
  );
}

interface PathParams {
  action: "list" | "new" | "edit";
  userId: string | null;
}

function parsePathParams(pathname: string): PathParams {
  const normalizedPath = pathname.replace(/^\/admin/, "").replace(/^\/users\/?/, "");

  if (!normalizedPath) return { action: "list", userId: null };

  const segments = normalizedPath.split("/").filter(Boolean);
  if (segments.length === 0) return { action: "list", userId: null };

  const firstSegment = segments[0];
  if (firstSegment === "new") {
    return { action: "new", userId: null };
  }

  // Treat anything else as a user ID
  return { action: "edit", userId: firstSegment ?? null };
}

function UsersContent() {
  const pathname = usePathname();
  const { action, userId } = parsePathParams(pathname);

  if (action === "new") {
    return <UserCreatePage />;
  }

  if (action === "edit" && userId) {
    return <UserDetailPage userId={userId} />;
  }

  return <UserListPage />;
}

function LoadingFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center">
      <Spinner size="lg" />
    </div>
  );
}
