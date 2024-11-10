"""
robz_elo_system.py

This script orchestrates the Robz Elo rating system, which processes game score sheets, extracts player names and scores,
calculates updated Elo ratings for each player, and maintains a database of player standings.

Technical Details:

- **Image Parsing and Data Extraction**:
  - Utilizes the Anthropic API (Claude AI) for extracting structured data from game score images.
  - Images are preprocessed (resized or cropped) to fit within the model's token and size constraints.
  - The `parse_game_score` function handles image processing and communicates with the AI model to obtain game data.

- **User Corrections**:
  - The script prompts users to review and correct extracted data through the `implement_user_corrections` function.
  - Allows modifications to team victory points, player details, winners, and adding/removing players.
  - Includes an option to skip future edit prompts within the same session.

- **Elo Rating Calculation**:
  - Employs a custom Elo calculation algorithm implemented in `elo_calculation.py`.
  - Factors in the difference in victory points and previous player ratings to adjust Elo scores.
  - The `calculatePoints` function computes updated ratings based on game outcomes.

- **Data Persistence**:
  - Game results and user corrections are saved to `game_results.json` for record-keeping.
  - Player Elo ratings and game counts are maintained in `elo_database.csv`.
  - The `process_and_save_game_data` and `prepareData` functions handle data storage and updating the Elo database.

- **Logging and Error Handling**:
  - Provides detailed console output for each processing step, including success messages and error notifications.
  - Exception handling ensures that processing continues even if individual images fail.

Dependencies:

- Requires the Anthropic API key configured in `configs/llm_config.py`.
- Depends on external libraries: `pandas`, `Pillow`, `anthropic`, among others listed in `requirements.txt`.

Configuration Variables:

- `NUM_ATTEMPTS`: Number of attempts for the AI to parse each image to achieve consensus. Increase this value to improve the accuracy of the game result data.
- `IMAGE_FOLDER_PATH`: Path to the folder containing the game score images to process.
- `ELO_DATABASE_PATH`: Path to the Elo database CSV file.

"""

import pandas as pd
import os
import sys

from configs.llm_config import API_KEYS
from modules.elo_calculation import calculatePoints
from modules.extract_data import parse_game_score, implement_user_corrections, order_data
from modules.save_data import process_and_save_game_data, prepareData
from modules.utils import print_game_results

# Configuration variable
NUM_ATTEMPTS = 1  # Number of times to send the image to Claude for consensus (increase this value to improve the accuracy of the game result data)
IMAGE_FOLDER_PATH = "test_image_sets/set_1" # Path to the folder containing the images (must contain only image files)
ELO_DATABASE_PATH = "elo_database.csv" # Path to the Elo database (will be created if it doesn't exist)

  
def main():
    image_path = IMAGE_FOLDER_PATH 
    if not os.path.exists(image_path):
        print(f"Error: Image path '{image_path}' does not exist")
        sys.exit(1)
    # Validate API key
    api_key = API_KEYS['claude']
    if api_key == 'your-api-key-here':
        print("Error: API key not configured. Please set your Claude API key in the environment variables.")
        print("See configs/llm_config.py for instructions on how to set up your API key.")
        sys.exit(1)
    elif len(api_key) < 10:  # Claude API keys are typically longer than 10 chars
        print("Error: Invalid API key format. Claude API keys should be longer than 10 characters.")
        print("Current key:", api_key[:8] + "..." if len(api_key) > 8 else api_key)
        print("Please check your API key configuration in the environment variables.")
        sys.exit(1)
    else:
        print("API key validation successful")

    try:
        image_files = os.listdir(image_path)
    except PermissionError:
        print(f"Error: Permission denied for directory '{image_path}'")
        sys.exit(1)

    # Filter image files 
    image_files = [f for f in image_files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    total_files = len(image_files)
    processed_files = 0  # Initialize counter (used to track the number of files processed)

    skip_edit_prompt = False  # Initialize skip_edit_prompt variable (used to skip the edit prompt if the game result is already correct)

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
            processed_files += 1  # Increment counter (used to track the number of files processed)
            full_image_path = os.path.join(image_path, image_file)
            # Parse the game score image (extracts the game result data from the image)
            game_result_dictionary = parse_game_score(full_image_path, num_attempts=NUM_ATTEMPTS)
            print(f"\nFinal consensus data stored in game_result_dictionary for image file '{image_file}':")
            print(game_result_dictionary)

            if game_result_dictionary:
                # Print game results (prints the game result data to the console)
                print_game_results(game_result_dictionary)

                # Implement user corrections, passing skip_edit_prompt (allows the user to correct the game result data if it is incorrect)
                game_result_dictionary, user_corrections, skip_edit_prompt = implement_user_corrections(
                    game_result_dictionary, skip_edit_prompt)

                # Process and save game data (saves the game result data to a JSON file)
                process_and_save_game_data(game_result_dictionary, user_corrections, image_file)

                # Order and calculate points (orders the game result data and calculates the points for each player)
                playerDictionary = order_data(game_result_dictionary, eloDatabase)
                updatedPlayerDictionary = calculatePoints(playerDictionary)

                # Prepare and save updated Elo database (saves the updated Elo database to a CSV file)
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