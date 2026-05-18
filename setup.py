from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        name="src.fast_risk",
        sources=["src/fast_risk.pyx"],
    )
]

setup(
    name="fast_risk",
    ext_modules=cythonize(extensions, language_level=3)
)
