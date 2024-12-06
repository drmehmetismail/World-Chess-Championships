"""The part below inputs the CSV player_stats.csv and outputs a CSV file 
    containing the following summary statistics:
    - Average and median of each numeric column
    - Average and median of the merged white and black columns
    - Total number of moves
    - Total number of games
    It also outputs a density distribution plot for each merged column.
"""
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_summary_stats(player_stats, summary_stats_path):
    # Calculate summary statistics
    summary_stats = player_stats.describe().transpose()
    summary_stats = summary_stats[['mean', '50%', 'std', 'min', 'max']]
    summary_stats.columns = ['Mean', 'Median', 'Std Dev', 'Min', 'Max']
    summary_stats = summary_stats.round(2)

    # Calculate total moves and games
    total_moves = player_stats['total_moves'].sum()
    total_games = player_stats['total_game_count'].sum()/2

    # Add total moves and games to summary stats
    summary_stats.loc['Total Moves'] = [total_moves, total_moves, 0, total_moves, total_moves]
    summary_stats.loc['Total Games'] = [total_games, total_games, 0, total_games, total_games]

    # Reorder rows for better readability: Total Moves, Total Games, avg_gi, avg_missed_points, avg_missed_points_white, avg_missed_points_black, avg_gi_white, avg_gi_black, avg_acpl, Elo, TPR, gi_median, missed_points_median
    summary_stats = summary_stats.reindex(['Total Moves', 'Total Games', 'avg_gi', 'avg_missed_points', 'avg_missed_points_white', 'avg_missed_points_black', 'avg_gi_white', 'avg_gi_black', 'avg_acpl', 'Elo', 'TPR', 'gi_median', 'missed_points_median'])

    # Save summary statistics to CSV
    summary_stats.to_csv(summary_stats_path)

# Main Functionality
def main_summary_stats(player_stats_output_path, player_stats_output_dir, folder):

    # Define the output of the summary_stats CSV file path within the output directory
    summary_stats_path = os.path.join(player_stats_output_dir, f'summary_stats_{folder}.csv')

    # Load player_stats from player_stats_output_path
    player_stats = pd.read_csv(player_stats_output_path)

    # Generate summary statistics and density plots
    generate_summary_stats(player_stats, summary_stats_path)

if __name__ == '__main__':
    player_stats_output_path = '/workspaces/Quick-Game-Intelligence-for-Chess/Stats/player_stats.csv'
    player_stats_output_dir = '/workspaces/Quick-Game-Intelligence-for-Chess/Stats'
    main_summary_stats(player_stats_output_path, player_stats_output_dir)