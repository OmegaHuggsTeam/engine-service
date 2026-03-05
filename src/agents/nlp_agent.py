"""
NLPAgent - Specialist for natural language processing tasks.

Capabilities: nlp, text_classification, sentiment_analysis, entity_extraction
Commands: classify, sentiment, entities, summarize, keywords
"""

import json
import logging
import re
import math
from pathlib import Path
from datetime import datetime
from collections import Counter

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class NLPAgent:
    """Specialist agent for natural language processing tasks."""

    # Positive and negative word lists for sentiment analysis
    POSITIVE_WORDS = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic", "awesome",
        "outstanding", "brilliant", "superb", "love", "happy", "joy", "pleased",
        "delighted", "perfect", "best", "beautiful", "nice", "positive", "success",
        "successful", "impressive", "remarkable", "exceptional", "superior", "terrific",
        "fabulous", "magnificent", "marvelous", "enjoy", "glad", "thankful", "grateful",
        "exciting", "satisfied", "helpful", "effective", "efficient", "reliable",
        "fast", "easy", "simple", "clean", "clear", "elegant", "robust", "powerful",
        "innovative", "creative", "improved", "better", "solved", "fixed", "resolved",
        "working", "complete", "ready", "approved", "accepted", "recommended",
    }

    NEGATIVE_WORDS = {
        "bad", "terrible", "horrible", "awful", "poor", "worst", "hate", "ugly",
        "broken", "failed", "failure", "error", "bug", "crash", "issue", "problem",
        "wrong", "slow", "complex", "complicated", "confusing", "difficult", "hard",
        "frustrating", "annoying", "disappointing", "useless", "waste", "missing",
        "incomplete", "unstable", "unreliable", "insecure", "vulnerable", "deprecated",
        "obsolete", "bloated", "messy", "hacky", "dirty", "painful", "angry",
        "sad", "unhappy", "worried", "concerned", "critical", "severe", "dangerous",
        "rejected", "denied", "blocked", "stuck", "impossible", "never", "nothing",
        "broken", "corrupt", "malformed", "invalid", "illegal", "unauthorized",
    }

    # Stopwords for keyword extraction
    STOPWORDS = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "can", "need", "must",
        "it", "its", "this", "that", "these", "those", "i", "me", "my", "we",
        "our", "you", "your", "he", "him", "his", "she", "her", "they", "them",
        "their", "what", "which", "who", "whom", "where", "when", "why", "how",
        "all", "each", "every", "both", "few", "more", "most", "other", "some",
        "such", "no", "not", "only", "own", "same", "so", "than", "too", "very",
        "just", "because", "as", "until", "while", "if", "then", "else", "about",
        "up", "out", "off", "over", "under", "again", "further", "once", "here",
        "there", "also", "into", "through", "during", "before", "after", "above",
        "below", "between", "any", "s", "t", "don", "didn", "doesn", "isn",
        "wasn", "weren", "won", "wouldn", "couldn", "shouldn", "re", "ve", "ll",
    }

    def __init__(self):
        self.capabilities = ["nlp", "text_classification", "sentiment_analysis", "entity_extraction"]
        self.commands = ["classify", "sentiment", "entities", "summarize", "keywords"]

    def execute(self, command: str) -> dict:
        """Dispatch to sub-methods based on command text."""
        command_lower = command.strip().lower()

        if command_lower.startswith("classify"):
            text = command[len("classify"):].strip()
            return self._classify(text)
        elif command_lower.startswith("sentiment"):
            text = command[len("sentiment"):].strip()
            return self._sentiment(text)
        elif command_lower.startswith("entities"):
            text = command[len("entities"):].strip()
            return self._entities(text)
        elif command_lower.startswith("summarize"):
            text = command[len("summarize"):].strip()
            return self._summarize(text)
        elif command_lower.startswith("keywords"):
            text = command[len("keywords"):].strip()
            return self._keywords(text)
        else:
            return {
                "status": "error",
                "message": f"Unknown command: {command}",
                "available_commands": self.commands,
            }

    def _classify(self, text: str) -> dict:
        """Classifies text into categories using keyword matching."""
        if not text:
            return {
                "status": "error",
                "command": "classify",
                "message": "No text provided. Usage: classify <text>",
            }

        text_lower = text.lower()
        scores = {
            "technical": 0,
            "business": 0,
            "creative": 0,
            "error": 0,
            "question": 0,
        }

        # Technical keywords
        technical_words = {
            "code", "function", "class", "api", "database", "server", "deploy",
            "algorithm", "variable", "module", "package", "library", "framework",
            "python", "javascript", "docker", "git", "debug", "compile", "runtime",
            "endpoint", "request", "response", "query", "schema", "sql", "json",
            "http", "tcp", "port", "config", "configuration", "install", "import",
            "interface", "implementation", "architecture", "performance", "memory",
            "cache", "async", "thread", "process", "binary", "regex", "parse",
        }

        # Business keywords
        business_words = {
            "revenue", "profit", "cost", "budget", "market", "customer", "client",
            "sales", "growth", "strategy", "plan", "meeting", "deadline", "project",
            "team", "management", "stakeholder", "roi", "kpi", "metric", "report",
            "quarterly", "annual", "fiscal", "invest", "contract", "proposal",
            "requirement", "scope", "milestone", "deliverable", "approval", "review",
            "compliance", "policy", "process", "workflow", "efficiency", "productivity",
        }

        # Creative keywords
        creative_words = {
            "design", "color", "layout", "font", "image", "visual", "art", "style",
            "creative", "brand", "logo", "illustration", "animation", "video",
            "content", "story", "narrative", "write", "writing", "blog", "article",
            "headline", "copy", "inspiration", "concept", "mockup", "prototype",
            "aesthetic", "theme", "palette", "typography", "composition", "canvas",
        }

        # Error keywords
        error_words = {
            "error", "bug", "fail", "crash", "exception", "traceback", "broken",
            "issue", "problem", "wrong", "fix", "debug", "stacktrace", "timeout",
            "null", "undefined", "missing", "invalid", "corrupt", "leak", "overflow",
            "404", "500", "403", "segfault", "deadlock", "race", "condition",
        }

        words = set(re.findall(r'\b\w+\b', text_lower))

        scores["technical"] = len(words & technical_words)
        scores["business"] = len(words & business_words)
        scores["creative"] = len(words & creative_words)
        scores["error"] = len(words & error_words)

        # Question detection
        question_indicators = ["?", "how", "what", "why", "when", "where", "who", "which", "can", "could", "would", "should"]
        if text.strip().endswith("?"):
            scores["question"] += 3
        for indicator in question_indicators:
            if indicator in text_lower.split():
                scores["question"] += 1

        # Determine primary category
        max_score = max(scores.values())
        if max_score == 0:
            primary = "general"
            confidence = 0.0
        else:
            primary = max(scores, key=scores.get)
            total = sum(scores.values())
            confidence = round(max_score / total, 2) if total > 0 else 0.0

        return {
            "status": "success",
            "command": "classify",
            "text_length": len(text),
            "primary_category": primary,
            "confidence": confidence,
            "scores": scores,
            "timestamp": datetime.now().isoformat(),
        }

    def _sentiment(self, text: str) -> dict:
        """Basic sentiment analysis using positive/negative word lists."""
        if not text:
            return {
                "status": "error",
                "command": "sentiment",
                "message": "No text provided. Usage: sentiment <text>",
            }

        words = re.findall(r'\b\w+\b', text.lower())
        total_words = len(words)

        if total_words == 0:
            return {
                "status": "success",
                "command": "sentiment",
                "score": 0.0,
                "label": "neutral",
                "positive_count": 0,
                "negative_count": 0,
                "timestamp": datetime.now().isoformat(),
            }

        positive_found = [w for w in words if w in self.POSITIVE_WORDS]
        negative_found = [w for w in words if w in self.NEGATIVE_WORDS]

        pos_count = len(positive_found)
        neg_count = len(negative_found)

        # Negation handling: check for "not" before positive/negative words
        negation_words = {"not", "no", "never", "neither", "nobody", "nothing", "nowhere", "nor", "dont", "doesn", "didn", "wasn", "weren", "wouldn", "couldn", "shouldn"}
        for i, w in enumerate(words):
            if i > 0 and words[i - 1] in negation_words:
                if w in self.POSITIVE_WORDS:
                    pos_count -= 1
                    neg_count += 1
                elif w in self.NEGATIVE_WORDS:
                    neg_count -= 1
                    pos_count += 1

        pos_count = max(0, pos_count)
        neg_count = max(0, neg_count)

        # Calculate score between -1 and 1
        if pos_count + neg_count == 0:
            score = 0.0
        else:
            score = round((pos_count - neg_count) / (pos_count + neg_count), 3)

        # Determine label
        if score > 0.25:
            label = "positive"
        elif score < -0.25:
            label = "negative"
        else:
            label = "neutral"

        return {
            "status": "success",
            "command": "sentiment",
            "score": score,
            "label": label,
            "positive_count": pos_count,
            "negative_count": neg_count,
            "positive_words": list(set(positive_found))[:10],
            "negative_words": list(set(negative_found))[:10],
            "total_words": total_words,
            "timestamp": datetime.now().isoformat(),
        }

    def _entities(self, text: str) -> dict:
        """Extracts named entities using regex patterns."""
        if not text:
            return {
                "status": "error",
                "command": "entities",
                "message": "No text provided. Usage: entities <text>",
            }

        entities = {
            "emails": [],
            "urls": [],
            "file_paths": [],
            "python_identifiers": [],
            "numbers": [],
            "ip_addresses": [],
            "dates": [],
        }

        # Email addresses
        email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        entities["emails"] = list(set(email_pattern.findall(text)))

        # URLs
        url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')
        entities["urls"] = list(set(url_pattern.findall(text)))

        # File paths (Unix and Windows style)
        unix_path_pattern = re.compile(r'(?:/[a-zA-Z0-9_.\-]+){2,}')
        win_path_pattern = re.compile(r'[A-Za-z]:\\(?:[^\s\\/:*?"<>|]+\\)*[^\s\\/:*?"<>|]+')
        unix_paths = unix_path_pattern.findall(text)
        win_paths = win_path_pattern.findall(text)
        entities["file_paths"] = list(set(unix_paths + win_paths))

        # Python-style identifiers (module.class.method patterns)
        py_ident_pattern = re.compile(r'\b[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)+\b')
        entities["python_identifiers"] = list(set(py_ident_pattern.findall(text)))

        # Numbers (integers and floats)
        number_pattern = re.compile(r'\b\d+(?:\.\d+)?\b')
        entities["numbers"] = list(set(number_pattern.findall(text)))

        # IP addresses
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        entities["ip_addresses"] = list(set(ip_pattern.findall(text)))

        # Date patterns (various formats)
        date_pattern = re.compile(
            r'\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b'
            r'|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b'
            r'|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s+\d{4}\b',
            re.IGNORECASE,
        )
        entities["dates"] = list(set(date_pattern.findall(text)))

        total_entities = sum(len(v) for v in entities.values())

        return {
            "status": "success",
            "command": "entities",
            "total_entities": total_entities,
            "entities": entities,
            "text_length": len(text),
            "timestamp": datetime.now().isoformat(),
        }

    def _summarize(self, text: str, num_sentences: int = 3) -> dict:
        """Extracts first N sentences from text as summary."""
        if not text:
            return {
                "status": "error",
                "command": "summarize",
                "message": "No text provided. Usage: summarize <text>",
            }

        # Split into sentences using regex
        sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z])')
        sentences = sentence_pattern.split(text.strip())

        # Also handle simple period splitting as fallback
        if len(sentences) <= 1:
            sentences = re.split(r'[.!?]+\s*', text.strip())
            sentences = [s.strip() for s in sentences if s.strip()]

        total_sentences = len(sentences)
        summary_sentences = sentences[:num_sentences]
        summary = ". ".join(summary_sentences)
        if summary and not summary.endswith("."):
            summary += "."

        # Calculate compression ratio
        original_length = len(text)
        summary_length = len(summary)
        compression = round(1 - (summary_length / original_length), 2) if original_length > 0 else 0

        return {
            "status": "success",
            "command": "summarize",
            "summary": summary,
            "total_sentences": total_sentences,
            "sentences_extracted": len(summary_sentences),
            "original_length": original_length,
            "summary_length": summary_length,
            "compression_ratio": compression,
            "timestamp": datetime.now().isoformat(),
        }

    def _keywords(self, text: str, top_n: int = 15) -> dict:
        """Extracts keywords using TF-like frequency analysis."""
        if not text:
            return {
                "status": "error",
                "command": "keywords",
                "message": "No text provided. Usage: keywords <text>",
            }

        # Tokenize: extract words, lowercase
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())

        # Remove stopwords
        filtered_words = [w for w in words if w not in self.STOPWORDS]

        if not filtered_words:
            return {
                "status": "success",
                "command": "keywords",
                "keywords": [],
                "total_words": len(words),
                "unique_words": 0,
                "timestamp": datetime.now().isoformat(),
            }

        # Count frequencies
        word_counts = Counter(filtered_words)
        total_filtered = len(filtered_words)

        # Calculate TF scores
        tf_scores = {}
        for word, count in word_counts.items():
            tf = count / total_filtered
            # Boost words that appear in reasonable frequency (not too rare, not too common)
            tf_scores[word] = round(tf, 4)

        # Sort by score and take top N
        sorted_keywords = sorted(tf_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]

        keywords = [
            {"word": word, "tf_score": score, "count": word_counts[word]}
            for word, score in sorted_keywords
        ]

        return {
            "status": "success",
            "command": "keywords",
            "keywords": keywords,
            "total_words": len(words),
            "unique_words_after_filtering": len(word_counts),
            "stopwords_removed": len(words) - len(filtered_words),
            "timestamp": datetime.now().isoformat(),
        }


def ask_agent(query: str) -> str:
    """Entry point for the NLPAgent. Creates instance, executes query, returns JSON."""
    agent = NLPAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "classify This is a test of the NLP agent"
    print(ask_agent(query))
