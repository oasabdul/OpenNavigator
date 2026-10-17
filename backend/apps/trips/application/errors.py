from __future__ import annotations


class TripPlanningError(Exception):
    """Base class for expected application errors."""


class InvalidTripRequest(TripPlanningError):
    pass


class LocationNotFound(TripPlanningError):
    pass


class NoRoutesFound(TripPlanningError):
    pass


class UpstreamUnavailable(TripPlanningError):
    pass


class PlanNotFound(TripPlanningError):
    pass
