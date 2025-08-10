"""
TyperTRS - Children's Book Downloader and Text Extractor
Refactored into modular components while maintaining the same interface.
"""

# Import all the necessary modules and expose their functionality
from .language_utils import *
from .config import *
from .network_utils import *
from .auth import *
from .claude_client import *
from .main_app import *

# Re-export the main symbols for compatibility
__all__ = [
    # Language utilities
    'LANGUAGE_DETECTION_AVAILABLE',
    'get_language_code',
    'filter_text_by_language',
    'clean_foreign_words_from_edges',
    'has_text_in_language',
    
    # Configuration constants
    'CLAUDE_CACHE',
    'OVPN_CACHE', 
    'ZLIB_AUTH_CACHE',
    'CACHE_DAYS',
    'CLAUDE_URL',
    'CLAUDE_MODEL',
    'BASE_DOWNLOAD_DIR',
    'DOWNLOAD_DIR',
    'URL_LOG_FILE',
    'SEARCH_LOG_FILE',
    'SEARCH_ROUND',
    'FAILED_CONVERSIONS',
    
    # UI class
    'NCursesUI',
    'ui',
    'selected_language',
    
    # Network utilities
    'get_cached_ovpn',
    'cache_ovpn',
    'is_vpn_connected',
    'start_vpn',
    
    # Authentication
    'get_cached_key',
    'cache_key',
    'get_bearer',
    'get_cached_zlib_auth',
    'cache_zlib_auth',
    'zlib_login',
    
    # Claude client
    'claude_author_query',
    'search_book_titles',
    
    # Main application
    'main_app',
    'clear_caches',
    'run_download_process', 
    'run_typing_practice',
    'main',
]