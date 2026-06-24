# ⚡ NabdCode CLI Agent OS ⚡

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**NabdCode CLI Agent OS** is a highly modular, safe, and bilingual (Arabic & English) autonomous coding assistant operating directly from your command line. Built on top of a custom zero-dependency **ReAct (Reasoning and Action) loop**, NabdCode integrates real-time codebase indexing (RAG), sqlite3 conversation logging, local fallback mechanisms, and sophisticated Terminal-based Arabic rendering.

---

## 🗺️ جدول المحتويات / Table of Contents
* [الميزات الأساسية / Core Features](#-الميزات-الأساسية--core-features)
* [البنية الهندسية للنظام / System Architecture](#-البنية-الهندسية-للنظام--system-architecture)
* [الأدوات المدمجة والمهارات / Built-in Tools](#-الأدوات-المدمجة-والمهارات--built-in-tools)
* [طريقة التثبيت والتشغيل / Installation & Setup](#-طريقة-التثبيت-والتشغيل--installation--setup)
* [أمثلة الاستخدام / Usage Examples](#-أمثلة-الاستخدام--usage-examples)

---

## 🚀 الميزات الأساسية / Core Features

*   **Offline-First Local Embedding (TF-IDF):** Generates local document embeddings and vocabulary databases from your source code using a custom TF-IDF model built entirely in Python. No external API key is needed for workspace semantic search.
*   **Bilingual Terminal Rendering (Arabic/English):** Solves the classic RTL text rendering issue on terminal consoles by integrating `arabic-reshaper` and `python-bidi`. Text streams dynamically with connected letters and proper reading direction.
*   **Zero-Tier Edge AI Fallback:** Checks local environments (Ollama) on boot. If active, it routes requests locally to avoid cloud latency and costs. If down, it cascades gracefully to primary providers, and then to a scraped pool of free backup APIs.
*   **Safe Execution Loop:** Prompts the developer with interactive visual plans for approval before mutating files or running shell scripts. Can be configured to run continuously with `--auto` mode.

---

## 🏛️ البنية الهندسية للنظام / System Architecture

```text
                               ┌───────────────────┐
                               │     CLI Input     │
                               └─────────┬─────────┘
                                         ▼
                               ┌───────────────────┐
                               │    NabdAgent      │◄────► [SQLite Message History]
                               └────┬─────────┬────┘
                                    │         │
            ┌───────────────────────┘         └────────────────────────┐
            ▼                                                          ▼
  [Local Vector Memory]                                         [LLM Client Engine]
  ├── Chunker (Text sliding)                                    ├── Zero-Tier: Local Ollama
  ├── Embedder (Custom local TF-IDF)                            ├── Primary Tier: OpenAI / Anthropic
  └── CodeIndexer (AST/Regex multi-language)                    └── Tertiary Tier: Scraped Free APIs Fallbacks
        (Python, Rust, Java, Kotlin, C++)
```

1.  **NabdAgent Core (`core/agent.py`):** Drives the loop. It handles user inputs, retrieves relevant code blocks from vector memory, structures system prompts based on task states (Planning, Executing), and safely routes tool calls with recursion depth limits (Circuit Breaker).
2.  **Vector DB & Indexer (`memory/`):** Splits files into overlapping chunks, tokenizes keywords, builds an IDF vocabulary from the project corpus, and performs local **Cosine Similarity** searches over `.nabd_vectors.json`. Supports full AST/Regex struct parsers for:
    *   **Python:** Built-in `ast.parse` syntax tree traversal.
    *   **Rust:** Struct, Enum, Trait, and function extracting patterns.
    *   **Kotlin & Java:** Static package, interface, class, and method parsers.
    *   **C++ & C:** Complex header and object implementation scanners.
3.  **Bilingual Console UI (`ui/console.py`):** Uses Rich's `Live` update loops for smooth, beautiful, and color-coded streaming. All Arabic outputs are reshaped and bidirectionalized on-the-fly for terminal consistency.

---

## 🛠️ الأدوات المدمجة والمهارات / Built-in Tools

NabdCode ships with highly tailored developer tools, all registered dynamically in the `ToolRegistry`:

*   **`design_taste` (DesignTasteTool):** Returns detailed UI/UX rules, Tailwind CSS primitive layouts, sophisticated color palettes (Slate, Emerald), typography hierarchies, and Soft Shadow aesthetics to keep your interfaces clean.
*   **`byox` (BuildYourOwnXTool):** Contains comprehensive, step-by-step code templates and engineering guidelines to build core systems from scratch (e.g., custom Git repositories, relational B-Tree databases, key-value Redis socket servers, or Linux Namespaces-based Docker containerizers).
*   **`agora` (AgoraTool):** Connects to `WebSearchTool` to look up active developer discussions and consensus on Hacker News or Reddit (`site:news.ycombinator.com OR site:reddit.com/r/programming`), falling back to a structured offline debate model if the machine is disconnected.
*   **`karpathy_skills` (KarpathySkillsTool):** Retrieves raw, low-dependency AI and deep learning architectural patterns (attention, nanoGPT, micrograd backpropagation) directly from local knowledge bases.
*   **`free_llm_apis` (FreeLLMAPIsTool):** Automatically scrapes and caches free OpenAI-compatible API providers as fallback routes.
*   **`file_tool` & `bash`:** Safe read/write/edit commands and terminal execution blocks.

---

## 📦 طريقة التثبيت والتشغيل / Installation & Setup

### 1. المتطلبات الأساسية / Prerequisites
Ensure you have Python 3.8+ installed on your computer.

### 2. التثبيت / Installation
Clone the repository and install it locally in editable mode:
```bash
git clone https://github.com/amiraq1/nabdcode-cli.git
cd nabdcode-cli
pip install -e .
```

### 3. إعداد البيئة / Environment Configuration
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Fill in your API keys (optional, as NabdCode operates locally with Ollama out-of-the-box):
```env
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

---

## 💡 أمثلة الاستخدام / Usage Examples

### الوضع التفاعلي / Interactive Mode (Default)
Launch NabdCode's retro cyberpunk developer workspace:
```bash
nabdcode
```

### وضعية التشغيل المستقل / Headless Task Execution
Execute a direct, non-interactive programming task and output results to a file:
```bash
nabdcode --headless --task "اكتب دالة بايثون سريعة لحساب فيبوناتشي مع كتابة اختبارات أحادية" --out fibonacci.py
```

### التشغيل الذاتي / Continuous Autonomous Execution
Run without requiring human confirmation blocks before executing safe bash or file actions:
```bash
nabdcode --auto
```

---

## 📄 الترخيص / License
This project is licensed under the MIT License - see the LICENSE file for details.
All clean-code practices are modeled under `taste.md`. Made with ⚡ for developers.