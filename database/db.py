"""Database helper (placeholder).

This module will hold Supabase connection logic for V1. Keep simple and testable.
"""
from config.settings import settings


class Database:
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL
        self.supabase_key = settings.SUPABASE_KEY
        # Actual client initialization postponed until step 3

    def ping(self):
        return bool(self.supabase_url and self.supabase_key)


db = Database()
