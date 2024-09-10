import chess
import chess.engine
import chess.pgn
import tkinter as tk
from tkinter import ttk, filedialog
import pygame
import numpy as np

# Setează calea către motorul de șah (Stockfish)
engine_path = r"stockfish-windows-x86-64\stockfish\stockfish-windows-x86-64.exe"  # Înlocuiește cu calea corectă

# Inițializează motorul de șah
engine = chess.engine.SimpleEngine.popen_uci(engine_path)

class ChessApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Analiză Partidă de Șah")

        # Inițializează tabla de șah
        self.board = chess.Board()
        self.game = None
        self.moves = []
        self.current_move = 0
        self.recommended_moves = []
        self.recommended_move = None
        self.accuracy_white = 0
        self.accuracy_black = 0
        self.move_evaluations = []

        # Configurare UI
        self.setup_ui()

        # Inițializează pygame pentru a desena tabla
        pygame.init()
        self.screen = pygame.display.set_mode((400, 400))
        self.clock = pygame.time.Clock()
        self.square_size = 50
        self.load_images()

        # Desenează tabla inițială la pornirea programului
        self.draw_board()

    def load_images(self):
        # Încarcă imaginile pieselor de șah
        self.pieces = {}
        pieces = ['bP', 'bN', 'bB', 'bR', 'bQ', 'bK', 'wP', 'wN', 'wB', 'wR', 'wQ', 'wK']
        for piece in pieces:
            self.pieces[piece] = pygame.image.load(fr'C:\Users\Traian\Desktop\images\{piece}.png')

    def setup_ui(self):
        # Configurarea UI inițială
        self.eval_label = ttk.Label(self.root, text="Evaluare: 0.00")
        self.eval_label.pack()

        # Creăm un Canvas pentru bara de evaluare
        self.evaluation_canvas = tk.Canvas(self.root, width=200, height=20)
        self.evaluation_canvas.pack(pady=10)

        self.next_button = ttk.Button(self.root, text="Mutare următoare", command=self.next_move)
        self.next_button.pack()

        self.previous_button = ttk.Button(self.root, text="Mutare anterioară", command=self.previous_move)
        self.previous_button.pack()

        self.load_button = ttk.Button(self.root, text="Încarcă PGN", command=self.load_pgn)
        self.load_button.pack()

        self.accuracy_label = ttk.Label(self.root, text="Acuratețea jucătorilor: ")
        self.accuracy_label.pack()

        self.analysis_progress = ttk.Progressbar(self.root, orient="horizontal", length=300, mode='determinate')
        self.analysis_progress.pack(pady=10)

    def update_evaluation_bar(self, eval):
        # Ștergem conținutul anterior al Canvas-ului
        self.evaluation_canvas.delete("all")

        # Calculăm pozițiile pentru părțile alb și negru
        canvas_width = 200
        mid_point = canvas_width // 2

        # Evaluarea este pe o scară de la -10 la 10, transformăm la o scară de 0 la 20
        bar_value = eval + 10

        # Calculăm lungimile părților alb și negru
        white_length = int((bar_value / 20) * canvas_width)
        black_length = canvas_width - white_length

        # Desenăm partea albă
        self.evaluation_canvas.create_rectangle(0, 0, white_length, 20, fill="white")

        # Desenăm partea neagră
        self.evaluation_canvas.create_rectangle(white_length, 0, canvas_width, 20, fill="black")

    def draw_board(self):
        # Desenează tabla de șah folosind pygame
        colors = [pygame.Color(235, 235, 208), pygame.Color(119, 148, 85)]
        for rank in range(8):
            for file in range(8):
                color = colors[(rank + file) % 2]
                pygame.draw.rect(self.screen, color,
                                 pygame.Rect(file * self.square_size, rank * self.square_size, self.square_size,
                                             self.square_size))

                piece = self.board.piece_at(chess.square(file, 7 - rank))
                if piece:
                    color_prefix = 'w' if piece.color == chess.WHITE else 'b'
                    piece_key = color_prefix + piece.symbol().upper()
                    self.screen.blit(self.pieces[piece_key],
                                     pygame.Rect(file * self.square_size, rank * self.square_size, self.square_size,
                                                 self.square_size))

        # Desenează săgeata pentru mutarea recomandată, dacă există
        if self.recommended_move:
            self.draw_recommended_move_arrow(self.recommended_move)

        pygame.display.flip()

    def draw_recommended_move_arrow(self, move):
        # Funcție pentru a desena o săgeată între pozițiile de start și destinație ale mutării recomandate
        if move is None:
            return

        start_square = move.from_square
        end_square = move.to_square

        # Calculăm coordonatele pentru pozițiile de start și destinație
        start_x = (chess.square_file(start_square)) * self.square_size + self.square_size // 2
        start_y = (7 - chess.square_rank(start_square)) * self.square_size + self.square_size // 2
        end_x = (chess.square_file(end_square)) * self.square_size + self.square_size // 2
        end_y = (7 - chess.square_rank(end_square)) * self.square_size + self.square_size // 2

        # Desenează o săgeată între pozițiile de start și destinație
        pygame.draw.line(self.screen, pygame.Color("red"), (start_x, start_y), (end_x, end_y), 5)

        # Desenează capătul săgeții
        arrow_size = 10
        direction = np.array([end_x - start_x, end_y - start_y])
        direction = direction / np.linalg.norm(direction)  # Normalizează direcția
        perp_direction = np.array([-direction[1], direction[0]])  # Perpendiculară la direcția săgeții

        # Calculăm coordonatele pentru vârful săgeții
        arrow_tip = np.array([end_x, end_y])
        arrow_left = arrow_tip - arrow_size * direction + arrow_size * perp_direction
        arrow_right = arrow_tip - arrow_size * direction - arrow_size * perp_direction

        # Desenează capătul săgeții
        pygame.draw.polygon(self.screen, pygame.Color("red"), [arrow_tip, arrow_left, arrow_right])

    def analyze_entire_game(self):
        # Analizează fiecare mutare din joc și stochează mutarea recomandată
        self.recommended_moves = []
        self.move_evaluations = []
        self.accuracy_white = 0
        self.accuracy_black = 0

        board_copy = self.game.board()  # Copie a tablei inițiale
        self.analysis_progress['maximum'] = len(self.moves)
        self.analysis_progress['value'] = 0

        total_white_score = 0
        total_black_score = 0
        total_white_moves = 0
        total_black_moves = 0

        for index, move in enumerate(self.moves):
            # Evaluarea mutării curente
            info = engine.analyse(board_copy, chess.engine.Limit(time=0.1))
            best_move = info.get("pv", [None])[0]

            # Calculăm scorul pentru evaluare
            score = info["score"].relative
            if score.is_mate():
                evaluation = 100 if score.mate() > 0 else -100
            else:
                # Verificăm dacă scorul este None
                if score.score() is None:
                    evaluation = 0  # Dacă nu avem scor, considerăm evaluarea ca fiind 0
                else:
                    evaluation = score.score() / 100.0  # Împărțit la 100 pentru a-l aduce pe o scară de la -10 la 10

            # Limitează evaluarea la -10 și 10
            evaluation = max(min(evaluation, 10), -10)

            # Stocăm mutările recomandate și evaluările
            self.recommended_moves.append(best_move)
            self.move_evaluations.append(evaluation)
            board_copy.push(move)

            # Actualizează progresul
            self.analysis_progress['value'] = index + 1
            self.root.update()

        # Calculăm acuratețea după ce toate mutările au fost analizate
        self.calculate_accuracy()

    def calculate_accuracy(self):
        total_white_score = 0
        total_black_score = 0
        total_white_moves = 0
        total_black_moves = 0

        for i in range(len(self.moves)):
            move = self.moves[i]
            evaluation = self.move_evaluations[i]
            recommended_move = self.recommended_moves[i]

            # Calculăm abaterea mutării jucătorului față de cea mai bună mutare
            if move == recommended_move:
                move_accuracy = 1.0  # Mutarea jucătorului este identică cu cea a motorului
            else:
                info = engine.analyse(self.board, chess.engine.Limit(time=0.1), root_moves=[move])
                move_score = info["score"].relative
                if move_score.is_mate():
                    deviation = 100 if move_score.mate() < 0 else -100
                else:
                    deviation = abs(evaluation - (move_score.score() / 100.0)) / 10.0

                move_accuracy = max(0, 1 - deviation)  # Normalizarea scorului între 0 și 1

            if i % 2 == 0:  # Mutarea albului
                total_white_moves += 1
                total_white_score += move_accuracy * 100
            else:  # Mutarea negrului
                total_black_moves += 1
                total_black_score += move_accuracy * 100

        # Calculăm acuratețea pentru fiecare jucător
        self.accuracy_white = total_white_score / total_white_moves if total_white_moves > 0 else 0
        self.accuracy_black = total_black_score / total_black_moves if total_black_moves > 0 else 0

        # Afișează acuratețea în interfață
        self.accuracy_label.config(
            text=f"Acuratețea Albului: {self.accuracy_white:.2f}%, Acuratețea Negrului: {self.accuracy_black:.2f}%")

    def custom_evaluate(self, board):
        # Folosim motorul de șah pentru a obține scorul de evaluare
        info = engine.analyse(board, chess.engine.Limit(time=0.1))
        score = info["score"].relative

        if score.is_mate():
            # Calculăm evaluarea pe baza mutărilor până la mat
            mate_in = score.mate()
            if mate_in > 0:
                evaluation = 10 - mate_in  # Mat în favoarea Albului, limitat la 10
            else:
                evaluation = -10 - mate_in  # Mat în favoarea Negrului, limitat la -10
        else:
            # Scorul normalizat al poziției
            evaluation = score.score() / 100.0  # Împărțit la 100 pentru a-l aduce pe o scară de la -10 la 10

        # Asigură-te că evaluarea este în intervalul de la -10 la 10
        evaluation = max(min(evaluation, 10), -10)
        return evaluation

    def next_move(self):
        if self.current_move < len(self.moves):
            self.board.push(self.moves[self.current_move])
            self.current_move += 1
            self.draw_board()

            # Actualizează evaluarea și bara de evaluare
            if self.current_move < len(self.move_evaluations):
                eval = self.move_evaluations[self.current_move - 1]
                self.eval_label.config(text=f"Evaluare: {eval:.2f}")

                # Actualizăm bara de evaluare pe baza noii evaluări
                self.update_evaluation_bar(eval)

            self.update_recommended_move()

    def previous_move(self):
        if self.current_move > 0:
            self.board.pop()
            self.current_move -= 1
            self.draw_board()

            # Actualizează evaluarea și bara de evaluare
            if self.current_move > 0:
                eval = self.move_evaluations[self.current_move - 1]
                self.eval_label.config(text=f"Evaluare: {eval:.2f}")

                # Actualizăm bara de evaluare pe baza noii evaluări
                self.update_evaluation_bar(eval)
            else:
                self.eval_label.config(text="Evaluare: 0.00")
                self.update_evaluation_bar(0)

            self.update_recommended_move()

    def update_recommended_move(self):
        if self.current_move < len(self.recommended_moves):
            self.recommended_move = self.recommended_moves[self.current_move]
        else:
            self.recommended_move = None

    def load_pgn(self):
        file_path = filedialog.askopenfilename(filetypes=[("PGN Files", "*.pgn")])
        if file_path:
            with open(file_path, "r") as pgn_file:
                self.game = chess.pgn.read_game(pgn_file)
                self.moves = list(self.game.mainline_moves())
                self.current_move = 0
                self.board = self.game.board()
                self.draw_board()
                self.analyze_entire_game()

    def run(self):
        # Rulează loop-ul principal al interfeței Tkinter
        self.root.mainloop()

        # Închide motorul de șah la terminarea programului
        engine.quit()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessApp(root)
    app.run()
