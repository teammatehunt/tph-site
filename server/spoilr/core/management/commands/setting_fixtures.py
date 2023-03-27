# Command to generate or load spoilr settings into a directory.
import os
from pathlib import Path

from django.conf import settings
from django.core.management import CommandError, call_command
from django.core.management.base import BaseCommand
from spoilr.core.models import HuntSetting

EXTENSION = ".yaml"
MODELS = ["settings"]


class Command(BaseCommand):
    help = "Loads or saves spoilr settings into a directory."

    def add_arguments(self, parser):
        parser.add_argument(
            "setting_dir", type=str, help="The directory to load or store from."
        )
        parser.add_argument("--save", action="store_true")
        parser.add_argument(
            "--model",
            "--models",
            help=f"Choose from {MODELS}",
            nargs="+",
            default=MODELS,
        )

    def _setting_path(self, fixture, extension=""):
        return os.path.join(self.setting_directory, fixture + extension)

    def _dumpdata(self, model, **options):
        call_command("dumpdata", model, format="yaml", verbosity=0, **options)

    def _save_setting_fixtures(self):
        for setting in HuntSetting.objects.all():
            path = self._setting_path(setting.name, extension=EXTENSION)
            self._dumpdata("spoilr_core.HuntSetting", pks=str(setting.id), output=path)

            self.stdout.write(f"Successfully saved fixture: {path}")

    def _load_setting_fixtures(self):
        fixtures = []
        for f in os.listdir(self.setting_directory):
            path = self._setting_path(f)
            if os.path.isfile(path) and path.endswith(EXTENSION):
                fixtures.append(path)

        if not fixtures:
            print("No setting fixtures found in directory. Skipping.")

        call_command("loaddata", *fixtures)

    def handle(self, *args, **options):
        fixture_dir = Path(os.path.abspath(__file__)).parents[2]
        self.setting_directory = os.path.join(fixture_dir, options["setting_dir"])

        def check_dir(path):
            if not os.path.isdir(path):
                raise CommandError(f"Invalid path specified: {path}")

        check_dir(self.setting_directory)

        if options["save"]:
            if "settings" in options["model"]:
                self._save_setting_fixtures()
        else:
            if "settings" in options["model"]:
                self._load_setting_fixtures()
