from __future__ import annotations

from rest_framework import serializers


class PlanTripRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=240, trim_whitespace=True)
    destination = serializers.CharField(max_length=240, trim_whitespace=True)
    departure = serializers.DateTimeField()
    load_weight_lb = serializers.FloatField(min_value=0, max_value=200_000)
    sampling_interval_miles = serializers.ChoiceField(
        choices=(10, 25, 50), default=25, required=False
    )

    def validate_origin(self, value: str) -> str:
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Enter an origin.")
        return value.strip()

    def validate_destination(self, value: str) -> str:
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Enter a destination.")
        return value.strip()


class HeatmapRequestSerializer(serializers.Serializer):
    route_id = serializers.CharField(max_length=80)
    hour = serializers.IntegerField(min_value=0, max_value=48)
