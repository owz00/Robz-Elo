import sys
from itertools import combinations
from modules.utils import load_elo_database
from configs.app_config import ELO_JSON_DATABASE_PATH
import json
from pick import pick
from loguru import logger

# Run from root directory with: python -m modules.matchmaker

# Configure Loguru
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>")

def main():
    # Prompt the user to choose input method
    input_method = input("Choose input method:\n1. Manually enter player names\n2. Select players from list\nEnter 1 or 2: ")

    if input_method == '1':
        # Manual input
        players_input = input("Enter player names separated by commas: ")
        players_list = [name.strip() for name in players_input.split(',')]
    elif input_method == '2':
        # Load players from the database
        try:
            database = load_elo_database(ELO_JSON_DATABASE_PATH)
        except Exception as e:
            logger.error("Failed to load database", exc_info=True)
            sys.exit(1)

        # Check if database is empty
        if not database or 'Players' not in database:
            logger.error("Database is empty or missing 'Players' key")
            sys.exit(1)

        # Extract player names and ELO ratings
        available_players = []
        player_elo_dict = {}
        for player in database['Players']:
            name = player['PlayerName']
            elo = player.get('Starting Elo', 1200)
            available_players.append(f"{name} (ELO: {elo})")
            player_elo_dict[name] = elo

        # Use pick to select players
        title = 'Select players to matchmake (press SPACE to mark, ENTER to continue):'
        selected = pick(available_players, title, multiselect=True, min_selection_count=2)
        # Extract player names from the selected options
        players_list = []
        for option, index in selected:
            # Extract the player's name before " (ELO:"
            name = option.split(" (ELO:")[0]
            players_list.append(name)
    else:
        logger.error("Invalid input method selected.")
        sys.exit(1)

    # Proceed with the rest of the matchmaking
    # Try to read the database
    try:
        database = load_elo_database(ELO_JSON_DATABASE_PATH)
    except Exception as e:
        logger.error("Failed to load database", exc_info=True)
        sys.exit(1)

    # Check if database is empty
    if not database or 'Players' not in database:
        logger.error("Database is empty or missing 'Players' key")
        sys.exit(1)

    # Filter out players specified in `players_list`
    playerList = []
    for player in database['Players']:
        if player['PlayerName'] in players_list:
            try:
                playerList.append((player['PlayerName'], player['Starting Elo']))
            except KeyError as e:
                logger.warning(f"Player data missing expected fields: {e}")
                continue

    if len(playerList) != len(players_list):
        missing_players = set(players_list) - {p[0] for p in playerList}
        logger.warning(f"The following players were not found in the database: {', '.join(missing_players)}")

    # Ensure we have an even number of players for splitting into teams
    players = playerList
    n = len(players)
    if n % 2 != 0:
        logger.error("Odd number of players, cannot split evenly into two teams")
        sys.exit(1)

    best_diff = float('inf')
    best_team1, best_team2 = [], []

    # Generate all possible ways to split players into two groups of equal size
    for team1_indices in combinations(range(n), n // 2):
        team1 = [players[i] for i in team1_indices]
        team2 = [players[i] for i in range(n) if i not in team1_indices]
        
        # Calculate total scores for each team
        score_team1 = sum(player[1] for player in team1)
        score_team2 = sum(player[1] for player in team2)
        score_diff = abs(score_team1 - score_team2)

        # Track the best split (minimizing the score difference)
        if score_diff < best_diff:
            best_diff = score_diff 
            Team_A_Score, Team_B_Score = score_team1, score_team2
            best_team1, best_team2 = team1, team2

    # Log the final teams and scores
    logger.info("Best Team Split Found:")
    logger.info(f"Team A: {best_team1}, Score: {Team_A_Score}")
    logger.info(f"Team B: {best_team2}, Score: {Team_B_Score}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical("An unexpected error occurred", exc_info=True)
        sys.exit(1)