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
          Kantahan is an independent songbook. It is not affiliated with, endorsed by or sponsored by Platinum Karaoke or
          Vismay International Corporation.
        </p>
      </div>
    </footer>
  );
}
