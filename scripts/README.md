# 📚 MkDocs Development Guide

This guide helps you work with MkDocs documentation locally for the Memori SDK project.

## 🚀 Quick Start

### Option 1: Automated Script (Recommended)

```bash
# Quick start - installs dependencies and starts dev server
python scripts/docs_dev.py

# Or use the convenience scripts:
./scripts/docs.sh          # macOS/Linux
scripts/docs.bat           # Windows
```

### Option 2: Manual Setup

```bash
# Install dependencies
pip install mkdocs mkdocs-material mkdocs-minify-plugin

# Start development server
mkdocs serve
```

## 🛠️ Available Commands

### Using `docs_dev.py`:

```bash
# Start development server (default)
python scripts/docs_dev.py
python scripts/docs_dev.py --serve

# Install dependencies only
python scripts/docs_dev.py --install-only

# Build documentation
python scripts/docs_dev.py --build

# Check for issues
python scripts/docs_dev.py --check

# Show statistics
python scripts/docs_dev.py --stats

# Clean build files
python scripts/docs_dev.py --clean

# Custom server options
python scripts/docs_dev.py --serve --port 8080 --host 0.0.0.0 --no-browser
```

### Direct MkDocs commands:

```bash
mkdocs serve                # Start dev server
mkdocs build               # Build static site
mkdocs build --clean       # Clean build
mkdocs build --strict      # Fail on warnings
```

## 📁 Project Structure

```
memori/
├── scripts/
│   ├── docs_dev.py        # 🔧 Automated development helper
│   ├── docs.sh           # 🍎 macOS/Linux script
│   └── docs.bat          # 🪟 Windows script
├── mkdocs.yml            # ⚙️ MkDocs configuration
├── docs/                 # 📝 Documentation source
│   ├── index.md          # 🏠 Homepage
│   ├── examples/         # 📋 Example integrations
│   ├── api/             # 🔌 API documentation
│   └── guides/          # 📖 User guides
├── site/                # 🏗️ Generated static site (local only)
└── .github/
    └── workflows/
        └── docs-generation.yml  # 🤖 Auto-generates example docs
```

## 🎯 Workflow

### 1. **Local Development**
```bash
# Start the dev server
python scripts/docs_dev.py

# Edit your markdown files in docs/
# Changes are automatically reloaded
# View at http://localhost:8000
```

### 2. **Testing Before Publishing**
```bash
# Build and validate
python scripts/docs_dev.py --build

# Check for issues
python scripts/docs_dev.py --check

# Review the built site in site/ folder
```

### 3. **Publishing to Lovable**
- After local testing is complete
- Manually publish to Lovable platform
- No automatic GitHub Pages deployment

## 🔧 Features of `docs_dev.py`

### ✨ **Auto-Dependency Installation**
- Automatically detects missing packages
- Installs required MkDocs dependencies
- Handles version constraints

### 🔍 **Validation & Checking**
- Validates MkDocs configuration
- Checks for missing images
- Detects broken internal links
- Shows documentation statistics

### 📊 **Statistics & Reporting**
- Word count and file statistics
- Build validation reports
- Issue detection and reporting

### 🎨 **User Experience**
- Colored terminal output
- Progress indicators
- Clear error messages
- Automatic browser opening

## 🧩 Dependencies

The script automatically installs these packages:

```
mkdocs>=1.5.0                                    # Core MkDocs
mkdocs-material>=9.0.0                          # Material theme
mkdocs-minify-plugin>=0.7.0                     # HTML/CSS/JS minification
pymdown-extensions>=10.0.0                      # Enhanced Markdown
mkdocs-git-revision-date-localized-plugin>=1.2.0  # Git modification dates
mkdocstrings[python]>=0.24.0                    # Python API documentation
mkdocs-autorefs>=0.5.0                          # Cross-references
```

## 🚨 Troubleshooting

### **Port Already in Use**
```bash
# Use a different port
python scripts/docs_dev.py --port 8080
```

### **Permission Issues**
```bash
# On macOS/Linux
chmod +x scripts/docs_dev.py scripts/docs.sh

# On Windows - run as Administrator if needed
```

### **Python Not Found**
```bash
# Try with python instead of python3
python scripts/docs_dev.py

# Or install Python from https://python.org/
```

### **Module Import Errors**
```bash
# Force reinstall dependencies
python scripts/docs_dev.py --install-only
```

## 📝 Writing Documentation

### **File Organization**
```
docs/
├── index.md              # Homepage - project overview
├── getting-started.md    # Installation and quick start
├── examples/             # Integration examples
│   ├── openai-integration.md
│   ├── litellm-integration.md
│   └── custom-integration.md
├── api/                  # API reference
│   ├── memory-client.md
│   ├── storage.md
│   └── utilities.md
└── guides/               # How-to guides
    ├── configuration.md
    ├── best-practices.md
    └── troubleshooting.md
```

### **Markdown Tips**
```markdown
# Use headers for navigation
## This creates table of contents

# Add code blocks with syntax highlighting
```python
from memori import MemoryClient
client = MemoryClient()
```

# Add admonitions for important info
!!! tip "Pro Tip"
    This is a helpful tip!

!!! warning "Important"
    Pay attention to this!

# Link to other pages
[See API Reference](api/memory-client.md)
```

## 🔄 CI/CD Integration

- **docs-generation.yml** automatically generates documentation for new example files
- Updates `mkdocs.yml` navigation
- But does **NOT** deploy to GitHub Pages
- You control what gets published to Lovable

## 💡 Tips

1. **Live Reload**: Changes to `.md` files are automatically reloaded
2. **Fast Builds**: Use `--no-strict` for faster development builds
3. **Mobile Testing**: Use `--host 0.0.0.0` to test on mobile devices
4. **Custom Themes**: Modify `mkdocs.yml` to customize appearance
5. **SEO**: Add meta descriptions and titles in frontmatter

## 📞 Need Help?

- Check `python scripts/docs_dev.py --help` for all options
- Review `mkdocs.yml` for configuration
- MkDocs documentation: https://mkdocs.org/
- Material theme: https://squidfunk.github.io/mkdocs-material/