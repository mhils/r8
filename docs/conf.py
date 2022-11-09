project = "r8"
master_doc = "index"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinxcontrib_trio",
]

autodoc_member_order = "bysource"

html_theme_options = {
    "show_powered_by": False,
}
html_show_copyright = False
html_show_sourcelink = False
html_sidebars = {"**": []}
