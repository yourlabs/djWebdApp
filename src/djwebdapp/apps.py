from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules


class DjwebdappConfig(AppConfig):
    name = 'djwebdapp'

    def ready(self):
        autodiscover_modules('normalizers')
