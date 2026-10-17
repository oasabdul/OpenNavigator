import { useEffect, useRef } from "react";
import L from "leaflet";

import type { Checkpoint, HeatmapFrame, RouteOption, TripPlan } from "../../types";
import { formatPrecip, formatShortDateTime, formatWind } from "../../lib/format";
import { riskColor, riskLabel } from "../../lib/risk";
import { planBounds, routeBounds, routeRiskPolylines } from "../../lib/route";
import { WeatherHeatmapLayer } from "./WeatherHeatmapLayer";

interface TripMapProps {
  plan: TripPlan | null;
  selectedRouteId: string | null;
  onSelectRoute: (routeId: string) => void;
  heatmapFrame: HeatmapFrame | null;
  heatmapVisible: boolean;
}

const TILE_URL = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function endpointIcon(kind: "origin" | "destination"): L.DivIcon {
  return L.divIcon({
    className: `endpoint-marker endpoint-marker--${kind}`,
    html: '<span class="endpoint-marker__halo"></span><span class="endpoint-marker__dot"></span>',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  });
}

function checkpointPopup(checkpoint: Checkpoint, route: RouteOption): string {
  const color = riskColor(checkpoint.risk.level);
  const reason = checkpoint.risk.reasons[0] ?? "";
  return `
    <div class="map-popup">
      <div class="map-popup__eyebrow">${escapeHtml(route.label)} · mile ${Math.round(checkpoint.mile)}</div>
      <div class="map-popup__risk" style="--risk-color:${color}">
        <span class="map-popup__risk-dot"></span>${escapeHtml(riskLabel(checkpoint.risk.level))}
      </div>
      <div class="map-popup__time">${escapeHtml(formatShortDateTime(checkpoint.eta))}</div>
      <div class="map-popup__grid">
        <span><small>Wind</small><b>${formatWind(checkpoint.weather.windMph)}</b></span>
        <span><small>Rain</small><b>${formatPrecip(checkpoint.weather.rainInPerHour)}</b></span>
        <span><small>Snow</small><b>${formatPrecip(checkpoint.weather.snowInPerHour)}</b></span>
      </div>
      <p class="map-popup__reason">${escapeHtml(reason)}</p>
    </div>
  `;
}

export function TripMap({
  plan,
  selectedRouteId,
  onSelectRoute,
  heatmapFrame,
  heatmapVisible,
}: TripMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const rendererRef = useRef<L.Renderer | null>(null);
  const routeLayerRef = useRef<L.LayerGroup | null>(null);
  const checkpointLayerRef = useRef<L.LayerGroup | null>(null);
  const endpointLayerRef = useRef<L.LayerGroup | null>(null);
  const heatmapLayerRef = useRef<WeatherHeatmapLayer | null>(null);
  const lastPlanIdRef = useRef<string | null>(null);
  const lastActiveRouteRef = useRef<string | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const map = L.map(container, {
      zoomControl: false,
      attributionControl: true,
      preferCanvas: true,
      minZoom: 3,
      worldCopyJump: true,
    });
    mapRef.current = map;

    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTRIBUTION,
      subdomains: "abc",
      maxZoom: 19,
    }).addTo(map);

    L.control.zoom({ position: "topright" }).addTo(map);
    L.control.scale({ position: "bottomleft", imperial: true, metric: false }).addTo(map);

    const weatherPane = map.createPane("weatherHeatmap");
    weatherPane.style.zIndex = "350";
    weatherPane.style.pointerEvents = "none";

    rendererRef.current = L.canvas({ padding: 0.45 });
    routeLayerRef.current = L.layerGroup().addTo(map);
    checkpointLayerRef.current = L.layerGroup().addTo(map);
    endpointLayerRef.current = L.layerGroup().addTo(map);

    const heatmapLayer = new WeatherHeatmapLayer();
    heatmapLayer.addTo(map);
    heatmapLayerRef.current = heatmapLayer;

    map.setView([39.5, -96.5], 4);
    map.on("click", () => map.closePopup());

    const resizeObserver = new ResizeObserver(() => map.invalidateSize());
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      map.remove();
      mapRef.current = null;
      rendererRef.current = null;
      routeLayerRef.current = null;
      checkpointLayerRef.current = null;
      endpointLayerRef.current = null;
      heatmapLayerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const routeLayer = routeLayerRef.current;
    const checkpointLayer = checkpointLayerRef.current;
    const endpointLayer = endpointLayerRef.current;
    const renderer = rendererRef.current;
    if (!map || !routeLayer || !checkpointLayer || !endpointLayer || !renderer) return;

    routeLayer.clearLayers();
    checkpointLayer.clearLayers();
    endpointLayer.clearLayers();

    if (!plan) {
      lastPlanIdRef.current = null;
      heatmapLayerRef.current?.setVisible(false);
      map.setView([39.5, -96.5], 4);
      return;
    }

    const activeRouteId = selectedRouteId ?? plan.recommendation.routeId;
    const activeRoute = plan.routes.find((route) => route.id === activeRouteId) ?? plan.routes[0];

    const addEndpoint = (
      place: TripPlan["origin"],
      kind: "origin" | "destination",
      label: string,
    ) => {
      const marker = L.marker([place.lat, place.lon], {
        icon: endpointIcon(kind),
        zIndexOffset: 1200,
      }).addTo(endpointLayer);
      marker.bindTooltip(`${label}: ${place.label}`, {
        direction: "top",
        offset: [0, -12],
        className: "endpoint-tooltip",
      });
      marker.bindPopup(
        `<div class="map-popup map-popup--endpoint"><div class="map-popup__eyebrow">${escapeHtml(label)}</div><div class="map-popup__place">${escapeHtml(place.label)}</div></div>`,
        { closeButton: false },
      );
    };

    addEndpoint(plan.origin, "origin", "Origin");
    addEndpoint(plan.destination, "destination", "Destination");

    for (const route of plan.routes) {
      const isActive = route.id === activeRoute?.id;
      if (isActive) {
        L.polyline(route.geometry, {
          color: "#ffffff",
          weight: 10,
          opacity: 0.92,
          lineCap: "round",
          lineJoin: "round",
          renderer,
          interactive: false,
        }).addTo(routeLayer);
      }

      const polylines = routeRiskPolylines(route);
      for (const polyline of polylines) {
        const line = L.polyline(polyline.positions, {
          color: riskColor(polyline.level),
          weight: isActive ? 6 : 4,
          opacity: isActive ? 0.96 : 0.36,
          lineCap: "round",
          lineJoin: "round",
          renderer,
        }).addTo(routeLayer);
        line.on("click", () => onSelectRoute(route.id));
      }

      for (const checkpoint of route.checkpoints) {
        const marker = L.circleMarker([checkpoint.lat, checkpoint.lon], {
          radius: isActive ? 5 : 2.4,
          color: "#ffffff",
          weight: isActive ? 2 : 1,
          opacity: isActive ? 1 : 0.45,
          fillColor: riskColor(checkpoint.risk.level),
          fillOpacity: isActive ? 1 : 0.55,
          renderer,
        }).addTo(checkpointLayer);
        if (isActive) {
          marker.bindPopup(checkpointPopup(checkpoint, route), {
            closeButton: false,
            offset: [0, -4],
            maxWidth: 280,
          });
        }
      }
    }

    if (lastPlanIdRef.current !== plan.planId) {
      lastPlanIdRef.current = plan.planId;
      map.fitBounds(L.latLngBounds(planBounds(plan.routes)), {
        padding: [54, 54],
        maxZoom: 10,
        animate: false,
      });
    } else if (
      activeRoute &&
      lastActiveRouteRef.current !== null &&
      lastActiveRouteRef.current !== activeRoute.id
    ) {
      map.flyToBounds(L.latLngBounds(routeBounds(activeRoute)), {
        padding: [64, 64],
        maxZoom: 11,
        duration: 0.65,
      });
    }
    lastActiveRouteRef.current = activeRoute?.id ?? null;
  }, [onSelectRoute, plan, selectedRouteId]);

  useEffect(() => {
    const layer = heatmapLayerRef.current;
    if (!layer) return;
    const activeRouteId = selectedRouteId ?? plan?.recommendation.routeId ?? null;
    if (
      !heatmapVisible ||
      !heatmapFrame ||
      !activeRouteId ||
      heatmapFrame.routeId !== activeRouteId
    ) {
      layer.setVisible(false);
      return;
    }
    layer.setPoints(
      heatmapFrame.points.map((point) => ({
        lat: point.lat,
        lon: point.lon,
        color: riskColor(point.risk.level),
      })),
    );
    layer.setVisible(true);
  }, [heatmapFrame, heatmapVisible, plan?.recommendation.routeId, selectedRouteId]);

  useEffect(() => {
    return () => {
      lastPlanIdRef.current = null;
    };
  }, []);

  return (
    <div className="trip-map">
      <div ref={containerRef} className="trip-map__canvas" aria-label="Trip route map" />
    </div>
  );
}
