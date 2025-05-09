import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import os
import pyautogui
import threading
import time
import chess
import chess.svg
import cairosvg
from stockfish import Stockfish
import io
from fen_predictor import load_model, load_image, predict_fen

EMPTY_BOARD_PATH = "empty_board.png"

def generate_empty_board(path):
    board = Image.new("RGB", (256, 256), "white")
    draw = ImageDraw.Draw(board)
    for row in range(8):
        for col in range(8):
            color = "#f0d9b5" if (row + col) % 2 == 0 else "#b58863"
            draw.rectangle([col * 32, row * 32, (col + 1) * 32, (row + 1) * 32], fill=color)
    board.save(path)

class ChessHelperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCN Chess Helper")
        self.root.geometry("800x400")

        if not os.path.exists(EMPTY_BOARD_PATH):
            generate_empty_board(EMPTY_BOARD_PATH)

        self.board_img = Image.open(EMPTY_BOARD_PATH)
        self.tk_board = ImageTk.PhotoImage(self.board_img)

        self.board_label = tk.Label(self.root, image=self.tk_board, borderwidth=2, relief="sunken")
        self.board_label.grid(row=0, column=0, padx=10, pady=10)

        self.controls_frame = tk.Frame(self.root)
        self.controls_frame.grid(row=0, column=1, sticky="n", padx=10, pady=10)

        self.set_region_button = ttk.Button(self.controls_frame, text="🖱 Set Region", command=self.set_region)
        self.set_region_button.pack(pady=5)

        self.start_button = ttk.Button(self.controls_frame, text="▶️ Start Analysis", command=self.start_analysis)
        self.start_button.pack(pady=5)

        self.pause_button = ttk.Button(self.controls_frame, text="⏸ Pause Analysis", command=self.stop_analysis)
        self.pause_button.pack(pady=5)

        self.restart_stockfish_button = ttk.Button(self.controls_frame, text="🔄 Restart Stockfish", command=self.restart_stockfish)
        self.restart_stockfish_button.pack(pady=5)

        self.fen_label = ttk.Label(self.controls_frame, text="FEN:")
        self.fen_label.pack(anchor="w", pady=(20, 0))
        self.fen_display = tk.Text(self.controls_frame, height=2, width=40)
        self.fen_display.pack()

        self.best_move_label = ttk.Label(self.controls_frame, text="Best Move:")
        self.best_move_label.pack(anchor="w", pady=(10, 0))
        self.best_move_display = ttk.Label(self.controls_frame, text="...", font=("Courier", 12))
        self.best_move_display.pack(anchor="w")

        self.eval_label = ttk.Label(self.controls_frame, text="Evaluation:")
        self.eval_label.pack(anchor="w", pady=(10, 0))

        self.eval_canvas = tk.Canvas(self.controls_frame, width=20, height=200, bg="white", bd=1, relief="sunken")
        self.eval_canvas.pack(anchor="w")

        ttk.Label(self.controls_frame, text="Settings:").pack(anchor="w", pady=(20, 0))

        ttk.Label(self.controls_frame, text="My Color:").pack(anchor="w")
        self.color_var = tk.StringVar(value="w")
        ttk.Radiobutton(self.controls_frame, text="White", variable=self.color_var, value="w", command=self.on_color_change).pack(anchor="w")
        ttk.Radiobutton(self.controls_frame, text="Black", variable=self.color_var, value="b", command=self.on_color_change).pack(anchor="w")

        ttk.Label(self.controls_frame, text="Depth:").pack(anchor="w", pady=(10, 0))
        self.depth_var = tk.IntVar(value=15)
        depth_entry = ttk.Entry(self.controls_frame, textvariable=self.depth_var, width=5)
        depth_entry.pack(anchor="w")

        self.region_box = None
        self.model = load_model("ccn_model.pth")
        self.stockfish = Stockfish(path="stockfish.exe", parameters={"Threads": 2, "Minimum Thinking Time": 30})
        self.last_fen = ""
        self.my_color = "w"
        self.depth = 15
        self.analysis_active = False

    def restart_stockfish(self):
        print("🔁 Restarting Stockfish...")
        self.stockfish = Stockfish(path="stockfish.exe", parameters={"Threads": 2, "Minimum Thinking Time": 30})

    def set_region(self):
        print("🖱 Click and drag to select a region...")
        self.root.withdraw()
        overlay = tk.Toplevel()
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.3)
        overlay.attributes("-topmost", True)
        overlay.config(bg="black")
        canvas = tk.Canvas(overlay, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self.region_start = None
        self.rect_id = None

        def on_mouse_down(event):
            self.region_start = (event.x, event.y)
            if self.rect_id:
                canvas.delete(self.rect_id)

        def on_mouse_drag(event):
            if self.region_start:
                x1, y1 = self.region_start
                x2, y2 = event.x, event.y
                if self.rect_id:
                    canvas.delete(self.rect_id)
                self.rect_id = canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)

        def on_mouse_up(event):
            x1, y1 = self.region_start
            x2, y2 = event.x, event.y
            overlay.destroy()
            self.root.deiconify()
            self.region_box = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            print(f"✅ Region set to: {self.region_box}")

        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

    def start_analysis(self):
        if not self.region_box:
            print("⚠️ Please set a region first.")
            return
        print("▶️ Starting live analysis...")
        self.analysis_active = True
        threading.Thread(target=self.analysis_loop, daemon=True).start()

    def on_color_change(self):
        print(f"🎨 Color changed to {self.color_var.get()}. Restarting analysis.")
        self.stop_analysis()
        self.start_analysis()

    def stop_analysis(self):
        print("⏹ Stopping analysis.")
        self.analysis_active = False

    def get_best_move(self, fen):
        try:
            self.stockfish.set_fen_position(fen)
            self.stockfish.set_depth(self.depth_var.get())
            info = self.stockfish.get_evaluation()
            score = info.get("value", 0)
            move = self.stockfish.get_best_move()
            return move or "(no move found)", score
        except Exception as e:
            print("❌ Stockfish evaluation failed:", e)
            self.restart_stockfish()
            return "(error)", 0

    def render_fen_to_board(self, fen, best_move=None, save_path="rendered_board.png"):
        board = chess.Board(fen.split()[0])
        from_square = to_square = None
        arrows = []
        squares = []
        if best_move and len(best_move) == 4:
            from_square = chess.parse_square(best_move[:2])
            to_square = chess.parse_square(best_move[2:])
            arrows = [chess.svg.Arrow(from_square, to_square, color="#00cc00")]
            squares = [from_square, to_square]
        svg = chess.svg.board(
            board,
            size=256,
            arrows=arrows,
            squares=squares,
            orientation=self.color_var.get() == "w",
            colors={
                "square light": "#f0d9b5",
                "square dark": "#b58863",
                "square highlight": "#ff0000",
                "arrow": "#00cc00"
            }
        )
        png_data = cairosvg.svg2png(bytestring=svg)
        with open(save_path, "wb") as f:
            f.write(png_data)

    def draw_eval_bar(self, score):
        self.eval_canvas.delete("all")
        height = 200
        score = max(min(score, 1000), -1000)
        percent = (score + 1000) / 2000
        fill_height = height * percent
        self.eval_canvas.create_rectangle(0, height - fill_height, 20, height, fill="#00cc00" if score >= 0 else "#cc0000")

    def analysis_loop(self):
        while self.analysis_active:
            screenshot = pyautogui.screenshot(region=self.region_box)
            screenshot = screenshot.resize((256, 256)).convert("RGB")
            screenshot.save("live_frame.png")
            my_color = self.color_var.get()
            image_tensor = load_image("live_frame.png", my_color=my_color)
            raw_fen = predict_fen(self.model, image_tensor, my_color=my_color)
            fen_parts = raw_fen.split(" ")
            fen_parts[1] = self.color_var.get()
            eval_fen = " ".join(fen_parts)
            try:
                board = chess.Board(eval_fen)
                if not board.is_valid() or board.is_game_over(claim_draw=True):
                    raise ValueError("Invalid or finished board state")
            except ValueError:
                print(f"❌ Skipping invalid FEN: {eval_fen}")
                time.sleep(2)
                continue
            if eval_fen != self.last_fen:
                print("🔁 Board changed! New FEN:", eval_fen)
                self.last_fen = eval_fen
                self.update_gui(eval_fen, eval_fen)
            time.sleep(2)

    def update_gui(self, display_fen, eval_fen):
        self.fen_display.delete("1.0", tk.END)
        self.fen_display.insert(tk.END, eval_fen)
        best_move, eval_score = self.get_best_move(eval_fen)
        self.best_move_display.config(text=best_move)
        self.render_fen_to_board(display_fen, best_move=best_move)
        img = Image.open("rendered_board.png")
        self.tk_board = ImageTk.PhotoImage(img)
        self.board_label.config(image=self.tk_board)
        self.board_label.image = self.tk_board
        self.draw_eval_bar(eval_score)

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessHelperApp(root)
    root.mainloop()
