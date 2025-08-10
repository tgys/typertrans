"""Language detection and filtering utilities."""

LANGUAGE_DETECTION_AVAILABLE = False
try:
    from langdetect import detect, detect_langs
    from langdetect.lang_detect_exception import LangDetectException
    LANGUAGE_DETECTION_AVAILABLE = True
except ImportError:
    print("⚠️ langdetect not available - language filtering disabled")


def get_language_code(language_name: str) -> str:
    """Map language names to langdetect codes"""
    language_map = {
        'french': 'fr',
        'spanish': 'es', 
        'german': 'de',
        'italian': 'it',
        'portuguese': 'pt',
        'russian': 'ru',
        'chinese': 'zh-cn',
        'japanese': 'ja',
        'korean': 'ko',
        'arabic': 'ar',
        'dutch': 'nl',
        'swedish': 'sv',
        'norwegian': 'no',
        'danish': 'da',
        'finnish': 'fi',
        'polish': 'pl',
        'czech': 'cs',
        'hungarian': 'hu',
        'turkish': 'tr',
        'greek': 'el',
        'hebrew': 'he',
        'hindi': 'hi',
        'bengali': 'bn',
        'tamil': 'ta',
        'thai': 'th',
        'english': 'en'
    }
    return language_map.get(language_name.lower(), 'en')


def filter_text_by_language(text: str, target_language: str) -> str:
    """Filter text to remove blocks (paragraphs) that are clearly not in target language"""
    if not LANGUAGE_DETECTION_AVAILABLE:
        return text  # Return all text if language detection unavailable
    
    target_code = get_language_code(target_language)
    
    # Split by double newlines to get paragraph blocks
    paragraphs = text.split('\n\n')
    filtered_paragraphs = []
    
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if len(paragraph) < 100:  # Keep short blocks (headers, titles, page numbers, etc.)
            filtered_paragraphs.append(paragraph)
            continue
            
        try:
            # Only detect language for substantial blocks of text
            detected = detect(paragraph)
            # Be more lenient - only remove if clearly different language
            if detected == target_code or (target_code == 'zh-cn' and detected in ['zh-cn', 'zh']):
                filtered_paragraphs.append(paragraph)
            else:
                # Check if the detection confidence is high before removing
                # For now, be conservative and keep mixed content
                try:
                    langs = detect_langs(paragraph)
                    # Only remove if very confident it's wrong language (>80% confidence)
                    if langs and langs[0].lang != target_code and langs[0].prob > 0.8:
                        continue  # Skip this paragraph
                    else:
                        filtered_paragraphs.append(paragraph)  # Keep it
                except:
                    filtered_paragraphs.append(paragraph)  # Keep if detection fails
        except LangDetectException:
            # If detection fails, keep the paragraph (might be numbers, names, etc.)
            filtered_paragraphs.append(paragraph)
    
    return '\n\n'.join(filtered_paragraphs)


def clean_foreign_words_from_edges(text: str, target_language: str) -> str:
    """Remove foreign language words from the beginning and end of text for typing practice"""
    if not LANGUAGE_DETECTION_AVAILABLE or not text.strip():
        return text
    
    target_code = get_language_code(target_language)
    words = text.split()
    
    if len(words) < 10:  # Too short to filter
        return text
    
    # Find first word in target language (from start)
    start_index = 0
    for i, word in enumerate(words[:20]):  # Check first 20 words max
        # Skip very short words, numbers, and punctuation
        if len(word) < 3 or word.isdigit() or not any(c.isalpha() for c in word):
            continue
        try:
            detected = detect(word)
            if detected == target_code or (target_code == 'zh-cn' and detected in ['zh-cn', 'zh']):
                start_index = i
                break
        except:
            continue
    
    # Find last word in target language (from end)
    end_index = len(words)
    for i in range(len(words) - 1, max(len(words) - 21, 0), -1):  # Check last 20 words max
        word = words[i]
        # Skip very short words, numbers, and punctuation
        if len(word) < 3 or word.isdigit() or not any(c.isalpha() for c in word):
            continue
        try:
            detected = detect(word)
            if detected == target_code or (target_code == 'zh-cn' and detected in ['zh-cn', 'zh']):
                end_index = i + 1
                break
        except:
            continue
    
    # Return filtered text
    if start_index < end_index:
        return ' '.join(words[start_index:end_index])
    return text




def has_text_in_language(text: str, target_language: str, min_chars: int = 50) -> bool:
    """Check if text contains at least min_chars meaningful characters"""
    if not text:
        return False
    
    # Count meaningful characters (letters, numbers, spaces, and basic punctuation)
    meaningful_chars = sum(1 for c in text if c.isalnum() or c.isspace() or c in '.,!?;:-()[]{}\'\"')
    
    # Only reject files with very little meaningful content
    return meaningful_chars >= min_chars