import { ContactForm } from "../components/ContactForm";

export function Rights() {
  return (
    <article className="prose">
      <h1>Rights and removal</h1>
      <p>
        If you own rights in a song list entry, or you see a wrong number, title or artist, tell us and we will correct or
        remove it. A request does not need a reason beyond what you want changed.
      </p>

      <h2>Send a request</h2>
      <p>Please include:</p>
      <ul>
        <li>the machine model and the song number (or the title and artist),</li>
        <li>what should change, or that the entry should be removed,</li>
        <li>if you are a rights holder, which work and what your connection to it is.</li>
      </ul>
      <ContactForm />
      <p>
        Prefer a public record? You can also open an issue at{" "}
        <a href="https://github.com/thekovie/kantahan/issues" rel="noreferrer noopener" target="_blank">
          github.com/thekovie/kantahan/issues
        </a>
        . Issues there are visible to everyone, so leave out personal details such as phone numbers or home addresses.
      </p>

      <h2>What happens next</h2>
      <p>
        We review each request as soon as we can. Confirmed corrections and removals are made in the song lists, and a
        catalog release can be paused while a request is checked. Corrected lists reach phones the next time the app
        refreshes its songs.
      </p>

      <h2>Where the songs come from</h2>
      <p>
        Song lists are compiled from the official{" "}
        <a href="https://platinumkaraoke.com/pages/songlist-update" rel="noreferrer noopener" target="_blank">
          Platinum Karaoke song list updates
        </a>
        . Kantahan is independent and is not affiliated with Platinum Karaoke or Vismay International Corporation.
      </p>
    </article>
  );
}
