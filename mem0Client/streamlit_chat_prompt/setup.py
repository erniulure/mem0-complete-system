from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))

setup(
    name="streamlit_chat_prompt",
    version="1.0.0",
    author="AI Memory System",
    author_email="ai@memory.system",
    description="A Streamlit component for chat input with clipboard paste support",
    long_description="A custom Streamlit component that provides chat-like input with support for pasting images from clipboard using Ctrl+V",
    long_description_content_type="text/markdown",
    url="https://github.com/ai-memory-system/streamlit-chat-prompt",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "streamlit_chat_prompt": [
            "frontend/build/*",
            "frontend/build/**/*",
            "frontend/build/**/**/*",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "streamlit>=1.28.0",
        "pydantic>=2.0.0",
    ],
)
