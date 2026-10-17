import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RouteCard } from "../components/RouteCard";
import { routeFixture } from "../test/fixtures";

describe("RouteCard", () => {
  it("renders route metrics and badges", () => {
    render(
      <RouteCard
        route={routeFixture}
        departure="2026-10-18T16:00:00Z"
        selected
        recommended
        fastest
        onSelect={() => {}}
      />,
    );

    expect(screen.getByText("Route 1")).toBeInTheDocument();
    expect(screen.getByText("Recommended")).toBeInTheDocument();
    expect(screen.getByText("Fastest")).toBeInTheDocument();
    expect(screen.getByText("214 mi")).toBeInTheDocument();
    expect(screen.getByText("4h 41m")).toBeInTheDocument();
    expect(screen.getByText("No Travel exposure")).toBeInTheDocument();
  });

  it("calls onSelect when clicked", async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(
      <RouteCard
        route={routeFixture}
        departure="2026-10-18T16:00:00Z"
        selected={false}
        recommended={false}
        fastest={false}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Select Route 1/ }));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});
