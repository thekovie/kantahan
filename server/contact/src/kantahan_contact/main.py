"""Production entry point: `uvicorn kantahan_contact.main:app`.

The service refuses to start when its settings are missing or wrong.
"""

import logging
import os

from .app import create_app
from .mailer import smtp_sender
from .settings import load_settings

# Our log lines hold no personal data (see app.py), so they can be shown at INFO.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
_settings = load_settings(os.environ)
app = create_app(_settings, smtp_sender(_settings))
