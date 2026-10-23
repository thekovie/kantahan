import { Link } from "wouter";

export function About() {
  return (
    <article className="prose">
      <h1>About Kantahan</h1>
      <p>
        Kantahan is a songbook for Platinum Karaoke machines. Choose your machine, search by song title, artist or song
        number, then key the number into your remote. Once the songs are saved on your phone it works without a signal.
      </p>

      <h2>What to trust, and what to check</h2>
      <p>
        Song numbers are different on different machines, so each songbook only lists the numbers published for that
        model. A song missing here may still exist on your machine. The lists are monthly or volume updates, so a
        songbook covers the volumes named under the results, and older songs are not in it.
      </p>

      <h2>Where the songs come from</h2>
      <p>
        Song lists are compiled from the official{" "}
        <a href="https://platinumkaraoke.com/pages/songlist-update" rel="noreferrer noopener" target="_blank">
          Platinum Karaoke song list updates
        </a>
        . Kantahan is independent. It is not affiliated with, endorsed by or sponsored by Platinum Karaoke or Vismay
        International Corporation. Their names are used only to say which machines the numbers are for.
      </p>

      <h2>What it does not do</h2>
      <ul>
        <li>No music, videos or lyrics.</li>
        <li>No song queue and no sharing.</li>
        <li>No accounts and no tracking.</li>
      </ul>

      <h2>Something wrong?</h2>
      <p>
        If a number or a name is wrong, or you want an entry corrected or removed, see{" "}
        <Link href="/rights">Rights and removal</Link>.
      </p>
    </article>
  );
}
