import os
# Ensure pure Python fallback for SQLAlchemy C-extensions under Windows Application Control
os.environ["DISABLE_SQLALCHEMY_CEXT"] = "1"
