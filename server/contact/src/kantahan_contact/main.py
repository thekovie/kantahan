"""Production entry point: `uvicorn kantahan_contact.main:app`.

The service refuses to start when its settings are missing or wrong.
"""

import os

from .app import create_app
from .mailer import smtp_sender
from .settings import load_settings

_settings = load_settings(os.environ)
app = create_app(_settings, smtp_sender(_settings))
