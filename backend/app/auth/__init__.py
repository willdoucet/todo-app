# app/auth — first-party auth subsystem (M3).
#
# Public surface — the rest of the codebase reaches into auth via:
#
#   from app.auth import router, get_current_user
#
# Internal modules (config, service, tokens, passwords, errors,
# logging_utils, schemas, models, dependencies) stay private. Audit
# surface for security review is intentionally one folder.

from app.auth.dependencies import get_current_user
from app.auth.routes import router

__all__ = ["router", "get_current_user"]
