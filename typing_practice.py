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
import logging
import warnings
import sys
import contextlib

# Suppress argostranslate/stanza warnings globally to avoid cluttering the UI
# This prevents various translation library warnings from cluttering the typing interface
logging.getLogger('stanza').setLevel(logging.ERROR)
logging.getLogger('argostranslate').setLevel(logging.ERROR)
logging.getLogger('transformers').setLevel(logging.ERROR)
logging.getLogger('torch').setLevel(logging.ERROR)

# Set root logging level to CRITICAL to suppress all translation warnings
logging.getLogger().setLevel(logging.CRITICAL)

# Suppress all translation-related warnings
warnings.filterwarnings('ignore', category=UserWarning, module='stanza')
warnings.filterwarnings('ignore', category=FutureWarning, module='stanza')
warnings.filterwarnings('ignore', category=UserWarning, module='transformers')
warnings.filterwarnings('ignore', message='.*mwt.*')
warnings.filterwarnings('ignore', message='.*Language.*package.*expects.*')

@contextlib.contextmanager
def suppress_stderr():
    """Context manager to temporarily suppress stderr output"""
    old_stderr = sys.stderr
    try:
        with open(os.devnull, "w") as devnull:
            sys.stderr = devnull
            yield
    finally:
        sys.stderr = old_stderr

@contextlib.contextmanager
def suppress_all_output():
    """Context manager to suppress both stdout and stderr"""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        with open(os.devnull, "w") as devnull:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def clean_word_for_fuzzy_matching(word):
    """Clean word by removing company/trademark symbols and normalizing"""
    if not word:
        return word
    
    # Remove common company/trademark symbols
    import re
    
    # Remove trademark symbols: ™, ®, ©, ℠
    cleaned = re.sub(r'[™®©℠]', '', word)
    
    # Remove common company suffixes/symbols
    cleaned = re.sub(r'\b(Inc|LLC|Ltd|Corp|GmbH|SA|SAS|AG)\b\.?', '', cleaned, flags=re.IGNORECASE)
    
    # Remove excessive punctuation (keep basic punctuation)
    cleaned = re.sub(r'[^\w\s\'-]', '', cleaned)
    
    # Remove extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    return cleaned


def get_language_character_set(language_code=None):
    """Get character set for a specific language or return multilingual set"""
    
    # Base Latin characters
    base_chars = set('abcdefghijklmnopqrstuvwxyz')
    
    # Extended character sets by language
    language_chars = {
        'fr': set('àâäçéèêëïîôùûüÿñæœ'),  # French
        'de': set('äöüß'),                      # German
        'es': set('áéíóúüñ'),                   # Spanish
        'it': set('àèéìíîòóùú'),               # Italian
        'pt': set('àáâãçéêíóôõú'),             # Portuguese
        'ru': set('абвгдеёжзийклмнопрстуфхцчшщъыьэюя'),  # Russian (Cyrillic)
        'zh': set(),  # Chinese characters are ideographic, handled separately
        'ja': set(),  # Japanese has hiragana/katakana/kanji, handled separately
        'ar': set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي'),  # Arabic
        'he': set('אבגדהוזחטיכלמנסעפצקרשת'),      # Hebrew
        'pl': set('ąćęłńóśźż'),                # Polish
        'cs': set('áčďéěíňóřšťúůýž'),          # Czech
        'hu': set('áéíóöőúüű'),                # Hungarian
        'tr': set('çğıöşü'),                   # Turkish
        'el': set('αβγδεζηθικλμνξοπρστυφχψω'),  # Greek
        'sv': set('åäö'),                      # Swedish
        'no': set('åæø'),                      # Norwegian
        'da': set('åæø'),                      # Danish
        'fi': set('äöå'),                      # Finnish
        'nl': set('áéíóúèàùìòäëïöüÿ'),         # Dutch
    }
    
    if language_code and language_code in language_chars:
        return base_chars | language_chars[language_code]
    
    # Return combined set for multilingual support
    all_chars = base_chars.copy()
    for chars in language_chars.values():
        all_chars |= chars
    
    return all_chars


def get_keyboard_layout_adjacencies(layout='qwerty'):
    """Get keyboard adjacency mappings for different layouts"""
    
    layouts = {
        'qwerty': {
            'a': 'sqwz', 'b': 'vghn', 'c': 'xdfv', 'd': 'erfcxs', 'e': 'wrds',
            'f': 'rtgvcd', 'g': 'tyhbvf', 'h': 'yugjnb', 'i': 'ujko', 'j': 'uikhm',
            'k': 'ijolm', 'l': 'okp', 'm': 'njk', 'n': 'bhjm', 'o': 'iklp',
            'p': 'ol', 'q': 'wa', 'r': 'etdf', 's': 'awedxz', 't': 'ryfg',
            'u': 'yihj', 'v': 'cfgb', 'w': 'qeass', 'x': 'zsdc', 'y': 'tugh',
            'z': 'asx'
        },
        'azerty': {
            'a': 'qszw', 'z': 'asqe', 'e': 'rzds', 'r': 'etfz', 't': 'ryfg',
            'y': 'tugh', 'u': 'yihj', 'i': 'ujko', 'o': 'iklp', 'p': 'olm',
            'q': 'wsaz', 's': 'qwdza', 'd': 'sefr', 'f': 'drgv', 'g': 'fthb',
            'h': 'gyjn', 'j': 'hukm', 'k': 'julp', 'l': 'kmpo', 'm': 'lp',
            'w': 'qsx', 'x': 'wdc', 'c': 'xfv', 'v': 'cgb', 'b': 'vhn',
            'n': 'bj'
        },
        'qwertz': {
            'q': 'wa', 'w': 'qeasd', 'e': 'wrds', 'r': 'etdf', 't': 'rzfg',
            'z': 'tagh', 'u': 'zihj', 'i': 'ujko', 'o': 'iklp', 'p': 'olü',
            'a': 'qswy', 's': 'awedy', 'd': 'sefr', 'f': 'drgv', 'g': 'fthb',
            'h': 'gzjn', 'j': 'hukm', 'k': 'julö', 'l': 'kmöä', 'y': 'asx',
            'x': 'ydc', 'c': 'xfv', 'v': 'cgb', 'b': 'vhn', 'n': 'bjm',
            'm': 'nk'
        }
    }
    
    return layouts.get(layout, layouts['qwerty'])


def generate_word_variants(word, max_distance=2, language_code=None, keyboard_layout='qwerty'):
    """Generate word variants for fuzzy matching by character operations"""
    
    # Clean the word first (remove trademark symbols, etc.)
    cleaned_word = clean_word_for_fuzzy_matching(word)
    if not cleaned_word:
        return [word]
    
    variants = set()
    word_lower = cleaned_word.lower()
    
    # Get character set for the language
    valid_chars = get_language_character_set(language_code)
    
    # Get keyboard layout adjacencies
    keyboard_adjacent = get_keyboard_layout_adjacencies(keyboard_layout)
    
    # Original word
    variants.add(word_lower)
    
    # Character substitution (idAGes -> images)
    for i in range(len(word_lower)):
        for char in valid_chars:
            if char != word_lower[i]:
                variant = word_lower[:i] + char + word_lower[i+1:]
                variants.add(variant)
    
    # Character deletion (extra characters)
    for i in range(len(word_lower)):
        variant = word_lower[:i] + word_lower[i+1:]
        if len(variant) > 2:  # Don't create very short words
            variants.add(variant)
    
    # Character insertion (missing characters)
    for i in range(len(word_lower) + 1):
        for char in valid_chars:
            variant = word_lower[:i] + char + word_lower[i:]
            if len(variant) <= len(word_lower) + max_distance:
                variants.add(variant)
    
    # Keyboard layout adjacent character substitutions
    for i, char in enumerate(word_lower):
        if char in keyboard_adjacent:
            for adjacent_char in keyboard_adjacent[char]:
                variant = word_lower[:i] + adjacent_char + word_lower[i+1:]
                variants.add(variant)
    
    # Accent-aware substitutions (é->e, ä->a, etc.)
    accent_map = {
        'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a', 'æ': 'ae',
        'ç': 'c', 'č': 'c', 'ć': 'c',
        'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e', 'ě': 'e', 'ę': 'e',
        'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
        'ñ': 'n', 'ň': 'n', 'ń': 'n',
        'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ø': 'o', 'ő': 'o',
        'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u', 'ů': 'u', 'ű': 'u',
        'ý': 'y', 'ÿ': 'y',
        'ß': 'ss', 'ł': 'l', 'ř': 'r', 'š': 's', 'ť': 't', 'ž': 'z',
        'ğ': 'g', 'ı': 'i', 'ş': 's'
    }
    
    # Generate accent-normalized variants
    for accented, base in accent_map.items():
        if accented in word_lower:
            variant = word_lower.replace(accented, base)
            variants.add(variant)
        # Also try the reverse (base -> accented)
        if base in word_lower and accented in valid_chars:
            variant = word_lower.replace(base, accented)
            variants.add(variant)
    
    return list(variants)


def find_similar_words_in_cache(target_word, word_translation_cache, max_suggestions=3, language_code=None, keyboard_layout='qwerty'):
    """Find cached translations of words similar to target_word"""
    try:
        import Levenshtein
        
        target_lower = target_word.lower()
        candidates = []
        
        # First try direct variants
        variants = generate_word_variants(target_word, max_distance=2, language_code=language_code, keyboard_layout=keyboard_layout)
        for variant in variants:
            if variant in word_translation_cache:
                distance = Levenshtein.distance(target_lower, variant)
                candidates.append((variant, word_translation_cache[variant], distance))
        
        # If no direct variants found, try fuzzy matching against all cached words
        if not candidates:
            for cached_word in word_translation_cache.keys():
                distance = Levenshtein.distance(target_lower, cached_word.lower())
                if distance <= 2 and len(cached_word) >= 3:  # Similar length and distance
                    candidates.append((cached_word, word_translation_cache[cached_word], distance))
        
        # Sort by distance and return top matches
        candidates.sort(key=lambda x: x[2])
        return candidates[:max_suggestions]
        
    except ImportError:
        # Fallback to basic string matching if Levenshtein not available
        target_lower = target_word.lower()
        candidates = []
        
        # Try variants with increasing distance
        for distance in [1, 2]:
            variants = generate_word_variants(target_word, max_distance=distance, language_code=language_code, keyboard_layout=keyboard_layout)
            for variant in variants:
                if variant in word_translation_cache and variant != target_lower:
                    # Simple distance calculation for fallback
                    actual_distance = abs(len(variant) - len(target_lower)) + sum(1 for a, b in zip(variant, target_lower) if a != b)
                    candidates.append((variant, word_translation_cache[variant], actual_distance))
            
            # If we found candidates at this distance, stop searching
            if candidates:
                break
        
        # Sort by distance and return top matches
        candidates.sort(key=lambda x: x[2])
        return candidates[:max_suggestions]


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
            return language_code
        else:
            # Default to English if no selection
            return "en"

    def _concatenate_hyphenated_words(self, text):
        """Concatenate words that are split by hyphens at line breaks.
        
        Finds words ending with a hyphen followed by whitespace and the next word,
        then concatenates them into a single hyphenated word.
        
        Example: "some-\nword" becomes "some-word"
        """
        import re
        
        # Pattern to find hyphen at end of word followed by whitespace and another word
        # This handles cases where words are split across lines with hyphens
        pattern = r'(\w+)-\s+(\w+)'
        
        # Replace with concatenated hyphenated word
        result = re.sub(pattern, r'\1-\2', text)
        
        return result

    def _filter_valid_words(self, words):
        """Filter out non-word tokens like OCR artifacts, single characters, and gibberish."""
        valid_words = []
        self.filtered_to_original_mapping = []  # Maps filtered word indices to original word indices
        self.original_word_filtered = []  # Tracks which original words were filtered out (True=kept, False=filtered)
        
        # Single-character words for multiple languages
        valid_single_chars = {
            # English
            'I', 'a', 'A',
            # French  
            'à', 'À', 'y', 'Y', 'ô', 'Ô', 'ù', 'Ù', 'û', 'Û', 'ê', 'Ê', 'ë', 'Ë', 'é', 'É', 'è', 'È',
            # Spanish
            'ñ', 'Ñ', 'ó', 'Ó', 'í', 'Í', 'ú', 'Ú', 'ü', 'Ü',
            # German
            'ä', 'Ä', 'ö', 'Ö', 'ü', 'Ü', 'ß',
            # Italian
            'è', 'È', 'é', 'É', 'ì', 'Ì', 'í', 'Í', 'ò', 'Ò', 'ó', 'Ó', 'ù', 'Ù', 'ú', 'Ú',
            # Common single letters that can be words
            'o', 'O', 'e', 'E', 'u', 'U'
        }
        
        # Common valid 2-character words (more restrictive list)
        valid_two_chars = {'is', 'to', 'be', 'of', 'or', 'in', 'on', 'at', 'it', 'we', 'he', 'me', 'my', 'no', 'so', 'up', 'do', 'go', 'if', 'an', 'as', 'am', 'us', 'la', 'le', 'el', 'de', 'du', 'da', 'et', 'un', 'es', 'en', 'im', 'zu', 'wo', 'da', 'er', 'es', 'ja', 'se', 'il', 'ce', 'on', 'ne', 'je', 'tu', 'ou', 'si', 'au', 'ai', 'où', 'eu', 'ni', 'bu', 'vu', 'su', 'lu', 'mu', 'nu', 'pu', 'fu', 'cu', 'ru', 'ta', 'sa', 'ma', 'ca', 'va', 'fa', 'ra', 'pa', 'ba', 'ga', 'ha', 'na', 'wa', 'ya', 'za'}
        
        for original_index, word in enumerate(words):
            # Check if this is a pure punctuation token (should be preserved for typing practice)
            is_pure_punctuation = bool(re.match(r'^[^\w\s]+$', word, flags=re.UNICODE))
            
            if is_pure_punctuation:
                # Always keep standalone punctuation tokens like ';', ',', '.', etc.
                valid_words.append(word)
                self.filtered_to_original_mapping.append(original_index)
                self.original_word_filtered.append(True)
                continue
            
            # Remove leading/trailing punctuation for analysis
            clean_word = re.sub(r'^[^\w]+|[^\w]+$', '', word, flags=re.UNICODE)
            
            # Skip empty words after cleaning
            if not clean_word:
                self.original_word_filtered.append(False)
                continue
                
            # Much stricter single character filtering, but allow single digits
            if len(clean_word) == 1:
                if clean_word not in valid_single_chars and not clean_word.isdigit():
                    self.original_word_filtered.append(False)
                    continue
                    
            # Allow numbers - don't skip if it's all digits
            # Numbers should be included in typing practice
            is_pure_number = clean_word.isdigit()
            
            # Skip if it contains no alphabetic characters, UNLESS it's a pure number
            if not any(c.isalpha() for c in clean_word) and not is_pure_number:
                self.original_word_filtered.append(False)
                continue
                
            # Allow words with digits mixed with letters (like "COVID-19", "3rd", etc.)
            # if any(c.isdigit() for c in clean_word) and any(c.isalpha() for c in clean_word):
            #     continue
                
            # Skip obvious OCR artifacts (mixed case with numbers/symbols in weird patterns)
            if re.search(r'[a-z][A-Z]|[A-Z]{2,}[a-z][A-Z]', clean_word):
                self.original_word_filtered.append(False)
                continue
                
            # Much stricter 2-character word filtering, but allow numbers
            if len(clean_word) == 2:
                if clean_word.lower() not in valid_two_chars and not clean_word.isdigit():
                    # Reject all uppercase 2-letter combinations that aren't known words or numbers
                    # (these are likely OCR artifacts or abbreviations, not words for typing practice)
                    self.original_word_filtered.append(False)
                    continue
                        
            # Skip 3-letter combinations that are likely OCR artifacts, but allow numbers
            # NOTE: Made this filter much more permissive to avoid filtering valid contractions like "s'y"
            if len(clean_word) == 3:
                # Only skip if it's all consonants AND doesn't contain apostrophe (contractions are valid)
                if not clean_word.isdigit() and "'" not in clean_word:
                    vowels = set('aeiouAEIOUäöüÄÖÜáéíóúàèìòùûêîôÊÎÔÛyY')
                    if not any(c in vowels for c in clean_word):
                        self.original_word_filtered.append(False)
                        continue
                    
            # Skip if it has too many consecutive consonants (likely OCR artifact), but allow numbers
            # NOTE: Disabled this filter as it was too aggressive and blocked valid words like "systèmes"
            # if len(clean_word) >= 3 and not clean_word.isdigit():
            #     consonant_pattern = re.compile(r'[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{4,}')
            #     if consonant_pattern.search(clean_word):
            #         continue
                    
            # Skip if it's mostly non-alphabetic characters (stricter threshold), but allow pure numbers
            if not clean_word.isdigit():
                alpha_ratio = sum(1 for c in clean_word if c.isalpha()) / len(clean_word)
                # Make exception for contractions with apostrophes (e.g., "l'on", "d'un", "n'est")
                has_apostrophe = "'" in clean_word
                min_alpha_ratio = 0.5 if has_apostrophe else 0.6
                if alpha_ratio < min_alpha_ratio:
                    self.original_word_filtered.append(False)
                    continue
                
            # Skip very short words with unusual character combinations, but allow numbers and contractions
            if len(clean_word) <= 3 and not clean_word.lower().isalpha() and not clean_word.isdigit() and "'" not in clean_word:
                self.original_word_filtered.append(False)
                continue
                
            # If we get here, it's probably a valid word
            valid_words.append(word)  # Keep original word with punctuation
            self.filtered_to_original_mapping.append(original_index)
            self.original_word_filtered.append(True)
            
        return valid_words

    def __init__(self, title, text, language, ui, timed_practice=False, timer_minutes=None):
        self.title = title
        self.ui = ui  # Store reference to UI for language selection
        self.timed_practice = timed_practice
        self.timer_minutes = timer_minutes
        self.timer_end_time = None
        # Aggressively normalize ALL punctuation to standard ASCII characters
        self.text = TypingPracticeInterface.normalize_text_for_typing_static(text)
        
        # Concatenate hyphenated words before word splitting
        self.text = self._concatenate_hyphenated_words(self.text)
        
        self.language = language
        self.typed_text = ""
        self.current_word_index = 0
        # Split into words - text is now fully normalized and hyphenated words are concatenated
        raw_words = self.text.split()
        self.words = self._filter_valid_words(raw_words)
        self.current_original_word_index = 0  # Track current position in original text
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
        
        # Word-level translation cache for fuzzy matching (organized by target language)
        self.word_translation_cache = {}  # Maps target_lang -> {source_word -> translated_word}
        self.fuzzy_match_cache = {}       # Maps target_lang -> {source_word -> translated_word}
        
        # Scrolling and wrapping variables
        self.input_scroll_offset = 0  # Vertical scroll offset for input area
        self.text_scroll_offset = 0   # Vertical scroll offset for text area
        self.translation_scroll_offset = 0  # Vertical scroll offset for translation area
        self.translation_error_msg = ""
        self.target_language = "en"  # Default target language
        
        # Initialize translation functionality (lazy initialization for speed)
        self.__init_translation_lazy()
        
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
        
    def __ensure_translation_initialized(self):
        """Ensure translation is initialized on-demand"""
        if self.translation_status == "pending":
            self.__init_translation()
    
    def get_incremental_translation(self, current_text_words, max_width):
        """Get translation using sentence-based retranslation"""
        if not current_text_words:
            return ""
        
        # Initialize translation on first use
        self.__ensure_translation_initialized()
        
        # Get the source text up to current position
        current_text = ' '.join(current_text_words)
        
        # Check if we need to update our translation
        import time
        import re
        force_refresh = getattr(self, 'force_translation_refresh', False)
        current_time = time.time()
        
        # Throttle translation requests (minimum 0.5 seconds between translations)
        time_since_last = current_time - self.last_translation_time
        
        # Only translate if we have new content or force refresh
        previously_translated_text = ' '.join(self.source_lines_cache) if self.source_lines_cache else ""
        has_new_content = current_text != previously_translated_text
        
        should_translate = (has_new_content or force_refresh)
        
        # Skip translation if circuit breaker is active
        if hasattr(self, 'translation_temporarily_disabled') and self.translation_temporarily_disabled:
            should_translate = False
        
        if should_translate and (time_since_last >= 0.5 or force_refresh):
            
            # Split text into sentences (completed and current incomplete sentence)
            # Use regex to find sentence boundaries
            sentence_endings = re.compile(r'[.!?]+\s+')
            
            # Find all completed sentences
            completed_sentences = []
            remaining_text = current_text
            
            for match in sentence_endings.finditer(current_text):
                sentence_end = match.end()
                sentence = current_text[:sentence_end].strip()
                completed_sentences.append(sentence)
                remaining_text = current_text[sentence_end:].strip()
            
            # The remaining text is the current incomplete sentence
            current_incomplete_sentence = remaining_text
            
            # Initialize translation cache if needed
            if not hasattr(self, 'completed_sentence_translations'):
                self.completed_sentence_translations = []
            
            # Only translate new completed sentences (preserve existing translations)
            new_completed_count = len(completed_sentences)
            existing_completed_count = len(self.completed_sentence_translations)
            
            # Translate any new completed sentences
            if new_completed_count > existing_completed_count:
                for i in range(existing_completed_count, new_completed_count):
                    sentence = completed_sentences[i]
                    try:
                        translated_sentence = self.translator.translate(sentence, self.source_lang, self.target_language)
                        if translated_sentence and translated_sentence.strip():
                            self.completed_sentence_translations.append(translated_sentence.strip())
                        else:
                            self.completed_sentence_translations.append(sentence)  # Fallback to original
                    except Exception as e:
                        self.completed_sentence_translations.append(sentence)  # Fallback to original
                        if hasattr(self, 'ui') and self.ui:
                            self.ui.log_to_file_only(f"❌ Translation error for completed sentence: {str(e)}")
            
            # Always retranslate the current incomplete sentence as user types
            current_sentence_translation = ""
            if current_incomplete_sentence.strip():
                try:
                    current_sentence_translation = self.translator.translate(current_incomplete_sentence, self.source_lang, self.target_language)
                    if not current_sentence_translation or not current_sentence_translation.strip():
                        current_sentence_translation = current_incomplete_sentence  # Fallback to original
                except Exception as e:
                    current_sentence_translation = current_incomplete_sentence  # Fallback to original
                    if hasattr(self, 'ui') and self.ui:
                        self.ui.log_to_file_only(f"❌ Translation error for current sentence: {str(e)}")
                    
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
            
            # Combine all translations
            all_translations = self.completed_sentence_translations[:]
            if current_sentence_translation:
                all_translations.append(current_sentence_translation)
            
            # Join all translations and wrap for display
            combined_translation = ' '.join(all_translations)
            self.translated_lines_cache = self.wrap_text_to_lines(combined_translation, max_width)
            
            # Update the cache to track what we've translated
            self.source_lines_cache = current_text_words[:]
            self.last_translation_time = current_time
            
            # Reset force refresh flag
            if hasattr(self, 'force_translation_refresh'):
                self.force_translation_refresh = False
        
        # Return the combined translation
        return '\n'.join(self.translated_lines_cache) if self.translated_lines_cache else current_text
    
    def __init_translation_lazy(self):
        """Fast lazy initialization - defer actual setup until needed"""
        # Set default values without doing expensive initialization
        self.translation_status = "pending"  # Will initialize on first use
        self.target_language = "en"  # Default to English translation (will be overridden)
        self.translator = None
        
        # Map text language to argostranslate language codes
        source_lang_map = {
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
        
        self.source_lang = source_lang_map.get(self.language, 'fr')  # Use book's language
        
    def __init_translation(self):
        """Initialize translation functionality using argostranslate"""
        # Use the target language set by the user (defaults to English if not set)
        if not hasattr(self, 'target_language') or not self.target_language:
            self.target_language = "en"
        
        # Try to import and set up argostranslate
        try:
            # Import within suppression context to prevent import-time warnings
            with suppress_stderr():
                import argostranslate.package
                import argostranslate.translate
            
            # Map text language to argostranslate language codes
            source_lang_map = {
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
            
            self.source_lang = source_lang_map.get(self.language, 'fr')  # Default to French
            
            # Create a simple translator wrapper for argostranslate
            class ArgosTranslator:
                def __init__(self, source_lang, target_lang):
                    self.source_lang = source_lang
                    self.target_lang = target_lang
                
                def translate(self, text, source_lang=None, target_lang=None):
                    # Use provided languages or fall back to instance defaults
                    src = source_lang or self.source_lang
                    tgt = target_lang or self.target_lang
                    # Suppress stderr during translation to avoid stanza warnings
                    with suppress_stderr():
                        return argostranslate.translate.translate(text, src, tgt)
            
            # Create translator and check packages within suppression context
            with suppress_stderr():
                self.translator = ArgosTranslator(self.source_lang, self.target_language)
                
                # Check if language packages are installed first
                installed_packages = argostranslate.package.get_installed_packages()
                available_pairs = [(pkg.from_code, pkg.to_code) for pkg in installed_packages]
            
            if (self.source_lang, self.target_language) not in available_pairs:
                self.translation_status = "missing_package"
                self.translation_error_msg = f"Language package {self.source_lang}→{self.target_language} not installed"
                self.translator = None
            else:
                # Test the translation with a meaningful phrase from the source language
                test_phrases = {
                    'fr': 'bonjour le monde',  # "hello world" in French
                    'de': 'hallo welt',        # "hello world" in German 
                    'es': 'hola mundo',        # "hello world" in Spanish
                    'it': 'ciao mondo',        # "hello world" in Italian
                    'pt': 'olá mundo',         # "hello world" in Portuguese
                    'ru': 'привет мир',        # "hello world" in Russian
                    'zh': '你好世界',           # "hello world" in Chinese
                    'ja': 'こんにちは世界',      # "hello world" in Japanese
                }
                
                # Skip the test translation during initialization to speed up startup
                # We'll test translation on-demand during actual typing
                test_result = "test_passed"  # Assume it works if packages are installed
                
                if test_result and test_result.strip():
                    # Any translation result (even if identical) is acceptable
                    # as some models might return the same for certain inputs
                    self.translation_status = "available"
                else:
                    raise Exception("argostranslate test translation returned empty result")
        except ImportError:
            self.translation_status = "missing_library"
            self.translation_error_msg = "argostranslate not installed"
            self.translator = None
        except Exception as e:
            error_msg = str(e)
            
            # Handle specific dependency issues
            if "sacremoses" in error_msg:
                self.translation_status = "missing_dependency"
                self.translation_error_msg = "Missing sacremoses dependency"
            elif "No module named" in error_msg:
                self.translation_status = "missing_dependency"
                self.translation_error_msg = f"Missing dependency: {error_msg}"
            else:
                self.translation_status = "error"
                self.translation_error_msg = f"argostranslate error: {error_msg}"
            
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
    
    def _get_word_cache_for_target_language(self, target_lang=None):
        """Get the word translation cache for the specified target language"""
        if target_lang is None:
            target_lang = getattr(self, 'target_language', 'en')
        
        if target_lang not in self.word_translation_cache:
            self.word_translation_cache[target_lang] = {}
        
        return self.word_translation_cache[target_lang]
    
    def _get_fuzzy_cache_for_target_language(self, target_lang=None):
        """Get the fuzzy match cache for the specified target language"""
        if target_lang is None:
            target_lang = getattr(self, 'target_language', 'en')
        
        if target_lang not in self.fuzzy_match_cache:
            self.fuzzy_match_cache[target_lang] = {}
        
        return self.fuzzy_match_cache[target_lang]
    
    def _get_keyboard_layout_for_language(self, language_code):
        """Determine keyboard layout based on language code"""
        if not language_code:
            return 'qwerty'
        
        # AZERTY keyboards (primarily French-speaking regions)
        if language_code in ['fr', 'be', 'dz', 'ma', 'tn']:  # France, Belgium, Algeria, Morocco, Tunisia
            return 'azerty'
        
        # QWERTZ keyboards (primarily German-speaking regions)
        elif language_code in ['de', 'at', 'ch', 'li']:  # Germany, Austria, Switzerland, Liechtenstein
            return 'qwertz'
        
        # QWERTY keyboards (most other languages)
        else:
            return 'qwerty'
    
    def translate_word_with_fuzzy_fallback(self, word):
        """Translate a single word with fuzzy matching fallback for failed translations"""
        if not word or not word.strip():
            return word
            
        word_clean = word.strip().lower()
        
        # Get target-language-specific caches
        word_cache = self._get_word_cache_for_target_language()
        fuzzy_cache = self._get_fuzzy_cache_for_target_language()
        
        # Check word cache first
        if word_clean in word_cache:
            return word_cache[word_clean]
        
        # Try direct translation
        if self.translator and self.translation_status == "available":
            try:
                with suppress_stderr():
                    direct_translation = self.translator.translate(word)
                    if direct_translation and direct_translation.strip() and direct_translation.lower() != word_clean:
                        # Cache successful translation in target-language-specific cache
                        word_cache[word_clean] = direct_translation
                        if hasattr(self, 'ui') and self.ui:
                            self.ui.log_to_file_only(f"💾 Cached translation: '{word}' → '{direct_translation}' ({self.target_language})")
                        return direct_translation
            except Exception as e:
                if hasattr(self, 'ui') and self.ui:
                    self.ui.log_to_file_only(f"Direct translation failed for '{word}': {str(e)}")
        
        # If direct translation failed, try fuzzy matching
        if word_clean in fuzzy_cache:
            return fuzzy_cache[word_clean]
        
        # Find similar words in cache and try their translations
        # Determine keyboard layout from source language
        keyboard_layout = self._get_keyboard_layout_for_language(getattr(self, 'source_lang', None))
        
        similar_matches = find_similar_words_in_cache(
            word_clean, 
            word_cache,  # Use target-language-specific cache
            max_suggestions=3,
            language_code=getattr(self, 'source_lang', None),
            keyboard_layout=keyboard_layout
        )
        
        if similar_matches:
            # Try the closest match
            closest_word, closest_translation, distance = similar_matches[0]
            if distance <= 2:  # Only use very close matches
                if hasattr(self, 'ui') and self.ui:
                    self.ui.log_to_file_only(f"🔍 Fuzzy match: '{word}' → '{closest_word}' → '{closest_translation}' (distance: {distance}, target: {self.target_language})")
                
                # Cache the fuzzy match result in target-language-specific cache
                fuzzy_cache[word_clean] = closest_translation
                return closest_translation
        
        # If no fuzzy match found, try translating similar word variants directly
        variants = generate_word_variants(
            word_clean, 
            max_distance=1,
            language_code=getattr(self, 'source_lang', None),
            keyboard_layout=keyboard_layout
        )
        for variant in variants[:5]:  # Try only first 5 variants to avoid slowdown
            if variant != word_clean and self.translator and self.translation_status == "available":
                try:
                    with suppress_stderr():
                        variant_translation = self.translator.translate(variant)
                        if variant_translation and variant_translation.strip() and variant_translation.lower() != variant:
                            if hasattr(self, 'ui') and self.ui:
                                self.ui.log_to_file_only(f"🔍 Variant match: '{word}' → '{variant}' → '{variant_translation}' (target: {self.target_language})")
                            
                            # Cache both the variant and the original word in target-language-specific caches
                            word_cache[variant] = variant_translation
                            fuzzy_cache[word_clean] = variant_translation
                            return variant_translation
                except Exception:
                    continue  # Try next variant
        
        # If all fuzzy matching failed, return original word
        return word
    
    def _translate_text_word_by_word(self, text):
        """Fallback method: translate text word by word with fuzzy matching"""
        if not text or not text.strip():
            return text
        
        words = text.split()
        translated_words = []
        
        for word in words:
            # Preserve punctuation by separating it from the word
            import re
            match = re.match(r'^(\W*)(.*?)(\W*)$', word)
            if match:
                prefix, core_word, suffix = match.groups()
                if core_word:
                    translated_core = self.translate_word_with_fuzzy_fallback(core_word)
                    translated_words.append(prefix + translated_core + suffix)
                else:
                    translated_words.append(word)  # Only punctuation
            else:
                translated_words.append(self.translate_word_with_fuzzy_fallback(word))
        
        return ' '.join(translated_words)
    
    def get_translation_for_display(self, text):
        """Get translation for display - translate full text without word limits"""
        import time
        
        # Initialize translation on first use
        self.__ensure_translation_initialized()
        
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
                
                # Extract and cache individual word translations in target-language-specific cache
                source_words = text.split()
                translated_words = translation.split()
                if len(source_words) == len(translated_words):
                    word_cache = self._get_word_cache_for_target_language()
                    for src_word, trans_word in zip(source_words, translated_words):
                        src_clean = src_word.strip().lower()
                        if src_clean and trans_word.strip() and src_clean != trans_word.lower():
                            word_cache[src_clean] = trans_word.strip()
                
                return translation
            else:
                # If full text translation is empty, try word-by-word with fuzzy fallback
                return self._translate_text_word_by_word(text)
            
        except Exception as e:
            # Track translation errors for circuit breaker
            if current_time - self.translation_error_window_start > 60:  # Reset error count every minute
                self.translation_error_count = 0
                self.translation_error_window_start = current_time
            
            self.translation_error_count += 1
            
            # Log specific error details for debugging
            if hasattr(self, 'ui') and self.ui:
                error_msg = str(e)
                self.ui.log_to_file_only(f"❌ argostranslate translation error #{self.translation_error_count}: {error_msg}")
                
                # Check for specific error types
                if any(keyword in error_msg.lower() for keyword in ['rate', 'limit', 'quota', '429']):
                    self.ui.log_to_file_only("⚠️ Rate limiting detected - translation will resume automatically")
                elif any(keyword in error_msg.lower() for keyword in ['quota', 'character', 'usage']):
                    self.ui.log_to_file_only("⚠️ Translation quota/usage limit reached")
                elif any(keyword in error_msg.lower() for keyword in ['network', 'connection', 'timeout']):
                    self.ui.log_to_file_only("⚠️ Network connection issue - translation will retry")
                
                # Enable circuit breaker if too many errors
                if self.translation_error_count >= 7:  # Increased threshold from 5 to 7
                    self.translation_temporarily_disabled = True
                    self.ui.log_to_file_only("🔌 Translation temporarily disabled due to repeated errors (will retry in 45s)")
                    
            # If translation fails, try word-by-word fallback before giving up
            try:
                return self._translate_text_word_by_word(text)
            except Exception:
                # If even word-by-word fails, return original text
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
        
        # Add partial word progress if currently typing (but not if word was skipped)
        if self.current_word_index < len(self.words) and hasattr(self, 'current_char_index'):
            current_word = self.words[self.current_word_index]
            # Only count partial progress if we have typed characters AND we haven't just skipped to this word
            current_typed_word = self.get_current_typed_word()
            if self.current_char_index > 0 and current_typed_word and len(current_typed_word.strip()) > 0:
                # Add fractional progress for current word only if we're actively typing it
                progress = min(self.current_char_index / len(current_word), 1.0)
                words_typed += progress
        
        return int(words_typed / elapsed_minutes)
    
    def update_wpm_if_needed(self):
        """Update WPM every 2 seconds, but not during skips"""
        current_time = time.time()
        if self.last_wpm_update is None or current_time - self.last_wpm_update >= 2:  # Update every 2 seconds
            self.wpm = self.calculate_wpm()
            self.last_wpm_update = current_time

    def _advance_original_position(self):
        """Advance position in original text, skipping over any filtered words that come before the next valid word."""
        if self.current_word_index >= len(self.words):
            return  # No more filtered words
        
        # Get the original position of the current filtered word
        current_filtered_index = self.current_word_index - 1  # Previous word we just advanced from
        if current_filtered_index >= 0 and current_filtered_index < len(self.filtered_to_original_mapping):
            current_original_pos = self.filtered_to_original_mapping[current_filtered_index]
            
            # Advance from this position, skipping filtered words until we find the next valid word
            self.current_original_word_index = current_original_pos + 1
            
            # Skip over any filtered words in the original text
            while (self.current_original_word_index < len(self.original_word_filtered) and 
                   not self.original_word_filtered[self.current_original_word_index]):
                self.current_original_word_index += 1

    def _retreat_original_position(self):
        """Retreat position in original text when backspacing over words."""
        if self.current_word_index >= 0 and self.current_word_index < len(self.filtered_to_original_mapping):
            # Set original position to match the current filtered word
            self.current_original_word_index = self.filtered_to_original_mapping[self.current_word_index]

    def run(self):
        """Main typing practice loop"""
        stdscr = self.ui.stdscr
        height, width = stdscr.getmaxyx()
        
        # Clear the main screen
        stdscr.clear()
        stdscr.refresh()
        
        # Completely disable mouse events during typing practice to prevent UI interference
        availmask, original_mousemask = curses.mousemask(0)
        
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
        
        # Skip initial full-text translation - we use incremental translation during typing
        # This significantly speeds up the startup time
        self.translated_text = ""  # Will be populated incrementally during typing
        
        # Pre-translate common words to avoid repeated API calls
        word_translations = {}
        
        # Mouse and scrollbars are disabled to prevent UI interference

        # Main practice loop
        self.start_time = time.time()
        if self.timed_practice and self.timer_minutes:
            self.timer_end_time = self.start_time + (self.timer_minutes * 60)
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
                # Clear and redraw borders on full redraw
                text_win.clear()
                translation_win.clear()
                input_win.clear()
                
                # Draw borders
                text_win.box()
                translation_win.box()
                input_win.box()
            else:
                # For partial redraws, still need to clear content areas to prevent color artifacts
                # Clear text content area (leave borders intact)
                for clear_y in range(1, text_height - 1):
                    try:
                        text_win.addstr(clear_y, 1, " " * (width - 3), curses.color_pair(0))
                    except curses.error:
                        pass
                
                # Clear input content area (leave borders intact)
                for clear_y in range(1, input_height - 1):
                    try:
                        input_win.addstr(clear_y, 1, " " * (width - 3), curses.color_pair(0))
                    except curses.error:
                        pass
                
                # Clear translation content area (leave borders intact)
                for clear_y in range(1, translation_height - 1):
                    try:
                        translation_win.addstr(clear_y, 1, " " * (width - 3), curses.color_pair(0))
                    except curses.error:
                        pass
            
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
                    if word_count + words_in_line > self.current_original_word_index:
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
                            if word_index == self.current_original_word_index:
                                # Current word - highlight character by character
                                current_typed_word = self.get_current_typed_word()
                                expected_word = word
                                
                                # Clear the entire current word area first to remove any background colors
                                # Use a wider clearing area to ensure all color artifacts are removed
                                clear_width = min(len(expected_word) + 3, width - current_x - 2)
                                try:
                                    text_win.addstr(y_pos, current_x, " " * clear_width, curses.color_pair(0))
                                except curses.error:
                                    pass
                                
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
                                            # Correct character - yellow with underline for better visibility
                                            text_win.addstr(y_pos, current_x + char_idx, char, 
                                                          curses.color_pair(8) | curses.A_BOLD | curses.A_UNDERLINE)
                                        else:
                                            # Incorrect character - white on red background
                                            text_win.addstr(y_pos, current_x + char_idx, char, 
                                                          curses.color_pair(1) | curses.A_BOLD)
                                    else:
                                        # Character not yet typed - highlight in yellow (current word)
                                        text_win.addstr(y_pos, current_x + char_idx, char,
                                                      curses.color_pair(8))
                                
                                # Add space after word
                                if current_x + len(expected_word) + 1 < width - 1:
                                    text_win.addstr(y_pos, current_x + len(expected_word), " ")
                                
                            elif word_index < self.current_original_word_index:
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
                if self.translation_status == "pending":
                    translation_win.addstr(0, 1, "Translation:", curses.A_BOLD | curses.color_pair(3))
                    info_msg = "📝 Translation will initialize when you start typing"
                    translation_win.addstr(1, 1, info_msg, curses.color_pair(3))
                elif self.translation_status == "disabled":
                    translation_win.addstr(0, 1, "Translation Info:", curses.A_BOLD | curses.color_pair(3))
                    info_msg = "📝 Translation not available - showing original text"
                    help_msg = "Install argostranslate for translation support"
                    translation_win.addstr(1, 1, info_msg, curses.color_pair(3))
                    translation_win.addstr(2, 1, help_msg, curses.color_pair(3))
                elif self.translation_status == "missing_library":
                    translation_win.addstr(0, 1, "Translation Warning:", curses.A_BOLD | curses.color_pair(3))
                    warning_msg = "⚠️ Translation disabled - argostranslate not installed"
                    install_msg = "Install with: pip install argostranslate"
                    translation_win.addstr(1, 1, warning_msg, curses.color_pair(3))
                    translation_win.addstr(2, 1, install_msg, curses.color_pair(3))
                elif self.translation_status == "missing_package":
                    translation_win.addstr(0, 1, "Translation Warning:", curses.A_BOLD | curses.color_pair(3))
                    warning_msg = f"⚠️ Language package not installed"
                    install_msg = f"Install with: argospm install translate-{self.source_lang}_{self.target_language}"
                    translation_win.addstr(1, 1, warning_msg, curses.color_pair(3))
                    translation_win.addstr(2, 1, install_msg[:width-3], curses.color_pair(3))
                elif self.translation_status == "missing_dependency":
                    translation_win.addstr(0, 1, "Translation Warning:", curses.A_BOLD | curses.color_pair(3))
                    warning_msg = f"⚠️ {self.translation_error_msg}"
                    help_msg = "Restart development shell to reload dependencies"
                    translation_win.addstr(1, 1, warning_msg[:width-3], curses.color_pair(3))
                    translation_win.addstr(2, 1, help_msg, curses.color_pair(3))
                elif self.translation_status == "error":
                    translation_win.addstr(0, 1, "Translation Error:", curses.A_BOLD | curses.color_pair(1))
                    error_msg = f"⚠️ {self.translation_error_msg}"
                    translation_win.addstr(1, 1, error_msg[:width-3], curses.color_pair(1))
                else:
                    # Translation is available - show normal translation
                    translation_win.addstr(0, 1, "Live Translation:", curses.A_BOLD)
                    
                    # Initialize translation when user starts typing
                    if self.translation_status == "pending" and (self.typed_text or self.current_word_index > 0):
                        self.__ensure_translation_initialized()
                    
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
                            # Use cached wrapped lines from get_incremental_translation for consistency
                            wrapped_lines = getattr(self, 'translated_lines_cache', live_translation.split('\n'))
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
                                    # More accurate calculation based on actual translation content
                                    typing_progress = self.current_word_index / max(1, len(self.words))
                                    
                                    # Estimate current line in translation more accurately
                                    # If we have sentence-based translations, try to align better
                                    if hasattr(self, 'completed_sentence_translations') and self.completed_sentence_translations:
                                        # Calculate based on completed sentences vs total estimated sentences
                                        completed_chars = sum(len(s) for s in self.completed_sentence_translations)
                                        if hasattr(self, 'translated_lines_cache') and self.translated_lines_cache:
                                            total_chars = sum(len(line) for line in self.translated_lines_cache)
                                            if total_chars > 0:
                                                char_progress = completed_chars / total_chars
                                                estimated_current_line = int(char_progress * len(wrapped_lines))
                                            else:
                                                estimated_current_line = int(typing_progress * len(wrapped_lines))
                                        else:
                                            estimated_current_line = int(typing_progress * len(wrapped_lines))
                                    else:
                                        estimated_current_line = int(typing_progress * len(wrapped_lines))
                                    
                                    # Auto-scroll to keep the current position visible
                                    # When near the end, prioritize showing the end; otherwise prefer showing from beginning early on
                                    # Also check if we're close to the end of visible content to trigger scrolling
                                    content_near_end = (estimated_current_line >= len(wrapped_lines) - effective_display_height // 2)
                                    
                                    if typing_progress > 0.8 or content_near_end:  # Close to end of text or content - more aggressive scrolling
                                        # Always scroll to show the very end of the translation
                                        target_position = max_scroll
                                        # Skip smooth scrolling near the end to ensure we reach max_scroll
                                        self.translation_scroll_offset = target_position
                                        self._last_auto_scroll_position = target_position
                                    elif typing_progress > 0.6:  # Approaching end
                                        # Gradually transition to showing more of the end
                                        end_bias = (typing_progress - 0.6) / 0.2  # Scale from 0 to 1
                                        middle_pos = max(0, estimated_current_line - effective_display_height // 2)
                                        target_position = int(middle_pos * (1 - end_bias) + max_scroll * end_bias)
                                        
                                        # Apply smooth scrolling
                                        if hasattr(self, '_last_auto_scroll_position'):
                                            max_jump = effective_display_height // 3  # Faster scrolling when approaching end
                                            if abs(target_position - self._last_auto_scroll_position) > max_jump:
                                                if target_position > self._last_auto_scroll_position:
                                                    target_position = self._last_auto_scroll_position + max_jump
                                                else:
                                                    target_position = self._last_auto_scroll_position - max_jump
                                        
                                        self.translation_scroll_offset = target_position
                                        self._last_auto_scroll_position = target_position
                                    elif typing_progress < 0.3:  # Early in typing - stay near beginning
                                        # Keep translation near the beginning to avoid jumping ahead
                                        target_position = min(estimated_current_line // 3, max(0, estimated_current_line - 2))
                                        
                                        # Apply smooth scrolling
                                        if hasattr(self, '_last_auto_scroll_position'):
                                            max_jump = effective_display_height // 2  # Standard scrolling speed
                                            if abs(target_position - self._last_auto_scroll_position) > max_jump:
                                                if target_position > self._last_auto_scroll_position:
                                                    target_position = self._last_auto_scroll_position + max_jump
                                                else:
                                                    target_position = self._last_auto_scroll_position - max_jump
                                        
                                        self.translation_scroll_offset = target_position
                                        self._last_auto_scroll_position = target_position
                                    else:
                                        # Show current position in the middle of the window for better context
                                        target_position = max(0, estimated_current_line - effective_display_height // 2)
                                        
                                        # Apply smooth scrolling
                                        if hasattr(self, '_last_auto_scroll_position'):
                                            max_jump = effective_display_height // 2  # Standard scrolling speed
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
                            
                            # Update current translation cache for consistent state
                            self.current_translation_cache = live_translation
                            
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
                
                # Display WPM and timer (if timed practice)
                wpm_text = f"WPM: {self.wpm}"
                if self.timed_practice and self.timer_end_time:
                    remaining_seconds = max(0, int(self.timer_end_time - time.time()))
                    remaining_minutes = remaining_seconds // 60
                    remaining_seconds = remaining_seconds % 60
                    timer_text = f" | Time: {remaining_minutes:02d}:{remaining_seconds:02d}"
                    wpm_and_timer = wpm_text + timer_text
                else:
                    wpm_and_timer = wpm_text
                
                input_win.addstr(input_height - 3, 1, wpm_and_timer)
                input_win.addstr(input_height - 2, 1, "Space: next word | Tab: skip word | Ctrl+n: skip line | Ctrl+O: skip visible block | PgUp/PgDn: scroll translation | ESC: exit")
                
                # Show progress on bottom right corner
                if self.timed_practice:
                    # For timed practice, show words typed instead of total progress
                    progress = f"Words: {self.actually_typed_words}"
                else:
                    # For complete text practice, show standard progress
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
                    
                    # Don't break here for timer expiry - let it be handled by the completion stats section
                    # so the user can see their final stats before exiting
                    continue
                
                # Handle input
                if key == 27:  # ESC key
                    break
                # Mouse events are disabled during typing practice to prevent interference
                elif key == 9:  # TAB key - skip current word
                    # Initialize translation on first keystroke
                    if self.translation_status == "pending":
                        self.__ensure_translation_initialized()
                    
                    if self.current_word_index < len(self.words):
                        # Throttle rapid Tab presses to prevent translation system overload
                        current_time = time.time()
                        if hasattr(self, '_last_tab_time') and current_time - self._last_tab_time < 0.2:
                            # Too fast - skip translation refresh for this press
                            skip_translation_refresh = True
                        else:
                            skip_translation_refresh = False
                        self._last_tab_time = current_time
                        
                        # Get the current word being typed and the expected word
                        current_typed_word = self.get_current_typed_word()
                        expected_word = self.words[self.current_word_index]
                        
                        if current_typed_word and len(current_typed_word) < len(expected_word):
                            # Complete the current word by adding the remaining characters
                            remaining_chars = expected_word[len(current_typed_word):]
                            self.typed_text += remaining_chars + " "
                        else:
                            # No partial word or word already complete, add the full word and space
                            if not self.typed_text.endswith(' '):
                                # Remove any partial incorrect word and replace with correct one
                                if current_typed_word:
                                    # Remove the incorrect partial word
                                    self.typed_text = self.typed_text[:-len(current_typed_word)]
                                self.typed_text += expected_word + " "
                            else:
                                # Already at word boundary, just add the word
                                self.typed_text += expected_word + " "
                        
                        self.current_word_index += 1
                        self.skipped_words += 1
                        
                        # Advance position in original text, skipping over any filtered words
                        self._advance_original_position()
                        
                        # Only refresh translation cache if not throttling rapid presses
                        if not skip_translation_refresh:
                            # Preserve existing translation while allowing incremental updates
                            # Don't clear the cache completely to avoid flickering
                            
                            # Set flag to allow translation refresh without clearing display
                            self.force_translation_refresh = True
                        
                        draw_screen(full_redraw=False)
                elif key == 14:  # CTRL+n key - skip one line
                    # Initialize translation on first keystroke
                    if self.translation_status == "pending":
                        self.__ensure_translation_initialized()
                    
                    if self.current_word_index < len(self.words):
                        # Throttle rapid Ctrl+n presses to prevent translation system overload
                        current_time = time.time()
                        if hasattr(self, '_last_ctrl_n_time') and current_time - self._last_ctrl_n_time < 0.15:
                            # Too fast - skip translation refresh for this press
                            skip_translation_refresh = True
                        else:
                            skip_translation_refresh = False
                        self._last_ctrl_n_time = current_time
                        
                        # Calculate words per line based on display width (for single line skip)
                        avg_word_length = 5  # Average word length estimate
                        max_width = width - 4  # Account for borders
                        estimated_words_per_line = max(8, max_width // (avg_word_length + 1))
                        
                        # Skip words for approximately one line
                        target_idx = min(len(self.words), self.current_word_index + estimated_words_per_line)
                        
                        # Fast bulk skip - avoid expensive string concatenation loop
                        if target_idx > self.current_word_index:
                            # Calculate how many words we're skipping
                            words_to_skip = target_idx - self.current_word_index
                            
                            # Bulk string concatenation - much faster than loop
                            skipped_words_text = " ".join(self.words[self.current_word_index:target_idx]) + " "
                            self.typed_text += skipped_words_text
                            
                            # Update counters in one operation
                            self.skipped_words += words_to_skip
                            self.current_word_index = target_idx
                            
                            # Advance position in original text, skipping over any filtered words
                            self._advance_original_position()
                        
                        # Only refresh translation cache occasionally to avoid lag
                        if not skip_translation_refresh:
                            self._ctrl_n_skip_count = getattr(self, '_ctrl_n_skip_count', 0) + 1
                            # Only refresh translation every 3rd ctrl+n press to reduce lag
                            if self._ctrl_n_skip_count % 3 == 0:
                                self.force_translation_refresh = True
                        
                        # Redraw screen to show changes
                        draw_screen(full_redraw=False)
                        
                        # Flush any buffered input to prevent double characters after Ctrl+n
                        curses.flushinp()
                        
                elif key == 78 or key == 527 or key == 538 or key == 526 or key == 1038 or key == 2078 or key == 15:  # Ctrl+Shift+N or Ctrl+O (visible block skip - multiple lines)
                    # Initialize translation on first keystroke
                    if self.translation_status == "pending":
                        self.__ensure_translation_initialized()
                    
                    if self.current_word_index < len(self.words):
                        # Throttle rapid Ctrl+Shift+N presses to prevent translation system overload
                        current_time = time.time()
                        if hasattr(self, '_last_ctrl_shift_n_time') and current_time - self._last_ctrl_shift_n_time < 0.3:
                            # Too fast - skip translation refresh for this press
                            skip_translation_refresh = True
                        else:
                            skip_translation_refresh = False
                        self._last_ctrl_shift_n_time = current_time
                        
                        # Skip entire visible block - calculate how much text is currently visible
                        words_skipped = 0
                        start_position = self.current_word_index
                        
                        # Calculate visible area dimensions
                        text_height = height // 3  # Original text window takes 1/3 of screen
                        display_height = text_height - 2  # Account for borders
                        effective_display_height = max(display_height - 1, 5)  # Leave space at bottom, minimum 5 lines
                        
                        # Estimate words per line based on display width (more conservative estimate)
                        avg_word_length = 4  # Shorter average to get more words per line
                        max_width = width - 4  # Account for borders
                        estimated_words_per_line = max(10, max_width // (avg_word_length + 1))
                        
                        # Calculate total words in visible block - multiply by 2 to ensure full screen coverage
                        words_in_visible_block = int(estimated_words_per_line * effective_display_height * 2)
                        
                        # Debug: show calculation temporarily
                        debug_info = f"[H:{effective_display_height} W:{estimated_words_per_line} T:{words_in_visible_block}] "
                        
                        # Be very aggressive - skip at least 150 words or the calculated block size
                        skip_amount = max(words_in_visible_block, 150)
                        target_idx = min(len(self.words), self.current_word_index + skip_amount)
                        
                        # Add debug info to typed text temporarily
                        self.typed_text += debug_info
                        
                        # Skip all words to the target position
                        while self.current_word_index < target_idx and self.current_word_index < len(self.words):
                            self.typed_text += self.words[self.current_word_index] + " "
                            self.current_word_index += 1
                            self.skipped_words += 1
                            words_skipped += 1
                        
                        # Update original text position after skipping multiple words
                        self._advance_original_position()
                        
                        # Only refresh translation cache if not throttling rapid presses
                        if not skip_translation_refresh:
                            # Set flag to allow translation refresh without clearing display
                            self.force_translation_refresh = True
                        
                        draw_screen(full_redraw=False)
                        
                        # Flush any buffered input to prevent double characters after Ctrl+Shift+N
                        curses.flushinp()
                        
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
                            
                            # Retreat position in original text when backspacing over words
                            if old_word_index > self.current_word_index:
                                self._retreat_original_position()
                        
                        self.typed_text = self.typed_text[:-1]
                        
                        # Update translation cache to sync with new cursor position
                        current_words = self.typed_text.split()
                        current_word_count = len(current_words)
                        
                        # If we've deleted words, trim the translation cache accordingly
                        if hasattr(self, 'source_lines_cache') and self.source_lines_cache:
                            cached_word_count = len(' '.join(self.source_lines_cache).split()) if self.source_lines_cache else 0
                            if current_word_count < cached_word_count:
                                # Rebuild cache to match current text
                                if current_words:
                                    # Find how many complete words we should keep in cache
                                    keep_words = current_word_count
                                    current_text = ' '.join(current_words)
                                    
                                    # Update source cache
                                    self.source_lines_cache = current_words
                                    
                                    # Trim translation cache to match (estimate proportionally)
                                    if hasattr(self, 'translated_lines_cache') and self.translated_lines_cache:
                                        # Estimate how much of the translation to keep based on word ratio
                                        full_translated_text = ' '.join(self.translated_lines_cache)
                                        translated_words = full_translated_text.split()
                                        
                                        if translated_words and cached_word_count > 0:
                                            # Calculate ratio of words to keep
                                            keep_ratio = current_word_count / cached_word_count
                                            words_to_keep = int(len(translated_words) * keep_ratio)
                                            
                                            if words_to_keep > 0:
                                                trimmed_translation = ' '.join(translated_words[:words_to_keep])
                                                self.translated_lines_cache = self.wrap_text_to_lines(trimmed_translation, 80)
                                            else:
                                                self.translated_lines_cache = []
                                else:
                                    # No text left, clear caches
                                    self.source_lines_cache = []
                                    self.translated_lines_cache = []
                        
                        draw_screen(full_redraw=False)
                elif key == ord(' '):  # Space - check word completion
                    # Initialize translation on first keystroke
                    if self.translation_status == "pending":
                        self.__ensure_translation_initialized()
                    
                    if self.current_word_index < len(self.words):
                        current_typed_word = self.get_current_typed_word()
                        expected_word = self.words[self.current_word_index]
                        
                        # Normalize both for comparison
                        typed_normalized = TypingPracticeInterface.normalize_accents(current_typed_word)
                        expected_normalized = TypingPracticeInterface.normalize_accents(expected_word)
                        
                        # Handle word completion properly to avoid duplication
                        if current_typed_word:
                            # Remove the partially typed word from typed_text before adding the complete word
                            words_list = self.typed_text.split()
                            if words_list and not self.typed_text.endswith(' '):
                                # Remove the last partial word
                                words_list = words_list[:-1]
                                self.typed_text = ' '.join(words_list)
                                if self.typed_text:
                                    self.typed_text += ' '
                        
                        if typed_normalized.lower() == expected_normalized.lower():
                            # Correct word
                            self.typed_text += expected_word + " "
                            self.actually_typed_words += 1
                        else:
                            # Incorrect word - mark it and move on
                            self.incorrect_words.add(self.current_word_index)
                            self.typed_text += expected_word + " "
                        
                        self.current_word_index += 1
                        
                        # Advance position in original text, skipping over any filtered words
                        self._advance_original_position()
                        
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
                elif key == ord('\n') or key == ord('\r') or key == 10 or key == 13:  # Enter/Return keys
                    # Only allow newline input if there's a corresponding newline in the original text
                    if self.current_word_index < len(self.words):
                        # Check if the current position in original text has a newline
                        # Look at the original text to see if there should be a newline here
                        current_pos = len(self.typed_text.replace(' ', ''))  # Character position ignoring spaces
                        original_text = ' '.join(self.words)
                        
                        # Find if there's a natural line break at this position
                        lines = self.original_text.split('\n') if hasattr(self, 'original_text') else [original_text]
                        
                        # For now, we'll be conservative and generally prevent manual newlines
                        # since the text wrapping is handled automatically
                        # Only allow if we can detect this should be a paragraph break
                        pass  # Don't add newline - let auto-wrapping handle it
                elif 32 <= key <= 126:  # Printable characters
                    # Initialize translation on first keystroke
                    if self.translation_status == "pending" and not self.typed_text:
                        self.__ensure_translation_initialized()
                    
                    # Add character to typed text
                    self.typed_text += chr(key)
                    draw_screen(full_redraw=False)
                else:
                    # Debug: Log unhandled key codes to help identify Ctrl+Shift+N
                    # This will help users find the correct key code for their terminal
                    if hasattr(self, '_debug_unknown_keys'):
                        if key not in self._debug_unknown_keys:
                            self._debug_unknown_keys.add(key)
                            # Show the key code temporarily in typed text for debugging
                            if hasattr(self, '_show_debug'):
                                self.typed_text += f"[KEY:{key}] "
                                draw_screen(full_redraw=False)
                    else:
                        self._debug_unknown_keys = {key}
                        # Enable debug mode on first unknown key
                        self._show_debug = True
                
                # Check if practice is complete (either all words typed or timer expired)
                practice_complete = self.current_word_index >= len(self.words)
                timer_expired = self.timed_practice and self.timer_end_time and time.time() >= self.timer_end_time
                
                
                if practice_complete or timer_expired:
                    # Calculate final WPM before showing completion stats
                    self.wpm = self.calculate_wpm()
                    
                    # Clear any pending input before showing completion stats
                    input_win.nodelay(True)
                    cleared_count = 0
                    while input_win.getch() != -1:
                        cleared_count += 1
                        if cleared_count > 10:  # Prevent infinite loop
                            break
                    input_win.nodelay(False)
                    
                    # Add a small delay to ensure screen updates properly
                    time.sleep(0.1)
                    
                    # Show completion stats
                    input_win.clear()
                    input_win.box()
                    
                    total_words = len(self.words)
                    correct_words = total_words - len(self.incorrect_words) - self.skipped_words
                    accuracy = (correct_words / total_words) * 100 if total_words > 0 else 0
                    
                    try:
                        if timer_expired:
                            input_win.addstr(2, 2, f"⏰ Time's Up! ({self.timer_minutes} minutes)")
                        else:
                            input_win.addstr(2, 2, f"🎉 Practice Complete!")
                        input_win.addstr(3, 2, f"Final WPM: {self.wpm}")
                        input_win.addstr(4, 2, f"Accuracy: {accuracy:.1f}%")
                        input_win.addstr(5, 2, f"Words typed: {self.actually_typed_words}")
                        input_win.addstr(6, 2, f"Words skipped: {self.skipped_words}")
                        input_win.addstr(7, 2, f"Incorrect words: {len(self.incorrect_words)}")
                        input_win.addstr(9, 2, "Press Ctrl+C to exit...")
                        
                        # Force screen update and ensure it's visible
                        input_win.refresh()
                        curses.doupdate()
                        stdscr.refresh()
                        
                        # Small delay to ensure user can see the completion screen
                        time.sleep(0.5)
                        
                        # Keep showing completion screen until Ctrl+C is pressed
                        input_win.timeout(-1)  # Block until key press
                        while True:
                            try:
                                key = input_win.getch()
                                # Only exit on Ctrl+C (key code 3) or ESC (key code 27)
                                if key == 3 or key == 27:  # Ctrl+C or ESC
                                    break
                                # Ignore all other keys and keep the screen visible
                            except KeyboardInterrupt:
                                break
                        
                        break
                    except Exception as e:
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
                line.startswith('PDF URL:') or line.startswith('Extraction Date:') or
                line.startswith('Search Score:') or line.startswith('Content Similarity:') or
                line.startswith('Title-Content Match:') or line.startswith('Match Score:') or
                line.startswith('Validation Method:') or line.startswith('Archive Title:') or
                line.startswith('Creator:')):
                continue
            # Skip separator lines (any line that's mostly = characters)
            if line.count('=') > len(line) * 0.5:
                continue
            # Skip page markers
            if line.startswith('=== PAGE') and line.endswith('==='):
                continue
            # Skip blocks with lots of roman numerals (chapter listings)
            roman_matches = re.findall(r'\b[IVXLCDM]+\b', line.upper())
            if len(roman_matches) >= 3:
                continue
            # Skip lines that are mostly roman numerals
            roman_chars = sum(1 for c in line.upper() if c in 'IVXLCDM')
            if roman_chars > len(line) * 0.3 and len(line) > 5:
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
            line.startswith('PDF URL:') or line.startswith('Extraction Date:') or
            line.startswith('Search Score:') or line.startswith('Content Similarity:') or
            line.startswith('Title-Content Match:') or line.startswith('Match Score:') or
            line.startswith('Validation Method:') or line.startswith('Archive Title:') or
            line.startswith('Creator:')):
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
        
        # Skip blocks with lots of roman numerals (chapter listings, table of contents)
        roman_numeral_pattern = r'\b[IVXLCDM]+\b'
        roman_matches = re.findall(roman_numeral_pattern, line.upper())
        if len(roman_matches) >= 3:  # Skip lines with 3+ roman numerals
            continue
        
        # Skip lines that are mostly roman numerals
        roman_chars = sum(1 for c in line.upper() if c in 'IVXLCDM')
        if roman_chars > len(line) * 0.3 and len(line) > 5:  # 30% or more roman numeral chars
            continue
        
        # Skip table of contents style lines (roman numeral followed by text and numbers)
        if re.match(r'^\s*[IVXLCDM]+\s*[\.‒–—-]\s*.+\s+\d+\s*$', line, re.IGNORECASE):
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
                # Skip metadata and chapter information
                roman_matches = re.findall(r'\b[IVXLCDM]+\b', line.upper())
                roman_chars = sum(1 for c in line.upper() if c in 'IVXLCDM')
                
                if not (line.startswith('Title:') or line.startswith('Source URL:') or 
                       line.startswith('PDF URL:') or line.startswith('Extraction Date:') or
                       line.startswith('Search Score:') or line.startswith('Content Similarity:') or
                       line.startswith('Title-Content Match:') or line.startswith('Match Score:') or
                       line.startswith('Validation Method:') or line.startswith('Archive Title:') or
                       line.startswith('Creator:') or line.count('=') > len(line) * 0.5 or
                       len(roman_matches) >= 3 or roman_chars > len(line) * 0.3):
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
    
    # Ask for translation target language
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
    
    # Show translation language selection menu
    ui.log("🌍 Select translation target language:")
    selected_translation_index = ui.show_menu("Select translation target language:", language_names)
    
    target_language = "en"  # Default to English
    if selected_translation_index is not None and 0 <= selected_translation_index < len(language_names):
        selected_language_name = language_names[selected_translation_index]
        target_language = language_options[selected_language_name]
        ui.log(f"🔤 Translation target: {selected_language_name}")
    else:
        ui.log("🔤 Using default translation target: English")
    
    # Show practice mode selection menu
    practice_mode_options = [
        "Complete Text - Type the entire text from beginning to end",
        "Timed Practice - Practice for a set amount of time"
    ]
    selected_mode_index = ui.show_menu("Select Practice Mode:", practice_mode_options)
    
    if selected_mode_index == -1:
        ui.log("❌ No practice mode selected")
        return
    
    # Initialize timer variables
    timed_practice = selected_mode_index == 1
    timer_minutes = None
    
    if timed_practice:
        # Show timer duration selection menu
        timer_options = [
            "1 minute",
            "3 minutes", 
            "5 minutes"
        ]
        selected_timer_index = ui.show_menu("Select Timer Duration:", timer_options)
        
        if selected_timer_index == -1:
            ui.log("❌ No timer duration selected")
            return
        
        # Convert selection to minutes
        timer_minutes = [1, 3, 5][selected_timer_index]
        ui.log(f"⏱️ Selected {timer_minutes} minute timed practice")
    else:
        ui.log("📖 Selected complete text practice")
    
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
    if timed_practice:
        ui.log(f"🎯 Starting {timer_minutes}-minute timed practice with {selected_file['title']}")
    else:
        ui.log(f"🎯 Starting complete text practice with {selected_file['title']}")
    
    practice = TypingPracticeInterface(
        title=selected_file['title'],
        text=text_content,
        language=selected_file['language'],
        ui=ui,
        timed_practice=timed_practice,
        timer_minutes=timer_minutes
    )
    
    # Set the target language for translation
    practice.target_language = target_language
    
    try:
        practice.run()
    except Exception as e:
        ui.log(f"❌ Error during typing practice: {e}")
    finally:
        ui.log("✅ Typing practice session ended")