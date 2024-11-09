# Robz Elo system
import math 

def playerProbability(enemyElo, playerElo):
    rcf = 1000  # Random chance factor
    subtractElo = (enemyElo - playerElo) / rcf
    probability  =  round(1 / (1 + pow(10, subtractElo)), 4)
    return probability 


def gamePrediction(playerDictionary):
    teams = sorted(playerDictionary.keys())  # Sort team names for consistent ordering
    if len(teams) != 2:
        print("Error: There must be exactly two teams.")
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



#when i find their probability i put it in the right index
def calculatePoints(playerDictionary):
    teams = sorted(playerDictionary.keys())  # Sort team names
    if len(teams) != 2:
        print("Error: There must be exactly two teams.")
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

    for player in updatedPlayerDictionary[teamB_name]['players']:
        k = 50 / (1 + (player[2] / 300))
        actual_score = 1 if winner == teamB_name else (0.5 if winner == 'TIE' else 0)
        newRating = player[1] + (k * pointFactor) * (actual_score - (1 - RA))
        player.append(round(newRating))

    return updatedPlayerDictionary