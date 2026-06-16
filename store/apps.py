from django.apps import AppConfig


class StoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'store'  # Ensure karo ye tumhare app ka sahi naam hai

    def ready(self):
        import store.signals