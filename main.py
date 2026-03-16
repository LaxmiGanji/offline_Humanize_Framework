import tkinter as tk
from gui_interface import SummarizerGUI
import warnings
warnings.filterwarnings('ignore')

def main():
    print("=" * 60)
    print("🧠 Offline Humanized Text Summarizer")
    print("=" * 60)
    print("\n🚀 Starting application...")
    
    root = tk.Tk()
    app = SummarizerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()