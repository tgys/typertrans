"""Main application logic and workflow orchestration."""

import os
import sys
from .config import ui, CLAUDE_CACHE, OVPN_CACHE, ZLIB_AUTH_CACHE, selected_language
from .network_utils import is_vpn_connected, start_vpn
from .auth import get_bearer
from .claude_client import search_book_titles
from .typing_practice import run_typing_practice
from .wasabi_cache import WasabiFailedTitlesCache


def main_app(stdscr):
    """Main application loop with menu interface."""
    ui.setup_screen(stdscr)
    ui.log("📚 Children's Book Downloader Started")
    ui.log("💡 Scroll logs: j/k keys, arrow keys, mouse wheel, or click scrollbar")
    
    # Initial setup complete
    
    ui.refresh_display()

    try:
        # Main menu
        while True:
            choice = ui.show_menu("Main Menu", [
                "Start Download Process",
                "Typing Practice",
                "Check VPN Status",
                "Clear Cached Credentials",
                "Exit"
            ])

            if choice == 0:  # Start download
                run_download_process()
            elif choice == 1:  # Typing practice
                run_typing_practice(ui)
            elif choice == 2:  # Check VPN
                if is_vpn_connected():
                    ui.log("🟢 VPN is connected")
                else:
                    ui.log("❌ VPN is not connected")
            elif choice == 3:  # Clear cache
                clear_caches()
            elif choice == 4 or choice == -1:  # Exit
                ui.log("👋 Goodbye!")
                break

    except KeyboardInterrupt:
        ui.log("🛑 Interrupted by user.")
    except Exception as e:
        ui.log(f"❌ Unexpected error: {e}")


def clear_caches():
    """Clear all cached credentials and configuration files."""
    files_to_remove = [CLAUDE_CACHE, OVPN_CACHE, ZLIB_AUTH_CACHE]
    removed = 0

    for cache_file in files_to_remove:
        try:
            if os.path.exists(cache_file):
                os.remove(cache_file)
                removed += 1
        except Exception as e:
            ui.log(f"⚠️ Could not remove {cache_file}: {e}")

    ui.log(f"🗑️ Cleared {removed} cache files")


def run_download_process():
    """Complete book download process with Internet Archive integration."""
    import requests
    import os
    import warnings
    import urllib3
    from .archive_downloader import (
        process_book_download, 
        count_valid_text_files, 
        get_processed_titles, 
        save_processed_title
    )
    
    # Suppress SSL warnings from appearing in UI but log them to file
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Custom warning handler to log warnings to file only
    def warning_handler(message, category, filename, lineno, file=None, line=None):
        """Custom warning handler that logs warnings to search log file only"""
        warning_msg = f"⚠️ {category.__name__}: {message}"
        if hasattr(ui, 'search_logging') and ui.search_logging and hasattr(ui, 'search_log_file'):
            ui.log_to_file_only(warning_msg)
    
    # Set the custom warning handler
    original_showwarning = warnings.showwarning
    warnings.showwarning = warning_handler
    
    # Check/setup VPN
    start_vpn()
    
    # Get API key
    api_key = get_bearer()
    if not api_key:
        return

    # Language selection with more options
    languages = [
        "French", "Spanish", "German", "Italian", "Portuguese", 
        "Russian", "Chinese", "Japanese", "Korean", "Arabic",
        "Dutch", "Swedish", "Norwegian", "Danish", "Finnish",
        "Polish", "Czech", "Hungarian", "Turkish", "Greek"
    ]
    
    lang_choice = ui.show_menu("Select Language", languages)
    if lang_choice == -1:
        ui.log("❌ No language selected")
        return
    
    lang = languages[lang_choice]
    ui.log(f"🌍 Selected language: {lang}")

    # Set up download directory
    BASE_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "children_books")
    download_dir = os.path.join(BASE_DOWNLOAD_DIR, lang)
    os.makedirs(download_dir, exist_ok=True)
    
    ui.log(f"📁 Download directory: {download_dir}")

    # Check existing files
    existing_files = count_valid_text_files(download_dir)
    ui.log(f"📚 Found {existing_files} existing text files")
    
    # Target: get 10 valid text files
    target_files = 10
    if existing_files >= target_files:
        ui.log(f"✅ Already have {existing_files} files (target: {target_files})")
        choice = ui.show_menu("What would you like to do?", [
            "Continue downloading more books",
            "Skip download (sufficient books available)"
        ])
        if choice == 1:
            ui.log("📚 Download skipped - sufficient books available")
            return

    # Get processed titles to avoid duplicates
    processed_titles = get_processed_titles(download_dir)
    ui.log(f"🔍 Loaded {len(processed_titles)} previously processed titles")

    # Enable search logging for file-only logs - put in root logs directory
    root_dir = os.path.dirname(download_dir)  # Get parent directory (children_books)
    logs_dir = os.path.join(root_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    search_log_file = os.path.join(logs_dir, f"search_log_{lang}.txt")
    ui.search_logging = True
    ui.search_log_file = search_log_file

    # Search for book titles
    ui.set_status("Searching for book titles...")
    ui.log("🤖 Generating book titles with Claude AI...")
    book_titles = search_book_titles(lang, api_key)
    if not book_titles:
        ui.log("❌ No book titles found")
        return

    ui.log(f"📚 Found {len(book_titles)} book titles from Claude AI")
    
    # Initialize Wasabi failed titles cache
    ui.log("🗃️ Initializing failed titles cache...")
    try:
        failed_cache = WasabiFailedTitlesCache(access_key="O9YRIDWGSOTFW07SB6AK")
        cache_stats = failed_cache.get_stats()
        ui.log(f"📊 Cache stats: {cache_stats['total_failed']} failed titles, Wasabi: {'✅' if cache_stats['wasabi_connected'] else '❌'}")
    except Exception as e:
        ui.log(f"⚠️ Failed to initialize Wasabi cache, using local only: {e}")
        failed_cache = None

    # Filter out already processed AND failed titles
    new_titles = []
    skipped_processed = 0
    skipped_failed = 0
    
    for title in book_titles:
        if title.lower() in processed_titles:
            skipped_processed += 1
            ui.log_to_file_only(f"⚠️ Skipping already processed: {title}")
        elif failed_cache and failed_cache.is_failed(title):
            skipped_failed += 1
            ui.log_to_file_only(f"🚫 Skipping previously failed: {title}")
        else:
            new_titles.append(title)
    
    if skipped_processed > 0:
        ui.log(f"⚠️ Skipped {skipped_processed} already processed titles")
    if skipped_failed > 0:
        ui.log(f"🚫 Skipped {skipped_failed} previously failed titles")
    
    if not new_titles:
        ui.log("❌ All titles have been processed or failed already")
        return
    
    ui.log(f"📖 Processing {len(new_titles)} new titles")

    # Create HTTP session for downloads
    session = requests.Session()
    session.verify = False  # Disable SSL verification for problematic sites
    
    # Process each title
    successful_downloads = 0
    for i, title in enumerate(new_titles):
        ui.log("")  # Empty line with timestamp and column separator
        # Truncate title if too long to maintain column alignment
        display_title = title[:50] + "..." if len(title) > 50 else title
        ui.log(f"📖 Processing {i+1}/{len(new_titles)}: {display_title}")
        
        try:
            # Mark title as processed regardless of outcome
            save_processed_title(download_dir, title)
            
            # Try to download and process the book
            success = process_book_download(session, title, lang, download_dir, ui, failed_cache)
            
            if success:
                successful_downloads += 1
                # Truncate title if too long to maintain column alignment
                display_title = title[:50] + "..." if len(title) > 50 else title
                ui.log(f"✅ Successfully processed: {display_title}")
            else:
                # Truncate title if too long to maintain column alignment
                display_title = title[:50] + "..." if len(title) > 50 else title
                ui.log(f"❌ Failed to process: {display_title}")
            
            # Check if we have enough files
            current_files = count_valid_text_files(download_dir)
            if current_files >= target_files:
                ui.log(f"🎯 Target reached! Found {current_files} valid text files")
                break
            
            # Small delay between requests
            import time
            time.sleep(2)
            
        except KeyboardInterrupt:
            ui.log("🛑 Download interrupted by user")
            break
        except Exception as e:
            ui.log(f"❌ Error processing {title}: {e}")
            continue

    # Final summary
    final_count = count_valid_text_files(download_dir)
    ui.log("")  # Empty line with timestamp and column separator
    ui.log(f"📊 Download Summary:")
    ui.log(f"   • Successfully processed: {successful_downloads} books")
    ui.log(f"   • Total text files: {final_count}")
    ui.log(f"   • Target: {target_files} files")
    
    if final_count >= target_files:
        ui.log(f"🎉 Success! Ready for typing practice")
    else:
        ui.log(f"⚠️ Still need {target_files - final_count} more books for optimal experience")
        ui.log(f"💡 You can run the download process again to get more books")
    
    # Restore original warning handler
    warnings.showwarning = original_showwarning




def main():
    """Entry point function."""
    try:
        import curses
        curses.wrapper(main_app)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)