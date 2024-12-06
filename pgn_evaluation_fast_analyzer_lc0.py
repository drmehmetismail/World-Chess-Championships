import chess
import chess.pgn
import chess.engine
import json
import os
from chess.engine import Cp, Wdl
from datetime import timedelta
import re

# Function to extract the evaluation from a node
def extract_eval_from_node(node):
    node_evaluation = node.eval()
    if node_evaluation:
        cp_value = node_evaluation.pov(chess.WHITE).score(mate_score=10000) / 100.0
        return cp_value
    else:
        return None

# Function to extract the WDL from a node's comment
def extract_wdl_from_node(node):
    comment = node.comment
    wdl_annotation = re.search(r'\[%wdl \[([\d\.]+), ([\d\.]+), ([\d\.]+)\]\]', comment)
    if wdl_annotation:
        win_prob = float(wdl_annotation.group(1))
        draw_prob = float(wdl_annotation.group(2))
        loss_prob = float(wdl_annotation.group(3))
        return [win_prob, draw_prob, loss_prob]
    else:
        return None

# Function to extract time from a node
def extract_time_from_node(node):
    # This attempts to find the [%clk hh:mm:ss] annotation within the node's comment
    comment = node.comment  # Extract the comment from the node
    time_annotation = re.search(r'\[%clk (\d+:\d+:\d+)\]', comment)
    if time_annotation:
        # Extract the time string from the regex match group
        time_string = time_annotation.group(1)
        # Optionally, convert the time string to a datetime.timedelta object for further manipulation
        hours, minutes, seconds = map(int, time_string.split(':'))
        return timedelta(hours=hours, minutes=minutes, seconds=seconds)
    else:
        return None

# Function to extract the evaluations from a PGN file
def extract_pawn_evals_from_pgn(game):
    pawns_list = [0]
    wdl_list = []
    nodes_list = [game]  # Start with the root node
    time_list = [timedelta(seconds=0)]
    for node in game.mainline():
        eval_value = extract_eval_from_node(node)
        wdl_value = extract_wdl_from_node(node)
        time_value = extract_time_from_node(node)
        if eval_value is not None:
            pawns_list.append(eval_value)
        else:
            # Append the previous evaluation if the current evaluation is None
            pawns_list.append(pawns_list[-1])
        if wdl_value is not None:
            wdl_list.append(wdl_value)
        else:
            # Append the previous WDL if the current WDL is None
            if len(wdl_list) > 0:
                wdl_list.append(wdl_list[-1])
            else:
                wdl_list.append([0.33, 0.34, 0.33])  # Default values
        nodes_list.append(node)
        if time_value is not None:
            time_list.append(time_value)
        else:
            if len(time_list) > 1 and time_list[-2] is not None:
                # Append the previous time of the same player if the current time is None
                time_list.append(time_list[-2])
            else:
                # list is empty, so continue the loop
                continue
    # Handle the case where there is only one evaluation
    if len(pawns_list) > 1:
        pawns_list[0] = pawns_list[1]
    if len(time_list) == 1:
        time_list = None
    return pawns_list if pawns_list else None, nodes_list if nodes_list else None, time_list if time_list else None, wdl_list if wdl_list else None

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

# Function to save the position and move before a blunder
def position_saver(i, nodes_list, counts, exp_point_loss, time_diff, turn):
    if i == 0:
        return  # Can't get position before move 0
    node_before_blunder = nodes_list[i - 1]
    node_with_blunder = nodes_list[i]
    fen_before_blunder = node_before_blunder.board().fen()
    move_blunder = node_with_blunder.move.uci()
    prev_move = node_before_blunder.move.uci() if node_before_blunder.move else None
    if time_diff is not None:
        # Make sure to convert the time_diff to a string for JSON serialization
        time_diff = str(time_diff)
    else:
        time_diff = None
    # define the move number from the halfmove number i
    move_number = i // 2 + 1
    counts['blunder_positions'].append({
        'turn': turn,
        'fen': fen_before_blunder,
        'move_number': move_number,
        'move': move_blunder,
        'prev_move': prev_move,
        'time_diff': time_diff,
        'exp_point_loss': exp_point_loss
    })

# Function to save the position and move before a critical position
def time_saver(i, nodes_list, counts, exp_point_loss, time_diff, turn):
    node_before_critical = nodes_list[i - 1]
    node_with_critical = nodes_list[i]
    fen_before_critical = node_before_critical.board().fen()
    move_critical = node_with_critical.move.uci()
    prev_move = node_before_critical.move.uci() if node_before_critical.move else None
    move_number = i // 2 + 1
    # Make sure to convert the time_diff to a string for JSON serialization
    time_diff = str(time_diff)
    # If exp_point_loss is negative, then set it 0.
    counts['critical_positions'].append({
        'turn': turn,
        'fen': fen_before_critical,
        'move_number': move_number,
        'move': move_critical,
        'prev_move': prev_move,
        'time_diff': time_diff,
        'exp_point_loss': max(0, exp_point_loss)
    })

# Function to calculate GI and GPL using WDL list for Leela
def gi_and_gpl(wdl_list, game_result, WhiteElo, BlackElo, wdl_values, plus_min_plus_sec, weighted, counts, nodes_list, time_list):
    win_value = wdl_values[0]
    white_gpl, black_gpl = 0, 0
    white_gi, black_gi = 0, 0
    white_move_number, black_move_number = 0, 0
    for i, win_probs in enumerate(wdl_list):
        # Determine whose turn it is
        turn = "White" if i % 2 == 0 else "Black"

        # Get premove_wdl and postmove_wdl
        if i == 0:
            premove_wdl = wdl_list[0]
        else:
            premove_wdl = wdl_list[i-1]
        postmove_wdl = wdl_list[i]

        # Extract win_prob, draw_prob, loss_prob
        premove_win_prob, premove_draw_prob, premove_loss_prob = premove_wdl
        postmove_win_prob, postmove_draw_prob, postmove_loss_prob = postmove_wdl

        if time_list is not None:
            # Calculate the time difference between the current move and the same player's previous move
            total_min, plus_min, plus_sec = plus_min_plus_sec[0], plus_min_plus_sec[1], plus_min_plus_sec[2]
            if i > 2 and i < len(time_list):
                if time_list[i].total_seconds() < time_list[i-2].total_seconds() + plus_sec:
                    # time_diff gives the time the player spent on the move
                    time_diff = time_list[i-2] + timedelta(seconds=plus_sec) - time_list[i]
                else: 
                    # it means that there was a time addition after the move, so plus_min should be added
                    time_diff = time_list[i-2] + timedelta(minutes=plus_min) + timedelta(seconds=plus_sec) - time_list[i]
                # Handle the case where the time difference is negative
                if time_diff.total_seconds() < 0:
                    # time_diff must be the absolute value of the time difference
                    time_diff = abs(time_diff)
            else:
                # set default value of time_diff 0 seconds as a timedelta object
                time_diff = timedelta(seconds=0)
        else:
            time_diff = None

        # Calculate expected values before the move
        premove_exp_white, premove_exp_black = calculate_expected_value(premove_win_prob, premove_draw_prob, premove_loss_prob, turn, wdl_values)

        # Calculate expected values after the move
        postmove_exp_white, postmove_exp_black = calculate_expected_value(postmove_win_prob, postmove_draw_prob, postmove_loss_prob, turn, wdl_values)

        # Calculate GPL and update move number
        if turn == "Black":
            exp_white_point_loss = postmove_exp_white - premove_exp_white
            white_gpl += exp_white_point_loss
            white_move_number += 1
            # Add blunder, mistake, inaccuracy
            if exp_white_point_loss >= 0.30 * win_value:
                counts['white_blunder'] += 1
                position_saver(i, nodes_list, counts, exp_white_point_loss, time_diff, 'White')
            elif exp_white_point_loss >= 0.15 * win_value:
                counts['white_mistake'] += 1
            elif exp_white_point_loss >= 0.07 * win_value:
                counts['white_inaccuracy'] += 1

            # Calculate critical positions for White
            if time_diff is not None:
                if time_diff.total_seconds() >= 1800:
                    counts['white_deepthink'] += 1
                    time_saver(i, nodes_list, counts, exp_white_point_loss, time_diff, 'White') 
                elif time_diff.total_seconds() >= 900:
                    counts['white_critical_position'] += 1
                    time_saver(i, nodes_list, counts, exp_white_point_loss, time_diff, 'White')

        else:
            exp_black_point_loss = premove_exp_black - postmove_exp_black
            black_gpl += exp_black_point_loss
            black_move_number += 1
            # Add blunder, mistake, inaccuracy
            if exp_black_point_loss >= 0.23 * win_value:
                counts['black_blunder'] += 1
                position_saver(i, nodes_list, counts, exp_black_point_loss, time_diff, 'Black')
            elif exp_black_point_loss >= 0.20 * win_value:
                counts['black_mistake'] += 1
            elif exp_black_point_loss >= 0.07 * win_value:
                counts['black_inaccuracy'] += 1
            # Calculate critical positions for Black
            if time_diff is not None:
                if time_diff.total_seconds() >= 1800:
                    counts['black_deepthink'] += 1
                    time_saver(i, nodes_list, counts, exp_black_point_loss, time_diff, 'Black') 
                elif time_diff.total_seconds() >= 900:
                    counts['black_critical_position'] += 1
                    time_saver(i, nodes_list, counts, exp_black_point_loss, time_diff, 'Black')

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

def main_analyze_lc0(input_pgn_dir, output_json_dir, wdl_values, plus_min_plus_sec, weighted):
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
                            whiteResult = None
                            blackResult = None
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
                        pawns_list, nodes_list, time_list, wdl_list = extract_pawn_evals_from_pgn(game)
                        if pawns_list is None or len(pawns_list) < 2:  # Skip this game if no evaluations are available
                            continue
                        white_acpl, black_acpl = calculate_acpl(pawns_list)

                        counts = {
                            'white_inaccuracy': 0,
                            'white_mistake': 0,
                            'white_blunder': 0,
                            'black_inaccuracy': 0,
                            'black_mistake': 0,
                            'black_blunder': 0,
                            'white_deepthink': 0,
                            'black_deepthink': 0,
                            'white_critical_position': 0,
                            'black_critical_position': 0,
                            'blunder_positions': [],
                            'critical_positions': []
                        }
                        # Calculate GI and GPL for both players using wdl_list
                        white_gi, black_gi, white_gpl, black_gpl, white_gi_raw, black_gi_raw, white_move_number, black_move_number, counts = gi_and_gpl(wdl_list, game_result, WhiteElo, BlackElo, wdl_values, plus_min_plus_sec, weighted, counts, nodes_list, time_list)
                        key = key_counter
                        game_data = {
                            "white_gi": round(white_gi, 1), "black_gi": round(black_gi, 1), "white_gi_permove": round(white_gi/white_move_number, 1), "black_gi_permove": round(black_gi/black_move_number, 1),
                            "white_missed_points": round(white_gpl, 2), "black_missed_points": round(black_gpl, 2), "white_missed_points_permove": round(white_gpl/white_move_number, 2), "black_missed_points_permove": round(black_gpl/black_move_number, 2),
                            "white_acpl": round(white_acpl, 2), "black_acpl": round(black_acpl, 2),
                            "white_gi_raw": round(white_gi_raw, 2), "black_gi_raw": round(black_gi_raw, 2),
                            "white_move_number": white_move_number, "black_move_number": black_move_number,
                            **game_details,
                            "counts": counts,
                        }
                        aggregated_data[key] = game_data
                        key_counter += 1                
                if aggregated_data:
                    with open(output_json_path, 'w') as f:
                        json.dump(aggregated_data, f, indent=4)                        
        print(f"#Games = {key_counter - 1}")

if __name__ == "__main__":
    # Example usage:
    input_pgn_dir = "/Users/k1767099/Dropbox/_Norway Chess/Main program/NorwayChess2024/PGNs"
    output_json_dir = input_pgn_dir
    # WDL values for Leela
    wdl_values = [1, 0.5, 0]
    # Analyze the PGN files
    weighted = True
    plus_min_plus_sec = [90, 30, 30] 
    main_analyze(input_pgn_dir, output_json_dir, wdl_values, plus_min_plus_sec, weighted)
