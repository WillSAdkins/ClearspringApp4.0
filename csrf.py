"""CSRF protection.

Without this, a malicious page can make a signed-in person's browser submit
forms to this app without their knowledge — deleting events, changing settings,
posting as them. Every state-changing form carries a token that only this site
can know.

Implemented directly rather than via Flask-WTF to avoid another dependency.
"""

import hmac
import secrets

from flask import session, request, abort

CSRF_SESSION_KEY = "_csrf_token"

# Endpoints that legitimately accept POSTs without a form token, because they
# are called by our own JavaScript with a header instead, or are public APIs
# where CSRF isn't meaningful.
EXEMPT_ENDPOINTS = set()


def get_token():
    """Current token for this session, creating one if needed."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def valid(submitted):
    expected = session.get(CSRF_SESSION_KEY)
    if not expected or not submitted:
        return False
    return hmac.compare_digest(expected, submitted)


def protect(app):
    """Check every state-changing request, and expose the token to templates."""

    @app.before_request
    def _check_csrf():
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return
        if request.endpoint in EXEMPT_ENDPOINTS:
            return

        # Accept the token from a form field or a header (for fetch calls).
        submitted = (
            request.form.get("csrf_token")
            or request.headers.get("X-CSRF-Token")
        )

        if not valid(submitted):
            abort(400, description="Your session expired or the form was stale. "
                                   "Please go back, reload the page and try again.")

    @app.context_processor
    def _inject_token():
        return {"csrf_token": get_token}
