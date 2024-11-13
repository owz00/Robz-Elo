"""
robz_elo_system.py

This script orchestrates the Robz Elo rating system, which processes game score sheets, extracts player names and scores,
calculates updated Elo ratings for each player, and maintains a database of player standings.

Begin by configuring the application in the app_config.py and llm_config.py files.

"""

import pandas as pd
import os
import sys
import json
from loguru import logger

from modules.elo_calculation import calculatePoints
from modules.extract_data import parse_game_score, implement_user_corrections, order_data
from modules.save_data import process_and_save_game_data, prepareData
from modules.utils import print_game_results, validate_configuration, display_final_elo_scores, load_elo_database

from configs.llm_config import API_KEYS
from configs.app_config import NUM_ATTEMPTS, IMAGE_FOLDER_PATH, ELO_JSON_DATABASE_PATH, GAME_RESULTS_JSON_PATH, LOG_LEVEL

# Configure Loguru
logger.remove()
logger.add("robz_elo_system.log", rotation="5 MB", level="DEBUG", format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>")
logger.add(sys.stdout, level=LOG_LEVEL, colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>")

def main():

    image_files, image_path = validate_configuration()

    # Filter image files 
    image_files = [f for f in image_files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    total_files = len(image_files)
    processed_files = 0  # Initialize counter (used to track the number of files processed)

    skip_edit_prompt = False  # Initialize skip_edit_prompt variable (used to skip the edit prompt if the game result is already correct)
    
    # Load the Elo database (loads the Elo database from a JSON file)
    eloDatabaseJson = load_elo_database(ELO_JSON_DATABASE_PATH)

    for image_file in image_files:
        try:

            processed_files += 1  # Increment counter (used to track the number of files processed)
            full_image_path = os.path.join(image_path, image_file)

            # Parse the game score image (extracts the game result data from the image)
            game_result_dictionary = parse_game_score(full_image_path, num_attempts=NUM_ATTEMPTS)
            logger.debug(f"Final consensus data stored in game_result_dictionary for image file '{image_file}':")
            logger.debug(json.dumps(game_result_dictionary, indent=4))

            if game_result_dictionary:

                # Print game results (prints the game result data to the console)
                print_game_results(game_result_dictionary, full_image_path)

                # Implement user corrections, passing skip_edit_prompt (allows the user to correct the game result data if it is incorrect)
                game_result_dictionary, user_corrections, skip_edit_prompt = implement_user_corrections(game_result_dictionary, skip_edit_prompt)

                # Process and save game data (saves the game result data to a JSON file)
                process_and_save_game_data(game_result_dictionary, user_corrections, image_file)

                # Order and calculate points (orders the game result data and calculates the ELO points for each player)
                playerDictionary = order_data(game_result_dictionary, eloDatabaseJson)
                updatedPlayerDictionary = calculatePoints(playerDictionary)

                # Prepare and save updated Elo database (saves the updated Elo database to a JSON file)
                eloDatabaseJson = prepareData(updatedPlayerDictionary, eloDatabaseJson)
            else:
                logger.error(f"Failed to parse game results for '{image_file}'.")
                continue
        except Exception as e:
            logger.error(f"An error occurred while processing '{image_file}': {e}")
            continue  # Continue with the next file even if there's an error

    # Display final ELO scores
    display_final_elo_scores(eloDatabaseJson)



if __name__ == "__main__":
    main()