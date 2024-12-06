import chess
import chess.engine
import chess.pgn
import os
from pathlib import Path
import time

def analyze_game_with_lc0(engine, file_path, output_directory, input_dir_path, analysis_time, nodes_limit):
    with open(file_path) as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break

            scores = []
            wdl_scores = []
            node = game
            while node and node.variations:
                next_node = node.variations[0]
                board = next_node.board()

                # Check if the game is over before analyzing
                if board.is_game_over():
                    print("Game over detected. Skipping analysis for this position.")
                    result = game.headers.get("Result", "*")
                    if result == "1-0":
                        evaluation = 100  # White won
                    elif result == "0-1":
                        evaluation = -100  # Black won
                    else:
                        evaluation = 0  # Draw
                    scores.append(evaluation)
                    wdl_scores.append([1.0, 0.0, 0.0] if result == "1-0" else 
                                      [0.0, 0.0, 1.0] if result == "0-1" else 
                                      [0.0, 1.0, 0.0])
                    break  # Stop analysis as the game is over

                try:
                    result = engine.analyse(board, chess.engine.Limit(nodes=nodes_limit, time=analysis_time))
                except Exception as e:
                    print(f"Engine analysis failed for position:\n{board}\nError: {e}")
                    scores.append(0.0)
                    wdl_scores.append([0.0, 0.0, 0.0])
                    node = next_node
                    continue

                # Extract score and WDL probabilities
                score = result["score"].relative
                if isinstance(score, chess.engine.Cp):
                    evaluation = score.score() / 100.0
                    if not board.turn:
                        evaluation *= -1
                    scores.append(evaluation)
                elif isinstance(score, chess.engine.Mate):
                    if score.mate() > 0:
                        # Side to move can deliver mate
                        evaluation = 100 if board.turn == chess.WHITE else -100
                    else:
                        # Opponent can deliver mate
                        evaluation = -100 if board.turn == chess.WHITE else 100
                    scores.append(evaluation)
                wdl = result.get("wdl")
                if wdl:
                    wins, draws, losses = wdl
                    total = wins + draws + losses
                    win_prob = wins / total if total else 0
                    draw_prob = draws / total if total else 0
                    loss_prob = losses / total if total else 0
                    wdl_probabilities = [win_prob, draw_prob, loss_prob]

                    # Reverse WDL probabilities if it's Black's turn
                    if not board.turn:
                        wdl_probabilities = wdl_probabilities[::-1]

                    wdl_scores.append(wdl_probabilities)
                else:
                    wdl_scores.append([0.0, 0.0, 0.0])

                node = next_node

            if game:
                annotate_game_with_scores_lc0(game, scores, wdl_scores, file_path, output_directory, input_dir_path)


def annotate_game_with_scores_lc0(game, scores, wdl_scores, file_path, output_directory, input_dir_path):
    node = game
    score_index = 0
    while node and node.variations:
        next_node = node.variations[0]
        if score_index < len(scores):
            eval_comment = f"[%eval_lc0 {scores[score_index]}]"
            wdl_comment = f"[%wdl [{wdl_scores[score_index][0]:.2f}, {wdl_scores[score_index][1]:.2f}, {wdl_scores[score_index][2]:.2f}]]"
            existing_comment = next_node.comment
            next_node.comment = f"{existing_comment} {eval_comment} {wdl_comment}" if existing_comment else f"{eval_comment} {wdl_comment}"
        node = next_node
        score_index += 1

    relative_path = Path(file_path).relative_to(input_dir_path)
    dest_folder = Path(output_directory) / relative_path.parent
    dest_folder.mkdir(parents=True, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file_path = dest_folder / f"{base_name}_annotated.pgn"

    with open(output_file_path, 'a') as annotated_pgn:
        exporter = chess.pgn.FileExporter(annotated_pgn)
        game.accept(exporter)


def main_lc0(input_dir_path, output_directory, lc0_path, weights_path, analysis_time, nodes_limit):
    with chess.engine.SimpleEngine.popen_uci([lc0_path, f"--weights={weights_path}"]) as engine:
        engine.configure({"UCI_ShowWDL": True})
        for subdir, dirs, files in os.walk(input_dir_path):
            for file in files:
                if file.endswith(".pgn"):
                    file_path = os.path.join(subdir, file)
                    analyze_game_with_lc0(engine, file_path, output_directory, input_dir_path, analysis_time, nodes_limit)

if __name__ == "__main__":
    start_time = time.time()
    print("Annotating games with lc0...")
    input_dir_path = '/path/to/PGNs'
    output_directory = '/path/to/output'
    lc0_path = '/path/to/lc0'
    weights_path = '/path/to/weights.pb.gz'
    analysis_time = None
    nodes_limit = 20000
    main_lc0(input_dir_path, output_directory, lc0_path, weights_path, analysis_time, nodes_limit)
    print("Engine analysis finished")
    end_time = time.time()
    print("Script finished in {:.2f} minutes".format((end_time - start_time) / 60.0))
