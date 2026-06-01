"""
Custom Rules Scheduler - Extends base scheduler with UI-configurable rules

This allows users to add custom rules through the Streamlit UI without editing code.
"""

from scheduler import BusChargingScheduler


class CustomRulesScheduler(BusChargingScheduler):
    """
    Scheduler that supports UI-configurable custom rules.

    Supported rules:
    1. Priority buses - specific buses get preferential charging
    2. Time-of-day pricing - off-peak hours get bonus priority
    3. Express service - express buses charge before regular buses
    4. Operator quotas - penalize operators exceeding their fair share
    """

    def __init__(self, scenario, route_config, custom_rules=None):
        super().__init__(scenario, route_config)
        self.custom_rules = custom_rules or {}

    def _calculate_priority(self, bus_id, operator, arrival_time,
                           charger_free_time, operator_total_waits):
        """
        Calculate priority with custom rules applied.
        Lower score = higher priority (charges first).
        """
        # Start with base priority from weights
        priority = super()._calculate_priority(
            bus_id, operator, arrival_time, charger_free_time, operator_total_waits
        )

        # Look up the bus
        bus = next((b for b in self.buses if b['id'] == bus_id), None)
        if not bus:
            return priority

        # Apply custom rules
        priority = self._apply_priority_buses(priority, bus)
        priority = self._apply_time_of_day(priority, arrival_time)
        priority = self._apply_express_service(priority, bus)
        priority = self._apply_operator_quota(priority, operator, operator_total_waits)

        return priority

    def _apply_priority_buses(self, priority, bus):
        """Rule: Priority buses get to charge first."""
        if not self.custom_rules.get('priority_buses_enabled', False):
            return priority

        priority_list = self.custom_rules.get('priority_bus_list', [])
        boost = self.custom_rules.get('priority_boost', 5000)

        if bus['id'] in priority_list:
            return priority - boost

        return priority

    def _apply_time_of_day(self, priority, arrival_time):
        """Rule: Off-peak hours get bonus priority."""
        if not self.custom_rules.get('time_of_day_enabled', False):
            return priority

        hour = (arrival_time // 60) % 24
        off_peak_start = self.custom_rules.get('off_peak_start', 0)
        off_peak_end = self.custom_rules.get('off_peak_end', 6)
        boost = self.custom_rules.get('off_peak_boost', 1000)

        if off_peak_start <= hour < off_peak_end:
            return priority - boost

        return priority

    def _apply_express_service(self, priority, bus):
        """Rule: Express buses get priority over regular service."""
        if not self.custom_rules.get('express_service_enabled', False):
            return priority

        boost = self.custom_rules.get('express_boost', 3000)

        if bus.get('service_type') == 'express':
            return priority - boost

        return priority

    def _apply_operator_quota(self, priority, operator, operator_total_waits):
        """Rule: Penalize operators exceeding their quota."""
        if not self.custom_rules.get('operator_quota_enabled', False):
            return priority

        quota = self.custom_rules.get('operator_quota_minutes', 500)
        penalty = self.custom_rules.get('quota_penalty', 2000)

        if operator_total_waits.get(operator, 0) > quota:
            return priority + penalty

        return priority
