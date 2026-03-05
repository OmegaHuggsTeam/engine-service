"use client";

import { UseCaseDashboard } from "@/modules/sovereign/UseCaseDashboard";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function UseCasesPage() {
  return (
    <ErrorBoundary>
      <UseCaseDashboard />
    </ErrorBoundary>
  );
}
