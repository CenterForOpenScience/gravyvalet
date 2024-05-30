class OsfDatabaseRouter:
    def db_for_read(self, model, **hints):
        if model.__module__ == "addon_service.osf_models.models":
            return "osf"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def db_for_write(self, model, **hints):
        return None

    def allow_migration(self, db, app_label, model_name=None, **hints):
        return None
