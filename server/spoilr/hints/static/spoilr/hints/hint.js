function copyHint(num) {
    var range = document.createRange();
    range.selectNode(document.getElementById("hint" + num));
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.execCommand("copy");
    window.getSelection().removeAllRanges();
}
