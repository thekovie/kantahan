export function Privacy() {
  return (
    <article className="prose">
      <h1>Privacy</h1>
      <p>
        Kantahan has no accounts, no ads, no analytics and no tracking. Searching happens on your phone, so what you
        search for is never sent anywhere.
      </p>

      <h2>What is saved on your phone</h2>
      <ul>
        <li>The song lists for the models you opened, so search works offline.</li>
        <li>Your chosen machine model and whether you prefer the light or dark theme.</li>
      </ul>
      <p>This stays in your browser. Clearing the site data in your browser removes all of it.</p>

      <h2>What the server sees</h2>
      <p>
        When the app downloads or refreshes song lists, the server that hosts them receives an ordinary web request. Like
        any web server it can keep standard access logs such as the time, your network address and the file requested. The
        app sends no cookies and no identifiers of its own.
      </p>

      <h2>Contacting us</h2>
      <p>
        A private contact form for rights requests is planned. This page will say exactly what it stores before the form
        goes live. Until then, requests go through the public issue tracker described under Rights and removal, so do not
        put personal details in them.
      </p>
    </article>
  );
}
