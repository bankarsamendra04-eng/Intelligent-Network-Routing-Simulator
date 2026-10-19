"""Application configuration settings for Intelligent Network Routing Simulator."""
import os

class Config:
    """Base configuration settings."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "network-routing-sim-secret-key-2026")
    DEBUG = False
    TESTING = False
    JSON_SORT_KEYS = False

class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True

class TestingConfig(Config):
    """Testing environment configuration."""
    TESTING = True
    DEBUG = True
