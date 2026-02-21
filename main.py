import sys
import subprocess

def check_dependencies():
    """Fail fast if critical OS dependencies are missing."""
    try:
        # Check FFmpeg binary
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except FileNotFoundError:
        print("CRITICAL ERROR: 'ffmpeg' binary not found in system PATH. Please install FFmpeg (e.g., `brew install ffmpeg`).")
        sys.exit(1)
    except subprocess.CalledProcessError:
        print("CRITICAL ERROR: 'ffmpeg' binary failed to execute properly.")
        sys.exit(1)
        
    try:
        import PySide6
    except ImportError as e:
        print(f"CRITICAL ERROR: Missing UI dependency. Run `pip install PySide6`.\nDetails: {e}")
        sys.exit(1)

check_dependencies()

from PySide6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # Set global application style attributes if necessary
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
