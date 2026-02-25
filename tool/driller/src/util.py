import importlib
import logging

logger = logging.getLogger(__name__)


def get_class(class_path):
    """Get's class based on string that points to it.
    Used for changing classes that are used easily in settings file.
    """

    module_path, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_path)

    return getattr(module, class_name)
