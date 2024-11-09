# Robz Elo system
import pandas as pd
import os
import sys

from llm_config import API_KEYS
from Elo_calculation import calculatePoints
from extract_data import parse_game_score, implement_user_corrections, order_data
from save_data import process_and_save_game_data, prepareData

from utils import print_game_results

# Configuration variable
NUM_ATTEMPTS = 1  # Number of times to send the image to Claude for consensus
IMAGE_FOLDER_PATH = "test_images"
ELO_DATABASE_PATH = "elo_database.csv"

  
def main():
    image_path = IMAGE_FOLDER_PATH
    if not os.path.exists(image_path):
        print(f"Error: Image path '{image_path}' does not exist")
        sys.exit(1)
    if len(API_KEYS['claude']) <= 10:
        print("Error: Invalid API key")
        sys.exit(1)

    try:
        image_files = os.listdir(image_path)
    except PermissionError:
        print(f"Error: Permission denied for directory '{image_path}'")
        sys.exit(1)

    # Filter image files
    image_files = [f for f in image_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    total_files = len(image_files)
    processed_files = 0  # Initialize counter

    skip_edit_prompt = False  # Initialize skip_edit_prompt variable

    # Load the Elo database (assumed to be a CSV file)
    if os.path.exists(ELO_DATABASE_PATH):
        try:
            eloDatabase = pd.read_csv(ELO_DATABASE_PATH)
        except Exception as e:
            print(f"Error reading '{ELO_DATABASE_PATH}': {e}")
            # Initialize an empty DataFrame if error occurs
            eloDatabase = pd.DataFrame(columns=['PlayerName', 'Starting Elo', 'games played'])
    else:
        # Initialize an empty DataFrame if the file doesn't exist
        eloDatabase = pd.DataFrame(columns=['PlayerName', 'Starting Elo', 'games played'])

    for image_file in image_files:
        try:
            processed_files += 1  # Increment counter
            full_image_path = os.path.join(image_path, image_file)
            # Parse the game score image
            game_result_dictionary = parse_game_score(full_image_path)
            print(f"\nFinal consensus data stored in game_result_dictionary for image file '{image_file}':")
            print(game_result_dictionary)

            if game_result_dictionary:
                # Print game results
                print_game_results(game_result_dictionary)

                # Implement user corrections, passing skip_edit_prompt
                game_result_dictionary, user_corrections, skip_edit_prompt = implement_user_corrections(
                    game_result_dictionary, skip_edit_prompt)

                # Process and save game data
                process_and_save_game_data(game_result_dictionary, user_corrections, image_file)

                # Order and calculate points
                playerDictionary = order_data(game_result_dictionary, eloDatabase)
                updatedPlayerDictionary = calculatePoints(playerDictionary)

                # Prepare and save updated Elo database
                eloDatabase = prepareData(updatedPlayerDictionary, eloDatabase)
            else:
                print(f"Failed to parse game results for '{image_file}'.")
                continue
        except Exception as e:
            print(f"An error occurred while processing '{image_file}': {e}")
            continue  # Continue with the next file even if there's an error

    # After all files have been processed, display final ELO scores
    try:
        # Save the updated Elo database
        eloDatabase.to_csv(ELO_DATABASE_PATH, index=False)
        print("\nElo database updated and saved.")

        # Display final ELO scores per player
        print("\n=== FINAL ELO SCORES ===")
        print("-" * 50)
        if len(eloDatabase) > 0:
            eloDatabase_sorted = eloDatabase.sort_values(by='Starting Elo', ascending=False)
            print(eloDatabase_sorted.to_string(index=False))
        else:
            print("No player data available.")
        print("-" * 50 + "\n")
    except Exception as e:
        print(f"An error occurred while saving or displaying final ELO scores: {e}")


if __name__ == "__main__":
    main()