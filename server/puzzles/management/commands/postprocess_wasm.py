import pathlib
import re

from django.core.management.base import BaseCommand

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[4]

PREFIX = b"""
function get_gain_destination(audio_context) {
    var audio_context_destination = audio_context.createGain();
    audio_context_destination.connect(audio_context.destination);
    function localstorage_audio_handler() {
        let value = window.localStorage.getItem('volume');
        value = value === null ? NaN : Number(value);
        if (isNaN(value)) value = 100;
        audio_context_destination.gain.value = value / 100;
    }
    localstorage_audio_handler();
    window.addEventListener('storage', localstorage_audio_handler);
    return audio_context_destination;
}
""".lstrip()


class Command(BaseCommand):
    help = "Postprocess wasm files to use site volume."

    AUDIO_CONTEXT_REGEXES = [
        r"codo_audio_context",
        r"SDL\.audioContext",
        r"SDL2\.audioContext",
    ]

    FILES = [
        # FIXME: include any files that use wasm and audio.
        # "server/puzzles/static/js/puzzle.js",
    ]

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        regexp = re.compile(
            rf"""({'|'.join(self.AUDIO_CONTEXT_REGEXES)})(\.destination|\[["']destination["']\])""".encode()
        )
        for relpath in self.FILES:
            path = PROJECT_ROOT / relpath
            with open(path, "rb") as f:
                contents = f.read()
            if b"\r\n" in contents:
                newline = b"\r\n"
            elif b"\r" in contents:
                newline = b"\r"
            else:
                newline = b"\n"
            prefix = newline.join(PREFIX.split(b"\n"))
            output = contents
            if not output.startswith(PREFIX):
                output = PREFIX + output
            output = regexp.sub(rb"get_gain_destination(\1)", output)
            if output != contents:
                with open(path, "wb") as f:
                    f.write(output)
