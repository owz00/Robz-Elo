import sys
import logging
from itertools import combinations
from modules.utils import load_elo_database
from configs.app_config import ELO_JSON_DATABASE_PATH

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main():
    players1 = ['Taters', 'The Grinch', 'THE LONG SHLONG', 'ShadowFalcon', 'Starly', 'naej7']
    
    # Try to read the database
    try:
        database = load_elo_database(ELO_JSON_DATABASE_PATH)
    except Exception as e:
        logging.error("Failed to load database", exc_info=True)
        sys.exit(1)
    
    # Check if database is empty
    if not database or 'Players' not in database:
        logging.error("Database is empty or missing 'Players' key")
        sys.exit(1)

    # Filter out players specified in `players1`
    playerList = []
    for player in database['Players']:
        if player['PlayerName'] in players1:
            try:
                playerList.append((player['PlayerName'], player['Starting Elo']))
            except KeyError as e:
                logging.warning(f"Player data missing expected fields: {e}")
                continue

    if len(playerList) != len(players1):
        missing_players = set(players1) - {p[0] for p in playerList}
        logging.warning(f"The following players were not found in the database: {', '.join(missing_players)}")
    
    # Ensure we have an even number of players for splitting into teams
    players = playerList
    n = len(players)
    if n % 2 != 0:
        logging.error("Odd number of players, cannot split evenly into two teams")
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
    logging.info("Best Team Split Found:")
    logging.info(f"Team A: {best_team1}, Score: {Team_A_Score}")
    logging.info(f"Team B: {best_team2}, Score: {Team_B_Score}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical("An unexpected error occurred", exc_info=True)
        sys.exit(1)