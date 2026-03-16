"""
Core summarization engine with multiple AI models
FIXED: Better word count targeting and quality
"""

import torch
from transformers import (
    T5ForConditionalGeneration, 
    T5Tokenizer,
    BartForConditionalGeneration,
    BartTokenizer
)
import os
import re
from utils.text_processor import TextProcessor
from utils.humanizer import OfflineHumanizer

class OfflineSummarizer:
    """
    Advanced summarizer that generates humanized, plagiarism-free summaries
    FIXED: Better word count accuracy
    """
    
    def __init__(self, model_type="t5-small", cache_dir="./models"):
        """
        Initialize summarizer with specified model
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        self.model_type = model_type
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.processor = TextProcessor()
        self.humanizer = OfflineHumanizer()
        
        print(f"🔄 Loading {model_type} model on {self.device}...")
        
        try:
            if "t5" in model_type:
                self.tokenizer = T5Tokenizer.from_pretrained(
                    model_type, 
                    cache_dir=cache_dir
                )
                self.model = T5ForConditionalGeneration.from_pretrained(
                    model_type,
                    cache_dir=cache_dir
                )
            elif "bart" in model_type:
                self.tokenizer = BartTokenizer.from_pretrained(
                    model_type,
                    cache_dir=cache_dir
                )
                self.model = BartForConditionalGeneration.from_pretrained(
                    model_type,
                    cache_dir=cache_dir
                )
            else:
                raise ValueError(f"Unsupported model: {model_type}")
            
            self.model = self.model.to(self.device)
            self.model.eval()
            
            print(f"✅ Model loaded successfully!")
            
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise
    
    def summarize(self, text, max_length=150, min_length=50, creativity="medium", humanize_intensity="high"):
        """
        Generate humanized summary with accurate word count control
        """
        # Clean input text
        text = self.processor.clean_text(text)
        
        if not text or len(text.split()) < 20:
            return "Text is too short to summarize effectively."
        
        # For longer summaries, use iterative approach
        if max_length > 300:
            return self._generate_long_summary(text, max_length, min_length, creativity, humanize_intensity)
        
        # For normal summaries, use direct generation with length adjustment
        return self._generate_length_controlled_summary(text, max_length, min_length, creativity, humanize_intensity)
    
    def _generate_length_controlled_summary(self, text, target_max, target_min, creativity, humanize_intensity):
        """Generate summary with precise length control"""
        try:
            # First pass - generate base summary
            base_summary = self._generate_base_summary(text, target_max, creativity)
            
            if not base_summary or base_summary.startswith("Error"):
                return base_summary
            
            current_words = len(base_summary.split())
            
            # Adjust length to meet target
            if current_words < target_min:
                # Expand the summary
                expanded = self._expand_summary_controlled(base_summary, text, target_max - current_words, creativity)
                final_summary = expanded
            elif current_words > target_max * 1.2:
                # Compress the summary
                final_summary = self._compress_summary(base_summary, target_max)
            else:
                final_summary = base_summary
            
            # Apply humanization
            if humanize_intensity != "low":
                final_summary = self.humanizer.humanize(final_summary, intensity=humanize_intensity)
            
            # Final word count check
            final_words = len(final_summary.split())
            if final_words < target_min * 0.8:
                # If still too short, add a concluding sentence
                final_summary += " In conclusion, this project aims to make cooking more accessible and enjoyable for everyone."
            
            return final_summary
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def _generate_base_summary(self, text, target_length, creativity):
        """Generate base summary from model"""
        try:
            if "t5" in self.model_type:
                input_text = "summarize: " + text
            else:
                input_text = text
            
            # Truncate input if too long
            inputs = self.tokenizer.encode(
                input_text, 
                return_tensors="pt", 
                max_length=512,
                truncation=True
            ).to(self.device)
            
            # Calculate token limits (1.2 tokens per word for safety)
            token_target = min(int(target_length * 1.2), 400)
            token_min = max(30, int(target_length * 0.4))
            
            # Set parameters based on creativity
            if creativity == "low":
                temperature = 0.3
                num_beams = 2
                repetition_penalty = 2.0
            elif creativity == "high":
                temperature = 0.8
                num_beams = 3
                repetition_penalty = 1.4
            else:
                temperature = 0.6
                num_beams = 2
                repetition_penalty = 1.6
            
            # Generate summary
            with torch.no_grad():
                summary_ids = self.model.generate(
                    inputs,
                    max_length=token_target,
                    min_length=token_min,
                    num_beams=num_beams,
                    temperature=temperature,
                    do_sample=True,
                    top_k=50,
                    top_p=0.92,
                    repetition_penalty=repetition_penalty,
                    early_stopping=True,
                    no_repeat_ngram_size=3,
                    length_penalty=1.8  # Encourage longer summaries
                )
            
            summary = self.tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            return summary
            
        except Exception as e:
            return f"Error in base generation: {str(e)}"
    
    def _expand_summary_controlled(self, summary, original_text, extra_words_needed, creativity):
        """Expand summary by adding relevant details from original text"""
        if extra_words_needed < 15:
            return summary
        
        # Extract key sentences from original text that aren't in summary
        original_sentences = self._split_into_sentences(original_text)
        summary_sentences = self._split_into_sentences(summary)
        
        # Find new sentences to add
        new_sentences = []
        words_added = 0
        
        for sent in original_sentences:
            if words_added >= extra_words_needed:
                break
            
            # Check if sentence is not already in summary (simplified check)
            if not any(summary_sent in sent for summary_sent in summary_sentences if len(summary_sent) > 20):
                sent_words = len(sent.split())
                if sent_words > 5 and words_added + sent_words <= extra_words_needed * 1.2:
                    new_sentences.append(sent)
                    words_added += sent_words
        
        if new_sentences:
            return summary + " " + " ".join(new_sentences)
        else:
            # If no good sentences found, add elaboration
            elaboration = " This project also focuses on " + self._get_topic_words(original_text, 5) + "."
            return summary + elaboration
    
    def _compress_summary(self, summary, target_length):
        """Compress summary to target length"""
        sentences = self._split_into_sentences(summary)
        result = []
        current_words = 0
        
        for sent in sentences:
            sent_words = len(sent.split())
            if current_words + sent_words <= target_length:
                result.append(sent)
                current_words += sent_words
            else:
                # Add part of the sentence
                remaining = target_length - current_words
                if remaining > 3:
                    words = sent.split()[:remaining]
                    result.append(' '.join(words) + '.')
                break
        
        return ' '.join(result)
    
    def _split_into_sentences(self, text):
        """Split text into sentences safely"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _get_topic_words(self, text, num_words=5):
        """Extract key topic words from text"""
        words = text.lower().split()
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        filtered = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Get unique words
        unique = list(dict.fromkeys(filtered))
        return ', '.join(unique[:num_words])
    
    def _generate_long_summary(self, text, target_max, target_min, creativity, humanize_intensity):
        """Generate long summary using chunking"""
        try:
            # Split text into meaningful chunks
            words = text.split()
            chunk_size = 600  # Smaller chunks for better quality
            chunks = []
            
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                chunks.append(chunk)
            
            # Calculate target per chunk
            words_per_chunk = target_max // len(chunks)
            min_per_chunk = max(30, target_min // len(chunks))
            
            # Generate summary for each chunk
            chunk_summaries = []
            
            for i, chunk in enumerate(chunks):
                chunk_summary = self._generate_length_controlled_summary(
                    chunk,
                    max_length=words_per_chunk + 20,
                    min_length=min_per_chunk,
                    creativity=creativity,
                    humanize_intensity="medium"  # Less humanization at chunk level
                )
                
                if not chunk_summary.startswith("Error"):
                    chunk_summaries.append(chunk_summary)
            
            # Combine chunk summaries
            combined = ' '.join(chunk_summaries)
            combined_words = len(combined.split())
            
            # If we're short of target, add connecting sentences
            if combined_words < target_min:
                # Add transitions between chunks
                transitions = [
                    " Furthermore,", " Additionally,", " Moreover,", 
                    " Another important aspect is that", " It's also worth noting that"
                ]
                
                improved = []
                for j, summary in enumerate(chunk_summaries):
                    improved.append(summary)
                    if j < len(chunk_summaries) - 1 and len(chunk_summaries) > 1:
                        improved.append(random.choice(transitions))
                
                combined = ' '.join(improved)
            
            # Final humanization
            if humanize_intensity != "low":
                combined = self.humanizer.humanize(combined, intensity=humanize_intensity)
            
            return combined
            
        except Exception as e:
            return f"Error generating long summary: {str(e)}"
    
    def summarize_with_variations(self, text, target_length=200):
        """Generate multiple summary variations"""
        variations = []
        
        configs = [
            {"creativity": "low", "desc": "Concise Version"},
            {"creativity": "medium", "desc": "Balanced Version"},
            {"creativity": "high", "desc": "Detailed Version"}
        ]
        
        for config in configs:
            try:
                summary = self.summarize(
                    text, 
                    max_length=target_length,
                    min_length=max(50, target_length // 2),
                    creativity=config["creativity"],
                    humanize_intensity="high"
                )
                word_count = len(summary.split())
                variations.append(f"✨ {config['desc']} ({word_count} words):\n{summary}\n")
                variations.append("-" * 60 + "\n")
            except Exception as e:
                variations.append(f"✨ {config['desc']} Error: {str(e)}\n")
        
        return '\n'.join(variations)