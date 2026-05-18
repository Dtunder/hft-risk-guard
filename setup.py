from setuptools import setup, Extension
from Cython.Build import cythonize

ext_modules = [
    Extension(
        "fast_risk",
        sources=["src/fast_risk.pyx"],
        extra_compile_args=["-O3", "-march=native", "-ffast-math"],
    )
]

setup(
    name="fast_risk",
    ext_modules=cythonize(ext_modules, compiler_directives={'language_level': "3"})
)
