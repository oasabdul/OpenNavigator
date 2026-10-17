import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { HeatmapControls } from "../components/HeatmapControls";

describe("HeatmapControls", () => {
  it("toggles the heatmap and changes the forecast hour", async () => {
    const onToggle = vi.fn();
    const onHourChange = vi.fn();
    const user = userEvent.setup();
    render(
      <HeatmapControls
        enabled
        hour={12}
        frame={null}
        isLoading={false}
        error={null}
        onToggle={onToggle}
        onHourChange={onHourChange}
        onRetry={() => {}}
      />,
    );

    await user.click(screen.getByRole("switch", { name: "Toggle corridor heatmap" }));
    expect(onToggle).toHaveBeenCalledTimes(1);

    fireEvent.change(screen.getByRole("slider", { name: "Forecast hour from departure" }), {
      target: { value: "24" },
    });
    expect(onHourChange).toHaveBeenCalledWith(24);
    expect(screen.getByText("+12h from departure")).toBeInTheDocument();
  });

  it("shows an error and retries", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <HeatmapControls
        enabled
        hour={0}
        frame={null}
        isLoading={false}
        error="Forecast unavailable"
        onToggle={() => {}}
        onHourChange={() => {}}
        onRetry={onRetry}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("Forecast unavailable");
    await user.click(screen.getByRole("button", { name: /Retry/ }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
