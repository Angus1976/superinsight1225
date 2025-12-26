"""
Text Processor for Knowledge Graph.

Provides text preprocessing, tokenization, and normalization for Chinese text.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# jieba for Chinese word segmentation
try:
    import jieba
    import jieba.posseg as pseg
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False
    logger.warning("jieba not installed. Install with: pip install jieba")


@dataclass
class Token:
    """Token representation."""
    text: str
    pos: str  # Part of speech
    start: int
    end: int
    is_stopword: bool = False
    lemma: Optional[str] = None


@dataclass
class ProcessedText:
    """Processed text result."""
    original_text: str
    cleaned_text: str
    tokens: List[Token] = field(default_factory=list)
    sentences: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    language: str = "zh"


class TextProcessor:
    """
    Text processor for Chinese text.

    Provides tokenization, POS tagging, stopword removal, and text normalization.
    """

    # Chinese stopwords
    DEFAULT_STOPWORDS = {
        "的", "了", "是", "在", "我", "有", "和", "就", "不", "人", "都", "一", "一个",
        "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好",
        "自己", "这", "那", "里", "来", "他", "她", "它", "们", "这个", "那个", "什么",
        "为", "以", "及", "或", "但", "如果", "因为", "所以", "而", "且", "与", "等",
        "吗", "呢", "啊", "吧", "呀", "哦", "嗯", "哪", "谁", "怎么", "多少", "为什么",
    }

    # POS tag mapping (jieba to universal)
    POS_MAPPING = {
        "n": "NOUN",      # 名词
        "nr": "PROPN",    # 人名
        "ns": "PROPN",    # 地名
        "nt": "PROPN",    # 机构名
        "nz": "PROPN",    # 其他专名
        "v": "VERB",      # 动词
        "vd": "VERB",     # 副动词
        "vn": "NOUN",     # 名动词
        "a": "ADJ",       # 形容词
        "ad": "ADV",      # 副形词
        "an": "NOUN",     # 名形词
        "d": "ADV",       # 副词
        "m": "NUM",       # 数词
        "q": "NOUN",      # 量词
        "r": "PRON",      # 代词
        "p": "ADP",       # 介词
        "c": "CCONJ",     # 连词
        "u": "PART",      # 助词
        "xc": "PART",     # 其他虚词
        "w": "PUNCT",     # 标点
        "x": "X",         # 其他
        "eng": "X",       # 英文
        "t": "NOUN",      # 时间词
        "f": "NOUN",      # 方位词
        "s": "NOUN",      # 处所词
        "j": "NOUN",      # 简称
        "i": "NOUN",      # 成语
        "l": "NOUN",      # 习语
    }

    def __init__(
        self,
        stopwords: Optional[set] = None,
        custom_dict_path: Optional[str] = None,
        enable_paddle: bool = False,
    ):
        """
        Initialize TextProcessor.

        Args:
            stopwords: Custom stopwords set
            custom_dict_path: Path to custom dictionary file
            enable_paddle: Whether to enable paddle mode for better accuracy
        """
        self.stopwords = stopwords or self.DEFAULT_STOPWORDS
        self.custom_dict_path = custom_dict_path
        self.enable_paddle = enable_paddle

        self._initialized = False

    def initialize(self) -> None:
        """Initialize the processor."""
        if self._initialized:
            return

        if not JIEBA_AVAILABLE:
            logger.warning("jieba not available, text processing will be limited")
            self._initialized = True
            return

        # Load custom dictionary
        if self.custom_dict_path:
            try:
                jieba.load_userdict(self.custom_dict_path)
                logger.info(f"Loaded custom dictionary from {self.custom_dict_path}")
            except Exception as e:
                logger.error(f"Failed to load custom dictionary: {e}")

        # Enable paddle mode if requested
        if self.enable_paddle:
            try:
                jieba.enable_paddle()
                logger.info("Enabled paddle mode")
            except Exception as e:
                logger.warning(f"Failed to enable paddle mode: {e}")

        self._initialized = True
        logger.info("TextProcessor initialized")

    def process(self, text: str) -> ProcessedText:
        """
        Process text and return structured result.

        Args:
            text: Input text

        Returns:
            ProcessedText with tokens, sentences, and keywords
        """
        if not self._initialized:
            self.initialize()

        # Clean text
        cleaned_text = self.clean_text(text)

        # Split into sentences
        sentences = self.split_sentences(cleaned_text)

        # Tokenize with POS tagging
        tokens = self.tokenize(cleaned_text)

        # Extract keywords
        keywords = self.extract_keywords(cleaned_text, top_k=10)

        return ProcessedText(
            original_text=text,
            cleaned_text=cleaned_text,
            tokens=tokens,
            sentences=sentences,
            keywords=keywords,
            language="zh",
        )

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)

        # Normalize unicode
        text = text.strip()

        # Convert full-width to half-width for numbers and letters
        result = []
        for char in text:
            code = ord(char)
            # Full-width ASCII (！ to ～)
            if 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            # Full-width space
            elif code == 0x3000:
                result.append(' ')
            else:
                result.append(char)

        return ''.join(result)

    def split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        if not text:
            return []

        # Chinese sentence delimiters
        delimiters = r'([。！？；\n])'
        parts = re.split(delimiters, text)

        sentences = []
        current = ""

        for part in parts:
            if re.match(delimiters, part):
                current += part
                if current.strip():
                    sentences.append(current.strip())
                current = ""
            else:
                current = part

        if current.strip():
            sentences.append(current.strip())

        return sentences

    def tokenize(self, text: str) -> List[Token]:
        """
        Tokenize text with POS tagging.

        Args:
            text: Input text

        Returns:
            List of tokens
        """
        if not text:
            return []

        if not JIEBA_AVAILABLE:
            # Fallback: character-level tokenization
            return [
                Token(
                    text=char,
                    pos="X",
                    start=i,
                    end=i + 1,
                    is_stopword=char in self.stopwords,
                )
                for i, char in enumerate(text) if not char.isspace()
            ]

        tokens = []
        current_pos = 0

        for word, flag in pseg.cut(text):
            # Find position in text
            start = text.find(word, current_pos)
            if start == -1:
                start = current_pos
            end = start + len(word)
            current_pos = end

            # Map POS tag
            pos = self.POS_MAPPING.get(flag, "X")

            # Check stopword
            is_stopword = word.lower() in self.stopwords

            tokens.append(Token(
                text=word,
                pos=pos,
                start=start,
                end=end,
                is_stopword=is_stopword,
            ))

        return tokens

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """
        Extract keywords from text using TF-IDF.

        Args:
            text: Input text
            top_k: Number of keywords to extract

        Returns:
            List of keywords
        """
        if not text or not JIEBA_AVAILABLE:
            return []

        try:
            import jieba.analyse
            keywords = jieba.analyse.extract_tags(text, topK=top_k, withWeight=False)
            return keywords
        except Exception as e:
            logger.error(f"Failed to extract keywords: {e}")
            return []

    def get_noun_phrases(self, tokens: List[Token]) -> List[str]:
        """
        Extract noun phrases from tokens.

        Args:
            tokens: List of tokens

        Returns:
            List of noun phrases
        """
        phrases = []
        current_phrase = []

        for token in tokens:
            if token.pos in ("NOUN", "PROPN", "ADJ"):
                current_phrase.append(token.text)
            else:
                if len(current_phrase) >= 2:
                    phrases.append("".join(current_phrase))
                elif len(current_phrase) == 1 and len(current_phrase[0]) >= 2:
                    phrases.append(current_phrase[0])
                current_phrase = []

        # Handle last phrase
        if len(current_phrase) >= 2:
            phrases.append("".join(current_phrase))
        elif len(current_phrase) == 1 and len(current_phrase[0]) >= 2:
            phrases.append(current_phrase[0])

        return phrases

    def remove_stopwords(self, tokens: List[Token]) -> List[Token]:
        """
        Remove stopwords from token list.

        Args:
            tokens: List of tokens

        Returns:
            Tokens with stopwords removed
        """
        return [t for t in tokens if not t.is_stopword]

    def add_custom_words(self, words: List[str]) -> None:
        """
        Add custom words to the dictionary.

        Args:
            words: List of words to add
        """
        if not JIEBA_AVAILABLE:
            return

        for word in words:
            jieba.add_word(word)

    def add_stopwords(self, words: List[str]) -> None:
        """
        Add words to stopwords set.

        Args:
            words: Words to add as stopwords
        """
        self.stopwords.update(words)

    def get_text_stats(self, text: str) -> Dict[str, Any]:
        """
        Get text statistics.

        Args:
            text: Input text

        Returns:
            Statistics dictionary
        """
        processed = self.process(text)

        # Count by POS
        pos_counts = {}
        for token in processed.tokens:
            pos_counts[token.pos] = pos_counts.get(token.pos, 0) + 1

        return {
            "char_count": len(text),
            "word_count": len(processed.tokens),
            "sentence_count": len(processed.sentences),
            "keyword_count": len(processed.keywords),
            "pos_distribution": pos_counts,
            "avg_sentence_length": len(text) / len(processed.sentences) if processed.sentences else 0,
            "stopword_ratio": sum(1 for t in processed.tokens if t.is_stopword) / len(processed.tokens) if processed.tokens else 0,
        }


# Global instance
_text_processor: Optional[TextProcessor] = None


def get_text_processor() -> TextProcessor:
    """Get or create global TextProcessor instance."""
    global _text_processor

    if _text_processor is None:
        _text_processor = TextProcessor()
        _text_processor.initialize()

    return _text_processor
