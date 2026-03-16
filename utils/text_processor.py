"""
Text preprocessing utilities for humanized summarization
"""

import re
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import random

# Download NLTK data (one-time)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')
    nltk.download('averaged_perceptron_tagger')

class TextProcessor:
    """Advanced text processing for human-like summarization"""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.transition_phrases = [
            'Furthermore', 'Moreover', 'However', 'Additionally', 
            'In contrast', 'Consequently', 'Therefore', 'Thus',
            'Nevertheless', 'Nonetheless', 'Meanwhile', 'Subsequently'
        ]
        
    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep sentences
        text = re.sub(r'[^\w\s\.\,\!\?\-\:]', '', text)
        # Fix multiple punctuation
        text = re.sub(r'\.+', '.', text)
        text = re.sub(r'\,+', ',', text)
        return text.strip()
    
    def extract_key_phrases(self, text, num_phrases=5):
        """Extract key phrases using statistical approach"""
        words = word_tokenize(text.lower())
        word_freq = {}
        
        for word in words:
            if word.isalnum() and word not in self.stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:num_phrases]]
    
    def add_transition_words(self, sentences):
        """Add transition words to make text flow better"""
        if len(sentences) <= 1:
            return sentences
        
        modified = [sentences[0]]  # Keep first sentence as is
        
        for i, sent in enumerate(sentences[1:], 1):
            # Add transition to some sentences (30% chance)
            if random.random() > 0.7 and len(sent.split()) > 5:
                transition = random.choice(self.transition_phrases)
                sent = f"{transition}, {sent[0].lower() + sent[1:]}"
            modified.append(sent)
        
        return modified
    
    def paraphrase_sentence(self, sentence):
        """Simple rule-based paraphrasing"""
        # Common paraphrasing patterns
        patterns = [
            (r'\b(is|are) used to\b', 'serves to'),
            (r'\b(important|significant)\b', 'crucial'),
            (r'\b(show|demonstrate)\b', 'indicate'),
            (r'\b(study|research)\b', 'investigation'),
            (r'\b(many|numerous)\b', 'various'),
            (r'\b(help|aid)\b', 'assist'),
            (r'\b(however|but)\b', 'nevertheless'),
            (r'\b(therefore|so)\b', 'consequently'),
        ]
        
        paraphrased = sentence
        for pattern, replacement in patterns:
            paraphrased = re.sub(pattern, replacement, paraphrased, flags=re.IGNORECASE)
        
        return paraphrased if paraphrased != sentence else sentence
    
    def humanize_summary(self, summary):
        """Apply human-like touches to summary"""
        if not summary:
            return summary
            
        # Clean the summary first
        summary = self.clean_text(summary)
        
        # Split into sentences
        sentences = sent_tokenize(summary)
        
        if not sentences:
            return summary
        
        # Apply paraphrasing to some sentences
        for i in range(len(sentences)):
            if random.random() > 0.5:  # 50% chance
                sentences[i] = self.paraphrase_sentence(sentences[i])
        
        # Add transition words
        sentences = self.add_transition_words(sentences)
        
        # Ensure first letter capital and proper ending
        for i, sent in enumerate(sentences):
            if sent:
                # Capitalize first letter
                if sent[0].islower():
                    sentences[i] = sent[0].upper() + sent[1:]
                
                # Add period if missing
                if not sent.endswith(('.', '!', '?')):
                    sentences[i] = sent + '.'
        
        # Join sentences
        final_summary = ' '.join(sentences)
        
        # Final cleanup
        final_summary = re.sub(r'\s+', ' ', final_summary)
        
        return final_summary
    
    def count_words(self, text):
        """Count words in text"""
        return len(word_tokenize(text))