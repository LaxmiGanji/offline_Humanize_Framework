"""
Offline Humanizer Module - CLEAN VERSION (No garbage text)
"""

import re
import random
from nltk.tokenize import sent_tokenize
import nltk

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

class OfflineHumanizer:
    """Humanizes AI-generated text - CLEAN VERSION (No random characters)"""
    
    def __init__(self):
        # Simple contraction mappings
        self.contractions = {
            "cannot": "can't", "will not": "won't", "would not": "wouldn't",
            "could not": "couldn't", "should not": "shouldn't", "is not": "isn't",
            "are not": "aren't", "was not": "wasn't", "were not": "weren't",
            "have not": "haven't", "has not": "hasn't", "had not": "hadn't",
            "do not": "don't", "does not": "doesn't", "did not": "didn't",
            "it is": "it's", "that is": "that's", "there is": "there's",
            "I am": "I'm", "you are": "you're", "we are": "we're",
            "they are": "they're", "I have": "I've", "you have": "you've",
            "we have": "we've", "they have": "they've", "I will": "I'll",
            "you will": "you'll", "we will": "we'll", "they will": "they'll",
        }
        
        # Natural transitions
        self.transitions = [
            " Additionally,", " Furthermore,", " Moreover,", 
            " In addition,", " Also,", " Plus,"
        ]
        
        # Conversational openers
        self.openers = [
            "You know,", "Honestly,", "The thing is,", "So,", 
            "Basically,", "In my experience,", "If you ask me,"
        ]
        
        # Personal phrases
        self.personal_phrases = [
            "I think ", "I feel ", "I believe ", "In my opinion, ", "For me, "
        ]
        
        # Simple phrase replacements (no regex complexity)
        self.replacements = [
            ("in order to", "to"),
            ("due to the fact that", "because"),
            ("in addition", "plus"),
            ("furthermore", "plus"),
            ("moreover", "also"),
            ("nevertheless", "still"),
            ("thus", "so"),
            ("therefore", "so"),
            ("provides", "gives"),
            ("utilize", "use"),
            ("demonstrates", "shows"),
        ]
        
    def humanize(self, text, intensity="medium"):
        """
        Humanize text - CLEAN VERSION with no garbage characters
        """
        if not text or len(text) < 10:
            return text
        
        # First, ensure text is clean (no special chars)
        text = self._basic_clean(text)
        
        # Apply humanization based on intensity
        if intensity == "low":
            text = self._light_humanize(text)
        elif intensity == "medium":
            text = self._medium_humanize(text)
        else:  # high
            text = self._heavy_humanize(text)
        
        # Final cleanup
        text = self._final_cleanup(text)
        
        return text
    
    def _basic_clean(self, text):
        """Remove any garbage characters"""
        # Keep only alphanumeric, spaces, and basic punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\-\']', '', text)
        # Remove multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _light_humanize(self, text):
        """Light humanization - mainly contractions"""
        # Add contractions
        for full, contraction in self.contractions.items():
            text = re.sub(r'\b' + full + r'\b', contraction, text, flags=re.IGNORECASE)
        
        # Replace formal phrases
        for formal, informal in self.replacements:
            text = re.sub(r'\b' + formal + r'\b', informal, text, flags=re.IGNORECASE)
        
        return text
    
    def _medium_humanize(self, text):
        """Medium humanization - add some personality"""
        # First apply light humanization
        text = self._light_humanize(text)
        
        # Add occasional personal touch
        sentences = sent_tokenize(text)
        if len(sentences) > 1:
            modified = []
            for i, sent in enumerate(sentences):
                if i == 0:
                    modified.append(sent)
                elif i < len(sentences) - 1 and random.random() > 0.7:
                    # Add transition
                    modified.append(random.choice(self.transitions) + " " + sent[0].lower() + sent[1:])
                else:
                    modified.append(sent)
            text = ' '.join(modified)
        
        return text
    
    def _heavy_humanize(self, text):
        """Heavy humanization - make it conversational"""
        # First apply medium humanization
        text = self._medium_humanize(text)
        
        # Add personal opinion to some sentences
        sentences = sent_tokenize(text)
        if len(sentences) > 1:
            modified = []
            for i, sent in enumerate(sentences):
                if i > 0 and len(sent.split()) > 5 and random.random() > 0.6:
                    # Check if already has personal phrase
                    if not any(p in sent.lower()[:20] for p in ["i think", "i feel", "in my"]):
                        personal = random.choice(self.personal_phrases)
                        sent = personal + sent[0].lower() + sent[1:]
                modified.append(sent)
            text = ' '.join(modified)
        
        # Maybe add a rhetorical question at the end
        if random.random() > 0.7:
            questions = [" Right?", " You know?", " Makes sense, doesn't it?"]
            text += random.choice(questions)
        
        return text
    
    def _final_cleanup(self, text):
        """Final cleanup - ensure no garbage remains"""
        # Fix punctuation spacing
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        # Ensure sentences end with punctuation
        if text and not text[-1] in '.!?':
            text += '.'
        # Capitalize first letter
        if text and len(text) > 1 and text[0].islower():
            text = text[0].upper() + text[1:]
        
        return text.strip()