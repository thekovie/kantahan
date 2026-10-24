// Sets the theme before first paint so the page never flashes the wrong colours.
// Kept as a file (not inline) so a strict Content-Security-Policy can allow it by source.
(function () {
  var theme = "light";
  try {
    var saved = localStorage.getItem("kantahan.theme");
    if (saved === "light" || saved === "dark") theme = saved;
    else if (window.matchMedia("(prefers-color-scheme: dark)").matches) theme = "dark";
  } catch (e) {
    /* storage blocked: keep the light default */
  }
  document.documentElement.setAttribute("data-theme", theme);
})();
