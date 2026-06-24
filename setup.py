from setuptools import setup, find_packages

setup(
    name="nabdcode",
    version="0.1.0",
    description="NabdCode CLI - Agentic OS for Code Generation and Management",
    author="Ammar Mohammed",
    packages=find_packages(),
    py_modules=["main"], # لأن ملف main.py موجود في المسار الرئيسي
    install_requires=[
        "rich",
        "python-dotenv",
        "openai",
        "anthropic",
        "arabic-reshaper",
        "python-bidi",
        "numpy",
        "beautifulsoup4",
        "toml",
    ],
    entry_points={
        "console_scripts": [
            # هذا السطر يربط الأمر 'nabdcode' بالدالة 'main' داخل ملف 'main.py'
            "nabdcode=main:main",
            "nabdcode-cli=main:main",
        ],
    },
    python_requires=">=3.8",
)
