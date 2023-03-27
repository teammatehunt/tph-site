function askGmailUser(force) {
  var account;
  prefix = "gmail=";
  var accountCookie = document.cookie
    .split("; ")
    .find((row) => row.startsWith(prefix));
  if (accountCookie) {
    account = decodeURIComponent(accountCookie.slice(prefix.length));
  }

  if (!account || force) {
    account = parseInt(
      prompt(
        "What account number is the MH Gmail? (the [NUMBER] in mail.google.com/mail/u/[NUMBER]/#inbox)"
      )
    );
    if (!isNaN(account)) {
      localStorage.account = account;
    }
  }
  if (!isNaN(account)) {
    document.cookie =
      "gmail=" + encodeURIComponent(account) + ";path=/;max-age=1209600"; // 2 weeks
    document.getElementById("gmail").textContent = account;
    for (var anchor of document.getElementsByClassName("gmail-search")) {
      anchor.setAttribute(
        "href",
        anchor.href.replace(
          /^https:\/\/mail\.google\.com\/mail\/u\/\d*\//,
          "https://mail.google.com/mail/u/" + account + "/"
        )
      );
    }
  }
}
