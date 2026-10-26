import { Suspense, lazy, useEffect, useRef } from "react";
import { Route, Switch, useLocation } from "wouter";
import { Footer } from "./components/Footer";
import { BackToTop } from "./components/BackToTop";
import { Header } from "./components/Header";
import { useCatalog } from "./hooks/useCatalog";
import { useTheme } from "./hooks/useTheme";
import { Home } from "./pages/Home";

// The text pages (and the contact form) load when first opened, keeping the songbook's first load small.
const About = lazy(() => import("./pages/About").then((m) => ({ default: m.About })));
const Privacy = lazy(() => import("./pages/Privacy").then((m) => ({ default: m.Privacy })));
const Rights = lazy(() => import("./pages/Rights").then((m) => ({ default: m.Rights })));

const TITLES: Record<string, string> = {
  "/": "Kantahan",
  "/about": "About · Kantahan",
  "/privacy": "Privacy · Kantahan",
  "/rights": "Rights and removal · Kantahan",
};

export default function App() {
  const { theme, toggle } = useTheme();
  const catalog = useCatalog();
  const demo = "manifest" in catalog.state && catalog.state.manifest.synthetic;
  const [location] = useLocation();
  const main = useRef<HTMLElement>(null);
  const first = useRef(true);

  useEffect(() => {
    document.title = TITLES[location] ?? "Not found · Kantahan";
    // After a page change, move focus to the new content so keyboard and screen reader users start there.
    if (first.current) first.current = false;
    else main.current?.focus();
    window.scrollTo(0, 0);
  }, [location]);

  return (
    <div className="shell">
      <a className="skip" href="#main">
        Skip to content
      </a>
      <Header theme={theme} onToggleTheme={toggle} demo={demo} />
      <main id="main" ref={main} tabIndex={-1} className="shell__main">
        <Suspense fallback={null}>
          <Switch>
            <Route path="/">
              <Home catalog={catalog} />
            </Route>
            <Route path="/about" component={About} />
            <Route path="/privacy" component={Privacy} />
            <Route path="/rights" component={Rights} />
            <Route>
              <article className="prose">
                <h1>Page not found</h1>
                <p>
                  That page does not exist. <a href="/">Back to the songbook</a>.
                </p>
              </article>
            </Route>
          </Switch>
        </Suspense>
      </main>
      <Footer />
      <BackToTop onTop={() => main.current?.focus({ preventScroll: true })} />
    </div>
  );
}
