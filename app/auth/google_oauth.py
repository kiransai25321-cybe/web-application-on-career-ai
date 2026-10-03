import logging
from authlib.integrations.starlette_client import OAuth
from app.config import settings

logger = logging.getLogger(__name__)

oauth = OAuth()

if settings.google_oauth_enabled:
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile"
        }
    )
else:
    logger.info("Google OAuth is not configured. Google login button will be hidden.")
