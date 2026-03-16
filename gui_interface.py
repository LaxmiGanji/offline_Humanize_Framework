"""
Tkinter GUI for offline summarizer - WITH DIRECT HUMANIZE FEATURE
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from summarizer_engine import OfflineSummarizer
from utils.file_handler import FileHandler
from utils.synonym_engine import SynonymEngine
from utils.humanizer import OfflineHumanizer
import threading
import os
import re

class DirectHumanizer:
    """Directly humanize text without summarization, preserving references"""
    
    def __init__(self, humanizer):
        self.humanizer = humanizer
    
    def humanize_text(self, text, intensity="high"):
        """
        Humanize text while preserving reference numbers like [1], [2], etc.
        
        Args:
            text: Input text to humanize
            intensity: "low", "medium", or "high"
        
        Returns:
            Humanized text with references preserved
        """
        if not text:
            return text
        
        # Step 1: Extract and protect reference numbers
        text, references = self._protect_references(text)
        
        # Step 2: Humanize the text (without affecting protected references)
        humanized = self.humanizer.humanize(text, intensity=intensity)
        
        # Step 3: Restore reference numbers
        humanized = self._restore_references(humanized, references)
        
        return humanized
    
    def _protect_references(self, text):
        """
        Find all reference numbers [1], [2], etc. and replace with placeholders
        Returns modified text and dictionary of placeholders
        """
        # Pattern to find reference numbers like [1], [2], etc.
        pattern = r'\[(\d+)\]'
        
        references = {}
        placeholder_counter = 0
        
        def replace_ref(match):
            nonlocal placeholder_counter
            ref_num = match.group(0)  # Full match like [1]
            placeholder = f"__REF_{placeholder_counter}__"
            references[placeholder] = ref_num
            placeholder_counter += 1
            return placeholder
        
        # Replace all references with placeholders
        modified_text = re.sub(pattern, replace_ref, text)
        
        return modified_text, references
    
    def _restore_references(self, text, references):
        """Restore original reference numbers from placeholders"""
        restored_text = text
        for placeholder, ref in references.items():
            restored_text = restored_text.replace(placeholder, ref)
        return restored_text
    
    def preview_changes(self, original, humanized):
        """Show preview of changes (for display purposes)"""
        # Simple diff view - can be expanded
        original_words = len(original.split())
        humanized_words = len(humanized.split())
        
        return {
            'original_length': original_words,
            'humanized_length': humanized_words,
            'reference_count': len(re.findall(r'\[\d+\]', original)),
            'change_percentage': abs(humanized_words - original_words) / original_words * 100
        }


class SynonymPopup:
    """Popup window for synonym selection"""
    
    def __init__(self, parent, x, y, word, synonyms, callback):
        self.top = tk.Toplevel(parent)
        self.top.title(f"Synonyms for '{word}'")
        self.top.geometry(f"300x250+{x}+{y}")
        self.top.configure(bg='#f0f0f0')
        self.top.transient(parent)
        self.top.grab_set()
        self.callback = callback
        self.word = word
        
        # Header
        header = tk.Label(self.top, text=f"Select synonym for '{word}':", 
                         bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
                         pady=5)
        header.pack(fill=tk.X)
        
        # Frame for synonyms
        frame = tk.Frame(self.top, bg='#f0f0f0', padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        canvas = tk.Canvas(frame, bg='#f0f0f0', highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f0f0f0')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Add synonym buttons
        if synonyms:
            for synonym in synonyms:
                btn = tk.Button(scrollable_frame, 
                               text=f"• {synonym}",
                               command=lambda s=synonym: self.select_synonym(s),
                               bg='#ecf0f1', font=('Arial', 10),
                               anchor=tk.W, padx=10, pady=5,
                               width=30, cursor='hand2')
                btn.pack(fill=tk.X, pady=2)
        else:
            tk.Label(scrollable_frame, text="No synonyms found", 
                    bg='#f0f0f0', font=('Arial', 10)).pack(pady=20)
        
        # Keep original button
        tk.Button(self.top, text="Keep Original", command=self.keep_original,
                 bg='#95a5a6', fg='white', font=('Arial', 9),
                 padx=20, pady=5).pack(pady=10)
        
        # Close button
        tk.Button(self.top, text="Close", command=self.top.destroy,
                 bg='#e74c3c', fg='white', font=('Arial', 9),
                 padx=20, pady=5).pack(pady=5)
    
    def select_synonym(self, synonym):
        self.callback(self.word, synonym)
        self.top.destroy()
    
    def keep_original(self):
        self.callback(self.word, self.word)
        self.top.destroy()


class SynonymHighlighter:
    """Handles word highlighting and synonym replacement"""
    
    def __init__(self, text_widget, synonym_engine):
        self.text_widget = text_widget
        self.synonym_engine = synonym_engine
        self.highlighted_words = []
        
        # Configure tags
        self.text_widget.tag_configure("synonym_candidate", 
                                       background="#fff3cd",
                                       foreground="#856404",
                                       borderwidth=1,
                                       relief="solid")
        
        self.text_widget.tag_configure("changed_word", 
                                       background="#d4edda",
                                       foreground="#155724",
                                       borderwidth=1,
                                       relief="solid")
        
        # Bind events
        self.text_widget.tag_bind("synonym_candidate", "<Button-1>", self.on_click)
        
        self.tooltip = None
    
    def clear_highlights(self):
        self.text_widget.tag_remove("synonym_candidate", "1.0", tk.END)
        self.text_widget.tag_remove("changed_word", "1.0", tk.END)
        self.highlighted_words = []
    
    def highlight_synonym_candidates(self):
        self.clear_highlights()
        
        text = self.text_widget.get("1.0", tk.END)
        candidates = self.synonym_engine.highlight_candidates(text)
        
        for candidate in candidates:
            start_index = f"1.0 + {candidate['start']} chars"
            end_index = f"1.0 + {candidate['end']} chars"
            
            candidate['start_index'] = start_index
            candidate['end_index'] = end_index
            self.highlighted_words.append(candidate)
            
            self.text_widget.tag_add("synonym_candidate", start_index, end_index)
        
        return len(candidates)
    
    def on_click(self, event):
        index = self.text_widget.index(f"@{event.x},{event.y}")
        
        for candidate in self.highlighted_words:
            if self._is_in_range(index, candidate['start_index'], candidate['end_index']):
                self.show_popup(event.x_root, event.y_root, candidate)
                break
    
    def show_popup(self, x, y, candidate):
        synonyms = self.synonym_engine.get_synonyms(candidate['word'])
        
        SynonymPopup(
            self.text_widget, x, y,
            candidate['word'], synonyms,
            self.replace_word
        )
    
    def replace_word(self, old_word, new_word):
        for candidate in self.highlighted_words:
            if candidate['word'] == old_word:
                self.text_widget.delete(candidate['start_index'], candidate['end_index'])
                self.text_widget.insert(candidate['start_index'], new_word)
                
                self.highlight_synonym_candidates()
                
                new_end = f"{candidate['start_index']} + {len(new_word)} chars"
                self.text_widget.tag_add("changed_word", candidate['start_index'], new_end)
                break
    
    def _is_in_range(self, index, start, end):
        try:
            return self.text_widget.compare(start, "<=", index) and \
                   self.text_widget.compare(index, "<=", end)
        except:
            return False


class SummarizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🧠 Offline Humanized Text Summarizer")
        self.root.geometry("1200x850")
        self.root.configure(bg='#f0f0f0')
        
        self.summarizer = None
        self.current_file = None
        self.synonym_engine = SynonymEngine()
        self.humanizer = OfflineHumanizer()
        self.direct_humanizer = DirectHumanizer(self.humanizer)
        self.highlighter = None
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)
        
        title = tk.Label(title_frame, text="🧠 AI-Powered Humanized Text Summarizer", 
                        font=('Arial', 18, 'bold'), bg='#2c3e50', fg='white')
        title.pack(expand=True)
        
        # Main container with scrollbar
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(main_container, bg='#f0f0f0', highlightthickness=0)
        scrollbar = tk.Scrollbar(main_container, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = tk.Frame(canvas, bg='#f0f0f0')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mouse wheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        
        # ===== MODEL SELECTION =====
        model_frame = tk.LabelFrame(self.scrollable_frame, text="🤖 Model Selection", 
                                    bg='#f0f0f0', font=('Arial', 10, 'bold'),
                                    padx=10, pady=10)
        model_frame.pack(fill=tk.X, pady=5)
        
        self.model_var = tk.StringVar(value="t5-small")
        
        models = [
            ("🚀 T5-Small (Fastest, 250MB)", "t5-small"),
            ("⚖️ T5-Base (Balanced, 900MB)", "t5-base"),
            ("🎯 BART-Base (Best Quality, 1.5GB)", "facebook/bart-base")
        ]
        
        for i, (text, value) in enumerate(models):
            rb = tk.Radiobutton(model_frame, text=text, value=value, 
                               variable=self.model_var, bg='#f0f0f0',
                               font=('Arial', 9))
            rb.grid(row=i, column=0, sticky=tk.W, pady=2)
        
        # Load Model Button
        btn_frame = tk.Frame(model_frame, bg='#f0f0f0')
        btn_frame.grid(row=len(models), column=0, pady=10)
        
        self.load_btn = tk.Button(btn_frame, text="📥 Load Model", 
                                  command=self.load_model,
                                  bg='#3498db', fg='white', font=('Arial', 10, 'bold'),
                                  padx=30, pady=8, cursor='hand2')
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        self.model_status = tk.Label(btn_frame, text="❌ Model not loaded", 
                                     bg='#f0f0f0', fg='red', font=('Arial', 9))
        self.model_status.pack(side=tk.LEFT, padx=10)
        
        # ===== INPUT TEXT =====
        input_frame = tk.LabelFrame(self.scrollable_frame, text="📝 Input Text", 
                                    bg='#f0f0f0', font=('Arial', 10, 'bold'),
                                    padx=10, pady=10)
        input_frame.pack(fill=tk.X, pady=5)
        
        # Toolbar
        toolbar = tk.Frame(input_frame, bg='#f0f0f0')
        toolbar.pack(fill=tk.X, pady=5)
        
        tk.Button(toolbar, text="📂 Load File (TXT, PDF, DOCX)", 
                 command=self.load_file,
                 bg='#27ae60', fg='white', padx=15, pady=3, cursor='hand2').pack(side=tk.LEFT, padx=2)
        
        tk.Button(toolbar, text="🗑️ Clear", 
                 command=lambda: self.input_text.delete('1.0', tk.END),
                 bg='#e67e22', fg='white', padx=15, pady=3, cursor='hand2').pack(side=tk.LEFT, padx=2)
        
        self.file_info_var = tk.StringVar(value="No file loaded")
        file_info_label = tk.Label(toolbar, textvariable=self.file_info_var,
                                  bg='#f0f0f0', fg='#7f8c8d', font=('Arial', 8))
        file_info_label.pack(side=tk.RIGHT, padx=10)
        
        # Input text area
        self.input_text = scrolledtext.ScrolledText(input_frame, height=6, 
                                                     wrap=tk.WORD, font=('Arial', 10),
                                                     padx=5, pady=5)
        self.input_text.pack(fill=tk.BOTH, expand=True)
        
        # Word count
        self.input_word_count_var = tk.StringVar(value="Words: 0")
        input_word_count = tk.Label(input_frame, textvariable=self.input_word_count_var,
                                   bg='#f0f0f0', font=('Arial', 8))
        input_word_count.pack(anchor=tk.E, pady=2)
        
        self.input_text.bind('<KeyRelease>', self.update_input_word_count)
        
        # ===== DIRECT HUMANIZE SECTION (NEW) =====
        direct_frame = tk.LabelFrame(self.scrollable_frame, text="🎭 Direct Humanize (Preserve References)", 
                                     bg='#f0f0f0', font=('Arial', 10, 'bold'),
                                     padx=10, pady=10)
        direct_frame.pack(fill=tk.X, pady=5)
        
        direct_btn_frame = tk.Frame(direct_frame, bg='#f0f0f0')
        direct_btn_frame.pack(fill=tk.X, pady=5)
        
        # Humanize Intensity for direct mode
        tk.Label(direct_btn_frame, text="Intensity:", bg='#f0f0f0', 
                font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        
        self.direct_intensity_var = tk.StringVar(value="High")
        direct_intensity_combo = ttk.Combobox(direct_btn_frame, textvariable=self.direct_intensity_var,
                                            values=["Low", "Medium", "High"], width=8)
        direct_intensity_combo.pack(side=tk.LEFT, padx=5)
        
        tk.Button(direct_btn_frame, text="✨ Humanize Directly (No Summary)", 
                 command=self.direct_humanize,
                 bg='#9b59b6', fg='white', font=('Arial', 10, 'bold'),
                 padx=20, pady=5).pack(side=tk.LEFT, padx=20)
        
        # Info label about reference preservation
        tk.Label(direct_btn_frame, text="✓ Preserves [1], [2] references", 
                bg='#f0f0f0', fg='#27ae60', font=('Arial', 9, 'italic')).pack(side=tk.LEFT, padx=10)
        
        # ===== SUMMARY PARAMETERS =====
        param_frame = tk.LabelFrame(self.scrollable_frame, text="⚙️ Summary Parameters", 
                                    bg='#f0f0f0', font=('Arial', 10, 'bold'),
                                    padx=10, pady=10)
        param_frame.pack(fill=tk.X, pady=5)
        
        # Max Words
        tk.Label(param_frame, text="Max Words:", bg='#f0f0f0', 
                font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        vcmd = (self.root.register(self._validate_number), '%P')
        self.max_words_var = tk.StringVar(value="300")
        self.max_words_entry = tk.Entry(param_frame, textvariable=self.max_words_var, 
                                        width=10, validate='key', validatecommand=vcmd)
        self.max_words_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Preset buttons
        preset_frame = tk.Frame(param_frame, bg='#f0f0f0')
        preset_frame.grid(row=0, column=2, padx=10, pady=5, sticky=tk.W)
        
        for val in [100, 250, 500, 1000, 1500, 2000]:
            btn = tk.Button(preset_frame, text=str(val), 
                           command=lambda v=val: self.max_words_var.set(str(v)),
                           bg='#ecf0f1', font=('Arial', 8), width=4)
            btn.pack(side=tk.LEFT, padx=2)
        
        # Min Words
        tk.Label(param_frame, text="Min Words:", bg='#f0f0f0', 
                font=('Arial', 9)).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.min_words_var = tk.StringVar(value="50")
        self.min_words_entry = tk.Entry(param_frame, textvariable=self.min_words_var, 
                                        width=10, validate='key', validatecommand=vcmd)
        self.min_words_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Creativity
        tk.Label(param_frame, text="Creativity:", bg='#f0f0f0', 
                font=('Arial', 9)).grid(row=1, column=2, padx=20, pady=5, sticky=tk.W)
        self.creativity_var = tk.StringVar(value="Medium")
        creativity_combo = ttk.Combobox(param_frame, textvariable=self.creativity_var,
                                      values=["Low", "Medium", "High"], width=10)
        creativity_combo.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Humanize
        tk.Label(param_frame, text="Humanize:", bg='#f0f0f0', 
                font=('Arial', 9)).grid(row=1, column=4, padx=20, pady=5, sticky=tk.W)
        self.humanize_var = tk.StringVar(value="High")
        humanize_combo = ttk.Combobox(param_frame, textvariable=self.humanize_var,
                                      values=["Low", "Medium", "High"], width=10)
        humanize_combo.grid(row=1, column=5, padx=5, pady=5, sticky=tk.W)
        
        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(param_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.grid(row=2, column=0, columnspan=3, pady=10, sticky=tk.W)
        
        self.progress_label = tk.Label(param_frame, text="", bg='#f0f0f0', font=('Arial', 8))
        self.progress_label.grid(row=2, column=3, columnspan=3, pady=10, sticky=tk.W)
        
        # Action Buttons
        action_frame = tk.Frame(param_frame, bg='#f0f0f0')
        action_frame.grid(row=3, column=0, columnspan=6, pady=10)
        
        tk.Button(action_frame, text="✨ Generate Summary", command=self.generate_summary,
                 bg='#e74c3c', fg='white', font=('Arial', 11, 'bold'),
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="🔄 3 Variations", command=self.generate_variations,
                 bg='#f39c12', fg='white', font=('Arial', 10),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="💾 Save", command=self.save_summary,
                 bg='#3498db', fg='white', font=('Arial', 10),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(action_frame, text="🔄 Re-Humanize", command=self.rehumanize_summary,
                 bg='#9b59b6', fg='white', font=('Arial', 10),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        # ===== SYNONYM TOOL =====
        synonym_frame = tk.LabelFrame(self.scrollable_frame, text="🔄 Synonym Tool", 
                                      bg='#f0f0f0', font=('Arial', 10, 'bold'),
                                      padx=10, pady=10)
        synonym_frame.pack(fill=tk.X, pady=5)
        
        synonym_btn_frame = tk.Frame(synonym_frame, bg='#f0f0f0')
        synonym_btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(synonym_btn_frame, text="🔍 Find Synonyms", 
                 command=self.highlight_synonyms,
                 bg='#1abc9c', fg='white', font=('Arial', 10, 'bold'),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Button(synonym_btn_frame, text="🧹 Clear Highlights", 
                 command=self.clear_synonym_highlights,
                 bg='#95a5a6', fg='white', font=('Arial', 10),
                 padx=15, pady=5).pack(side=tk.LEFT, padx=5)
        
        tk.Label(synonym_btn_frame, text="Click on highlighted words to see synonyms", 
                bg='#f0f0f0', fg='#7f8c8d', font=('Arial', 9, 'italic')).pack(side=tk.LEFT, padx=20)
        
        # ===== OUTPUT =====
        output_frame = tk.LabelFrame(self.scrollable_frame, text="📊 Humanized Output", 
                                     bg='#f0f0f0', font=('Arial', 10, 'bold'),
                                     padx=10, pady=10)
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Output toolbar
        output_toolbar = tk.Frame(output_frame, bg='#f0f0f0')
        output_toolbar.pack(fill=tk.X, pady=5)
        
        # Mode indicator
        self.mode_var = tk.StringVar(value="Summary Mode")
        mode_label = tk.Label(output_toolbar, textvariable=self.mode_var, 
                             bg='#f0f0f0', fg='#3498db', font=('Arial', 9, 'bold'))
        mode_label.pack(side=tk.LEFT, padx=5)
        
        tk.Label(output_toolbar, text="|", bg='#f0f0f0', 
                font=('Arial', 9)).pack(side=tk.LEFT, padx=5)
        
        # Target display
        tk.Label(output_toolbar, text="Target: ", bg='#f0f0f0', 
                font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        
        self.target_word_count_var = tk.StringVar(value="300")
        target_label = tk.Label(output_toolbar, textvariable=self.target_word_count_var, 
                               bg='#f0f0f0', font=('Arial', 9, 'bold'), fg='#e74c3c')
        target_label.pack(side=tk.LEFT)
        
        tk.Label(output_toolbar, text="words | Current: ", bg='#f0f0f0', 
                font=('Arial', 9)).pack(side=tk.LEFT, padx=(10,0))
        
        self.output_word_count_var = tk.StringVar(value="0")
        self.output_word_count_label = tk.Label(output_toolbar, textvariable=self.output_word_count_var, 
                                                bg='#f0f0f0', font=('Arial', 9, 'bold'), fg='#27ae60')
        self.output_word_count_label.pack(side=tk.LEFT)
        
        tk.Label(output_toolbar, text="words", bg='#f0f0f0', 
                font=('Arial', 9)).pack(side=tk.LEFT, padx=(2,0))
        
        # Reference count display
        self.ref_count_var = tk.StringVar(value="")
        ref_label = tk.Label(output_toolbar, textvariable=self.ref_count_var, 
                            bg='#f0f0f0', fg='#9b59b6', font=('Arial', 8, 'italic'))
        ref_label.pack(side=tk.RIGHT, padx=10)
        
        # Long summary progress
        self.long_summary_progress = tk.Label(output_toolbar, text="", 
                                             bg='#f0f0f0', fg='#f39c12', font=('Arial', 8))
        self.long_summary_progress.pack(side=tk.RIGHT, padx=10)
        
        # Output text area
        self.output_text = scrolledtext.ScrolledText(output_frame, height=8,
                                                      wrap=tk.WORD, font=('Arial', 10),
                                                      padx=5, pady=5, bg='#f9f9f9')
        self.output_text.pack(fill=tk.BOTH, expand=True)
        
        # Initialize highlighter
        self.highlighter = SynonymHighlighter(self.output_text, self.synonym_engine)
        
        # Status Bar
        status_frame = tk.Frame(self.root, bg='#ecf0f1', height=25)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        self.status_var = tk.StringVar(value="✅ Ready. Load a model to begin.")
        status_bar = tk.Label(status_frame, textvariable=self.status_var, 
                             anchor=tk.W, bg='#ecf0f1', padx=10)
        status_bar.pack(fill=tk.BOTH, expand=True)
    
    def _validate_number(self, value):
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False
    
    def load_model(self):
        def load():
            try:
                self.load_btn.config(state=tk.DISABLED, text="⏳ Loading...")
                self.model_status.config(text="🔄 Loading model...", fg='orange')
                self.status_var.set(f"Loading {self.model_var.get()} model...")
                
                self.summarizer = OfflineSummarizer(model_type=self.model_var.get())
                
                self.model_status.config(text="✅ Model loaded!", fg='green')
                self.status_var.set(f"✅ {self.model_var.get()} model ready!")
                self.load_btn.config(text="✅ Model Loaded", state=tk.NORMAL)
                
            except Exception as e:
                self.model_status.config(text="❌ Error", fg='red')
                self.status_var.set("❌ Failed to load model")
                self.load_btn.config(text="📥 Load Model", state=tk.NORMAL)
                messagebox.showerror("Error", f"Failed to load model:\n{str(e)}")
        
        thread = threading.Thread(target=load)
        thread.daemon = True
        thread.start()
    
    def load_file(self):
        file_path = filedialog.askopenfilename(
            title="Select File",
            filetypes=[
                ("All supported files", "*.txt *.pdf *.docx"),
                ("Text files", "*.txt"),
                ("PDF files", "*.pdf"),
                ("Word documents", "*.docx"),
            ]
        )
        
        if file_path:
            try:
                file_info = FileHandler.get_file_info(file_path)
                self.file_info_var.set(f"📄 {file_info['name']} ({file_info['size']})")
                
                text = FileHandler.read_file(file_path)
                
                self.input_text.delete("1.0", tk.END)
                self.input_text.insert("1.0", text)
                
                word_count = len(text.split())
                self.input_word_count_var.set(f"Words: {word_count}")
                self.status_var.set(f"✅ Loaded: {file_info['name']} ({word_count} words)")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
                self.file_info_var.set("No file loaded")
    
    def get_word_count_params(self):
        try:
            max_words = int(self.max_words_var.get())
            min_words = int(self.min_words_var.get())
            
            if max_words < 20:
                max_words = 20
                self.max_words_var.set("20")
            if min_words < 10:
                min_words = 10
                self.min_words_var.set("10")
            if min_words > max_words:
                min_words = max_words // 3
                self.min_words_var.set(str(min_words))
                
            return max_words, min_words
        except ValueError:
            return 300, 50
    
    def update_progress(self, value, text):
        self.progress_var.set(value)
        self.progress_label.config(text=text)
        self.root.update()
    
    def update_long_progress(self, text):
        self.long_summary_progress.config(text=text)
        self.root.update()
    
    def update_word_count_display(self):
        try:
            text = self.output_text.get("1.0", tk.END).strip()
            if text and not text.startswith("⏳") and not text.startswith("❌"):
                current_words = len(text.split())
                self.output_word_count_var.set(str(current_words))
                
                target = int(self.target_word_count_var.get())
                
                if current_words >= target * 0.9 and current_words <= target * 1.1:
                    self.output_word_count_label.config(fg='#27ae60')
                elif current_words >= target * 0.7:
                    self.output_word_count_label.config(fg='#f39c12')
                else:
                    self.output_word_count_label.config(fg='#e74c3c')
                
                # Count references
                ref_count = len(re.findall(r'\[\d+\]', text))
                if ref_count > 0:
                    self.ref_count_var.set(f"📚 {ref_count} references preserved")
                else:
                    self.ref_count_var.set("")
        except:
            pass
    
    def highlight_synonyms(self):
        if not self.output_text.get("1.0", tk.END).strip():
            messagebox.showinfo("Info", "Generate or humanize text first!")
            return
        count = self.highlighter.highlight_synonym_candidates()
        self.status_var.set(f"✅ Found {count} words with synonyms")
        messagebox.showinfo("Synonym Tool", f"Found {count} words with synonyms.\n\nClick on highlighted words to see synonyms.")
    
    def clear_synonym_highlights(self):
        self.highlighter.clear_highlights()
        self.status_var.set("✅ Highlights cleared")
    
    def direct_humanize(self):
        """Directly humanize input text without summarization"""
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter some text to humanize!")
            return
        
        intensity = self.direct_intensity_var.get().lower()
        
        # Update mode
        self.mode_var.set("Direct Humanize Mode")
        self.target_word_count_var.set("N/A")
        
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", f"⏳ Humanizing text with {intensity} intensity...\n\n")
        self.root.update()
        
        def humanize():
            try:
                self.update_progress(10, "Preparing...")
                self.update_progress(30, "Humanizing...")
                
                # Humanize directly
                humanized = self.direct_humanizer.humanize_text(text, intensity=intensity)
                
                self.update_progress(90, "Finalizing...")
                
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert("1.0", humanized)
                
                # Update word count
                original_words = len(text.split())
                humanized_words = len(humanized.split())
                
                self.update_word_count_display()
                
                # Show comparison
                change = ((humanized_words - original_words) / original_words) * 100
                self.status_var.set(
                    f"✅ Humanized: {original_words} → {humanized_words} words ({change:+.1f}% change)"
                )
                
                self.update_progress(100, "Complete")
                self.root.after(2000, lambda: self.update_progress(0, ""))
                
            except Exception as e:
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert("1.0", f"❌ Error: {str(e)}")
                self.status_var.set("❌ Error")
                self.update_progress(0, "")
                messagebox.showerror("Error", str(e))
        
        thread = threading.Thread(target=humanize)
        thread.daemon = True
        thread.start()
    
    def generate_summary(self):
        if not self.summarizer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter some text!")
            return
        
        input_words = len(text.split())
        if input_words < 20:
            messagebox.showwarning("Warning", "Text too short (min 20 words)")
            return
        
        # Update mode
        self.mode_var.set("Summary Mode")
        
        max_words, min_words = self.get_word_count_params()
        self.target_word_count_var.set(str(max_words))
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert("1.0", f"⏳ Generating {max_words}-word summary...\n\n")
        self.root.update()
        
        def generate():
            try:
                self.update_progress(10, "Preparing...")
                
                creativity = self.creativity_var.get().lower()
                humanize_intensity = self.humanize_var.get().lower()
                
                if max_words > 500:
                    self.update_long_progress(f"Long mode: {max_words} words")
                    self.status_var.set(f"⏳ Generating {max_words}-word summary...")
                
                self.update_progress(30, "Generating...")
                
                summary = self.summarizer.summarize(
                    text, 
                    max_length=max_words,
                    min_length=min_words,
                    creativity=creativity,
                    humanize_intensity=humanize_intensity
                )
                
                self.update_progress(90, "Finalizing...")
                
                if summary.startswith("Error"):
                    self.output_text.delete("1.0", tk.END)
                    self.output_text.insert("1.0", f"❌ {summary}")
                    self.status_var.set("❌ Generation failed")
                else:
                    self.output_text.delete("1.0", tk.END)
                    self.output_text.insert("1.0", summary)
                    
                    self.update_word_count_display()
                    
                    summary_words = len(summary.split())
                    if summary_words < min_words:
                        self.status_var.set(f"⚠️ Got {summary_words}/{max_words} words")
                    elif summary_words > max_words * 1.2:
                        self.status_var.set(f"⚠️ Got {summary_words}/{max_words} words")
                    else:
                        self.status_var.set(f"✅ Success: {summary_words}/{max_words} words")
                
                self.update_progress(100, "Complete")
                self.update_long_progress("")
                self.root.after(2000, lambda: self.update_progress(0, ""))
                
            except Exception as e:
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert("1.0", f"❌ Error: {str(e)}")
                self.status_var.set("❌ Error")
                self.update_progress(0, "")
                self.update_long_progress("")
                messagebox.showerror("Error", str(e))
        
        thread = threading.Thread(target=generate)
        thread.daemon = True
        thread.start()
    
    def generate_variations(self):
        if not self.summarizer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter some text!")
            return
        
        # Update mode
        self.mode_var.set("Variations Mode")
        
        max_words, _ = self.get_word_count_params()
        self.target_word_count_var.set(str(max_words))
        
        def generate():
            try:
                self.update_progress(20, "Generating variations...")
                self.status_var.set(f"⏳ Creating 3 variations...")
                
                variations = self.summarizer.summarize_with_variations(text, target_length=max_words)
                
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert("1.0", variations)
                
                self.update_word_count_display()
                self.status_var.set(f"✅ 3 variations generated")
                self.update_progress(100, "Complete")
                self.root.after(2000, lambda: self.update_progress(0, ""))
                
            except Exception as e:
                self.output_text.delete("1.0", tk.END)
                self.output_text.insert("1.0", f"❌ Error: {str(e)}")
                self.status_var.set("❌ Error")
                self.update_progress(0, "")
                messagebox.showerror("Error", str(e))
        
        thread = threading.Thread(target=generate)
        thread.daemon = True
        thread.start()
    
    def rehumanize_summary(self):
        if not self.summarizer:
            messagebox.showwarning("Warning", "Please load a model first!")
            return
        
        current = self.output_text.get("1.0", tk.END).strip()
        if not current or current.startswith("⏳") or current.startswith("❌"):
            messagebox.showwarning("Warning", "No text to re-humanize!")
            return
        
        intensity = self.humanize_var.get().lower()
        
        try:
            self.update_progress(50, "Re-humanizing...")
            
            # Check if we're in direct mode or summary mode
            if "Direct Humanize" in self.mode_var.get():
                rehumanized = self.direct_humanizer.humanize_text(current, intensity=intensity)
            else:
                rehumanized = self.summarizer.humanizer.humanize(current, intensity=intensity)
            
            self.output_text.delete("1.0", tk.END)
            self.output_text.insert("1.0", rehumanized)
            
            self.update_word_count_display()
            self.status_var.set(f"✅ Re-humanized")
            self.update_progress(100, "Complete")
            self.root.after(2000, lambda: self.update_progress(0, ""))
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.update_progress(0, "")
    
    def save_summary(self):
        text = self.output_text.get("1.0", tk.END).strip()
        if not text or text.startswith("⏳") or text.startswith("❌"):
            messagebox.showwarning("Warning", "No valid text to save!")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Output",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    # Add header with mode info
                    header = f"=== {self.mode_var.get()} ===\n"
                    header += f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    header += "-" * 50 + "\n\n"
                    file.write(header + text)
                self.status_var.set(f"✅ Saved to: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def update_input_word_count(self, event=None):
        text = self.input_text.get("1.0", tk.END).strip()
        words = len(text.split())
        self.input_word_count_var.set(f"Words: {words}")

def main():
    root = tk.Tk()
    app = SummarizerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    import time
    main()