"""Sphinx configuration for litestar-admin documentation."""

from __future__ import annotations

import os
import sys

# Add source directory to path for autodoc
sys.path.insert(0, os.path.abspath("../src"))

# Project information
project = "litestar-admin"
copyright = "2024, Jacob Coffee"  # noqa: A001
author = "Jacob Coffee"
release = "0.1.0"

# General configuration
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_autodoc_typehints",
    "sphinx_copybutton",
    "sphinx_design",
    "myst_parser",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# HTML output configuration
html_theme = "shibuya"
html_static_path = ["_static"]
html_css_files = ["custom.css"]
html_title = "litestar-admin"

# Theme options
html_theme_options = {
    "accent_color": "lime",
    "dark_code": True,
    "github_url": "https://github.com/JacobCoffee/litestar-admin",
    "nav_links": [
        {"title": "Litestar", "url": "https://litestar.dev/"},
        {"title": "PyPI", "url": "https://pypi.org/project/litestar-admin/"},
    ],
}

# Autodoc configuration
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}
autodoc_typehints = "description"
autodoc_class_signature = "separated"
autodoc_inherit_docstrings = True

# Autosummary configuration
autosummary_generate = True

# Napoleon configuration
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_attr_annotations = True

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "litestar": ("https://docs.litestar.dev/latest/", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "advanced-alchemy": ("https://docs.advanced-alchemy.jolt.rs/latest/", None),
}

# MyST configuration
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "fieldlist",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]
myst_heading_anchors = 3

# Copy button settings
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True

# Suppress warnings for cross-references to classes that might not resolve
suppress_warnings = ["myst.xref_missing", "ref.duplicate_object"]
