"""Which of the deployments this container is.

`NINANATUR_ENV` has been passed into the container since Wave 8 and read by
nothing. It matters now: the preview and the live site are the same application,
byte for byte, and somebody who plants a garden on the wrong one loses it when
the volume is next cleared.

Reported through `/healthz` rather than compiled into the frontend, for the same
reason the version is: only the server knows which build is running, and a
baked-in value keeps claiming the old one after a partial rollout.
"""
from __future__ import annotations

import os

ENV_VAR = "NINANATUR_ENV"

#: The environment nothing needs to be told about. Anything else is a place a
#: gardener did not mean to be, so the default is the one that says nothing —
#: an unset variable must not turn production into a page shouting "preview".
PRODUCTION = "prod"


def environment() -> str:
    """The deployment's own name, lower-cased. `prod` when nothing says."""
    return (os.environ.get(ENV_VAR) or PRODUCTION).strip().lower() or PRODUCTION


def is_production() -> bool:
    return environment() == PRODUCTION


__all__ = ["ENV_VAR", "PRODUCTION", "environment", "is_production"]
