import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { PlannerForm } from "../components/PlannerForm";

describe("PlannerForm", () => {
  it("submits a valid trip", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PlannerForm isLoading={false} onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("Origin"), "New York, NY");
    await user.type(screen.getByLabelText("Destination"), "Boston, MA");
    await user.click(screen.getByRole("button", { name: /Plan safest route/ }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const request = onSubmit.mock.calls[0]?.[0];
    expect(request).toMatchObject({
      origin: "New York, NY",
      destination: "Boston, MA",
      loadWeightLb: 42000,
      samplingIntervalMiles: 25,
    });
    expect(Number.isNaN(new Date(request.departure).getTime())).toBe(false);
  });

  it("shows validation errors instead of submitting", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PlannerForm isLoading={false} onSubmit={onSubmit} />);

    await user.click(screen.getByRole("button", { name: /Plan safest route/ }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Enter an origin");
  });

  it("fills an example and swaps endpoints", async () => {
    const user = userEvent.setup();
    render(<PlannerForm isLoading={false} onSubmit={() => {}} />);

    await user.click(screen.getByRole("button", { name: "NYC → Boston" }));
    expect(screen.getByLabelText("Origin")).toHaveValue("New York, NY");
    expect(screen.getByLabelText("Destination")).toHaveValue("Boston, MA");

    await user.click(screen.getByRole("button", { name: "Swap origin and destination" }));
    expect(screen.getByLabelText("Origin")).toHaveValue("Boston, MA");
    expect(screen.getByLabelText("Destination")).toHaveValue("New York, NY");
  });

  it("changes the sampling interval", async () => {
    const onSubmit = vi.fn();
    const user = userEvent.setup();
    render(<PlannerForm isLoading={false} onSubmit={onSubmit} />);

    await user.type(screen.getByLabelText("Origin"), "Dallas, TX");
    await user.type(screen.getByLabelText("Destination"), "Atlanta, GA");
    await user.click(screen.getByRole("button", { name: "10 mi" }));
    await user.click(screen.getByRole("button", { name: /Plan safest route/ }));

    expect(onSubmit.mock.calls[0]?.[0]).toMatchObject({ samplingIntervalMiles: 10 });
  });
});
