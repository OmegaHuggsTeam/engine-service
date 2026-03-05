"use client";

import JourneyCanvas from "@/modules/sovereign/JourneyCanvas";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function JornadasPage() {
  return (
    <ErrorBoundary>
      <JourneyCanvas />
    </ErrorBoundary>
  );
}
