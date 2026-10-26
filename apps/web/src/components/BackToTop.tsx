import { ArrowUp } from "lucide-react";
import { useEffect, useState } from "react";

/** How many screens down the page has to be before the button shows. */
const SHOW_AFTER_SCREENS = 2;

interface BackToTopProps {
  /** Called after scrolling up, so focus can move to the start of the content. */
  onTop: () => void;
}

/** A way back to the top of a long list, shown only after scrolling a long way. */
export function BackToTop({ onTop }: BackToTopProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const update = () => setVisible(window.scrollY > window.innerHeight * SHOW_AFTER_SCREENS);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);

  if (!visible) return null;
  const go = () => {
    const calm = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    window.scrollTo({ top: 0, behavior: calm ? "auto" : "smooth" });
    onTop();
  };
  return (
    <button type="button" className="to-top" onClick={go} aria-label="Back to top">
      <ArrowUp size={22} aria-hidden="true" />
      Top
    </button>
  );
}
