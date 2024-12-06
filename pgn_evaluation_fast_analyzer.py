"""
This script inputs the PGN files with games annotated with Stockfish and outputs a JSON file including calculations of stats such as GI, GPL, ACPL, etc. for each game. 
"""

import chess
import chess.pgn
import chess.engine
import json
import os
from chess.engine import Cp, Wdl
import time


# Function to extract the evaluation from a node
def extract_eval_from_node(node):
    node_evaluation = node.eval()
    #print("node_evaluation: ", node_evaluation)
    if node_evaluation:
        cp_value = node_evaluation.pov(chess.WHITE).score(mate_score=10000) / 100.0
        return cp_value
    else:
        return None

# Function to extract the evaluations from a PGN file
def extract_pawn_evals_from_pgn(game):
    # set the initial value to 0
    pawns_list = [0]
    for node in game.mainline():
        eval_value = extract_eval_from_node(node)
        if eval_value is not None:
            pawns_list.append(eval_value)
    if len(pawns_list) > 1:
        pawns_list[0] = pawns_list[1]
    #print("pawns_list: ", pawns_list)
    return pawns_list if pawns_list else None

# Function to calculate the ACPL for both players
def calculate_acpl(pawns_list):
    white_losses, black_losses = [], []
    for i in range(1, len(pawns_list)):
        centipawn_loss = 100*(pawns_list[i] - pawns_list[i - 1])
        if i % 2 == 1:  # White's turn
            white_losses.append(-centipawn_loss)
        else:  # Black's turn
            black_losses.append(centipawn_loss)
    white_acpl = sum(white_losses) / len(white_losses) if white_losses else 0
    black_acpl = sum(black_losses) / len(black_losses) if black_losses else 0
    return white_acpl, black_acpl

def calculate_gi_by_result(white_gpl, black_gpl, game_result, wdl_values, postmove_exp_white, postmove_exp_black):
    win_value, draw_value, loss_value = wdl_values[0], wdl_values[1], wdl_values[2]
    # Calculate GI based on game result
    if game_result == '1/2-1/2':
        white_gi = draw_value - white_gpl
        black_gi = draw_value - black_gpl
    elif game_result == '1-0':
        white_gi = win_value - white_gpl
        black_gi = loss_value - black_gpl
    elif game_result == '0-1':
        black_gi = win_value - black_gpl
        white_gi = loss_value - white_gpl
    else:
        white_gi = postmove_exp_white - white_gpl
        black_gi = postmove_exp_black - black_gpl
    # Normalize GI scores to the standard 1,0.5,0 scoring system.
    white_gi = white_gi / win_value
    black_gi = black_gi / win_value
    return white_gi, black_gi

# Function to calculate GI and GPL in the usual way
def gi_and_gpl(pawns_list, game_result, WhiteElo, BlackElo, wdl_values, weighted, counts):
    white_gpl, black_gpl = 0, 0
    white_gi, black_gi = 0, 0
    white_move_number, black_move_number = 0, 0

    for i, cp in enumerate(pawns_list):
        # Determine whose turn it is
        turn = "White" if i % 2 == 0 else "Black"
        
        # Convert centipawn value to probability
        # handle the initial case
        premove_eval = Cp(int(100 * pawns_list[i-1] if i > 0 else 100 * pawns_list[1]))
        postmove_eval = Cp(int(100 * cp))

        # Calculate expected values before the move
        win_draw_loss = premove_eval.wdl()
        # Convert win, draw, loss values to probabilities win_prob always gives White's win probability
        win_prob, draw_prob, loss_prob = win_draw_loss.wins / 1000, win_draw_loss.draws / 1000, win_draw_loss.losses / 1000
        premove_exp_white, premove_exp_black = calculate_expected_value(win_prob, draw_prob, loss_prob, turn, wdl_values)

        # Calculate expected values after the move
        win_draw_loss = postmove_eval.wdl()
        win_prob, draw_prob, loss_prob = win_draw_loss.wins / 1000, win_draw_loss.draws / 1000, win_draw_loss.losses / 1000
        postmove_exp_white, postmove_exp_black = calculate_expected_value(win_prob, draw_prob, loss_prob, turn, wdl_values)

        # Calculate GPL and update move number
        if turn == "Black":
            exp_white_point_loss = postmove_exp_white - premove_exp_white
            white_gpl += exp_white_point_loss
            white_move_number += 1
            # Add blunder, mistake, inaccuracy
            if exp_white_point_loss >= 0.5:
                counts['white_blunder'] += 1
            elif exp_white_point_loss >= 0.2:
                counts['white_mistake'] += 1
            elif exp_white_point_loss >= 0.05:
                counts['white_inaccuracy'] += 1
        else:
            exp_black_point_loss = premove_exp_black - postmove_exp_black
            black_gpl += exp_black_point_loss
            # Add blunder, mistake, inaccuracy
            if exp_black_point_loss >= 0.5:
                counts['black_blunder'] += 1
            elif exp_black_point_loss >= 0.2:
                counts['black_mistake'] += 1
            elif exp_black_point_loss >= 0.05:
                counts['black_inaccuracy'] += 1
            black_move_number += 1
    # Calculate GI based on game result
    white_gi, black_gi = calculate_gi_by_result(white_gpl, black_gpl, game_result, wdl_values, postmove_exp_white, postmove_exp_black)
    # Normalize GPLs to the standard 1,0.5,0 scoring system.
    white_gpl = white_gpl / wdl_values[0]
    black_gpl = black_gpl / wdl_values[0]
    # Adjust the GI scores with respect to the opponent's rating (if weighted is True)
    if weighted and WhiteElo is not None and BlackElo is not None:
        white_gi = calculate_adjusted_gi(white_gi, BlackElo, 2800)
        black_gi = calculate_adjusted_gi(black_gi, WhiteElo, 2800)
    # Record raw GIs
    white_gi_raw, black_gi_raw = white_gi, black_gi
    # Normalize GI
    white_gi = calculate_normalized_gi(white_gi)
    black_gi = calculate_normalized_gi(black_gi)
    return white_gi, black_gi, white_gpl, black_gpl, white_gi_raw, black_gi_raw, white_move_number, black_move_number-1, counts

# Function to calculate the expected value of a position
def calculate_expected_value(win_prob, draw_prob, loss_prob, turn, wdl_values):
    win_value, draw_value, loss_value = wdl_values[0], wdl_values[1], wdl_values[2]
    if turn == "White":
        expected_value_white = win_prob * win_value + draw_prob * draw_value
        expected_value_black = loss_prob * win_value + draw_prob * draw_value
    else:
        expected_value_white = loss_prob * win_value + draw_prob * draw_value
        expected_value_black = win_prob * win_value + draw_prob * draw_value
    return expected_value_white, expected_value_black

# Calculate normalized GI score
def calculate_normalized_gi(gi):
    # set a and b for normalized_gi = a + b *gi
    a, b = 157.57, 18.55
    return a  + b* gi
    
# Adjust the GI score with respect to the opponent's rating
def calculate_adjusted_gi(gi, opponent_elo, reference_elo):
    return gi - (1 - 2 * expected_score(opponent_elo, reference_elo)) * abs(gi)

# Adjust the GI score with respect to the opponent's rating
def expected_score(opponent_elo, reference_elo):
    return 1 / (1 + 10 ** ((reference_elo - opponent_elo) / 400))
    
def main_analyze(input_pgn_dir, output_json_dir, wdl_values, weighted):
    # Ensure the output directory exists
    if not os.path.exists(output_json_dir):
        os.makedirs(output_json_dir)
    key_counter = 1
    # walk through all pgn files in the dir
    for dirpath, dirnames, filenames in os.walk(input_pgn_dir):
        for filename in filenames:
            if filename.endswith('.pgn'):
                aggregated_data = {}
                pgn_file_path = os.path.join(dirpath, filename)
                json_file_name = filename.replace('.pgn', '.json')
                output_json_path = os.path.join(output_json_dir, json_file_name)
                with open(pgn_file_path) as pgn:
                    while True:
                        game = chess.pgn.read_game(pgn)
                        if game is None:
                            break
                        # Get the headers of the game
                        game_result = game.headers.get('Result', None)
                        if game_result == '1-0':
                            whiteResult = 1
                            blackResult = 0
                        elif game_result == '0-1':
                            whiteResult = 0
                            blackResult = 1
                        elif game_result == '1/2-1/2':
                            whiteResult = 0.5
                            blackResult = 0.5
                        else:
                            whiteResult = '...'
                            blackResult = '...'
                        # Further game details
                        game_details = {
                            "White": game.headers.get("White", None),
                            "Black": game.headers.get("Black", None),
                            "Event": game.headers.get("Event", None),
                            "Site": game.headers.get("Site", None),
                            "Round": game.headers.get("Round", None),
                            "WhiteElo": game.headers.get("WhiteElo", None),
                            "BlackElo": game.headers.get("BlackElo", None),
                            "WhiteResult": whiteResult,
                            "BlackResult": blackResult,
                            "Date": game.headers.get("Date", None),
                                }
                        # Get the ELO ratings of the players as integers
                        WhiteElo = int(game.headers.get("WhiteElo", None)) if game.headers.get("WhiteElo", None) else None
                        BlackElo = int(game.headers.get("BlackElo", None)) if game.headers.get("BlackElo", None) else None
                        pawns_list = extract_pawn_evals_from_pgn(game)
                        if pawns_list is None or len(pawns_list) < 2:  # Skip this game if no evaluations are available
                            continue
                        white_acpl, black_acpl = calculate_acpl(pawns_list)

                        #black_moves = (len(pawns_list) - 1) // 2
                        #white_moves = len(pawns_list) - 1 - black_moves
                        counts = {
                            'white_inaccuracy': 0,
                            'white_mistake': 0,
                            'white_blunder': 0,
                            'black_inaccuracy': 0,
                            'black_mistake': 0,
                            'black_blunder': 0,
                        }
                        # Calculate GI and GPL for both players
                        white_gi, black_gi, white_gpl, black_gpl, white_gi_raw, black_gi_raw, white_move_number, black_move_number, counts = gi_and_gpl(pawns_list, game_result, WhiteElo, BlackElo, wdl_values, weighted, counts)
                        key = key_counter
                        game_data = {
                            "white_gi": round(white_gi, 1), "black_gi": round(black_gi, 1), 
                            "white_missed_points": round(white_gpl, 2), "black_missed_points": round(black_gpl, 2), "white_missed_points_permove": round(white_gpl/white_move_number, 4), "black_missed_points_permove": round(black_gpl/black_move_number, 4),
                            "white_acpl": round(white_acpl, 2), "black_acpl": round(black_acpl, 2),
                            "white_gi_permove": round(white_gi/white_move_number, 1), "black_gi_permove": round(black_gi/black_move_number, 1),
                            "white_gi_raw": round(white_gi_raw, 2), "black_gi_raw": round(black_gi_raw, 2),
                            "white_move_number": white_move_number, "black_move_number": black_move_number,
                            **game_details,
                            "counts": counts,
                        }
                        # "RawEval": pawns_list,
                        aggregated_data[key] = game_data
                        key_counter += 1                
                if aggregated_data:
                    with open(output_json_path, 'w') as f:
                        json.dump(aggregated_data, f, indent=4)                        
                    # print(f"Aggregated data saved to {output_json_path}")
    # print(f"#Games = {key_counter - 1}")

if __name__ == "__main__":
    # Example usage:
    input_pgn_dir = "/workspaces/Quick-Game-Intelligence-for-Chess/PGNs"
    output_json_dir = input_pgn_dir
    # WDL values for Leela
    wdl_values = [1, 0.5, 0]
    # Analyze the PGN files
    weighted = True
    engine = 'Stockfish'
    main_analyze(input_pgn_dir, output_json_dir, wdl_values, weighted)