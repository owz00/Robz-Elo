"""
This script tests the Robz Elo rating system's ability to correctly parse game score images and extract player data.
It validates:
1. The correct parsing of team names and victory points from score sheet images
2. The accurate extraction of player names and their individual scores
3. That the extracted data exactly matches known correct results stored in JSON files

The test compares the parsed results against expected JSON files, validating that:
- The number of teams matches
- Victory points for each team are correct 
- All players are detected
- Player names are extracted accurately
- Player scores are parsed correctly
"""

IMAGE_SET_PATH = 'images/set_1'
EXPECTED_RESULTS_PATH = 'expected_results/set_1'

import os
import sys
import json
import unittest
from loguru import logger

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, parent_dir)

# Now you can import modules from the parent directory
from modules.extract_data import parse_game_score
from modules.utils import load_elo_database
from configs.app_config import ELO_JSON_DATABASE_PATH, LOGGING_FILE_PATH, LOG_LEVEL

# Configure Loguru
logger.remove()
logger.add(
    LOGGING_FILE_PATH,
    rotation="5 MB",
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
)
logger.add(
    sys.stdout,
    level=LOG_LEVEL,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
)

class TestRobzEloSystem(unittest.TestCase):
    def setUp(self):
        logger.info("=== Setting up test environment ===")
        
        # Set up paths
        self.test_set_path = os.path.join(current_dir, IMAGE_SET_PATH)
        self.expected_results_path = os.path.join(current_dir, EXPECTED_RESULTS_PATH)
        logger.info(f"Test images path: {self.test_set_path}")
        logger.info(f"Expected results path: {self.expected_results_path}")
        
        # Load the Elo database before tests
        logger.info("Loading Elo database...")
        self.elo_database = load_elo_database(ELO_JSON_DATABASE_PATH)
        logger.info("Elo database loaded successfully")

    def test_game_results(self):
        logger.info("=== Starting game results tests ===")
        # Listing all test images
        test_images = [
            f for f in os.listdir(self.test_set_path) 
            if f.lower().endswith(('.png', '.jpg', '.jpeg'))
        ]
        logger.info(f"Found {len(test_images)} test images to process")
        
        for image_file in test_images:
            with self.subTest(image=image_file):
                logger.info(f"--- Testing image: {image_file} ---")
                # Full path to the image
                image_path = os.path.join(self.test_set_path, image_file)
                logger.info(f"Processing image at: {image_path}")
                
                # Parse game score using your existing function
                logger.info("Parsing game score...")
                game_result = parse_game_score(image_path, num_attempts=1)
                self.assertIsNotNone(game_result, f"Failed to parse game result for {image_file}")
                logger.info("Game score parsed successfully")

                # Load expected result
                expected_result_file = os.path.join(
                    self.expected_results_path,
                    os.path.splitext(image_file)[0] + '.json'
                )
                logger.info(f"Loading expected results from: {expected_result_file}")
                with open(expected_result_file, 'r') as file:
                    expected_result = json.load(file)
                logger.info("Expected results loaded successfully")
                
                # Compare actual result with expected result
                logger.info("Comparing results...")
                self.compare_game_results(game_result, expected_result)
                logger.info("Results comparison completed")

    def compare_game_results(self, actual, expected):
        logger.info("=== Comparing Game Results ===")

        # Compare teams
        actual_teams = actual.get('teams', {})
        expected_teams = expected.get('teams', {})
        logger.info(f"Checking number of teams - Expected: {len(expected_teams)}, Actual: {len(actual_teams)}")
        self.assertEqual(
            len(actual_teams), len(expected_teams),
            f"Number of teams does not match. Expected: {len(expected_teams)}, Actual: {len(actual_teams)}"
        )

        logger.info("--- Comparing Team Details ---")
        # Sort teams by victory points to compare them regardless of faction names
        actual_teams_sorted = sorted(actual_teams.values(), key=lambda x: x.get('victory_points', 0), reverse=True)
        expected_teams_sorted = sorted(expected_teams.values(), key=lambda x: x.get('victory_points', 0), reverse=True)

        for i, (actual_team, expected_team) in enumerate(zip(actual_teams_sorted, expected_teams_sorted), 1):
            logger.info(f"--- Team {i} ---")
            # Compare victory points
            logger.info(f"Checking victory points - Expected: {expected_team.get('victory_points')}, Actual: {actual_team.get('victory_points')}")
            self.assertEqual(
                actual_team.get('victory_points'), expected_team.get('victory_points'),
                f"Victory points do not match. Expected: {expected_team.get('victory_points')}, Actual: {actual_team.get('victory_points')}"
            )
            
            # Compare players
            actual_players = actual_team.get('players', [])
            expected_players = expected_team.get('players', [])
            logger.info(f"Checking number of players - Expected: {len(expected_players)}, Actual: {len(actual_players)}")
            self.assertEqual(
                len(actual_players), len(expected_players),
                f"Number of players does not match. Expected: {len(expected_players)}, Actual: {len(actual_players)}"
            )

            logger.info("Comparing player details:")
            # Sort players by score to compare them in order
            actual_players_sorted = sorted(actual_players, key=lambda x: x.get('score', 0), reverse=True)
            expected_players_sorted = sorted(expected_players, key=lambda x: x.get('score', 0), reverse=True)

            for actual_player, expected_player in zip(actual_players_sorted, expected_players_sorted):
                logger.info("Player comparison:")
                # Compare player names
                logger.info(f"Checking player name - Expected: {expected_player.get('name')}, Actual: {actual_player.get('name')}")
                self.assertEqual(
                    actual_player.get('name'), expected_player.get('name'),
                    f"Player name does not match. Expected: {expected_player.get('name')}, Actual: {actual_player.get('name')}"
                )
                # Compare player scores
                logger.info(f"Checking player score - Expected: {expected_player.get('score')}, Actual: {actual_player.get('score')}")
                self.assertEqual(
                    actual_player.get('score'), expected_player.get('score'),
                    f"Score for player '{expected_player['name']}' does not match. Expected: {expected_player.get('score')}, Actual: {actual_player.get('score')}"
                )

if __name__ == '__main__':
    unittest.main()
    logger.info("All tests completed")