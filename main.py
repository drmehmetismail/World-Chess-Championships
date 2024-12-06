# Main function for the Fast GI calculator
from pgn_evaluation_fast_analyzer import main_analyze
from pgn_evaluation_fast_analyzer_lc0 import main_analyze_lc0
from stockfish_pgn_annotator import main_stockfish
from lc0_pgn_annotator import main_lc0
from csv_to_player_stats import main_stats
from summary_stats import main_summary_stats
from json_to_csv_converter import main_json_to_csv
from wcc_stats import process_chess_data
import time
import os

start_time = time.time()

# WCC_matches folder contains a few games. You can download all games from Lichess or from another website and analyze them by setting games_annotated = False 
# the main function will run the Fast GI calculator for each PGN file in the directory.
input_main_pgn_dir = '/workspaces/World-Chess-Championships/WCC_matches'
for folder in os.listdir(input_main_pgn_dir): 
    # Set a variable folder_name store the folder name, note that "folder" is NOT the name.

    # Set the input and output directories for the Fast GI calculator
    input_pgn_dir = os.path.join(input_main_pgn_dir, folder)    

    # Skip the file if it is not a directory
    if not os.path.isdir(input_pgn_dir) or folder == 'Stats':
        continue

    # If the games are annotated with Stockfish evaluations, set this to True. Otherwise, set it to False.
    games_annotated = True

    # Set the engine Leela Chess Zero or Stockfish
    engine = 'Stockfish'

    if not games_annotated:
        print(f"Annotating games with {engine}...")
        # Set the dir paths for the PGN files and the output directory
        input_dir_path = input_pgn_dir
        output_directory = input_pgn_dir
        # set the path to the Stockfish executable
        # e.g.: 'C:\...\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe'
        # stockfish_path = '/home/linuxbrew/.linuxbrew/bin/stockfish'
        if engine == 'Stockfish':
            engine_path = '/home/linuxbrew/.linuxbrew/bin/stockfish'
            DEPTH = 25
            weights_path = None
            main_stockfish(input_dir_path, output_directory, engine_path, DEPTH)
        else: # Leela Chess Zero
            engine_path = '/opt/homebrew/Cellar/lc0/0.31.2/libexec/lc0'
            weights_path = '/opt/homebrew/Cellar/lc0/0.31.2/libexec/42850.pb.gz'
            DEPTH = 10
            main_lc0(input_dir_path, output_directory, lc0_path, weights_path, analysis_time=0.1)
        # Call the main function to annotate the games
        print(f"{engine} analysis finished")

    # Change the output directory if needed
    output_json_dir = input_pgn_dir
    # Define Stats directory inside the input PGN directory
    output_stats_dir = os.path.join(input_main_pgn_dir, 'Stats')

    # Set whether the game intelligence (GI0 score should be weighted by opponent's Elo. For WCC, it's set False.
    weighted = False
    # Input win, draw, and loss values. Standard FIDE: [1, 0.5, 0]. Norway Chess: [3, 1.25, 0] (will be normalized by 1/3; Armageddon score added manually).
    # In case of Norway Chess with Armageddon (weighted: False)
    wdl_values = [1, 0.5, 0]
    # Enter total_min, +minutes after certain moves (usually 40) and plus secs after each move. Many WCC games are not annotated with time control.
    plus_min_plus_sec = [90, 30, 30]
    if engine == 'Stockfish':
        main_analyze(input_pgn_dir, output_json_dir, wdl_values, weighted)
    else: # Leela Chess Zero
        main_analyze_lc0(input_pgn_dir, output_json_dir, wdl_values, plus_min_plus_sec, weighted)

    # Set the input and output directories for the JSON to CSV converter
    json_input_dir = output_json_dir
    # Define the output CSV directory inside the input PGN directory, call is 'Stats'
    csv_output_dir = output_stats_dir
    main_json_to_csv(json_input_dir, csv_output_dir, folder)

    # Set the input and output directories for the player stats 
    # If multiple CSVs set input_dir, otherwise, set csv_all_games_path 
    # input_dir = "..."
    # Export the output CSV file in the 'Stats' directory: csv_output_dir/aggregated_game_data.csv
    csv_all_games_path = os.path.join(csv_output_dir, f'aggregated_game_data_{folder}.csv')
    player_stats_output_dir = csv_output_dir
    main_stats(csv_all_games_path, player_stats_output_dir, folder)

    # Summarize the player stats
    player_stats_output_path = os.path.join(player_stats_output_dir, f'player_stats_{folder}.csv')
    main_summary_stats(player_stats_output_path, player_stats_output_dir, folder)

# Process all WCC games and plot the average missed points per year
process_chess_data(output_stats_dir)

# Now process JSON files altogether to create an overall player stats CSV
json_input_dir = input_main_pgn_dir
main_json_to_csv(json_input_dir, csv_output_dir, 'all')

# Set the input and output directories for the player stats
csv_all_games_path = os.path.join(csv_output_dir, 'aggregated_game_data_all.csv')
player_stats_output_dir = csv_output_dir
main_stats(csv_all_games_path, player_stats_output_dir, 'all')

end_time = time.time()
print("Script finished in {:.2f} minutes".format((end_time - start_time) / 60.0))
