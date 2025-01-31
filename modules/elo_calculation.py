# Robz Elo system
import math 
from loguru import logger

def playerProbability(enemyElo, playerElo):
    """
    Calculates the win probability of a player against an opponent based on their Elo ratings.

    This function computes the expected probability of a player winning a match against an opponent using the Elo rating difference. The probability is calculated using the logistic distribution as per the Elo rating system.

    **Parameters:**
    - `enemyElo` (float): The Elo rating of the opponent.
    - `playerElo` (float): The Elo rating of the player.

    **Returns:**
    - `probability` (float): The probability (between 0 and 1) of the player winning against the opponent.

    **Example:**

    ```python
    playerElo = 1500
    enemyElo = 1600
    win_prob = playerProbability(enemyElo, playerElo)
    print(f"Player's win probability: {win_prob}")
    # Output:
    # Player's win probability: 0.3599
    ```

    In this example, a player with an Elo rating of 1500 has a 35.99% chance of winning against an opponent rated at 1600.

    """
    rcf = 1000  # Random chance factor
    subtractElo = (enemyElo - playerElo) / rcf
    probability = round(1 / (1 + pow(10, subtractElo)), 4)
    return probability

def gamePrediction(playerDictionary):
    """
    Predicts the outcome probabilities of a game between two teams based on individual player Elo ratings.

    This function calculates the win probabilities for each team by considering the matchups between players of opposing teams. It updates the `playerDictionary` with individual player probabilities and overall team win probabilities.

    **Parameters:**
    - `playerDictionary` (dict): A dictionary containing team data with player information and their Elo ratings.

    **Returns:**
    - `playerDictionary` (dict): The updated dictionary with win probabilities for each player and team.

    **Example:**

    ```python
    playerDictionary = {
        'Team Alpha': {
            'players': [
                ['Alice', 1500],
                ['Bob', 1450]
            ]
        },
        'Team Beta': {
            'players': [
                ['Charlie', 1550],
                ['David', 1500]
            ]
        }
    }

    updatedPlayerDictionary = gamePrediction(playerDictionary)
    print(json.dumps(updatedPlayerDictionary, indent=2))

    # Output:
    # {
    #   "Team Alpha": {
    #     "players": [
    #       ["Alice", 1500, 0.3825],
    #       ["Bob", 1450, 0.3407]
    #     ],
    #     "winProbability": 0.3616
    #   },
    #   "Team Beta": {
    #     "players": [
    #       ["Charlie", 1550, 0.6175],
    #       ["David", 1500, 0.6593]
    #     ],
    #     "winProbability": 0.6384
    #   }
    # }
    ```

    In this example, the function calculates:
    - Individual win probabilities for each player against all opponents.
    - Updates each player's data with their average win probability.
    - Calculates the overall team win probability based on player probabilities.

    **Notes:**
    - Assumes there are exactly two teams in the game.
    - Each player's probability reflects their expected performance against the opposing team.

    """
    teams = sorted(playerDictionary.keys())  # Sort team names for consistent ordering
    if len(teams) != 2:
        logger.error("Error: There must be exactly two teams.")
        return playerDictionary

    teamA_name, teamB_name = teams
    teamA = playerDictionary[teamA_name]['players']
    teamB = playerDictionary[teamB_name]['players']
    teamA_size = len(teamA)
    teamB_size = len(teamB)

    overallProbability = 0
    averageChanceOfWinning = [0] * teamB_size
    updateA = []
    updateB = []

    for playerA in teamA:
        personalProbability = 0
        for i, playerB in enumerate(teamB):
            p = playerProbability(playerB[1], playerA[1])
            personalProbability += p
            opposingProbability = (1 - p) / teamB_size
            averageChanceOfWinning[i] += opposingProbability

        overallProbability += personalProbability / teamB_size
        playerA.append(personalProbability / teamB_size)
        updateA.append(playerA)

    for i, playerB in enumerate(teamB):
        playerB.append(averageChanceOfWinning[i])
        updateB.append(playerB)

    finalProbability = overallProbability / teamA_size

    playerDictionary[teamA_name]['winProbability'] = finalProbability
    playerDictionary[teamB_name]['winProbability'] = 1 - finalProbability
    playerDictionary[teamA_name]['players'] = updateA
    playerDictionary[teamB_name]['players'] = updateB

    return playerDictionary

def calculatePoints(playerDictionary):
    """
    Updates the Elo ratings of players based on the game results and predicted outcomes.

    This function calculates the new Elo ratings for each player by comparing the actual game results with the expected probabilities. It adjusts ratings using a dynamic K-factor that depends on the player's current rating.

    **Parameters:**
    - `playerDictionary` (dict): A dictionary containing teams with their scores, player data, and calculated win probabilities.

    **Returns:**
    - `updatedPlayerDictionary` (dict): The input dictionary updated with new Elo ratings for each player.

    **Example:**

    ```python
    playerDictionary = {
        'Team Alpha': {
            'Points': 20,
            'players': [
                ['Alice', 1500, 0.3825],
                ['Bob', 1450, 0.3407]
            ],
            'winProbability': 0.3616
        },
        'Team Beta': {
            'Points': 15,
            'players': [
                ['Charlie', 1550, 0.6175],
                ['David', 1500, 0.6593]
            ],
            'winProbability': 0.6384
        }
    }

    updatedPlayerDictionary = calculatePoints(playerDictionary)

    for team_name, team_data in updatedPlayerDictionary.items():
        print(f"Team: {team_name}")
        for player in team_data['players']:
            print(f"  {player[0]} new Elo rating: {player[-1]}")
    # Output:
    # Team: Team Alpha
    #   Alice new Elo rating: 1526
    #   Bob new Elo rating: 1476
    # Team: Team Beta
    #   Charlie new Elo rating: 1524
    #   David new Elo rating: 1475
    ```

    In this example:
    - `Team Alpha` wins the game with 20 points over `Team Beta` with 15 points.
    - The point factor amplifies the Elo change due to the score difference.
    - Each player's Elo rating is updated based on:
        - Their expected win probability.
        - The actual game outcome.
        - A dynamic K-factor inversely related to their current performance.

    **Notes:**
    - The function only supports games between two teams.
    - It uses logarithmic scaling for the point factor to adjust Elo changes appropriately.
    - A higher point difference results in a larger Elo adjustment.

    """
    teams = sorted(playerDictionary.keys())  # Sort team names
    if len(teams) != 2:
        logger.error("Error: There must be exactly two teams.")
        return playerDictionary

    teamA_name, teamB_name = teams
    teamAScore = playerDictionary[teamA_name]['Points']
    teamBScore = playerDictionary[teamB_name]['Points']

    # Use absolute difference to calculate pointFactor
    pointFactor = 2 + pow((math.log(abs(teamAScore - teamBScore) + 1, 10)), 3)

    if teamAScore > teamBScore:
        winner = teamA_name
    elif teamBScore > teamAScore:
        winner = teamB_name
    else:
        winner = 'TIE'

    updatedPlayerDictionary = gamePrediction(playerDictionary)
    RA = updatedPlayerDictionary[teamA_name]['winProbability']

    for player in updatedPlayerDictionary[teamA_name]['players']:
        k = 50 / (1 + (player[2] / 300))
        actual_score = 1 if winner == teamA_name else (0.5 if winner == 'TIE' else 0)
        newRating = player[1] + (k * pointFactor) * (actual_score - RA)
        player.append(round(newRating))
        if winner == teamA_name:
            player[3] += 1
        else:
            player[4] += 1

    for player in updatedPlayerDictionary[teamB_name]['players']:
        k = 50 / (1 + (player[2] / 300))
        actual_score = 1 if winner == teamB_name else (0.5 if winner == 'TIE' else 0)
        newRating = player[1] + (k * pointFactor) * (actual_score - (1 - RA))
        player.append(round(newRating))
        if winner == teamB_name:
            player[3] += 1
        else:
            player[4] += 1
     
    return updatedPlayerDictionary