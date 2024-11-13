NUM_ATTEMPTS = 1 # Number of times to send the game score image to Claude for consensus (increase this value to improve the accuracy of the game result data)
IMAGE_FOLDER_PATH = "test_image_sets/set_2" # Path to the folder containing the game score images (must contain only image files)
ELO_JSON_DATABASE_PATH = "players_data.json" # Path to the Elo JSON database (will be created if it doesn't exist)
GAME_RESULTS_JSON_PATH = "game_results.json" # Path to the game results JSON file (will be created if it doesn't exist)
LOGGING_FILE_PATH = "robz_elo_system.log" # Path to the logging file (will be created if it doesn't exist)
LOG_LEVEL = "INFO" # INFO / DEBUG