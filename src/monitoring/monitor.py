"""
Energy Infrastructure Monitor - Simulated sensor readings for audit missions.

Provides EnergyReading model and EnergyMonitor class that simulates
voltage/current/power readings across multiple energy sources.
"""

import random
from datetime import datetime

from pydantic import BaseModel, Field

# Thresholds
VOLTAGE_NOMINAL = 120.0
VOLTAGE_TOLERANCE = 0.10  # +/- 10%
CRITICAL_POWER_W = 5000


class EnergyReading(BaseModel):
    """Single sensor reading from an energy source."""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    source: str
    voltage_v: float
    current_a: float
    power_w: float
    status: str = "ok"  # ok | warning | critical


class EnergyMonitor:
    """Monitors energy infrastructure sources with simulated sensor data."""

    def __init__(self, sources: list[str]):
        self.sources = sources

    def read(self, source: str) -> EnergyReading:
        """Simulate a single sensor reading with realistic ranges."""
        voltage = random.uniform(
            VOLTAGE_NOMINAL * (1 - VOLTAGE_TOLERANCE),
            VOLTAGE_NOMINAL * (1 + VOLTAGE_TOLERANCE),
        )
        current = random.uniform(5.0, 50.0)
        power = voltage * current

        # Determine status
        v_low = VOLTAGE_NOMINAL * (1 - VOLTAGE_TOLERANCE)
        v_high = VOLTAGE_NOMINAL * (1 + VOLTAGE_TOLERANCE)

        if power >= CRITICAL_POWER_W:
            status = "critical"
        elif voltage < v_low or voltage > v_high:
            status = "warning"
        else:
            status = "ok"

        return EnergyReading(
            source=source,
            voltage_v=round(voltage, 2),
            current_a=round(current, 2),
            power_w=round(power, 2),
            status=status,
        )

    def audit_all(self) -> list[EnergyReading]:
        """Read all registered sources and return list of readings."""
        return [self.read(source) for source in self.sources]

    def generate_report(self, readings: list[EnergyReading]) -> dict:
        """Aggregate readings into a summary report."""
        if not readings:
            return {
                "total_power_w": 0,
                "avg_voltage_v": 0,
                "critical_count": 0,
                "efficiency_pct": 0,
                "source_count": 0,
            }

        total_power = sum(r.power_w for r in readings)
        avg_voltage = sum(r.voltage_v for r in readings) / len(readings)
        critical_count = sum(1 for r in readings if r.status == "critical")

        # Efficiency: ratio of sources within nominal voltage range
        nominal_count = sum(1 for r in readings if r.status == "ok")
        efficiency_pct = round((nominal_count / len(readings)) * 100, 1)

        return {
            "total_power_w": round(total_power, 2),
            "avg_voltage_v": round(avg_voltage, 2),
            "critical_count": critical_count,
            "efficiency_pct": efficiency_pct,
            "source_count": len(readings),
        }

    def check_thresholds(self, readings: list[EnergyReading]) -> list[str]:
        """Return list of warning strings for out-of-range readings."""
        warnings = []
        v_low = VOLTAGE_NOMINAL * (1 - VOLTAGE_TOLERANCE)
        v_high = VOLTAGE_NOMINAL * (1 + VOLTAGE_TOLERANCE)

        for r in readings:
            if r.voltage_v < v_low:
                warnings.append(
                    f"{r.source}: voltage LOW ({r.voltage_v}V < {v_low}V)"
                )
            elif r.voltage_v > v_high:
                warnings.append(
                    f"{r.source}: voltage HIGH ({r.voltage_v}V > {v_high}V)"
                )
            if r.power_w >= CRITICAL_POWER_W:
                warnings.append(
                    f"{r.source}: power CRITICAL ({r.power_w}W >= {CRITICAL_POWER_W}W)"
                )

        return warnings
