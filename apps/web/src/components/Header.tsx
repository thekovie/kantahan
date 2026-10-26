import { Menu, Moon, Sun, X } from "lucide-react";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link, useLocation } from "wouter";

interface HeaderProps {
  theme: "dark" | "light";
  onToggleTheme: () => void;
  /** True while the demo catalog (made-up songs) is loaded. */
  demo?: boolean;
}

const LINKS = [
  { href: "/", label: "Songbook" },
  { href: "/about", label: "About" },
  { href: "/privacy", label: "Privacy" },
  { href: "/rights", label: "Rights and removal" },
] as const;

export function Header({ theme, onToggleTheme, demo = false }: HeaderProps) {
  const [open, setOpen] = useState(false);
  const [location] = useLocation();
  const root = useRef<HTMLDivElement>(null);
  const bar = useRef<HTMLElement>(null);

  // The machine sign and the scroll padding sit just under this bar, so publish its real height.
  useLayoutEffect(() => {
    const el = bar.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const publish = () => document.documentElement.style.setProperty("--header-h", `${el.getBoundingClientRect().height}px`);
    publish();
    const watcher = new ResizeObserver(publish);
    watcher.observe(el);
    return () => {
      watcher.disconnect();
      document.documentElement.style.removeProperty("--header-h");
    };
  }, []);

  useEffect(() => setOpen(false), [location]);
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => event.key === "Escape" && setOpen(false);
    const onPointer = (event: PointerEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [open]);

  return (
    <header className="header" ref={bar}>
      <div className="header__bar">
        <Link href="/" className="brand" aria-label="Kantahan, songbook home">
          <img src="/brand/logo.svg" alt="" width={36} height={36} />
          Kantahan
        </Link>
        {demo && (
          <span className="badge" title="Demo data: these are made-up songs for trying the app, not real song numbers">
            Demo
          </span>
        )}
        <div className="header__actions">
          <button
            type="button"
            className="icon-btn"
            onClick={onToggleTheme}
            aria-label={theme === "dark" ? "Switch to the light theme" : "Switch to the dark theme"}
          >
            {theme === "dark" ? <Sun size={24} aria-hidden="true" /> : <Moon size={24} aria-hidden="true" />}
          </button>
          <div className="menu" ref={root}>
            <button
              type="button"
              className="icon-btn"
              aria-expanded={open}
              aria-controls="site-menu"
              onClick={() => setOpen((v) => !v)}
            >
              {open ? <X size={24} aria-hidden="true" /> : <Menu size={24} aria-hidden="true" />}
              Menu
            </button>
            {open && (
              <nav id="site-menu" className="menu__panel" aria-label="Site">
                {LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="menu__link"
                    aria-current={location === link.href ? "page" : undefined}
                  >
                    {link.label}
                  </Link>
                ))}
              </nav>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
