CCN Project - Commercial Version
===============================

This project uses a Convolutional Chess Network (CCN) to predict chessboard positions
from images and evaluate them using the Stockfish chess engine.

-------------------------------
📦 SETUP INSTRUCTIONS (Windows)
-------------------------------

1. Download Stockfish:
   → Visit https://stockfishchess.org/download/
   → Download the Windows version (stockfish_XX_x64.exe)
   → Rename it to `stockfish.exe`
   → Place `stockfish.exe` in the **same folder** as the app script (e.g., app.py)

2. Install dependencies:
   Open a terminal in this folder and run:
   ```
   pip install -r requirements.txt
   ```

3. Run the application:
   Double-click `run_app.bat` or run manually:
   ```
   python app.py
   ```

----------------------------------
🐍 REQUIREMENTS (Python Libraries)
----------------------------------

See `requirements.txt` for exact dependencies.

------------------------
📂 FILE STRUCTURE (Simplified)
------------------------

- app.py                  → Main application
- stockfish.exe           → Download separately (not included)
- ccn_model.pth           → Trained CCN model
- empty_board.png         → Reference board
- models/                 → Additional model weights
- data/train/             → Training data (if needed)
