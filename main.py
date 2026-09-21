"""
main.py - Entry point for BeamAnalyzer Pro
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app.ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RM Calculadora de Momentos y Cortantes")
    app.setWindowIcon(QIcon("icon.ico"))
    app.setOrganizationName("UTA - Ing Civil")
    
    # Set Fusion style for a modern look
    app.setStyle("Fusion")
    
    # Main Window
    window = MainWindow()
    
    # Try to load dark theme
    theme_path = os.path.join(os.path.dirname(__file__), "app", "assets", "styles", "dark_theme.qss")
    window.apply_theme(theme_path)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
