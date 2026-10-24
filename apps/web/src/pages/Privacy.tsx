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
      <p>The form on the Rights and removal page collects only what you type into it:</p>
      <ul>
        <li>what the message is about and the message itself,</li>
        <li>optionally a machine and song, your name and your e-mail address.</li>
      </ul>
      <p>
        The server relays this to the project owner by e-mail and does not keep a copy: it is not saved in a database
        and not written to logs. The e-mail then sits in the owner&apos;s mailbox and with the mail provider. It is kept
        as long as it takes to handle your request and any follow-up, and you can ask for it to be deleted. It is not
        shared, sold or used for anything else.
      </p>
      <p>
        To limit abuse, the server counts messages per network address for an hour, in memory only. The count is not
        logged and disappears when the service restarts. A hidden field in the form catches automated bots; people
        never see or fill it.
      </p>
      <p>
        You can also open a public issue on GitHub instead. Anything written there is public, so keep personal details
        out of it.
      </p>
    </article>
  );
}
