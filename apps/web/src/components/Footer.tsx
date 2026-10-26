import { Link } from "wouter";

export function Footer() {
  return (
    <footer className="footer">
      <div className="footer__inner">
        <nav aria-label="About Kantahan">
          <Link href="/about">About</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/rights">Rights and removal</Link>
        </nav>
        <p>
          Kantahan is independent and not affiliated with Platinum Karaoke or Vismay International Corporation. More
          local machines coming soon.
        </p>
      </div>
    </footer>
  );
}
