"""Business module catalog exposed by the enterprise control plane."""

from app.modules.catalog import MODULE_CATALOG, get_module_template

__all__ = ["MODULE_CATALOG", "get_module_template"]
