"use client";

import LeadNetwork from "@/modules/sovereign/LeadNetwork";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function NeuralLinkPage() {
  return (
    <ErrorBoundary>
      <LeadNetwork />
    </ErrorBoundary>
  );
}
