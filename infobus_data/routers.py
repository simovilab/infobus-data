"""
Database router for infobus-data project.
Routes queries for GTFS models to the main infobus database.
"""


class DatabaseRouter:
    """
    A router to control all database operations on models for different
    databases.
    """
    
    # Apps and models that should use the main infobus database
    route_app_labels = {'gtfs_proxy'}
    
    def db_for_read(self, model, **hints):
        """Suggest the database that should be read from."""
        if model._meta.app_label in self.route_app_labels:
            return 'infobus_main'
        return None

    def db_for_write(self, model, **hints):
        """Suggest the database that should be written to."""
        if model._meta.app_label in self.route_app_labels:
            return 'infobus_main'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if models are in the same app."""
        db_set = {'default', 'infobus_main'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that certain apps' models get created on the right database."""
        if app_label in self.route_app_labels:
            return db == 'infobus_main'
        return db == 'default'
