"""
This script annotates each game with Stockfish evaluations in each PGN file in a directory.
"""

import chess
import chess.engine
import chess.pgn
import os
import time
from pathlib import Path

def analyze_game_with_stockfish(file_path, stockfish_path, depth, output_directory, input_dir_path):
    # Open and read the PGN file
    with open(file_path) as pgn_file:
        while True:  # Loop to process each game in the PGN file
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break  # No more games in the file

            scores = []
            with chess.engine.SimpleEngine.popen_uci(stockfish_path) as engine:
                node = game
                while node.variations:
                    next_node = node.variations[0]
                    board = next_node.board()
                    info = engine.analyse(board, chess.engine.Limit(depth=depth))
                    score = info.get("score", None)
                    if score is not None:
                        cp = score.relative.score(mate_score=10000)
                        evaluation = cp / 100.0
                        if not board.turn:
                            evaluation *= -1
                        scores.append(evaluation)
                    node = next_node

            # Call the function to annotate the game with the scores
            annotate_game_with_scores(game, scores, file_path, output_directory, input_dir_path)

def annotate_game_with_scores(game, scores, file_path, output_directory, input_dir_path):
    # Iterate over the nodes and add the scores as comments
    node = game
    score_index = 0
    while node.variations:
        next_node = node.variations[0]
        if score_index < len(scores):
            score = scores[score_index]
            eval_string = f"[%eval {score}]" if isinstance(score, float) else f"[{score}]"
            next_node.comment = eval_string
        node = next_node
        score_index += 1

    # Construct the output file path and save the game
    relative_path = Path(file_path).relative_to(input_dir_path)
    dest_folder = Path(output_directory) / relative_path.parent
    dest_folder.mkdir(parents=True, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file_path = dest_folder / f"{base_name}_annotated.pgn"

    with open(output_file_path, 'a') as annotated_pgn:  # 'a' to append each game
        exporter = chess.pgn.FileExporter(annotated_pgn)
        game.accept(exporter)
        
def main_stockfish(input_dir_path, output_directory, stockfish_path, DEPTH):
    for subdir, dirs, files in os.walk(input_dir_path):
        for file in files:
            if file.endswith(".pgn"):
                file_path = os.path.join(subdir, file)
                analyze_game_with_stockfish(file_path, stockfish_path, DEPTH, output_directory, input_dir_path)
