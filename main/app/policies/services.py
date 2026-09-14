"""Presentation shape for the policy listing."""
from . import models


def policy_panel(force=False):
    """What the dialog and the standalone page both render."""
    result = models.policies(force=force)
    return {**result, 'count': len(result['policies'])}
