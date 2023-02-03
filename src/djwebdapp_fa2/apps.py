from django.apps import AppConfig


class Fa2Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "djwebdapp_fa2"

    def ready(self):
        import djwebdapp_fa2.indexers  # noqa: F401
