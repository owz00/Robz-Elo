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
    subtractElo = abs(enemyElo - playerElo) / rcf
    probability  =  round(1 / (1 + pow(10, subtractElo)), 4)

    return probability 


def gamePrediction(playerElo):

    personalProbability  = 0 
    overallProbability = 0
    finalProbability = 0
    teamA = []
    teamB = []
  
#this adds the elo to the correct team
    i = 0
    for players in playerElo:
        if players[0] == 'B':
           item = (players[1], i)
           teamB.append(item)
        elif players[0] == 'A':
           item = (players[1], i)
           teamA.append(item)
        else:
           print("incorrect team in array")
        i += 1   
    ##print(teamB)       
    teamBSize = len(teamB)
    teamASize = len(teamA)
    teamBPersonalProbability = [0] * teamBSize
    averageChanceofWinning = [0] * (teamBSize + teamASize)
   #this calculates the probability of each individual players vs each player of the other team
   #the average for that players if found and then added to the averages of all the othe players on the A team
   #the probability of A team winning vs B team is then found by averaging the averages of the A team
    for playerA in teamA: 
        personalProbability = 0 
        for playerB in teamB:
           print(playerB[0], playerB[1])
           p = playerProbability(playerB[0] , playerA[0])
           
           personalProbability += p #this calculates for every A players
           opposingProbability  = abs(1 - p)/teamBSize
           averageChanceofWinning[playerB[1]] += opposingProbability #this holds chance for every B players 

        overallProbability += personalProbability / teamBSize
        averageChanceofWinning[playerA[1]] = personalProbability / teamBSize

    finalProbability = overallProbability / teamASize
    teamAProbability = finalProbability
    teamBProbability = abs(1 - finalProbability)

    return teamAProbability, teamBProbability, averageChanceofWinning

#when i find their probability i put it in the right indedx
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
