import os
import sys
import json
from loguru import logger

from configs.llm_config import API_KEYS
from configs.app_config import NUM_ATTEMPTS, IMAGE_FOLDER_PATH, ELO_JSON_DATABASE_PATH, GAME_RESULTS_JSON_PATH, LOG_LEVEL

def print_game_results(game_result_dictionary, full_image_path=None):
    """
    Prints the game results in a formatted manner.
    """
    logger.info("")
    logger.info("=== GAME RESULTS ===")
    logger.info(f"Image file: {full_image_path}")
    logger.info("")
    
    for team_name, team_info in game_result_dictionary['teams'].items():
        logger.info("----------------------------------------")
        logger.info(f"{team_name} ({team_info['victory_points']} VP)")
        logger.info("----------------------------------------")
        for player in team_info['players']:
            # Pad player name to 15 chars and align score value
            logger.info(f"{player['name']:<15} Score: {player['score']}")
    logger.info("----------------------------------------")
    logger.info(f"WINNER: {game_result_dictionary['winner']}")
    logger.info("========================================")

def validate_configuration():
    """
    Validates the current application configuration and checks the existence of necessary paths and API keys.

    This function ensures that the image directory exists and the API key for Claude is properly configured.
    It logs the current configuration settings and performs necessary checks to prevent runtime errors.

    **Returns:**
    - A tuple containing a list of image files in the specified directory and the image folder path.
    """
    logger.info(f"Current configuration (configs/app_config.py):")
    logger.info(f"NUM_ATTEMPTS: {NUM_ATTEMPTS}")
    logger.info(f"IMAGE_FOLDER_PATH: {IMAGE_FOLDER_PATH}")
    logger.info(f"ELO_JSON_DATABASE_PATH: {ELO_JSON_DATABASE_PATH}")
    logger.info(f"GAME_RESULTS_JSON_PATH: {GAME_RESULTS_JSON_PATH}")
    logger.info(f"LOG_LEVEL: {LOG_LEVEL}")

    image_path = IMAGE_FOLDER_PATH 
    if not os.path.exists(image_path):
        logger.error(f"Error: Image path '{image_path}' does not exist")
        sys.exit(1)

    # Validate API key
    api_key = API_KEYS['claude']
    if api_key == 'your-api-key-here':
        logger.error("Error: API key not configured. Please set your Claude API key in the environment variables.")
        logger.error("See configs/llm_config.py for instructions on how to set up your API key.")
        sys.exit(1)
    elif len(api_key) < 20:  # Claude API keys are typically longer than 20 chars
        logger.error("Error: Invalid API key format. Claude API keys should be longer than 20 characters.")
        logger.error("Current key:", api_key[:20] + "..." if len(api_key) > 20 else api_key)
        logger.error("Please check your API key configuration in the environment variables.")
        sys.exit(1)
    else:
        logger.success("API key validation successful")

    try:
        image_files = os.listdir(image_path)
    except PermissionError:
        logger.error(f"Error: Permission denied for directory '{image_path}'")
        sys.exit(1)

    return image_files, image_path

def display_final_elo_scores(eloDatabaseJson):
    """
    Displays the final ELO scores for each player in a formatted table.

    This function logs the ELO scores of players sorted in descending order.
    It handles any errors that occur during the process and logs appropriate messages.

    **Parameters:**
    - `eloDatabaseJson` (dict): A dictionary containing player data with ELO scores.

    **Returns:**
    - None
    """
    try:
        logger.info("=== FINAL ELO SCORES ===")
        logger.info("-" * 50)
        if eloDatabaseJson:
            logger.info(f"{'Player Name':<20} {'Elo Rating':>10}")
            logger.info("-" * 50)
            sorted_players = sorted(eloDatabaseJson['Players'], 
                                    key=lambda x: x['Starting Elo'], 
                                    reverse=True)
            for player in sorted_players:
                logger.info(f"{player['PlayerName']:<20} {player['Starting Elo']:>10}")
        else:
            logger.error("No player data available.")
        logger.info("-" * 50 + "")
    except Exception as e:
        logger.error(f"An error occurred while saving or displaying final ELO scores: {e}")

def load_elo_database(path):
    """
    Loads the ELO database from a specified file path.

    This function attempts to read a JSON file containing player ELO data. 
    If the file does not exist or an error occurs during reading, it initializes 
    an empty database structure. The function also ensures the file is created 
    if it doesn't exist.

    **Parameters:**
    - `path` (str): The file path to the ELO database JSON file.

    **Returns:**
    - A dictionary representing the ELO database, with player data.
    """
    if os.path.exists(path):
        try:
            with open(path, "r") as file:
                eloDatabaseJson = json.load(file)
                logger.info(f"Elo database loaded from '{path}'")
        except Exception as e:
            logger.error(f"Error reading '{path}': {e}")
            # Initialize an empty JSON structure if there's an error
            eloDatabaseJson = {"Players": []}
    else:
        # Initialize an empty JSON structure if the file doesn't exist
        eloDatabaseJson = {"Players": []}
        logger.info(f"Elo database not found, initialized empty database in '{path}'")

    # Ensure the file is created if it doesn't exist
    if not os.path.exists(path):
        with open(path, "w") as file:
            json.dump(eloDatabaseJson, file, indent=4)

    return eloDatabaseJson