function toggleExpandResponses(id) {
    $(`.submitted-text#${id}-short`).toggle();
    $(`.submitted-text#${id}`).toggle();
}

function copyHint(id) {
    document.querySelector('textarea').textContent =
        document.getElementById(id).textContent;
}

// We used to use localStorage here, which is a lot easier to access on the
// client-side, but can lead to confusingly inconsistent state between the
// client and server. In particular, if the user's cookie expired but they have
// their name in localStorage and they click a claim link, the server will
// think they're anonymous (since it can't see localStorage) but they'll think
// they're not (after this JavaScript runs). So we use cookies on both server
// and client side so they have a consistent view of whether the user has ID'ed
// themselves.

function askName(force) {
    var name;
    var prefix = 'claimer=';
    var claimerCookie = document.cookie.split('; ').find(row => row.startsWith(prefix));
    if (claimerCookie) {
      name = decodeURIComponent(claimerCookie.slice(prefix.length));
    }

    if (!name || force) {
        name = prompt('Who are you? (personal Discord name/username; this is for internal use)');
        if (name) {
            localStorage.name = name;
        }
    }
    if (name) {
        document.cookie = 'claimer=' + encodeURIComponent(name) + ';path=/;max-age=1209600'; // 2 weeks
        document.getElementById('claimer').textContent = name;
    }
}

function askGmailUser(force) {
    var account;
    prefix = 'gmail=';
    var accountCookie = document.cookie.split('; ').find(row => row.startsWith(prefix));
    if (accountCookie) {
      account = decodeURIComponent(accountCookie.slice(prefix.length));
    }

    if (!account || force) {
        // FIXME: Update team email
        account = parseInt(prompt('What account number is myhuntemail@gmail.com? (the [NUMBER] in mail.google.com/mail/u/[NUMBER]/#inbox)'));
        if (!isNaN(account)) {
            localStorage.account = account;
        }
    }
    if (!isNaN(account)) {
        document.cookie = 'gmail=' + encodeURIComponent(account) + ';path=/;max-age=1209600'; // 2 weeks
        document.getElementById('gmail').textContent = account;
        for (var anchor of document.getElementsByClassName('gmail-search')) {
            anchor.setAttribute('href', anchor.href.replace(/^https:\/\/mail\.google\.com\/mail\/u\/\d*\//, "https://mail.google.com/mail/u/" + account + "/"));
        }
    }
}

askName(false);
