"""
Repackaging of Google's Diff Match and Patch libraries.

Offers robust algorithms to perform the operations required for synchronizing plain text.
"""

from .__version__ import __version__
from .diff_match_patch import __author__, __doc__, diff_match_patch, patch_obj
from .patch_applier import PatchApplier

__packager__ = "Amethyst Reese (amy@noswap.com)"

__all__ = [
    "__version__",
    "__author__",
    "__packager__",
    "diff_match_patch",
    "patch_obj",
    "PatchApplier",
]