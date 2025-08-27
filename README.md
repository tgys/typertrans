# TyperTRS

## Overview

TyperTRS is an educational typing practice application written in Python that allows users to practice typing with children's books. The application downloads text from various sources, processes it for typing practice, and provides an interactive terminal-based typing interface (and you can also add your own books in the downloads folder).

## Architecture

The project is organized into several key modules:

### Core Components

1. **Typing Practice (`typing_practice.py`)** - The interactive typing practice interface
2. **Archive Downloader (`archive_downloader.py`)** - Downloads and processes books from various sources
3. **Claude Client (`claude_client.py`)** - Integrates with Claude AI API for book title generation
4. **Configuration (`config.py`)** - UI management and application configuration
5. **Network Utilities (`network_utils.py`)** - VPN and network connectivity management
6. **Authentication (`auth.py`)** - API key and credential management
7. **Caching System (`wasabi_cache.py`)** - Distributed caching (for titles with download failures) using Wasabi S3-compatible storage

### Supporting Modules

- **Language Utilities (`language_utils.py`)** - Multilingual support and text processing

## Key Features

### 1. Book Discovery and Download
- Uses Claude AI API to generate relevant children's book titles in 20+ languages
- Downloads content from Internet Archive and other sources
- Implements OCR capabilities for PDF text extraction (with fallback methods)
- Intelligent caching system to avoid re-attempting failed downloads

### 2. Caching Strategy
- **Local Cache**: Tracks processed titles and failed downloads locally
- **Distributed Cache**: Uses Wasabi object storage for sharing failed download attempts across instances
- **Smart Filtering**: Avoids re-downloading previously processed or failed titles

### 3. Multilingual Support
- Supports 20 languages including French, Spanish, German, Italian, Portuguese, Russian, Chinese, Japanese, Korean, Arabic, Dutch, Swedish, Norwegian, Danish, Finnish, Polish, Czech, Hungarian, Turkish, and Greek
- Language-specific text processing and validation
- Fuzzy translation matching for typing practice

### 4. Interactive Typing Practice
- Terminal-based UI with color-coded feedback
- Real-time typing accuracy tracking
- Progress indicators and statistics
- Mouse and keyboard navigation support
- Scrollable interface with vim-style navigation

### 5. Network and Security Features
- VPN integration for accessing geo-restricted content
- Secure credential management with local caching
- SSL certificate handling for various download sources

## Technical Implementation

### Dependencies
- **Core**: Python 3.8+, curses, requests, beautifulsoup4
- **OCR**: pytesseract, pdf2image, opencv-python, pillow, numpy
- **Translation**: argostranslate, langdetect, python-Levenshtein
- **Cloud Storage**: boto3, wasabi (for caching)
- **Network**: httpx, socksio (for advanced HTTP handling)

### File Organization
```
typertrs/
├── typertrs/           # Main package
├── typertrs_2/         # Version 2 (development)
├── typertrs_3/         # Version 3 (latest)
├── mono_typertrs/      # Monolithic version with additional tools
├── downloads/          # Downloaded content storage
└── *.md files         # Feature documentation and fixes
```

### Configuration
- Uses temporary file caching for credentials
- Downloads stored in `~/Downloads/children_books/[language]/`
- Logging with timestamped entries and file-based search logs
- Configurable through environment variables and cached settings

## Recent Improvements

Based on the documentation files, recent enhancements include:
- Fixed Ctrl+N duplication issues in typing interface
- Improved mouse scroll support and scrollbar interaction  
- Enhanced translation accuracy with fuzzy matching
- Better OCR availability detection and fallback handling
- Flatpak packaging support for Linux distributions
- Improved content filtering and word count validation

## How to Run TyperTRS

### Prerequisites

#### NixOS/Nix Users (Recommended)
If you're using NixOS or have Nix installed, you can use the provided flake for the easiest setup:

```bash
# Clone the repository
git clone <repository-url>
cd typertrs

# Option 1: Enter development shell with all dependencies
nix develop

# Option 2: Build and run directly
nix run

# Option 3: Build the package
nix build
```

The flake.nix automatically handles all Python dependencies, OCR libraries, and system packages.

#### Apt-based Installation
1. **Python 3.8+** with pip
2. **System dependencies** for OCR:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr poppler-utils
   
   # macOS
   brew install tesseract poppler
   
   # Fedora/RHEL
   sudo dnf install tesseract poppler-utils
   ```

#### For NixOS/Nix Users
```bash
git clone <repository-url>
cd typertrs
nix develop  # This provides all dependencies
python -m typertrs
```

#### For Other Systems
1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd typertrs
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   # Method 1: Direct execution
   python -m typertrs
   
   # Method 2: Using the run script
   ./typertrs-run
   
   # Method 3: After pip install
   pip install -e .
   typertrs
   ```

### Quick Start
1. Launch TyperTRS from your terminal
2. Navigate the main menu using arrow keys
3. Select "Start Download Process" to get books
4. Choose your preferred language
5. Wait for books to download and process
6. Select "Typing Practice" to start practicing
7. Use j/k keys or arrow keys to scroll through logs

### Adding Your Own Books
You can add your own text files to practice with:
```bash
mkdir -p ~/Downloads/children_books/English
cp your_book.txt ~/Downloads/children_books/English/
```

## Demo Videos (with random text downloaded by ai)

### Typing Practice Session
![Typing Practice Demo](recording.gif)
*Live typing practice session showing color-coded feedback, accuracy tracking, and progress indicators.*

### Typing Practice Session
![Typing Practice Demo 2](recording2.gif)
*Live typing practice session showing color-coded feedback, accuracy tracking, and progress indicators.*
