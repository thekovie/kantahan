import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import type { LetterCount } from "../lib/search";
import type { ModelInfo } from "../lib/types";
import { LetterStrip } from "./LetterStrip";
import { ModelPicker } from "./ModelPicker";

const model = (n: number, family = "Family one"): ModelInfo => ({
  slug: `m${n}`,
  name: `Model ${n}`,
  family,
  hue: "magenta",
  file: `m${n}.json`,
  sha256: "0".repeat(64),
  bytes: 1,
  songs: 1,
  coverage: "Demo",
});

function Picker({ models }: { models: ModelInfo[] }) {
  const [value, setValue] = useState(models[0]?.slug ?? "");
  return <ModelPicker models={models} value={value} onChange={setValue} />;
}

describe("ModelPicker", () => {
  it("moves the selection with the arrow keys and wraps around", async () => {
    const user = userEvent.setup();
    render(<Picker models={[model(1), model(2), model(3)]} />);
    const first = screen.getByRole("radio", { name: "Model 1" });
    first.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: "Model 2" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Model 2" })).toHaveFocus();
    await user.keyboard("{ArrowLeft}{ArrowLeft}");
    expect(screen.getByRole("radio", { name: "All machines" })).toBeChecked();
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("radio", { name: "Model 3" })).toBeChecked();
    await user.keyboard("a");
    expect(screen.getByRole("radio", { name: "Model 3" })).toBeChecked();
  });

  it("only the selected chip is in the tab order", () => {
    render(<Picker models={[model(1), model(2)]} />);
    expect(screen.getByRole("radio", { name: "Model 1" })).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("radio", { name: "Model 2" })).toHaveAttribute("tabindex", "-1");
  });

  it("shows nothing to choose when there is a single model", () => {
    const { container } = render(<Picker models={[model(1)]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("falls back to a native select grouped by family when there are many models", async () => {
    const user = userEvent.setup();
    const many = [1, 2, 3, 4, 5, 6].map((n) => model(n, n > 3 ? "Family two" : "Family one"));
    render(<Picker models={many} />);
    const select = screen.getByRole("combobox", { name: "Machine model" });
    // The arrow is drawn by us (not the browser) so it can have its own spacing from the edge.
    expect(document.querySelector(".select-wrap .select__icon")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Family two" })).toBeInTheDocument();
    await user.selectOptions(select, "Model 5");
    expect(select).toHaveValue("m5");
    await user.selectOptions(select, "All machines");
    expect(select).toHaveValue("all");
  });
});

const LETTERS: LetterCount[] = [
  { letter: "A", count: 3 },
  { letter: "B", count: 1 },
  { letter: "#", count: 2 },
];

function Strip() {
  const [active, setActive] = useState("A");
  return <LetterStrip letters={LETTERS} active={active} onChange={setActive} panelId="panel" />;
}

describe("LetterStrip", () => {
  it("names each letter with its song count, and numbers by what they are", () => {
    render(<Strip />);
    expect(screen.getByRole("tab", { name: "A, 3 songs" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "B, 1 song" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Numbers and symbols, 2 songs" })).toBeInTheDocument();
  });

  it("supports arrow, Home and End keys and stops at the ends", async () => {
    const user = userEvent.setup();
    render(<Strip />);
    screen.getByRole("tab", { name: "A, 3 songs" }).focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: "B, 1 song" })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{End}");
    expect(screen.getByRole("tab", { name: /^Numbers/ })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("tab", { name: /^Numbers/ })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{Home}");
    expect(screen.getByRole("tab", { name: "A, 3 songs" })).toHaveAttribute("aria-selected", "true");
    await user.keyboard("{ArrowLeft}");
    expect(screen.getByRole("tab", { name: "A, 3 songs" })).toHaveAttribute("aria-selected", "true");
  });
});
