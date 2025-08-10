#!/usr/bin/env python3
"""
Typing Practice Interface for TyperTRS
Extracted and adapted from typerai.py
"""

import curses
import time
import unicodedata
import os
import re


class TypingPracticeInterface:
    """Advanced typing practice interface with real-time feedback"""
    
    @staticmethod
    def normalize_text_for_typing_static(text):
        """Aggressively normalize ALL punctuation to standard ASCII characters"""
        if not text:
            return text
            
        # Create translation table mapping all variants to standard characters
        translation_table = str.maketrans({
            # ALL APOSTROPHE VARIANTS → standard apostrophe  
            "\u2019": "'",  # U+2019 RIGHT SINGLE QUOTATION MARK
            "\u2018": "'",  # U+2018 LEFT SINGLE QUOTATION MARK  
            "`": "'",  # U+0060 GRAVE ACCENT
            "ʼ": "'",  # U+02BC MODIFIER LETTER APOSTROPHE
            "ˈ": "'",  # U+02C8 MODIFIER LETTER VERTICAL LINE
            "ʻ": "'",  # U+02BB MODIFIER LETTER TURNED COMMA
            "´": "'",  # U+00B4 ACUTE ACCENT
            "ˊ": "'",  # U+02CA MODIFIER LETTER ACUTE ACCENT
            "ˋ": "'",  # U+02CB MODIFIER LETTER GRAVE ACCENT
            "′": "'",  # U+2032 PRIME
            "‛": "'",  # U+201B SINGLE HIGH-REVERSED-9 QUOTATION MARK
            "‚": "'",  # U+201A SINGLE LOW-9 QUOTATION MARK
            "ʹ": "'",  # U+02B9 MODIFIER LETTER PRIME
            "ʺ": "'",  # U+02BA MODIFIER LETTER DOUBLE PRIME
            "‵": "'",  # U+2035 REVERSED PRIME
            "‶": "'",  # U+2036 REVERSED DOUBLE PRIME
            "‴": "'",  # U+2033 DOUBLE PRIME
            "″": "'",  # U+2033 DOUBLE PRIME (alternate)
            "‸": "'",  # U+2038 CARET
            "‹": "'",  # U+2039 SINGLE LEFT-POINTING ANGLE QUOTATION MARK
            "›": "'",  # U+203A SINGLE RIGHT-POINTING ANGLE QUOTATION MARK
            
            # ALL QUOTE VARIANTS → standard quote
            "\u201C": '"',  # U+201C LEFT DOUBLE QUOTATION MARK
            "\u201D": '"',  # U+201D RIGHT DOUBLE QUOTATION MARK
            "„": '"',  # U+201E DOUBLE LOW-9 QUOTATION MARK
            "«": '"',  # U+00AB LEFT DOUBLE ANGLE QUOTATION MARK
            "»": '"',  # U+00BB RIGHT DOUBLE ANGLE QUOTATION MARK
            
            # ALL DASH VARIANTS → standard hyphen
            "–": "-",  # U+2013 EN DASH
            "—": "-",  # U+2014 EM DASH
            "―": "-",  # U+2015 HORIZONTAL BAR
            "‒": "-",  # U+2012 FIGURE DASH
            "⸺": "-",  # U+2E3A TWO-EM DASH
            "⸻": "-",  # U+2E3B THREE-EM DASH
            
            # Additional punctuation normalization
            "•": "*",    # U+2022 BULLET
            "·": "*",    # U+00B7 MIDDLE DOT
            "‰": "%",    # U+2030 PER MILLE SIGN
        })
        
        # Apply translation table to normalize all characters at once
        normalized_text = text.translate(translation_table)
        
        # Handle multi-character replacements separately
        normalized_text = normalized_text.replace("…", "...")  # U+2026 HORIZONTAL ELLIPSIS
        
        # Apply Unicode NFKC normalization for any remaining issues
        normalized_text = unicodedata.normalize('NFKC', normalized_text)
        
        return normalized_text

    @staticmethod
    def normalize_char_for_typing_static(char):
        """Static version of character normalization for use in constructor"""
        # List of ALL possible apostrophe variants
        if char in ["'", "'", "'", "`", "ʼ", "ˈ", "ʻ", "´", "ˊ", "ˋ", "′", "‛", "‚", "ʹ", "ʺ", "‵", "‶", "‴", "″", "‸", "‹", "›"]:
            return "'"
        # Quote variants
        elif char in ['"', """, """, "„", "«", "»", "‚", "‛"]:
            return '"'
        # Dash variants  
        elif char in ["-", "–", "—", "―", "‒", "⸺", "⸻"]:
            return "-"
        else:
            return char
    
    @staticmethod
    def normalize_accents(text):
        """Remove accents from text to make accented and non-accented characters interchangeable"""
        if not text:
            return ""
        
        # Use Unicode NFD normalization to separate base characters from combining marks
        # Normalize to NFD (decomposed form) to separate accents from base characters
        nfd_text = unicodedata.normalize('NFD', text)
        
        # Filter out combining characters (accents, diacritics)
        # Category 'Mn' = Mark, nonspacing (combining diacritical marks)
        # Category 'Mc' = Mark, spacing combining 
        no_accents = ''.join(char for char in nfd_text 
                           if unicodedata.category(char) not in ('Mn', 'Mc'))
        
        # Common additional accent removals for characters that might not be handled by NFD
        accent_map = {
            'ß': 'ss',  # German eszett
            'æ': 'ae',  # Latin ae
            'œ': 'oe',  # Latin oe  
            'ø': 'o',   # Nordic o
            'đ': 'd',   # Croatian/Vietnamese d
            'ð': 'd',   # Icelandic eth
            'þ': 'th',  # Icelandic thorn
            'ł': 'l',   # Polish l
            'ı': 'i',   # Turkish dotless i
        }
        
        for accented, base in accent_map.items():
            no_accents = no_accents.replace(accented, base)
            no_accents = no_accents.replace(accented.upper(), base.upper())
        
        return no_accents

    def get_translation_language(self):
        """Let user select target language for translation"""
        # Language codes mapping for translation services
        language_options = {
            "English": "en",
            "French": "fr", 
            "Spanish": "es",
            "German": "de",
            "Italian": "it",
            "Portuguese": "pt",
            "Russian": "ru",
            "Chinese": "zh",
            "Japanese": "ja",
            "Korean": "ko",
            "Arabic": "ar",
            "Dutch": "nl",
            "Swedish": "sv",
            "Norwegian": "no",
            "Danish": "da",
            "Finnish": "fi",
            "Polish": "pl",
            "Czech": "cs",
            "Hungarian": "hu",
            "Turkish": "tr",
            "Greek": "el",
            "Hebrew": "he",
            "Hindi": "hi",
            "Bengali": "bn",
            "Tamil": "ta",
            "Thai": "th"
        }
        
        language_names = list(language_options.keys())
        
        # Show language selection menu
        selected_index = self.ui.show_menu(
            "Select translation target language:", 
            language_names
        )
        
        if selected_index is not None and 0 <= selected_index < len(language_names):
            selected_language = language_names[selected_index]
            language_code = language_options[selected_language]
            self.ui.log(f"🌍 Translation target: {selected_language}")
            return language_code
        else:
            # Default to English if no selection
            return "en"

    def _filter_valid_words(self, words):
        """Filter out non-word tokens like OCR artifacts, single characters, and gibberish."""
        valid_words = []
        
        # Very restrictive: only allow these specific single-character words
        valid_single_chars = {'I', 'a', 'A'}  # Only the most essential single-char words
        
        # Common valid 2-character words (more restrictive list)
        valid_two_chars = {'is', 'to', 'be', 'of', 'or', 'in', 'on', 'at', 'it', 'we', 'he', 'me', 'my', 'no', 'so', 'up', 'do', 'go', 'if', 'an', 'as', 'am', 'us', 'la', 'le', 'el', 'de', 'du', 'da', 'et', 'un', 'es', 'en', 'im', 'zu', 'wo', 'da', 'er', 'es', 'ja', 'se', 'il', 'ce', 'on', 'ne', 'je', 'tu', 'ou', 'si'}
        
        for word in words:
            # Remove leading/trailing punctuation for analysis
            clean_word = re.sub(r'^[^\w]+|[^\w]+$', '', word, flags=re.UNICODE)
            
            # Skip empty words after cleaning
            if not clean_word:
                continue
                
            # Much stricter single character filtering
            if len(clean_word) == 1:
                if clean_word not in valid_single_chars:
                    continue
                    
            # Skip if it's all digits
            if clean_word.isdigit():
                continue
                
            # Skip if it contains no alphabetic characters
            if not any(c.isalpha() for c in clean_word):
                continue
                
            # Skip if it contains any digits mixed with letters
            if any(c.isdigit() for c in clean_word) and any(c.isalpha() for c in clean_word):
                continue
                
            # Skip obvious OCR artifacts (mixed case with numbers/symbols in weird patterns)
            if re.search(r'[a-z][A-Z]|[A-Z]{2,}[a-z][A-Z]', clean_word):
                continue
                
            # Much stricter 2-character word filtering
            if len(clean_word) == 2:
                if clean_word.lower() not in valid_two_chars:
                    # Reject all uppercase 2-letter combinations that aren't known words
                    # (these are likely OCR artifacts or abbreviations, not words for typing practice)
                    continue
                        
            # Skip 3-letter combinations that are likely OCR artifacts
            if len(clean_word) == 3:
                # Skip if it's all consonants or has unusual patterns
                vowels = set('aeiouAEIOUäöüÄÖÜáéíóúàèìòù')
                if not any(c in vowels for c in clean_word):
                    continue
                    
            # Skip if it has too many consecutive consonants (likely OCR artifact)
            if len(clean_word) >= 3:
                consonant_pattern = re.compile(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{4,}')
                if consonant_pattern.search(clean_word):
                    continue
                    
            # Skip if it's mostly non-alphabetic characters (stricter threshold)
            alpha_ratio = sum(1 for c in clean_word if c.isalpha()) / len(clean_word)
            if alpha_ratio < 0.8:  # Raised from 0.6 to 0.8
                continue
                
            # Skip very short words with unusual character combinations
            if len(clean_word) <= 3 and not clean_word.lower().isalpha():
                continue
                
            # If we get here, it's probably a valid word
            valid_words.append(word)  # Keep original word with punctuation
            
        return valid_words

    def __init__(self, title, text, language, ui):
        self.title = title
        self.ui = ui  # Store reference to UI for language selection
        # Aggressively normalize ALL punctuation to standard ASCII characters
        self.text = TypingPracticeInterface.normalize_text_for_typing_static(text)
        self.language = language
        self.typed_text = ""
        self.current_word_index = 0
        # Split into words - text is now fully normalized
        raw_words = self.text.split()
        self.words = self._filter_valid_words(raw_words)
        self.start_time = None
        self.wpm = 0
        self.last_wpm_update = None
        self.incorrect_words = set()  # Track words that were typed incorrectly
        self.actually_typed_words = 0  # Track words actually typed (excluding skips)
        self.skipped_words = 0  # Track words skipped via Tab or Ctrl+N
        self.current_char_index = 0  # Track character position within current word
        self.translator = None
        self.translated_text = ""
        self.current_translation = ""
        self.translation_status = "disabled"  # Start with translation disabled
        
        # Translation caching to avoid excessive API calls
        self.current_translation_cache = ""
        self.last_translated_word_count = 0
        self.last_translated_text = ""
        
        # Circuit breaker for translation errors
        self.translation_error_count = 0
        self.translation_error_window_start = 0
        self.translation_temporarily_disabled = False
        
        # Line-based translation caching for incremental updates
        self.translated_lines_cache = []  # List of translated lines
        self.source_lines_cache = []      # Corresponding source lines
        self.last_translated_line_index = -1  # Track which line was last translated
        self.last_translation_time = 0   # Throttle translation requests
        
        # Scrolling and wrapping variables
        self.input_scroll_offset = 0  # Vertical scroll offset for input area
        self.text_scroll_offset = 0   # Vertical scroll offset for text area
        self.translation_scroll_offset = 0  # Vertical scroll offset for translation area
        self.translation_error_msg = ""
        self.target_language = "en"  # Default target language
        
        # Initialize translation functionality
        self.__init_translation()
        
    def wrap_text_to_lines(self, text, max_width):
        """Wrap text to lines respecting word boundaries"""
        if not text:
            return []
        
        lines = []
        words = text.split(' ')
        current_line = ""
        
        for word in words:
            # Check if adding this word would exceed the line width
            test_line = current_line + (" " if current_line else "") + word
            if len(test_line) <= max_width:
                current_line = test_line
            else:
                # Start new line
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        # Add the last line if it has content
        if current_line:
            lines.append(current_line)
        
        return lines

    def draw_scrollbar(self, win, height, width, current_line, total_lines, transparent_track=False):
        """Draw a vertical scrollbar on the right side of a window"""
        display_height = height - 2  # Account for window borders
        if total_lines <= display_height:  # No scrollbar needed if content fits
            return
        
        # Calculate scrollbar dimensions
        scrollbar_height = display_height
        if scrollbar_height <= 0:
            return
        
        # Calculate scrollbar position
        max_scroll_offset = max(1, total_lines - display_height)
        scroll_ratio = current_line / max_scroll_offset
        scrollbar_pos = int(scroll_ratio * (scrollbar_height - 1))
        scrollbar_pos = max(0, min(scrollbar_pos, scrollbar_height - 1))
        
        try:
            # Draw scrollbar track (only if not transparent)
            if not transparent_track:
                for y in range(1, height - 1):
                    win.addstr(y, width - 1, "│", curses.color_pair(6))  # Use cyan for track
            
            # Draw scrollbar thumb
            thumb_y = scrollbar_pos + 1
            if 1 <= thumb_y < height - 1:
                win.addstr(thumb_y, width - 1, "█", curses.color_pair(8) | curses.A_BOLD)  # Yellow for thumb
        except curses.error:
            pass  # Ignore drawing errors
        
    def get_incremental_translation(self, current_text_words, max_width):
        """Get translation using incremental line-based caching"""
        if not current_text_words:
            return ""
        
        # Get the source text up to current position
        current_text = ' '.join(current_text_words)
        
        # Wrap the source text into lines to determine current line
        source_wrapped_lines = self.wrap_text_to_lines(current_text, max_width)
        
        # Find which line the user is currently typing on
        current_line_index = 0
        word_count = 0
        for line_idx, line in enumerate(source_wrapped_lines):
            words_in_line = len(line.split())
            if word_count + words_in_line >= len(current_text_words):
                current_line_index = line_idx
                break
            word_count += words_in_line
        
        # Check if we need to update our line caches
        import time
        force_refresh = getattr(self, 'force_translation_refresh', False)
        current_time = time.time()
        
        # Throttle translation requests (minimum 0.5 seconds between translations)
        time_since_last = current_time - self.last_translation_time
        should_translate = (len(self.source_lines_cache) != len(source_wrapped_lines) or 
                           self.source_lines_cache != source_wrapped_lines or force_refresh)
        
        # Skip translation if circuit breaker is active
        if hasattr(self, 'translation_temporarily_disabled') and self.translation_temporarily_disabled:
            should_translate = False
        
        if should_translate and (time_since_last >= 0.5 or force_refresh):
            
            # Source lines have changed, we need to update translation
            lines_to_translate = []
            
            # Keep previously translated lines that are more than 1 line ago
            stable_line_count = max(0, current_line_index - 1) if not force_refresh else 0
            
            # Preserve stable lines from cache if they exist and match
            if (len(self.translated_lines_cache) >= stable_line_count and
                len(self.source_lines_cache) >= stable_line_count and
                self.source_lines_cache[:stable_line_count] == source_wrapped_lines[:stable_line_count]):
                
                # Keep the stable translated lines
                lines_to_translate.extend(self.translated_lines_cache[:stable_line_count])
            else:
                # Cache mismatch, need to translate stable lines too
                stable_line_count = 0
            
            # Translate from the first unstable line to the end
            if stable_line_count < len(source_wrapped_lines):
                # Get text from unstable line onward
                unstable_text_parts = source_wrapped_lines[stable_line_count:]
                unstable_text = ' '.join(unstable_text_parts)
                
                try:
                    if unstable_text.strip():
                        translated_unstable = self.translate_text(unstable_text)
                        if translated_unstable and translated_unstable.strip():
                            # Wrap the translated unstable text and add to lines_to_translate
                            translated_unstable_lines = self.wrap_text_to_lines(translated_unstable, max_width)
                            lines_to_translate.extend(translated_unstable_lines)
                        else:
                            # Translation failed, use original text and reset translation state
                            lines_to_translate.extend(unstable_text_parts)
                            # Log the issue for debugging
                            if hasattr(self, 'ui') and self.ui:
                                self.ui.log_to_file_only(f"⚠️ Translation returned empty for text of {len(unstable_text)} chars")
                    else:
                        lines_to_translate.extend(unstable_text_parts)
                except Exception as e:
                    # Translation error, use original unstable text and log the error
                    lines_to_translate.extend(unstable_text_parts)
                    if hasattr(self, 'ui') and self.ui:
                        self.ui.log_to_file_only(f"❌ Translation error at word {len(current_text_words)}: {str(e)}")
                    
                    # Check if this looks like a rate limit error and increase throttling
                    error_str = str(e).lower()
                    if any(keyword in error_str for keyword in ['rate', 'limit', 'quota', '429', 'too many']):
                        # Increase throttle time for rate limiting
                        self.last_translation_time = current_time + 3.0  # Wait extra 3 seconds
                        if hasattr(self, 'ui') and self.ui:
                            self.ui.log_to_file_only("⏳ Detected rate limiting, slowing down translation requests")
                    elif any(keyword in error_str for keyword in ['connection', 'network', 'timeout']):
                        # Network issues - wait a bit longer
                        self.last_translation_time = current_time + 1.5
                        if hasattr(self, 'ui') and self.ui:
                            self.ui.log_to_file_only("🌐 Network issue detected, pausing translation requests")
            
            # Update the caches
            self.translated_lines_cache = lines_to_translate
            self.source_lines_cache = source_wrapped_lines[:]
            self.last_translated_line_index = current_line_index
            self.last_translation_time = current_time
            
            # Reset force refresh flag
            if hasattr(self, 'force_translation_refresh'):
                self.force_translation_refresh = False
        
        # Return the combined translation
        return '\n'.join(self.translated_lines_cache) if self.translated_lines_cache else current_text
    
    def __init_translation(self):
        """Initialize translation functionality"""
        # Check if DeepL API key is available before setting up translation
        api_key = os.getenv('DEEPL_API_KEY')
        
        if not api_key:
            # No API key - skip translation setup entirely
            self.translation_status = "disabled"
            self.translator = None
            self.translated_text = ""
            self.ui.log("📝 No translation - practicing with original text")
            self.ui.log("💡 For translation: export DEEPL_API_KEY=your_key (get key at deepl.com/pro-api)")
        else:
            # API key available - set up translation
            self.target_language = self.get_translation_language()
            
            # Try to import translation library
            try:
                from deep_translator import DeeplTranslator
                
                # Map text language to DeepL source code, default to French since most texts are French
                source_lang_map = {
                    'French': 'fr',
                    'Spanish': 'es', 
                    'German': 'de',
                    'Italian': 'it',
                    'Portuguese': 'pt',
                    'Russian': 'ru',
                    'Chinese': 'zh',
                    'Japanese': 'ja',
                    'Korean': 'ko',  # May not be supported by DeepL
                    'Arabic': 'ar',  # May not be supported by DeepL
                    'Dutch': 'nl',
                    'Swedish': 'sv',
                    'Norwegian': 'no',  # May not be supported by DeepL  
                    'Danish': 'da',
                    'Finnish': 'fi',
                    'Polish': 'pl',
                    'Czech': 'cs',
                    'Hungarian': 'hu',
                    'Turkish': 'tr',
                    'Greek': 'el',
                    'Hebrew': 'he',  # May not be supported by DeepL
                    'Hindi': 'hi',   # May not be supported by DeepL
                    'Bengali': 'bn', # May not be supported by DeepL
                    'Tamil': 'ta',   # May not be supported by DeepL
                    'Thai': 'th'     # May not be supported by DeepL
                }
                
                source_lang = source_lang_map.get(self.language, 'fr')  # Default to French
                self.translator = DeeplTranslator(api_key=api_key, source=source_lang, target=self.target_language, use_free_api=False)
                
                # Test the connection with a simple translation to validate API key
                test_result = self.translator.translate("test")
                if test_result:
                    self.translation_status = "available"
                    self.ui.log("✅ Translation ready (using DeepL API)")
                else:
                    raise Exception("DeepL test translation returned empty result")
            except ImportError:
                self.translation_status = "missing_library"
                self.translation_error_msg = "deep_translator not installed"
                self.ui.log("⚠️ deep_translator not installed. Translation disabled.")
                self.ui.log("💡 Install with: pip install deep_translator")
            except Exception as e:
                error_msg = str(e)
                
                if "Unauthorized" in error_msg:
                    self.ui.log("⚠️ DeepL API key invalid")
                    self.ui.log("🔑 Get a valid key at: https://www.deepl.com/pro-api")
                    self.ui.log("💡 Then set: export DEEPL_API_KEY=your_key_here")
                else:
                    self.ui.log(f"⚠️ DeepL error: {error_msg}")
                
                self.ui.log("📝 Translation disabled - practicing with original text")
                self.translation_status = "error"
                self.translation_error_msg = f"DeepL error: {error_msg}"
                self.translator = None

    def get_current_typed_word(self):
        """Get the current word being typed by the user"""
        # Handle the case where typed_text doesn't end with a space
        # This means we're in the middle of typing a word
        if not self.typed_text:
            return ""
        
        typed_words = self.typed_text.split()
        
        # If typed_text ends with a space, we've completed all words in the list
        if self.typed_text.endswith(' '):
            return ""
        
        # Otherwise, return the last word being typed
        if typed_words:
            return typed_words[-1]
        
        return ""
    
    def get_translation_for_display(self, text):
        """Get translation for display - translate full text without word limits"""
        import time
        
        if not self.translator or not text.strip() or self.translation_status != "available":
            return text
            
        # Check circuit breaker - if too many errors recently, temporarily disable translation
        current_time = time.time()
        if self.translation_temporarily_disabled:
            if current_time - self.translation_error_window_start > 45:  # Reset after 45 seconds
                self.translation_temporarily_disabled = False
                self.translation_error_count = 0
                if hasattr(self, 'ui') and self.ui:
                    self.ui.log_to_file_only("✅ Translation re-enabled after cooldown period")
            else:
                return text  # Return original text during cooldown
        
        try:
            # Translate the complete text to avoid losing previous lines
            translation = self.translator.translate(text)
            
            # Reset error count on successful translation
            if translation and translation.strip():
                self.translation_error_count = 0
                return translation
            else:
                return text
            
        except Exception as e:
            # Track translation errors for circuit breaker
            if current_time - self.translation_error_window_start > 60:  # Reset error count every minute
                self.translation_error_count = 0
                self.translation_error_window_start = current_time
            
            self.translation_error_count += 1
            
            # Log specific error details for debugging
            if hasattr(self, 'ui') and self.ui:
                error_msg = str(e)
                self.ui.log_to_file_only(f"❌ DeepL translation error #{self.translation_error_count}: {error_msg}")
                
                # Check for specific error types
                if any(keyword in error_msg.lower() for keyword in ['rate', 'limit', 'quota', '429']):
                    self.ui.log_to_file_only("⚠️ Rate limiting detected - translation will resume automatically")
                elif any(keyword in error_msg.lower() for keyword in ['quota', 'character', 'usage']):
                    self.ui.log_to_file_only("⚠️ DeepL quota/usage limit reached")
                elif any(keyword in error_msg.lower() for keyword in ['network', 'connection', 'timeout']):
                    self.ui.log_to_file_only("⚠️ Network connection issue - translation will retry")
                
                # Enable circuit breaker if too many errors
                if self.translation_error_count >= 7:  # Increased threshold from 5 to 7
                    self.translation_temporarily_disabled = True
                    self.ui.log_to_file_only("🔌 Translation temporarily disabled due to repeated errors (will retry in 45s)")
                    
            # If translation fails, return original text
            return text
    
    def translate_text(self, text):
        """Legacy method - now just calls get_translation_for_display"""
        return self.get_translation_for_display(text)
    
    def calculate_wpm(self):
        """Calculate words per minute (excluding skipped words)"""
        if not self.start_time:
            return 0
        
        elapsed_minutes = (time.time() - self.start_time) / 60
        if elapsed_minutes == 0:
            return 0
        
        # Count completed words plus estimate for current partial word
        words_typed = self.actually_typed_words
        
        # Add partial word progress if currently typing
        if self.current_word_index < len(self.words) and hasattr(self, 'current_char_index'):
            current_word = self.words[self.current_word_index]
            if self.current_char_index > 0:
                # Add fractional progress for current word
                progress = min(self.current_char_index / len(current_word), 1.0)
                words_typed += progress
        
        return int(words_typed / elapsed_minutes)
    
    def update_wpm_if_needed(self):
        """Update WPM every 2 seconds, but not during skips"""
        current_time = time.time()
        if self.last_wpm_update is None or current_time - self.last_wpm_update >= 2:  # Update every 2 seconds
            self.wpm = self.calculate_wpm()
            self.last_wpm_update = current_time

    def run(self):
        """Main typing practice loop"""
        stdscr = self.ui.stdscr
        height, width = stdscr.getmaxyx()
        
        # Clear the main screen
        stdscr.clear()
        stdscr.refresh()
        
        # Completely disable mouse events during typing practice to prevent UI interference
        original_mousemask = curses.mousemask(0)
        
        # Calculate section heights
        text_height = height // 3
        translation_height = height // 3
        input_height = height - text_height - translation_height
        
        # Create windows for each section
        text_win = curses.newwin(text_height, width, 0, 0)
        translation_win = curses.newwin(translation_height, width, text_height, 0)
        input_win = curses.newwin(input_height, width, text_height + translation_height, 0)
        
        # Enable scrolling for text window
        text_win.scrollok(True)
        translation_win.scrollok(True)
        input_win.scrollok(True)
        
        # Initial translation of the text
        self.ui.log("🔄 Translating text...")
        try:
            # Only translate if translation is available and not in error state
            if self.translation_status == "available" and self.translator:
                self.translated_text = self.translate_text(self.text)
            else:
                self.translated_text = self.text  # Fallback to original text
                self.ui.log("⚠️ Translation not available, using original text")
        except Exception as e:
            self.ui.log(f"⚠️ Translation failed during initialization: {e}")
            self.translated_text = self.text  # Fallback to original text
        
        # Pre-translate common words to avoid repeated API calls
        word_translations = {}
        
        # Mouse and scrollbars are disabled to prevent UI interference

        # Main practice loop
        self.start_time = time.time()
        self.last_wpm_update = time.time()
        last_display_state = None  # Track when we need to redraw
        
        def needs_redraw(current_state):
            """Check if screen needs to be redrawn"""
            nonlocal last_display_state
            if last_display_state != current_state:
                last_display_state = current_state
                return True
            return False

        def draw_screen(full_redraw=True):
            """Draw all screen content"""
            if full_redraw:
                # Only clear and redraw borders on full redraw
                text_win.clear()
                translation_win.clear()
                input_win.clear()
                
                # Draw borders
                text_win.box()
                translation_win.box()
                input_win.box()
            
            # Always draw content (regardless of full_redraw flag)
            draw_text_area()
            draw_translation_area()
            draw_input_area()
            
            # Refresh all windows
            text_win.refresh()
            translation_win.refresh()
            input_win.refresh()

        def draw_text_area():
            """Draw the original text area with proper text wrapping and scrolling"""
            try:
                safe_title = self.title[:width-30] if len(self.title) > width-30 else self.title
                text_win.addstr(0, 1, f"Original Text ({self.language}) - {safe_title}:", curses.A_BOLD)
            except curses.error:
                pass
                
            if self.text.strip():  # Only if we have text
                # Wrap the full text into lines
                max_width = width - 4  # Account for borders
                wrapped_lines = self.wrap_text_to_lines(self.text, max_width)
                display_height = text_height - 2  # Reserve space for title
                effective_display_height = display_height - 1  # Leave empty line at bottom during scroll
                
                # Find which line contains the current word
                current_word_line = 0
                word_count = 0
                for line_idx, line in enumerate(wrapped_lines):
                    words_in_line = len(line.split())
                    if word_count + words_in_line > self.current_word_index:
                        current_word_line = line_idx
                        break
                    word_count += words_in_line
                
                # Auto-scroll to keep current word visible (leave empty line at bottom)
                if current_word_line >= self.text_scroll_offset + effective_display_height:
                    self.text_scroll_offset = current_word_line - effective_display_height + 1
                elif current_word_line < self.text_scroll_offset:
                    self.text_scroll_offset = current_word_line
                
                # Display visible lines with word highlighting (leave empty line at bottom)
                word_index = 0
                for display_line in range(effective_display_height):
                    line_idx = self.text_scroll_offset + display_line
                    y_pos = display_line + 1
                    
                    if line_idx >= len(wrapped_lines):
                        break
                    
                    line = wrapped_lines[line_idx]
                    words_in_line = line.split()
                    
                    # Skip words that come before this line
                    if display_line == 0:
                        # Calculate word_index for the first displayed line
                        word_index = 0
                        for i in range(self.text_scroll_offset):
                            if i < len(wrapped_lines):
                                word_index += len(wrapped_lines[i].split())
                    
                    # Draw words with proper highlighting
                    current_x = 1
                    for word in words_in_line:
                        word_with_space = f"{word} "
                        
                        # Check if word fits on the line
                        if current_x + len(word_with_space) >= width - 1:
                            break
                            
                        try:
                            if word_index == self.current_word_index:
                                # Current word - highlight character by character
                                current_typed_word = self.get_current_typed_word()
                                expected_word = word
                                
                                # Draw each character of the current word individually
                                for char_idx, char in enumerate(expected_word):
                                    if char_idx < len(current_typed_word):
                                        # Character has been typed - direct comparison (text is pre-normalized)
                                        typed_char = current_typed_word[char_idx]
                                        expected_char = char
                                        
                                        # Compare characters with accent normalization for interchangeable accented/non-accented characters
                                        typed_char_normalized = TypingPracticeInterface.normalize_accents(typed_char)
                                        expected_char_normalized = TypingPracticeInterface.normalize_accents(expected_char)
                                        
                                        if typed_char_normalized == expected_char_normalized:
                                            # Correct character - yellow
                                            text_win.addstr(y_pos, current_x + char_idx, char, 
                                                          curses.color_pair(8) | curses.A_BOLD)
                                        else:
                                            # Incorrect character - red
                                            text_win.addstr(y_pos, current_x + char_idx, char, 
                                                          curses.color_pair(1) | curses.A_BOLD)
                                    else:
                                        # Character not yet typed - highlight in yellow (current word)
                                        text_win.addstr(y_pos, current_x + char_idx, char,
                                                      curses.color_pair(8))
                                
                                # Add space after word
                                if current_x + len(expected_word) + 1 < width - 1:
                                    text_win.addstr(y_pos, current_x + len(expected_word), " ")
                                
                            elif word_index < self.current_word_index:
                                if word_index in self.incorrect_words:
                                    # Incorrect word - highlighted in red
                                    text_win.addstr(y_pos, current_x, word_with_space, 
                                                  curses.color_pair(1) | curses.A_BOLD)
                                else:
                                    # Correctly completed word - highlighted in purple
                                    text_win.addstr(y_pos, current_x, word_with_space, 
                                                  curses.color_pair(7))
                            else:
                                # Future word - normal text
                                text_win.addstr(y_pos, current_x, word_with_space)
                                
                            current_x += len(word_with_space)
                        except curses.error:
                            break
                        
                        word_index += 1
            
            # Draw scrollbar for text area (with transparent track)
            self.draw_scrollbar(text_win, text_height, width, self.text_scroll_offset, len(wrapped_lines), transparent_track=True)

        def draw_translation_area():
            """Draw the translation area content"""
            # Display live translation
            try:
                # Check translation status and show info if needed
                if self.translation_status == "disabled":
                    translation_win.addstr(0, 1, "Translation Info:", curses.A_BOLD | curses.color_pair(3))
                    info_msg = "📝 No DeepL API key - showing original text"
                    help_msg = "Set DEEPL_API_KEY env variable for translation"
                    translation_win.addstr(1, 1, info_msg, curses.color_pair(3))
                    translation_win.addstr(2, 1, help_msg, curses.color_pair(3))
                elif self.translation_status == "missing_library":
                    translation_win.addstr(0, 1, "Translation Warning:", curses.A_BOLD | curses.color_pair(3))
                    warning_msg = "⚠️ Translation disabled - deep_translator not installed"
                    install_msg = "Install with: pip install deep_translator"
                    translation_win.addstr(1, 1, warning_msg, curses.color_pair(3))
                    translation_win.addstr(2, 1, install_msg, curses.color_pair(3))
                elif self.translation_status == "error":
                    translation_win.addstr(0, 1, "Translation Error:", curses.A_BOLD | curses.color_pair(1))
                    error_msg = f"⚠️ {self.translation_error_msg}"
                    translation_win.addstr(1, 1, error_msg[:width-3], curses.color_pair(1))
                else:
                    # Translation is available - show normal translation
                    translation_win.addstr(0, 1, "Live Translation:", curses.A_BOLD)
                    
                    # Get text up to current typing position
                    current_text_words = self.words[:self.current_word_index]
                    if current_text_words:
                        # Use incremental translation that preserves old content
                        max_width = width - 4  # Account for borders
                        try:
                            live_translation = self.get_incremental_translation(current_text_words, max_width)
                        except Exception as e:
                            # Fallback to original text if incremental translation fails
                            live_translation = ' '.join(current_text_words)
                        
                        # Display the live translation with proper wrapping and scrolling
                        if live_translation.strip():
                            # Split the pre-wrapped translation into lines
                            wrapped_lines = live_translation.split('\n')
                            display_height = translation_height - 2  # Reserve space for title
                            effective_display_height = display_height - 1  # Leave empty line at bottom during scroll
                            
                            # Initialize scroll offset if not set
                            if not hasattr(self, 'translation_scroll_offset'):
                                self.translation_scroll_offset = 0
                            
                            # Auto-scroll management
                            max_scroll = max(0, len(wrapped_lines) - effective_display_height)
                            if not hasattr(self, 'user_manually_scrolled'):
                                self.user_manually_scrolled = False
                            
                            # Check if we should re-enable auto-scroll after manual scrolling
                            # Re-enable auto-scroll if user hasn't manually scrolled in last 10 seconds
                            if (self.user_manually_scrolled and 
                                hasattr(self, '_manual_scroll_timestamp') and
                                time.time() - self._manual_scroll_timestamp > 10):
                                self.user_manually_scrolled = False
                            
                            # Auto-scroll logic: follow the current typing position
                            if not self.user_manually_scrolled:
                                if len(wrapped_lines) <= effective_display_height:
                                    # Content fits in window, show from top
                                    self.translation_scroll_offset = 0
                                else:
                                    # Calculate which line corresponds to current typing position
                                    # Estimate current position in translation based on typing progress
                                    typing_progress = self.current_word_index / max(1, len(self.words))
                                    estimated_current_line = int(typing_progress * len(wrapped_lines))
                                    
                                    # Auto-scroll to keep the current position visible
                                    # When near the end, prioritize showing the end; otherwise keep current position in middle third
                                    if typing_progress > 0.9:  # Very close to end of text
                                        # Scroll to show the end of the translation
                                        target_position = max_scroll
                                    elif typing_progress > 0.7:  # Approaching end
                                        # Gradually transition to showing more of the end
                                        end_bias = (typing_progress - 0.7) / 0.2  # Scale from 0 to 1
                                        middle_pos = max(0, estimated_current_line - effective_display_height // 2)
                                        target_position = int(middle_pos * (1 - end_bias) + max_scroll * end_bias)
                                    else:
                                        # Show current position in the middle of the window for better context
                                        target_position = max(0, estimated_current_line - effective_display_height // 2)
                                    
                                    # Smooth scrolling: don't jump too far at once
                                    if hasattr(self, '_last_auto_scroll_position'):
                                        max_jump = effective_display_height // 2  # Maximum jump per update
                                        if abs(target_position - self._last_auto_scroll_position) > max_jump:
                                            if target_position > self._last_auto_scroll_position:
                                                target_position = self._last_auto_scroll_position + max_jump
                                            else:
                                                target_position = self._last_auto_scroll_position - max_jump
                                    
                                    self.translation_scroll_offset = target_position
                                    self._last_auto_scroll_position = target_position
                            
                            # Clamp scroll offset to valid range
                            self.translation_scroll_offset = max(0, min(self.translation_scroll_offset, max_scroll))
                            
                            # Clear the translation content area (but not borders)
                            for clear_line in range(1, display_height + 1):
                                translation_win.addstr(clear_line, 1, " " * (width - 4))
                            
                            # Display visible lines (leave one empty line at bottom during scroll)
                            for display_line in range(effective_display_height):
                                line_idx = self.translation_scroll_offset + display_line
                                y_pos = display_line + 1
                                
                                if line_idx < len(wrapped_lines):
                                    translation_win.addstr(y_pos, 1, wrapped_lines[line_idx])
                            
                            # Draw scrollbar for translation area (with transparent track)
                            self.draw_scrollbar(translation_win, translation_height, width, 
                                              self.translation_scroll_offset, len(wrapped_lines), transparent_track=True)
                    else:
                        # Clear the content area when no translation
                        for clear_line in range(1, translation_height - 1):
                            translation_win.addstr(clear_line, 1, " " * (width - 4))
                        translation_win.addstr(1, 1, "[Start typing to see translation]")
                    
            except curses.error:
                pass

        def draw_input_area():
            """Draw the input area content with text wrapping"""
            try:
                input_win.addstr(0, 1, "Typing Input:", curses.A_BOLD)
                
                # Show current word to type
                if self.current_word_index < len(self.words):
                    current_word = self.words[self.current_word_index]
                    input_win.addstr(1, 1, f"Type this word: {current_word}", curses.A_REVERSE)
                
                # Available space for typed text
                max_width = width - 4  # Account for borders
                text_start_y = 3
                text_display_height = input_height - 6  # Reserve space for headers and footer
                effective_text_display_height = text_display_height - 1  # Leave empty line at bottom during scroll
                
                # Wrap typed text into lines
                if self.typed_text:
                    wrapped_lines = self.wrap_text_to_lines(self.typed_text, max_width)
                    
                    # Calculate cursor position in wrapped text
                    cursor_line = 0
                    cursor_col = 0
                    chars_counted = 0
                    
                    for line_idx, line in enumerate(wrapped_lines):
                        line_length = len(line)
                        if chars_counted + line_length >= len(self.typed_text):
                            cursor_line = line_idx
                            cursor_col = len(self.typed_text) - chars_counted
                            break
                        chars_counted += line_length + 1  # +1 for space between words
                    
                    # Auto-scroll to keep cursor visible (leave empty line at bottom)
                    if cursor_line >= self.input_scroll_offset + effective_text_display_height:
                        self.input_scroll_offset = cursor_line - effective_text_display_height + 1
                    elif cursor_line < self.input_scroll_offset:
                        self.input_scroll_offset = cursor_line
                    
                    # Display visible lines (leave empty line at bottom)
                    for display_line in range(effective_text_display_height):
                        line_idx = self.input_scroll_offset + display_line
                        y_pos = text_start_y + display_line
                        
                        if line_idx < len(wrapped_lines):
                            input_win.addstr(y_pos, 1, wrapped_lines[line_idx])
                    
                    # Draw cursor
                    cursor_display_line = cursor_line - self.input_scroll_offset
                    if 0 <= cursor_display_line < effective_text_display_height:
                        cursor_y = text_start_y + cursor_display_line
                        cursor_x = 1 + cursor_col
                        if cursor_x < width - 2:
                            try:
                                input_win.addstr(cursor_y, cursor_x, "_", curses.A_BLINK | curses.A_REVERSE)
                            except curses.error:
                                pass
                else:
                    # No typed text, cursor at start
                    try:
                        input_win.addstr(text_start_y, 1, "_", curses.A_BLINK | curses.A_REVERSE)
                    except curses.error:
                        pass
                
                # Draw scrollbar for input area if there's wrapped text
                if self.typed_text:
                    wrapped_lines = self.wrap_text_to_lines(self.typed_text, max_width)
                    # Draw scrollbar for input area (with transparent track)
                    self.draw_scrollbar(input_win, input_height, width, self.input_scroll_offset, len(wrapped_lines), transparent_track=True)
                
                # Display WPM and instructions
                input_win.addstr(input_height - 3, 1, f"WPM: {self.wpm}")
                input_win.addstr(input_height - 2, 1, "Space: next word | Tab: skip word | Ctrl+N: skip line | PgUp/PgDn: scroll translation | ESC: exit")
                
                # Show progress on bottom right corner
                progress = f"Progress: {self.current_word_index}/{len(self.words)} words"
                progress_x = max(1, width - len(progress) - 2)
                if progress_x + len(progress) < width - 1:
                    input_win.addstr(input_height - 3, progress_x, progress)
                
            except curses.error:
                pass

        # Initial draw
        draw_screen()
        
        while True:
            try:
                # Create current state for comparison
                current_state = (self.current_word_index, len(self.typed_text), self.text_scroll_offset)
                
                # Get user input (blocking with timeout)
                input_win.timeout(100)  # 100ms timeout
                key = input_win.getch()
                
                if key == -1:  # No input (timeout)
                    # Update WPM periodically
                    self.update_wpm_if_needed()
                    continue
                
                # Handle input
                if key == 27:  # ESC key
                    break
                # Mouse events are disabled during typing practice to prevent interference
                elif key == 9:  # TAB key - skip current word
                    if self.current_word_index < len(self.words):
                        # Throttle rapid Tab presses to prevent translation system overload
                        current_time = time.time()
                        if hasattr(self, '_last_tab_time') and current_time - self._last_tab_time < 0.2:
                            # Too fast - skip translation refresh for this press
                            skip_translation_refresh = True
                        else:
                            skip_translation_refresh = False
                        self._last_tab_time = current_time
                        
                        self.current_word_index += 1
                        self.typed_text += self.words[self.current_word_index - 1] + " "
                        self.skipped_words += 1
                        
                        # Only refresh translation cache if not throttling rapid presses
                        if not skip_translation_refresh:
                            # Gracefully update translation cache instead of completely invalidating
                            self.current_translation_cache = ""
                            self.last_translated_word_count = 0
                            self.last_translated_text = ""
                            
                            # Set flag to force translation bypass on next draw
                            self.force_translation_refresh = True
                        
                        draw_screen(full_redraw=False)
                elif key == 14:  # CTRL+N key - skip current line
                    if self.current_word_index < len(self.words):
                        # Throttle rapid Ctrl+N presses to prevent translation system overload
                        current_time = time.time()
                        if hasattr(self, '_last_ctrl_n_time') and current_time - self._last_ctrl_n_time < 0.3:
                            # Too fast - skip translation refresh for this press
                            skip_translation_refresh = True
                        else:
                            skip_translation_refresh = False
                        self._last_ctrl_n_time = current_time
                        
                        # Improved line skipping: skip to next natural break point
                        words_skipped = 0
                        start_position = self.current_word_index
                        
                        # Strategy 1: Look for sentence endings within reasonable distance
                        sentence_end_found = False
                        for look_ahead in range(15):  # Look ahead up to 15 words
                            word_idx = self.current_word_index + look_ahead
                            if word_idx >= len(self.words):
                                break
                            
                            word = self.words[word_idx]
                            # Check if this word ends a sentence
                            if any(punct in word for punct in ['.', '!', '?', ':', ';']):
                                # Skip to after this word
                                target_idx = word_idx + 1
                                sentence_end_found = True
                                break
                        
                        # Strategy 2: If no sentence end found, use line wrapping calculation
                        if not sentence_end_found:
                            # Estimate words per line based on display width
                            avg_word_length = 5  # Average word length estimate
                            max_width = width - 4  # Account for borders
                            estimated_words_per_line = max(8, max_width // (avg_word_length + 1))
                            
                            # Skip approximately one line's worth of words
                            target_idx = min(
                                len(self.words), 
                                self.current_word_index + estimated_words_per_line
                            )
                        
                        # Skip all words to the target position
                        while self.current_word_index < target_idx and self.current_word_index < len(self.words):
                            self.typed_text += self.words[self.current_word_index] + " "
                            self.current_word_index += 1
                            self.skipped_words += 1
                            words_skipped += 1
                        
                        # Ensure minimum skip if nothing was skipped
                        if words_skipped == 0 and self.current_word_index < len(self.words):
                            # Skip at least 8 words as fallback
                            for _ in range(8):
                                if self.current_word_index < len(self.words):
                                    self.typed_text += self.words[self.current_word_index] + " "
                                    self.current_word_index += 1
                                    self.skipped_words += 1
                        
                        # Only refresh translation cache if not throttling rapid presses
                        if not skip_translation_refresh:
                            # Gracefully update translation cache instead of completely invalidating
                            self.current_translation_cache = ""
                            self.last_translated_word_count = 0
                            self.last_translated_text = ""
                            
                            # Set flag to force translation bypass on next draw
                            self.force_translation_refresh = True
                        
                        draw_screen(full_redraw=False)
                elif key == curses.KEY_PPAGE:  # Page Up - scroll translation up
                    if hasattr(self, 'translation_scroll_offset'):
                        self.translation_scroll_offset = max(0, self.translation_scroll_offset - 5)
                        self.user_manually_scrolled = True  # Mark as manually scrolled
                        self._manual_scroll_timestamp = time.time()  # Track when manual scroll happened
                        self._words_since_manual_scroll = 0  # Reset word counter for re-enabling auto-scroll
                        draw_screen(full_redraw=False)
                elif key == curses.KEY_NPAGE:  # Page Down - scroll translation down
                    if hasattr(self, 'translation_scroll_offset'):
                        # Get current translation to calculate max scroll
                        if hasattr(self, 'current_translation_cache') and self.current_translation_cache:
                            max_width = width - 4
                            wrapped_lines = self.wrap_text_to_lines(self.current_translation_cache, max_width)
                            display_height = translation_height - 2
                            max_scroll = max(0, len(wrapped_lines) - display_height)
                            self.translation_scroll_offset = min(max_scroll, self.translation_scroll_offset + 5)
                            self.user_manually_scrolled = True  # Mark as manually scrolled
                            self._manual_scroll_timestamp = time.time()  # Track when manual scroll happened
                            self._words_since_manual_scroll = 0  # Reset word counter for re-enabling auto-scroll
                            draw_screen(full_redraw=False)
                elif key == curses.KEY_BACKSPACE or key == 127 or key == 8:  # Backspace
                    if self.typed_text:
                        # Check if we're deleting a space (going back to previous word)
                        if self.typed_text.endswith(' '):
                            old_word_index = self.current_word_index
                            self.current_word_index = max(0, self.current_word_index - 1)
                            # Remove from incorrect words set if it was marked as incorrect
                            self.incorrect_words.discard(self.current_word_index)
                            # Decrease actually typed words count when going back
                            if old_word_index > self.current_word_index and self.actually_typed_words > 0:
                                self.actually_typed_words -= 1
                        
                        self.typed_text = self.typed_text[:-1]
                        draw_screen(full_redraw=False)
                elif key == ord(' '):  # Space - check word completion
                    if self.current_word_index < len(self.words):
                        current_typed_word = self.get_current_typed_word()
                        expected_word = self.words[self.current_word_index]
                        
                        # Normalize both for comparison
                        typed_normalized = TypingPracticeInterface.normalize_accents(current_typed_word)
                        expected_normalized = TypingPracticeInterface.normalize_accents(expected_word)
                        
                        if typed_normalized.lower() == expected_normalized.lower():
                            # Correct word
                            self.typed_text += expected_word + " "
                            self.actually_typed_words += 1
                        else:
                            # Incorrect word - mark it and move on
                            self.incorrect_words.add(self.current_word_index)
                            self.typed_text += expected_word + " "
                        
                        self.current_word_index += 1
                        
                        # Re-enable auto-scroll when user makes progress
                        if hasattr(self, 'user_manually_scrolled') and self.user_manually_scrolled:
                            # If user has been typing actively (completed 3+ words), re-enable auto-scroll
                            if hasattr(self, '_words_since_manual_scroll'):
                                self._words_since_manual_scroll += 1
                                if self._words_since_manual_scroll >= 3:
                                    self.user_manually_scrolled = False
                                    self._words_since_manual_scroll = 0
                            else:
                                self._words_since_manual_scroll = 1
                        
                        draw_screen(full_redraw=False)
                elif 32 <= key <= 126:  # Printable characters
                    # Add character to typed text
                    self.typed_text += chr(key)
                    draw_screen(full_redraw=False)
                
                # Check if practice is complete
                if self.current_word_index >= len(self.words):
                    # Show completion stats
                    input_win.clear()
                    input_win.box()
                    
                    total_words = len(self.words)
                    correct_words = total_words - len(self.incorrect_words) - self.skipped_words
                    accuracy = (correct_words / total_words) * 100 if total_words > 0 else 0
                    
                    input_win.addstr(2, 2, f"🎉 Practice Complete!")
                    input_win.addstr(3, 2, f"Final WPM: {self.wpm}")
                    input_win.addstr(4, 2, f"Accuracy: {accuracy:.1f}%")
                    input_win.addstr(5, 2, f"Words typed: {self.actually_typed_words}")
                    input_win.addstr(6, 2, f"Words skipped: {self.skipped_words}")
                    input_win.addstr(7, 2, f"Incorrect words: {len(self.incorrect_words)}")
                    input_win.addstr(9, 2, "Press any key to exit...")
                    input_win.refresh()
                    
                    input_win.timeout(-1)  # Block until key press
                    input_win.getch()
                    break
                    
            except KeyboardInterrupt:
                break
            except curses.error:
                # Handle terminal resize or other curses errors
                continue
        
        # Restore mouse events
        curses.mousemask(original_mousemask)
        
        # Clear screen when exiting
        stdscr.clear()
        stdscr.refresh()


def get_language_code(language_name: str) -> str:
    """Map language name to langdetect language code"""
    language_map = {
        'French': 'fr',
        'Spanish': 'es',
        'German': 'de',
        'Italian': 'it',
        'Portuguese': 'pt',
        'Russian': 'ru',
        'Chinese': 'zh',
        'Japanese': 'ja',
        'Korean': 'ko',
        'Arabic': 'ar',
        'Dutch': 'nl',
        'Swedish': 'sv',
        'Norwegian': 'no',
        'Danish': 'da',
        'Finnish': 'fi',
        'Polish': 'pl',
        'Czech': 'cs',
        'Hungarian': 'hu',
        'Turkish': 'tr',
        'Greek': 'el',
        'Hebrew': 'he',
        'Hindi': 'hi',
        'Bengali': 'bn',
        'Tamil': 'ta',
        'Thai': 'th'
    }
    return language_map.get(language_name, 'en')


def filter_text_by_language(text: str, target_language: str) -> str:
    """Filter text to keep only content in the target language"""
    try:
        # Try to import langdetect
        from langdetect import detect, LangDetectException
    except ImportError:
        # If langdetect is not available, return text as-is
        return text
    
    if not text or not target_language:
        return text
    
    target_code = get_language_code(target_language)
    
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
            # Keep paragraph if detection is uncertain (conservative approach)
        except LangDetectException:
            # If language detection fails, keep the paragraph
            filtered_paragraphs.append(paragraph)
    
    return '\n\n'.join(filtered_paragraphs)


def clean_foreign_words_from_edges(text: str, target_language: str) -> str:
    """Remove foreign language words from the beginning and end of text"""
    try:
        from langdetect import detect, LangDetectException
    except ImportError:
        return text
    
    if not text or not target_language:
        return text
    
    target_code = get_language_code(target_language)
    words = text.split()
    
    if len(words) < 40:  # Don't process very short texts
        return text
    
    # Check first 20 words
    start_index = 0
    for i, word in enumerate(words[:20]):
        # Skip short words, numbers, and punctuation
        if len(word) < 3 or word.isdigit() or not word.isalpha():
            continue
        
        try:
            word_lang = detect(word)
            if word_lang == target_code or (target_code == 'zh' and word_lang in ['zh-cn', 'zh']):
                start_index = i
                break
        except LangDetectException:
            continue
    
    # Check last 20 words
    end_index = len(words)
    for i in range(len(words) - 1, max(len(words) - 21, 0), -1):
        word = words[i]
        # Skip short words, numbers, and punctuation
        if len(word) < 3 or word.isdigit() or not word.isalpha():
            continue
        
        try:
            word_lang = detect(word)
            if word_lang == target_code or (target_code == 'zh' and word_lang in ['zh-cn', 'zh']):
                end_index = i + 1
                break
        except LangDetectException:
            continue
    
    return ' '.join(words[start_index:end_index])


def extract_from_chapter_1(text):
    """Extract text starting from Chapter 1 in multiple languages"""
    if not text:
        return text
    
    # Comprehensive multilingual Chapter 1 patterns
    chapter_1_patterns = [
        # English
        r'chapter\s+1\b', r'chapter\s+one\b', r'1\.\s*chapter\b',
        # French
        r'chapitre\s+1\b', r'chapitre\s+premier\b',
        # Spanish
        r'capítulo\s+1\b', r'capítulo\s+uno\b',
        # German
        r'kapitel\s+1\b', r'erstes\s+kapitel\b',
        # Italian
        r'capitolo\s+1\b', r'capitolo\s+primo\b',
        # Portuguese
        r'capítulo\s+1\b', r'primeiro\s+capítulo\b',
        # Dutch
        r'hoofdstuk\s+1\b', r'eerste\s+hoofdstuk\b',
        # Chinese
        r'第一章', r'第1章',
        # Japanese
        r'第一章', r'第1章', r'一章',
        # Russian
        r'глава\s+1\b', r'первая\s+глава\b',
        # Generic patterns
        r'1\s*\.\s*$',  # Just "1." on its own line
        r'^1$',         # Just "1" on its own line
    ]
    
    text_lower = text.lower()
    
    for pattern in chapter_1_patterns:
        matches = list(re.finditer(pattern, text_lower, re.MULTILINE | re.IGNORECASE))
        if matches:
            # Find the start of the line containing the match
            match_start = matches[0].start()
            line_start = text.rfind('\n', 0, match_start)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1  # Skip the newline
            
            return text[line_start:]
    
    # If no chapter 1 found, return original text
    return text


def has_meaningful_text_content(file_path: str) -> tuple[bool, int]:
    """Check if a text file has meaningful content. Returns (is_valid, char_count)"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        # Remove all metadata and formatting to get just the extracted text
        lines = content.split('\n')
        text_content = ''
        
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            # Skip metadata lines
            if (line.startswith('Title:') or line.startswith('Source URL:') or 
                line.startswith('PDF URL:') or line.startswith('Extraction Date:')):
                continue
            # Skip separator lines (any line that's mostly = characters)
            if line.count('=') > len(line) * 0.5:
                continue
            # Skip page markers
            if line.startswith('=== PAGE') and line.endswith('==='):
                continue
            # This is likely actual text content
            text_content += line + ' '
        
        # Clean up the text content
        text_content = text_content.strip()
        
        # Basic validation:
        # 1. Must have at least 100 characters
        # 2. Must not be mostly numbers or symbols
        char_count = len(text_content)
        alpha_chars = sum(1 for c in text_content if c.isalpha())
        alpha_ratio = alpha_chars / len(text_content) if text_content else 0
        
        is_valid = (char_count >= 100 and 
                   alpha_ratio >= 0.4)  # At least 40% alphabetic characters (OCR-friendly)
        
        return is_valid, char_count
        
    except Exception as e:
        return False, 0


def get_text_files():
    """Get all text files from the downloaded books directories (same as typerai.py)"""
    text_files = []
    
    # Use the same base download directory as the main app
    BASE_DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads", "children_books")
    
    # Look for text files in all language directories
    if os.path.exists(BASE_DOWNLOAD_DIR):
        for lang_dir in os.listdir(BASE_DOWNLOAD_DIR):
            lang_path = os.path.join(BASE_DOWNLOAD_DIR, lang_dir)
            if os.path.isdir(lang_path):
                # Find all .txt files that are not log files
                import glob
                pattern = os.path.join(lang_path, "*.txt")
                for file_path in glob.glob(pattern):
                    filename = os.path.basename(file_path)
                    # Skip system files
                    if (filename not in ['extracted_urls.txt', 'search_log.txt', 'processed_titles.txt'] and
                        not filename.startswith(('extracted_urls_', 'search_log_', 'processed_titles_'))):
                        # Check if file has meaningful content
                        is_valid, word_count = has_meaningful_text_content(file_path)
                        if is_valid:
                            # Extract book title from filename
                            title = filename.replace('_text.txt', '').replace('_', ' ')
                            text_files.append({
                                'title': title,
                                'path': file_path,
                                'language': lang_dir,
                                'word_count': word_count,
                                'char_count': word_count,  # For backward compatibility
                                'name': filename  # Keep for compatibility
                            })
    
    # Also look for any local text files as fallback
    import glob
    fallback_patterns = [
        "*.txt",
        "texts/*.txt", 
        "../texts/*.txt",
        "downloads/*.txt"
    ]
    
    for pattern in fallback_patterns:
        files = glob.glob(pattern)
        for file_path in files:
            if os.path.isfile(file_path):
                filename = os.path.basename(file_path)
                # Skip if already found in book directories
                if any(tf['name'] == filename for tf in text_files):
                    continue
                    
                # Get basic file info with word count validation
                is_valid, word_count = has_meaningful_text_content(file_path)
                if is_valid:
                    text_files.append({
                        'title': filename.replace('.txt', '').replace('_', ' '),
                        'path': file_path,
                        'name': filename,
                        'word_count': word_count,
                        'char_count': word_count,  # For backward compatibility
                        'language': 'Local'  # Mark local files
                    })
    
    return text_files


def clean_text_for_typing_practice(text: str, language: str) -> str:
    """Comprehensive text cleaning for typing practice (same as typerai.py)"""
    if not text:
        return text
    
    # First, extract from Chapter 1 if possible
    text = extract_from_chapter_1(text)
    
    lines = text.split('\n')
    filtered_lines = []
    
    for line in lines:
        original_line = line
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip metadata lines
        if (line.startswith('Title:') or line.startswith('Source URL:') or 
            line.startswith('PDF URL:') or line.startswith('Extraction Date:')):
            continue
        
        # Skip separator lines (any line that's mostly = characters)
        if line.count('=') > len(line) * 0.5:
            continue
        
        # Skip page markers
        if line.startswith('=== PAGE') and line.endswith('==='):
            continue
        
        # Table of contents detection - skip lines with multiple dots
        if '...' in line and line.count('.') > 5:
            continue
        
        # Skip chapter listings with page numbers
        if re.search(r'chapter\s+\d+.*\d+$', line.lower()) or re.search(r'chapitre\s+\d+.*\d+$', line.lower()):
            continue
        
        # Skip page references and numbers
        if re.match(r'^\d+$', line) or re.match(r'^page\s+\d+', line.lower()):
            continue
        
        # Skip short uppercase lines (likely headers)
        if len(line) < 30 and line.isupper() and not line.isdigit():
            continue
        
        # Skip copyright and publication info
        if any(keyword in line.lower() for keyword in ['copyright', '©', 'isbn', 'publisher', 'printed in']):
            continue
        
        # Chapter headers in multiple languages
        chapter_patterns = [
            r'^chapter\s+\d+', r'^chapitre\s+\d+', r'^capítulo\s+\d+', 
            r'^kapitol\s+\d+', r'^capitolo\s+\d+', r'^hoofdstuk\s+\d+'
        ]
        
        is_chapter_header = False
        for pattern in chapter_patterns:
            if re.match(pattern, line.lower()):
                is_chapter_header = True
                break
        
        if is_chapter_header and len(line) < 50:  # Skip short chapter headers
            continue
        
        # Content requirements: must have reasonable length and contain letters
        if len(line) >= 10 and any(c.isalpha() for c in line):
            filtered_lines.append(original_line.strip())
    
    # Join lines and clean up
    cleaned_text = ' '.join(filtered_lines)
    
    # Apply language filtering if available
    cleaned_text = filter_text_by_language(cleaned_text, language)
    
    # Clean foreign words from edges
    cleaned_text = clean_foreign_words_from_edges(cleaned_text, language)
    
    # Final validation - must have at least 100 characters
    if len(cleaned_text.strip()) < 100:
        # If cleaning was too aggressive, return original with just basic cleaning
        basic_lines = []
        for line in text.split('\n'):
            line = line.strip()
            if line and len(line) >= 10 and any(c.isalpha() for c in line):
                # Skip only obvious metadata
                if not (line.startswith('Title:') or line.startswith('Source URL:') or 
                       line.startswith('PDF URL:') or line.startswith('Extraction Date:') or
                       line.count('=') > len(line) * 0.5):
                    basic_lines.append(line)
        return ' '.join(basic_lines)
    
    return cleaned_text.strip()


def run_typing_practice(ui):
    """Main entry point for typing practice (same workflow as typerai.py)"""
    ui.log("📝 Starting typing practice...")
    
    # Get available text files from book directories
    text_files = get_text_files()
    
    if not text_files:
        ui.log("❌ No text files found. Please download some books first using the main download process.")
        ui.log("💡 Or add .txt files to current directory, texts/, or downloads/ folder")
        return
    
    ui.log(f"📚 Found {len(text_files)} text files")
    
    # Get unique languages from available text files
    available_languages = list(set(file_info['language'] for file_info in text_files))
    available_languages.sort()
    
    # Show language selection menu (same as typerai.py)
    lang_options = ["All Languages"] + available_languages
    selected_lang_index = ui.show_menu("Select Language:", lang_options)
    
    if selected_lang_index == -1:
        ui.log("❌ No language selected")
        return
    
    # Filter text files by selected language
    if selected_lang_index == 0:  # "All Languages"
        filtered_files = text_files
        ui.log("📚 Showing books in all languages")
    else:
        selected_language = available_languages[selected_lang_index - 1]
        filtered_files = [f for f in text_files if f['language'] == selected_language]
        ui.log(f"📚 Showing books in {selected_language}")
    
    if not filtered_files:
        ui.log("❌ No books found in selected language")
        return
    
    # Show book selection menu with titles and languages
    book_options = []
    for file_info in filtered_files:
        # Show book title with language and word count
        words = file_info.get('word_count', file_info.get('char_count', 0))
        lang = file_info['language']
        book_options.append(f"{file_info['title']} ({lang}) - {words} words")
    
    selected_book_index = ui.show_menu("Select Book for Typing Practice:", book_options)
    
    if selected_book_index == -1 or selected_book_index >= len(filtered_files):
        ui.log("❌ No book selected")
        return
    
    # Load selected book
    selected_file = filtered_files[selected_book_index]
    ui.log(f"📖 Selected: {selected_file['title']} ({selected_file['language']})")
    
    try:
        with open(selected_file['path'], 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except Exception as e:
        ui.log(f"❌ Error reading file: {e}")
        return
    
    if not content:
        ui.log("❌ Selected file is empty")
        return
    
    # Apply comprehensive text cleaning for typing practice
    ui.log(f"🔍 Processing text content for {selected_file['language']} typing practice...")
    text_content = clean_text_for_typing_practice(content, selected_file['language'])
    
    if not text_content:
        ui.log("❌ No readable text content found in selected file")
        return
    
    # Create and run typing practice interface
    ui.log(f"🎯 Starting typing practice with {selected_file['title']}")
    practice = TypingPracticeInterface(
        title=selected_file['title'],
        text=text_content,
        language=selected_file['language'],
        ui=ui
    )
    
    try:
        practice.run()
    except Exception as e:
        ui.log(f"❌ Error during typing practice: {e}")
    finally:
        ui.log("✅ Typing practice session ended")