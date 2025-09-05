# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

# See https://www.sphinx-doc.org/en/master/usage/configuration.html
# To build the documentation locally: sphinx-build -b html docs docs/_build/html


project = 'Capture2Go Python SDK'
author = 'SensorStim Neurotechnology GmbH'
copyright = f"2025, {author}"

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'myst_parser',
    'sphinxcontrib.mermaid',
]

autosummary_generate = True
autodoc_typehints = 'description'
autodoc_member_order = 'bysource'
autodoc_inherit_docstrings = False
napoleon_google_docstring = True
napoleon_numpy_docstring = True

templates_path = ['_templates']
exclude_patterns = ['_build']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = None
html_theme_options = {
    'collapse_navigation': False,
    'style_external_links': True,
    'navigation_depth': 4,
}

html_css_files = [
    'custom.css',
]

myst_enable_extensions = [
    'deflist',
    'fieldlist',
    'colon_fence',
    'attrs_block',
    'attrs_inline',
]

myst_fence_as_directive = [
    'mermaid',
]

myst_heading_anchors = 3

mermaid_version = '10.9.1'

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'bleak': ('https://bleak.readthedocs.io/en/latest/', None),
}

todo_include_todos = True
