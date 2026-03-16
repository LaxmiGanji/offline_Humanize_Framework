"""
Offline Synonym Engine
Uses WordNet for synonym lookup - completely offline
"""

import nltk
from nltk.corpus import wordnet
import re

# Download WordNet data if not present
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

class SynonymEngine:
    """
    Handles synonym lookup and replacement - completely offline
    """
    
    def __init__(self):
        self.cache = {}  # Cache synonyms for performance
        self.common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'between', 'under', 'over', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
            'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too',
            'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now'
        }
        
    def get_synonyms(self, word):
        """
        Get synonyms for a word from WordNet
        
        Args:
            word: The word to find synonyms for
            
        Returns:
            List of unique synonyms
        """
        # Check cache first
        word_lower = word.lower()
        if word_lower in self.cache:
            return self.cache[word_lower]
        
        # Skip common words
        if word_lower in self.common_words or len(word_lower) < 4:
            return []
        
        synonyms = set()
        
        try:
            # Get synsets for the word
            synsets = wordnet.synsets(word_lower)
            
            for synset in synsets:
                for lemma in synset.lemmas():
                    synonym = lemma.name().replace('_', ' ')
                    # Don't include the original word
                    if synonym.lower() != word_lower and len(synonym) > 2:
                        synonyms.add(synonym)
            
            # Convert to list and cache
            synonym_list = list(synonyms)[:10]  # Limit to 10 synonyms
            self.cache[word_lower] = synonym_list
            return synonym_list
            
        except Exception as e:
            print(f"Error getting synonyms for {word}: {e}")
            return []
    
    def get_synonyms_with_pos(self, word):
        """
        Get synonyms with part of speech information
        
        Returns:
            List of (synonym, pos) tuples
        """
        word_lower = word.lower()
        synonyms = []
        
        try:
            synsets = wordnet.synsets(word_lower)
            
            for synset in synsets:
                pos = synset.pos()
                pos_name = {'n': 'noun', 'v': 'verb', 'a': 'adjective', 'r': 'adverb'}.get(pos, pos)
                
                for lemma in synset.lemmas():
                    synonym = lemma.name().replace('_', ' ')
                    if synonym.lower() != word_lower and len(synonym) > 2:
                        synonyms.append((synonym, pos_name))
            
            # Remove duplicates while preserving order
            seen = set()
            unique_synonyms = []
            for syn, pos in synonyms:
                if syn not in seen:
                    seen.add(syn)
                    unique_synonyms.append((syn, pos))
            
            return unique_synonyms[:15]  # Limit to 15 synonyms
            
        except Exception as e:
            print(f"Error getting synonyms for {word}: {e}")
            return []
    
    def highlight_candidates(self, text):
        """
        Find words that have synonyms and can be highlighted
        
        Returns:
            List of (word, start_pos, end_pos, synonyms) tuples
        """
        candidates = []
        
        # Split into words while preserving positions
        words = re.finditer(r'\b([a-zA-Z]{3,})\b', text)
        
        for match in words:
            word = match.group(1)
            start = match.start()
            end = match.end()
            
            # Get synonyms
            synonyms = self.get_synonyms(word)
            
            # Only highlight if there are synonyms and word is not too common
            if synonyms and word.lower() not in self.common_words:
                candidates.append({
                    'word': word,
                    'start': start,
                    'end': end,
                    'synonyms': synonyms[:8],  # Show max 8 synonyms
                    'original': word
                })
        
        return candidates
    
    def replace_word(self, text, start, end, new_word):
        """
        Replace a word in text at given position
        
        Args:
            text: Original text
            start: Start position
            end: End position
            new_word: New word to insert
            
        Returns:
            Modified text
        """
        return text[:start] + new_word + text[end:]

    def get_synonym_groups(self, text):
        """
        Group words by their synonym sets for better UI organization
        
        Returns:
            Dictionary of word -> list of synonyms
        """
        groups = {}
        words = re.finditer(r'\b([a-zA-Z]{3,})\b', text)
        
        for match in words:
            word = match.group(1)
            if word.lower() not in self.common_words:
                synonyms = self.get_synonyms(word)
                if synonyms:
                    groups[word] = synonyms
        
        return groups