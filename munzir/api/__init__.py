"""
MUNZIR REST API and Frontend package.
"""

from munzir.api.app import app
from munzir.api.rbac import EntraRole, AuthenticatedUser

__all__ = ["app", "EntraRole", "AuthenticatedUser"]

