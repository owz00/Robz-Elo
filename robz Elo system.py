#robz Elo system
import math 
import pandas as pd
import os
from PIL import Image
import pytesseract
import cv2
#this programme is based on this article
#https://towardsdatascience.com/developing-an-elo-based-data-driven-ranking-system-for-2v2-multiplayer-games-7689f7d42a53

def playerProbability(enemyElo, playerElo):

    rcf = 1000 #random chance factor
    subtractElo = (enemyElo - playerElo) / rcf
    probability  =  round(1 / (1 + pow(10, subtractElo)), 4)

    return probability 


def gamePrediction(playerElo):

    personalProbability  = 0 
    overallProbability = 0
    finalProbability = 0
    teamA = []
    teamB = []
    averageChanceofWinning = []
   
#this adds the elo to the correct team
    for players in playerElo:
        print(players)
        if players[0] == 'B':
           teamB.append(players[1])
        elif players[0] == 'A':
           teamA.append(players[1])
        else:
           print("incorrect team in array")
    teamBSize = len(teamB)
    teamASize = len(teamA)
    teamBPersonalProbability = [0] * teamBSize
   #this calculates the probability of each individual players vs each player of the other team
   #the average for that players if found and then added to the averages of all the othe players on the A team
   #the probability of A team winning vs B team is then found by averaging the averages of the A team
    for playerA in teamA: 
        personalProbability = 0 
        i = 0
        for playerB in teamB:
           p = playerProbability(playerB , playerA)
           personalProbability += p
           opposingProbability  = abs(1 - p)/teamBSize
           teamBPersonalProbability[i] += opposingProbability
           i += 1
        overallProbability += personalProbability / teamBSize
        averageChanceofWinning.append(personalProbability / teamBSize) 
    finalProbability = overallProbability / teamASize
    averageChanceofWinning = averageChanceofWinning + teamBPersonalProbability
    teamAProbability = finalProbability
    teamBProbability = abs(1 - finalProbability)

    return teamAProbability, teamBProbability, averageChanceofWinning


def calculatePoints(playerDictionary):
   
    teamAScore = round(playerDictionary['TeamAPoints'][0])
    teamBScore  = round(playerDictionary['TeamBPoints'][0])
    playerElo = list(zip(playerDictionary['team'], playerDictionary['playerElo']))
    playerInformation = list(zip(playerDictionary['playerElo'], 
                                playerDictionary['gamesPlayed'], 
                                playerDictionary['team'],))


    pointFactor = 2 + pow((math.log((abs(teamAScore - teamBScore)) + 1, 10)), 3)
    
    if teamAScore > teamBScore:
        winner = 'A'
    else:
        winner = 'B'

    newPlayerElo = []
    RA, RB, RP = gamePrediction(playerElo)
    print(RA, RB)

   #this calculates the score gained or lossed for each player
    for player in playerInformation:
        k = 50 / (1 + (player[1]/300))
        if winner == 'B':
            if player[2] == 'B':
                newRating = player[0] + ((k*pointFactor) * (1 - RB))
            elif player[2] == 'A':
                newRating = player[0] + ((k*pointFactor) * (0 - RA))
            else:
                print('this team in not A or B')
        elif winner == 'A':
            if player[2] == 'B':
                newRating = player[0] + ((k*pointFactor) * (0 - RB))
            elif player[2] == 'A':
                newRating = player[0] + ((k*pointFactor) * (1 - RA))
            else:
                print('this team in not A or B')
        else:
            print('no winner provided')
        newPlayerElo.append(round(newRating))
    return newPlayerElo, RB, RA, RP
  

def main():

    #pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 
    os.chdir('Desktop/robzScripts')

    df = pd.read_csv("RobzElo.csv")
    dictionary = df.to_dict('list')
    
    newPlayerElo, RB, RA, RP = calculatePoints(dictionary)
    dictionary['new Elo'] = newPlayerElo
    dictionary['TeamBPoints'][1] = RB
    dictionary['TeamAPoints'][1] = RA
    dictionary['RP'] = RP
    
    data_frame = pd.DataFrame(dictionary)
    data_frame.to_csv('newElo.csv', index=False)


if __name__ == "__main__":
    main()