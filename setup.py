from setuptools import setup


setup(
    name="hfsync",
    version="0.1.1",
    description="Manifest-driven Hugging Face upload/download CLI.",
    py_modules=["upload_to_hf"],
    install_requires=["huggingface_hub>=0.23.0"],
    entry_points={
        "console_scripts": [
            "hfsync=upload_to_hf:main",
        ]
    },
)
