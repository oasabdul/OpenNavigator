import L from "leaflet";

export interface HeatmapLayerPoint {
  lat: number;
  lon: number;
  color: string;
}

function rgba(hex: string, alpha: number): string {
  const value = hex.replace("#", "");
  const red = Number.parseInt(value.slice(0, 2), 16);
  const green = Number.parseInt(value.slice(2, 4), 16);
  const blue = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${red}, ${green}, ${blue}, ${alpha})`;
}

export class WeatherHeatmapLayer extends L.Layer {
  private leafletMap: L.Map | null = null;
  private canvas: HTMLCanvasElement | null = null;
  private points: HeatmapLayerPoint[] = [];
  private visible = true;

  onAdd(map: L.Map): this {
    this.leafletMap = map;
    const pane = map.getPane("weatherHeatmap") ?? map.getPanes().overlayPane;
    const canvas = L.DomUtil.create("canvas", "weather-heatmap-canvas");
    canvas.style.pointerEvents = "none";
    pane.appendChild(canvas);
    this.canvas = canvas;

    map.on("move zoom resize viewreset", this.reset, this);
    this.reset();
    return this;
  }

  onRemove(map: L.Map): this {
    map.off("move zoom resize viewreset", this.reset, this);
    this.canvas?.remove();
    this.canvas = null;
    this.leafletMap = null;
    return this;
  }

  setPoints(points: HeatmapLayerPoint[]): void {
    this.points = points;
    this.redraw();
  }

  setVisible(visible: boolean): void {
    this.visible = visible;
    if (this.canvas) {
      this.canvas.style.display = visible ? "block" : "none";
    }
    if (visible) this.redraw();
  }

  private reset(): void {
    const map = this.leafletMap;
    const canvas = this.canvas;
    if (!map || !canvas) return;
    const size = map.getSize();
    const topLeft = map.containerPointToLayerPoint([0, 0]);
    L.DomUtil.setPosition(canvas, topLeft);
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(size.x * ratio));
    canvas.height = Math.max(1, Math.round(size.y * ratio));
    canvas.style.width = `${size.x}px`;
    canvas.style.height = `${size.y}px`;
    this.redraw();
  }

  private redraw(): void {
    const map = this.leafletMap;
    const canvas = this.canvas;
    if (!map || !canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;

    const ratio = window.devicePixelRatio || 1;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, canvas.width / ratio, canvas.height / ratio);
    if (!this.visible) return;

    const radius = 74;
    for (const point of this.points) {
      const position = map.latLngToContainerPoint([point.lat, point.lon]);
      if (
        position.x < -radius ||
        position.y < -radius ||
        position.x > map.getSize().x + radius ||
        position.y > map.getSize().y + radius
      ) {
        continue;
      }
      const gradient = context.createRadialGradient(
        position.x,
        position.y,
        0,
        position.x,
        position.y,
        radius,
      );
      gradient.addColorStop(0, rgba(point.color, 0.62));
      gradient.addColorStop(0.45, rgba(point.color, 0.28));
      gradient.addColorStop(1, rgba(point.color, 0));
      context.fillStyle = gradient;
      context.beginPath();
      context.arc(position.x, position.y, radius, 0, Math.PI * 2);
      context.fill();
    }
  }
}
