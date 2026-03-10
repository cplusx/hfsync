from setuptools import setup


setup(
    name="huggingfacesync",
    version="0.1.3",
    description="Manifest-driven Hugging Face upload/download CLI.",
    py_modules=["upload_to_hf"],
    install_requires=["huggingface_hub>=0.23.0"],
    entry_points={
        "console_scripts": [
            "huggingfacesync=upload_to_hf:main",
            "hfsync=upload_to_hf:main",
        ]
    },
)
