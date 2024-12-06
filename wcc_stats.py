import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Define the function to process the directory
def process_chess_data(directory_path):
    # Dictionary to store average missed_points per year
    avg_missed_points_per_year = {}
    total_game_count = 0
    total_moves = 0
    # Iterate through files in the directory
    for file_name in os.listdir(directory_path):
        if file_name.endswith('.csv') and file_name.startswith('player_stats_'):
            try:
                # Extract year from file name
                year = int(file_name.split('_')[-1].split('.')[0])

                # Read the CSV file
                file_path = os.path.join(directory_path, file_name)
                data = pd.read_csv(file_path)

                # Ensure avg_missed_points exists in the CSV
                if 'avg_missed_points' in data.columns:
                    # Calculate the average missed_points for the year
                    avg_missed_points = data['avg_missed_points'].mean()
                    avg_missed_points_per_year[year] = avg_missed_points
                # calculate the total_game_count column for all years
                total_game_count += data['total_game_count'].sum() / 2
                # calculate the total_moves column for all years
                total_moves += data['total_moves'].sum()
            except Exception as e:
                print(f"Error processing file {file_name}: {e}")

    # Create a sorted DataFrame from the dictionary
    avg_missed_points_df = pd.DataFrame(list(avg_missed_points_per_year.items()), columns=['Year', 'Average Missed Points'])
    avg_missed_points_df.sort_values('Year', inplace=True)

    print("Total game count: ", total_game_count)
    print("Total move count: ", total_moves)

    # Plot the results
    plt.figure(figsize=(10, 6))
    plt.plot(avg_missed_points_df['Year'], avg_missed_points_df['Average Missed Points'], marker='o')
    plt.title('World Chess Championships 1886 - 2024')
    plt.xlabel('Year')
    plt.ylabel('Average Missed Points')
    plt.grid()
    # Set y-axis ticks every 0.2 starting from 0
    y_ticks = np.arange(0, max(avg_missed_points_df['Average Missed Points']) + 0.2, 0.2)
    plt.yticks(y_ticks)
    # Add trendline
    z = np.polyfit(avg_missed_points_df['Year'], avg_missed_points_df['Average Missed Points'], 1)
    p = np.poly1d(z)
    plt.plot(avg_missed_points_df['Year'],p(avg_missed_points_df['Year']),"r--")
    plt.show()
    # Save the plot as an image
    plt.savefig(os.path.join(directory_path, 'average_missed_points_per_year.png'))


