from setuptools import setup, Extension
from Cython.Build import cythonize

ext_modules = [
    Extension(
        "src.fast_risk",
        ["src/fast_risk.pyx"],
    )
]

setup(
    name="fast_risk",
    ext_modules=cythonize(ext_modules, compiler_directives={'language_level': "3"})
)
