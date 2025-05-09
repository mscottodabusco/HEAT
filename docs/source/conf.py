# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
# sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../../source'))

# -- Project information -----------------------------------------------------

project = 'HEAT'
copyright = '2023, Tom Looby'
author = 'Tom Looby'

# The full version, including alpha/beta/rc tags
release = '4.0'


# -- General configuration ---------------------------------------------------
import sphinx_rtd_theme
# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx_rtd_theme', 'sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

#fake imports so that we dont need the docker container to run sphinx builds
autodoc_mock_imports = ["EFIT", "FreeCAD", "Part", "Mesh", "MeshPart", "Import", 
                        "werkzeug", "numpy",
                        "PyFoam",
                        "dash",
                        "dash_html_components",
                        "dash_core_components",
                        "dash_bootstrap_components",
                        "dash_bootstrap_templates",
                        "visdcc",
                        "flask",
                        "plotly",
                        "dash_table",
                        "dash_extensions",
                        "stl",
                        "scipy",
                        "psutil",
                        "trimesh",
                        "pandas",
                        "pillow",
                        "matplotlib",
                        "tk",
                        "vtk",
                        "click",
                        "h5py",
                        "netCDF4",
                        "mpi4py",
                        "gmsh",
                        "scikit-image",
                        "open3d",
                        "Fem"
                        ]

