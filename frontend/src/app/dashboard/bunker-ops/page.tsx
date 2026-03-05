"use client";

import ClusterHealth from "@/modules/sovereign/ClusterHealth";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function BunkerOpsPage() {
  return (
    <ErrorBoundary>
      <ClusterHealth />
    </ErrorBoundary>
  );
}
