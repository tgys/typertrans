#!/usr/bin/env python3
"""
Internet Archive downloader and text extraction for TyperTRS
Based on typerai.py functionality
"""

import os
import requests
import json
import time
import glob
import tempfile
import warnings
from urllib.parse import quote, urljoin
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Tuple
from difflib import SequenceMatcher
import re
import sys
import os

# Import content validator and Wasabi cache
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from content_validator import validate_childrens_book_content, ChildrensBookValidator
from .wasabi_cache import WasabiFailedTitlesCache

# Suppress SSL warnings from appearing in console/UI
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# OCR library availability flags (following typerai.py pattern)
ADVANCED_OCR_AVAILABLE = False
BASIC_OCR_AVAILABLE = False
OCR_IMPORT_ERROR = "Not tested yet"

try:
    # Try advanced OCR with numpy and OpenCV
    import numpy as np
    import cv2
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    # Test PIL import by trying to access _imaging
    try:
        from PIL import _imaging
    except ImportError:
        raise ImportError("PIL _imaging module not available")
    ADVANCED_OCR_AVAILABLE = True
    OCR_IMPORT_ERROR = None
except ImportError as e:
    # Parse specific error types for better messages
    error_msg = str(e)
    if "libstdc++" in error_msg:
        parsed_error = "Missing system libraries (libstdc++.so.6) - OCR requires additional system dependencies"
    elif "numpy from its source directory" in error_msg or "numpy source tree" in error_msg:
        parsed_error = "NumPy environment issue - likely missing system dependencies (libstdc++.so.6 or similar)"
    elif "No module named" in error_msg:
        parsed_error = f"Missing Python packages: {error_msg}"
    else:
        parsed_error = str(e)
    
    OCR_IMPORT_ERROR = f"Advanced OCR: {parsed_error}"
    
    try:
        # Try basic OCR without numpy/OpenCV
        from pdf2image import convert_from_path
        import pytesseract
        from PIL import Image
        # Test PIL import by trying to access _imaging
        try:
            from PIL import _imaging
        except ImportError:
            raise ImportError("PIL _imaging module not available")
        BASIC_OCR_AVAILABLE = True
        OCR_IMPORT_ERROR = f"Advanced OCR: {parsed_error}, but Basic OCR available"
    except ImportError as e2:
        error_msg2 = str(e2)
        if "libstdc++" in error_msg2:
            parsed_error2 = "Missing system libraries - OCR requires additional system dependencies"
        elif "No module named" in error_msg2:
            parsed_error2 = f"Missing Python packages: {error_msg2}"
        else:
            parsed_error2 = str(e2)
        OCR_IMPORT_ERROR = f"Advanced OCR: {parsed_error}, Basic OCR: {parsed_error2}"

OCR_DEPENDENCIES_AVAILABLE = ADVANCED_OCR_AVAILABLE or BASIC_OCR_AVAILABLE


# Title-Content Matching Functions
def calculate_title_similarity(expected_title: str, content: str) -> float:
    """Calculate similarity between expected title and actual content"""
    if not expected_title or not content:
        return 0.0
    
    # Normalize titles for comparison
    title_words = set(re.findall(r'\w+', expected_title.lower()))
    content_lower = content.lower()
    
    # Count direct word matches
    direct_matches = sum(1 for word in title_words if word in content_lower)
    title_word_match_ratio = direct_matches / len(title_words) if title_words else 0.0
    
    # Use sequence matching for overall similarity
    sequence_similarity = SequenceMatcher(None, expected_title.lower(), content[:500].lower()).ratio()
    
    # Combined score weighted toward direct word matches
    return (title_word_match_ratio * 0.7) + (sequence_similarity * 0.3)


def get_expected_content_keywords(title: str, language: str = "german") -> List[str]:
    """Get expected keywords for known children's books"""
    title_lower = title.lower()
    
    # German children's books keywords
    if language.lower() == "german":
        known_books = {
            "das kleine gespenst": ["gespenst", "spuk", "schloss", "burg", "geist", "mitternacht", "uhr"],
            "das kleine ich bin ich": ["ich bin ich", "identität", "tier", "suche", "wer bin ich", "patchwork"],
            "der struwwelpeter": ["struwwelpeter", "peter", "haare", "nägel", "kinder", "daumen", "suppenkaspar"],
            "die kleine dame": ["dame", "eleganz", "fein", "vornehm", "manieren"],
            "die kleine hexe": ["hexe", "zaubern", "zauber", "besen", "kessel", "magie", "abraxas"],
            "heidi": ["heidi", "alpen", "berg", "großvater", "almöhi", "ziegen", "schweiz", "clara"],
            "max und moritz": ["max", "moritz", "streiche", "wilhelm busch", "zwei buben", "witwe bolte"],
            "momo": ["momo", "zeit", "graue herren", "schildkröte", "kassiopeia", "beppo", "gigi", "stundenblumen"]
        }
        
        # Find matching book
        for book_title, keywords in known_books.items():
            if book_title in title_lower or any(word in title_lower for word in book_title.split()):
                return keywords
    
    # Default keywords from title
    return re.findall(r'\w+', title.lower())


def validate_content_length(content: str) -> Tuple[bool, str]:
    """Validate that content has minimum character count"""
    if not content:
        return False, "No content to validate"
    
    # Count characters
    char_count = len(content.strip())
    
    # Only filter by minimum character count
    if char_count < 2000:
        return False, f"Content too short ({char_count} characters, minimum 2000)"
    
    return True, f"Content acceptable ({char_count} characters)"


def score_search_result(result: Dict, expected_title: str, language: str) -> float:
    """Score a search result based on title similarity and metadata"""
    if not result or not result.get('title'):
        return 0.0
    
    result_title = result['title']
    identifier = result.get('identifier', '')
    
    # Base title similarity
    title_similarity = SequenceMatcher(None, expected_title.lower(), result_title.lower()).ratio()
    
    # Boost for exact word matches
    expected_words = set(re.findall(r'\w+', expected_title.lower()))
    result_words = set(re.findall(r'\w+', result_title.lower()))
    word_overlap = len(expected_words.intersection(result_words)) / len(expected_words) if expected_words else 0
    
    # Final score based only on title similarity and word overlap
    score = (title_similarity * 0.5) + (word_overlap * 0.5)
    return max(0.0, min(1.0, score))  # Clamp between 0 and 1


def search_internet_archive(session: requests.Session, title: str, language: str = None, ui=None):
    """Search Internet Archive for book titles with improved ranking"""
    # Try multiple search strategies
    search_strategies = [
        title,  # Exact title
        f'"{title}"',  # Quoted exact title
        title.replace(' ', ' AND '),  # AND search
    ]
    
    if language:
        # Add language variants
        search_strategies.extend([
            f"{title} {language}",
            f'"{title}" {language}',
        ])
    
    all_results = []
    
    for search_query in search_strategies[:3]:  # Try top 3 strategies
        if ui:
            ui.log_to_file_only(f"🔍 Trying search: {search_query}")
        
        # Internet Archive search endpoint
        url = f"https://archive.org/advancedsearch.php?q={quote(search_query)}&fl=identifier,title,creator,date,language,mediatype&rows=20&page=1&output=json"
        
        try:
            # Add better headers to avoid 403 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            # Add small delay to avoid rate limiting
            time.sleep(1)
            r = session.get(url, headers=headers, timeout=30, verify=False)
            r.raise_for_status()
            data = r.json()
            
            if 'response' in data and 'docs' in data['response']:
                docs = data['response']['docs']
                
                for doc in docs:
                    identifier = doc.get('identifier')
                    doc_title = doc.get('title', [''])[0] if isinstance(doc.get('title'), list) else doc.get('title', '')
                    mediatype = doc.get('mediatype', [''])[0] if isinstance(doc.get('mediatype'), list) else doc.get('mediatype', '')
                    creator = doc.get('creator', [''])[0] if isinstance(doc.get('creator'), list) else doc.get('creator', '')
                    
                    # Filter for books/texts
                    if identifier and mediatype in ['texts', 'data'] and doc_title:
                        result = {
                            'url': f"https://archive.org/details/{identifier}",
                            'title': doc_title,
                            'identifier': identifier,
                            'creator': creator,
                            'search_query': search_query
                        }
                        
                        # Calculate relevance score
                        result['score'] = score_search_result(result, title, language or "")
                        all_results.append(result)
                        
        except Exception as e:
            if ui:
                ui.log_to_file_only(f"⚠️ Search strategy '{search_query}' failed: {e}")
            continue
    
    # Remove duplicates based on identifier
    seen_identifiers = set()
    unique_results = []
    for result in all_results:
        if result['identifier'] not in seen_identifiers:
            seen_identifiers.add(result['identifier'])
            unique_results.append(result)
    
    # Sort by relevance score (highest first)
    unique_results.sort(key=lambda x: x['score'], reverse=True)
    
    if ui and unique_results:
        ui.log_to_file_only(f"📊 Found {len(unique_results)} results, top scores:")
        for i, result in enumerate(unique_results[:5]):
            ui.log_to_file_only(f"  {i+1}. {result['title'][:50]}... (score: {result['score']:.2f})")
    
    return unique_results


def find_pdf_download_url(session: requests.Session, url: str, title: str, ui=None) -> Optional[str]:
    """Find the PDF download URL from a book page URL"""
    try:
        # Get the book page  
        r = session.get(url, timeout=30, verify=False)
        r.raise_for_status()
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Check if the page contains 'comic' or 'newspaper' keywords
        page_text = soup.get_text().lower()
        if 'comic' in page_text or 'newspaper' in page_text:
            if ui:
                ui.log_to_file_only(f"⚠️ Skipping {title} - contains comic/newspaper content")
            return None
        
        download_links = soup.find_all("a", href=True)
        
        # Look for links that end with .pdf
        for link in download_links:
            href = link.get("href")
            
            # Check if the href ends with .pdf
            if href and href.lower().endswith('.pdf'):
                download_url = urljoin(url, href)
                return download_url
        
        return None

    except Exception as e:
        if ui:
            ui.log(f"❌ PDF link search failed: {e}")
        return None


def download_pdf(session: requests.Session, pdf_url: str, title: str, download_dir: str, ui=None) -> Optional[str]:
    """Download PDF file and return local path"""
    try:
        if ui:
            ui.log(f"📥 Downloading PDF: {title}")
        
        # Create safe filename first
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:100]  # Limit length
        fname = f"{safe_title}.pdf"
        path = os.path.join(download_dir, fname)
        
        # Ensure directory exists
        os.makedirs(download_dir, exist_ok=True)
        
        # Get file size for progress tracking
        try:
            head_response = session.head(pdf_url, timeout=10, verify=False)
            total_size = int(head_response.headers.get('content-length', 0))
        except:
            total_size = 0
        
        # Stream download with progress updates
        with session.get(pdf_url, timeout=60, verify=False, stream=True) as pdf_response:
            pdf_response.raise_for_status()
            
            downloaded = 0
            chunk_size = 8192  # 8KB chunks
            
            with open(path, "wb") as f:
                for chunk in pdf_response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Update progress bar if UI available and we know total size
                        if ui and total_size > 0:
                            ui.show_progress(downloaded, total_size, title, "Downloading PDF")
                        elif ui:
                            # Show indeterminate progress if size unknown
                            ui.show_progress(downloaded // 1024, 0, title, f"Downloading PDF ({downloaded // 1024}KB)")
            
            # Show completion progress
            if ui and total_size > 0:
                ui.show_progress(total_size, total_size, title, "Download complete")
        
        # Validate file size
        if os.path.getsize(path) < 1024:  # Less than 1KB
            os.remove(path)
            if ui:
                ui.log(f"❌ Downloaded file too small, removed: {path}")
            return None
        
        if ui:
            ui.log(f"✅ Downloaded PDF: {path}")
        return path

    except Exception as e:
        if ui:
            ui.log(f"❌ PDF download failed: {e}")
        return None


def filter_text_by_language(text: str, target_language: str, ui=None) -> str:
    """Filter text to keep only content in the target language"""
    try:
        # Try to import langdetect
        from langdetect import detect, LangDetectException
    except ImportError:
        if ui:
            ui.log_to_file_only("⚠️ langdetect not available - skipping language filtering")
        return text
    
    if not text or not target_language:
        return text
    
    # Map language names to langdetect codes
    language_map = {
        'French': 'fr', 'Spanish': 'es', 'German': 'de', 'Italian': 'it',
        'Portuguese': 'pt', 'Russian': 'ru', 'Chinese': 'zh', 'Japanese': 'ja',
        'Korean': 'ko', 'Arabic': 'ar', 'Dutch': 'nl', 'Swedish': 'sv',
        'Norwegian': 'no', 'Danish': 'da', 'Finnish': 'fi', 'Polish': 'pl',
        'Czech': 'cs', 'Hungarian': 'hu', 'Turkish': 'tr', 'Greek': 'el'
    }
    
    target_code = language_map.get(target_language, 'en')
    
    # Split text into paragraph blocks
    paragraphs = text.split('\n\n')
    filtered_paragraphs = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        
        # Keep short blocks (likely headers, titles, page numbers)
        if len(paragraph) < 100:
            filtered_paragraphs.append(paragraph)
            continue
        
        try:
            detected_lang = detect(paragraph)
            # Handle Chinese language variants
            if target_code == 'zh' and detected_lang in ['zh-cn', 'zh']:
                filtered_paragraphs.append(paragraph)
            elif detected_lang == target_code:
                filtered_paragraphs.append(paragraph)
            # Conservative approach - keep paragraph if detection is uncertain
        except LangDetectException:
            # If language detection fails, keep the paragraph
            filtered_paragraphs.append(paragraph)
    
    filtered_text = '\n\n'.join(filtered_paragraphs)
    
    if ui and len(filtered_text) != len(text):
        removed = len(text) - len(filtered_text)
        ui.log_to_file_only(f"📝 Language filtering removed {removed} characters")
    
    return filtered_text


def has_meaningful_content(text: str) -> bool:
    """Check if text has meaningful content"""
    if not text or len(text.strip()) < 100:
        return False
    
    # Count alphabetic characters
    alpha_chars = sum(1 for c in text if c.isalpha())
    alpha_ratio = alpha_chars / len(text) if text else 0
    
    # Must have at least 40% alphabetic characters
    if alpha_ratio < 0.4:
        return False
    
    # Must have at least 10 words
    words = text.split()
    if len(words) < 10:
        return False
    
    return True


def extract_text_from_pdf(pdf_path: str, title: str, ui=None) -> Optional[str]:
    """Extract text from PDF using multiple methods (following typerai.py pattern)"""
    if not os.path.exists(pdf_path):
        return None
    
    # Log OCR availability status
    if ui and OCR_IMPORT_ERROR:
        ui.log_to_file_only(f"OCR Status: {OCR_IMPORT_ERROR}")
    
    text_content = None
    extraction_method = "unknown"
    
    # Check OCR availability and use appropriate method
    # Check environment variable to determine OCR preference
    use_advanced_ocr = os.getenv('USE_ADVANCED_OCR', 'true').lower() == 'true'
    
    if not OCR_DEPENDENCIES_AVAILABLE:
        if ui:
            ui.log(f"⚠️ OCR libraries not available: {OCR_IMPORT_ERROR}")
            ui.log(f"🔍 Trying pdftotext extraction: {title}")
    else:
        # Use OCR-based extraction based on environment variable preference
        if not use_advanced_ocr and BASIC_OCR_AVAILABLE:
            if ui:
                ui.log(f"🔍 Extracting text using basic OCR: {title}")
            text_content = extract_with_basic_ocr(pdf_path, ui)
            if text_content:
                extraction_method = "basic_ocr"
        elif use_advanced_ocr and ADVANCED_OCR_AVAILABLE:
            if ui:
                ui.log(f"🔍 Extracting text using advanced OCR: {title}")
            text_content = extract_with_advanced_ocr(pdf_path, ui)
            if text_content:
                extraction_method = "advanced_ocr"
    
    # Fallback to pdftotext if OCR failed or not available
    if not text_content:
        try:
            import subprocess
            
            if ui:
                ui.log(f"🔍 Extracting text using pdftotext: {title}")
            
            # Use pdftotext command
            result = subprocess.run(['pdftotext', pdf_path, '-'], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                text_content = result.stdout
                extraction_method = "pdftotext"
        
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            if ui:
                ui.log(f"⚠️ pdftotext failed: {e}")
    
    # Final fallback to PyPDF2
    if not text_content:
        try:
            import PyPDF2
            
            if ui:
                ui.log(f"🔍 Extracting text using PyPDF2: {title}")
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                extracted_text = ""
                
                # Extract from first 5 pages
                for page_num in range(min(5, len(pdf_reader.pages))):
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    extracted_text += f"\n=== PAGE {page_num + 1} ===\n{page_text}\n"
                
                if extracted_text.strip():
                    text_content = extracted_text
                    extraction_method = "pypdf2"
        
        except ImportError:
            if ui:
                ui.log("⚠️ PyPDF2 not available")
        except Exception as e:
            if ui:
                ui.log(f"⚠️ PyPDF2 extraction failed: {e}")
    
    if text_content:
        if ui:
            ui.log(f"✅ Text extracted using {extraction_method}: {len(text_content)} characters")
        return text_content
    else:
        if ui:
            ui.log(f"❌ Failed to extract text from: {title}")
        return None


def extract_with_advanced_ocr(pdf_path: str, ui=None) -> Optional[str]:
    """Extract text using advanced OCR with image preprocessing"""
    if not ADVANCED_OCR_AVAILABLE:
        return None
    
    try:
        # Convert PDF to images (first 5 pages only for speed)
        pages = convert_from_path(pdf_path, first_page=1, last_page=5, dpi=300)
        
        extracted_text = ""
        for page_num, page in enumerate(pages):
            # Convert PIL image to numpy array
            img_array = np.array(page)
            
            # Convert to grayscale
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            # Apply Gaussian blur
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply adaptive thresholding
            thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Convert back to PIL Image
            processed_image = Image.fromarray(thresh)
            
            # Extract text using Tesseract
            page_text = pytesseract.image_to_string(processed_image, lang='eng')
            extracted_text += f"\n=== PAGE {page_num + 1} ===\n{page_text}\n"
        
        return extracted_text if extracted_text.strip() else None
        
    except Exception as e:
        if ui:
            ui.log(f"⚠️ Advanced OCR processing failed: {e}")
        return None


def extract_with_basic_ocr(pdf_path: str, ui=None) -> Optional[str]:
    """Extract text using basic OCR without image preprocessing"""
    if not BASIC_OCR_AVAILABLE:
        return None
    
    try:
        # Convert PDF to images (first 5 pages)
        pages = convert_from_path(pdf_path, first_page=1, last_page=5, dpi=200)
        
        extracted_text = ""
        for page_num, page in enumerate(pages):
            page_text = pytesseract.image_to_string(page, lang='eng')
            extracted_text += f"\n=== PAGE {page_num + 1} ===\n{page_text}\n"
        
        return extracted_text if extracted_text.strip() else None
        
    except Exception as e:
        if ui:
            ui.log(f"⚠️ Basic OCR processing failed: {e}")
        return None


def process_book_download(session: requests.Session, title: str, language: str, download_dir: str, ui=None, failed_cache=None) -> bool:
    """Complete process: search -> find PDF -> download -> extract text with content validation"""
    try:
        # Check if title should be skipped due to previous failure
        if failed_cache and failed_cache.should_skip(title):
            return False
        # Step 1: Search Internet Archive with improved ranking
        search_results = search_internet_archive(session, title, language, ui)
        
        if not search_results:
            if ui:
                ui.log(f"❌ No search results for: {title}")
            # Add to failed cache - no search results
            if failed_cache:
                failed_cache.add_failed(title, "no_search_results")
            return False
        
        # Step 2: Try results in order of relevance score
        for i, result in enumerate(search_results[:5]):  # Try top 5 results
            if ui:
                ui.log_to_file_only(f"🔍 Trying result {i+1}: {result['title'][:50]}... (score: {result['score']:.2f})")
                ui.show_progress(0, 1, title, f"Checking result {i+1}")
            
            pdf_url = find_pdf_download_url(session, result['url'], title, ui)
            
            if pdf_url:
                if ui:
                    ui.show_progress(0, 1, title, "Downloading PDF")
                
                pdf_path = download_pdf(session, pdf_url, title, download_dir, ui)
                
                if pdf_path:
                    if ui:
                        ui.show_progress(0, 1, title, "Extracting text")
                    
                    # Step 3: Extract text from PDF
                    text_content = extract_text_from_pdf(pdf_path, title, ui)
                    
                    if text_content and len(text_content.strip()) > 100:
                        # Step 4: Filter text by language
                        if ui:
                            ui.show_progress(0, 1, title, "Filtering by language")
                        
                        filtered_text = filter_text_by_language(text_content, language, ui)
                        
                        # Step 5: Validate content type and meaningfulness
                        if not has_meaningful_content(filtered_text):
                            if ui:
                                ui.log_to_file_only(f"❌ Text lacks meaningful content: {result['title']}")
                            # Remove PDF and continue
                            try:
                                os.remove(pdf_path)
                            except:
                                pass
                            continue
                        
                        
                        # Step 6: Validate content length only
                        content_valid, validation_msg = validate_content_length(filtered_text)
                        if not content_valid:
                            if ui:
                                ui.log_to_file_only(f"❌ Content validation failed: {validation_msg}")
                            # Remove PDF and continue
                            try:
                                os.remove(pdf_path)
                            except:
                                pass
                            continue
                        
                        # Step 7: Validate title-content match (no content filtering)
                        is_valid, validation_reason, content_analysis = validate_childrens_book_content(
                            filtered_text, title, language
                        )
                        
                        if not is_valid:
                            if ui:
                                ui.log_to_file_only(f"❌ Title-content match failed: {validation_reason}")
                            # Remove PDF and continue
                            try:
                                os.remove(pdf_path)
                            except:
                                pass
                            continue
                        
                        # Step 8: Get additional similarity score for logging
                        similarity_score = calculate_title_similarity(title, filtered_text)
                        
                        if ui:
                            ui.log_to_file_only(f"✅ Title-content match validation passed")
                            ui.log_to_file_only(f"   Validation reason: {validation_reason}")
                            ui.log_to_file_only(f"   Additional similarity score: {similarity_score:.2f}")
                        
                        # Step 9: Save text file with enhanced metadata
                        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_title = safe_title.replace(' ', '_')[:100]
                        text_filename = f"{safe_title}_text.txt"
                        text_path = os.path.join(download_dir, text_filename)
                        
                        # Create text file with enhanced metadata including content validation
                        with open(text_path, 'w', encoding='utf-8') as f:
                            f.write(f"Title: {title}\n")
                            f.write(f"Source URL: {result['url']}\n")
                            f.write(f"PDF URL: {pdf_url}\n")
                            f.write(f"Extraction Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                            f.write(f"Search Score: {result['score']:.3f}\n")
                            f.write(f"Content Similarity: {similarity_score:.3f}\n")
                            f.write(f"Title-Content Match: PASSED\n")
                            f.write(f"Match Score: {content_analysis.child_friendly_score:.3f}\n")
                            f.write(f"Validation Method: Title matching only\n")
                            f.write(f"Archive Title: {result['title']}\n")
                            f.write(f"Creator: {result.get('creator', 'Unknown')}\n")
                            f.write("=" * 50 + "\n\n")
                            f.write(filtered_text)
                        
                        # Step 10: Clean up PDF file
                        try:
                            os.remove(pdf_path)
                            if ui:
                                ui.log(f"🗑️ Removed PDF file: {pdf_path}")
                        except:
                            pass
                        
                        if ui:
                            # Truncate title if too long to maintain column alignment
                            display_title = title[:40] + "..." if len(title) > 40 else title
                            ui.finish_progress(f"📄 {display_title} - extracted {len(filtered_text)} chars")
                        return True
                    else:
                        # Remove PDF if text extraction failed
                        try:
                            os.remove(pdf_path)
                        except:
                            pass
                        
                        if ui:
                            # Truncate title if too long to maintain column alignment
                            display_title = title[:50] + "..." if len(title) > 50 else title
                            ui.log(f"❌ Text extraction failed for: {display_title}")
        
        if ui:
            # Truncate title if too long to maintain column alignment
            display_title = title[:50] + "..." if len(title) > 50 else title
            ui.finish_progress(f"❌ No PDF found for: {display_title}")
        # Add to failed cache - no PDF found
        if failed_cache:
            failed_cache.add_failed(title, "no_pdf_found")
        return False
        
    except Exception as e:
        if ui:
            # Truncate title if too long to maintain column alignment
            display_title = title[:50] + "..." if len(title) > 50 else title
            ui.log(f"❌ Error processing {display_title}: {e}")
        # Add to failed cache - general error
        if failed_cache:
            failed_cache.add_failed(title, f"error: {str(e)[:100]}")
        return False


def count_valid_text_files(directory: str) -> int:
    """Count valid text files in directory"""
    if not os.path.exists(directory):
        return 0
    
    count = 0
    pattern = os.path.join(directory, "*_text.txt")
    for file_path in glob.glob(pattern):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Check if file has meaningful content (similar to has_meaningful_text_content)
                if len(content.strip()) > 500:  # At least 500 chars
                    count += 1
        except:
            continue
    
    return count


def get_processed_titles(directory: str) -> set:
    """Get list of already processed titles"""
    processed_file = os.path.join(directory, "processed_titles.txt")
    processed_titles = set()
    
    if os.path.exists(processed_file):
        try:
            with open(processed_file, 'r', encoding='utf-8') as f:
                for line in f:
                    title = line.strip()
                    if title:
                        processed_titles.add(title.lower())
        except:
            pass
    
    return processed_titles


def save_processed_title(directory: str, title: str):
    """Save processed title to avoid reprocessing"""
    processed_file = os.path.join(directory, "processed_titles.txt")
    os.makedirs(directory, exist_ok=True)
    
    try:
        with open(processed_file, 'a', encoding='utf-8') as f:
            f.write(f"{title}\n")
    except:
        pass