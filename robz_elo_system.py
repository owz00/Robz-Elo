#robz Elo system
import math 
import pandas as pd
import os
from PIL import Image
import pytesseract
import cv2
import base64
import json
import sys
from anthropic import Anthropic
from config import API_KEYS
#this programme is based on this article
#https://towardsdatascience.com/developing-an-elo-based-data-driven-ranking-system-for-2v2-multiplayer-games-7689f7d42a53

def parse_game_score(image_path):
    """
    Uses Claude API to parse game score images and return structured data
    """
    # Read and encode image
    try:
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        print(f"Error reading image file: {str(e)}")
        return None

    # Determine media type based on file extension
    media_type = "image/jpeg"  # default
    if image_path.lower().endswith(".png"):
        media_type = "image/png"
    elif image_path.lower().endswith(".webp"):
        media_type = "image/webp"
    elif image_path.lower().endswith(".gif"):
        media_type = "image/gif"

    client = Anthropic(api_key=API_KEYS['claude'])
    
    # Prepare the prompt
    prompt = """
    You are given a text extracted from a game score sheet. Your task is to parse the text and provide the information in a structured JSON format. Please follow these instructions carefully:

    1. Extract the data from the text, paying close attention to accuracy in player names and scores.
    2. The data to extract includes:
    - For each team (Allies and Axis):
        - List of player names under the 'Player' column.
        - Team's total victory points from the 'Victory P.' column.
        - Each player's individual score from the 'Score' column.
    3. Organize the data into the following JSON structure:

    {
    "teams": {
        "ALLIES": {
        "victory_points": <integer>,
        "players": [
            {
            "name": "<player_name>",
            "score": <integer>
            },
            ...
        ]
        },
        "AXIS": {
        "victory_points": <integer>,
        "players": [
            {
            "name": "<player_name>",
            "score": <integer>
            },
            ...
        ]
        }
    },
    "winner": "<ALLIES or AXIS based on higher victory_points>"
    }

    4. Ensure all numeric values are integers.
    5. If any data is missing or cannot be read, indicate it with a null value in the JSON.
    6. The winner field should contain "ALLIES" if Allies victory points are higher, "AXIS" if Axis victory points are higher, or "TIE" if they are equal.

    Provide only the JSON output and no additional text.
    """

    try:
        # Send image to Claude
        message = client.messages.create(
            model="claude-3-5-sonnet-latest",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_data
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )

        # Parse JSON response
        parsed_data = json.loads(message.content[0].text)
        
        print(f"Parsed claude data: {parsed_data}")
        
        return parsed_data


    except Exception as e:
        print(f"Error parsing game score: {str(e)}")
        return None
    
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

   
#this adds the elo to the correct team
    i = 0
    for players in playerElo:
        if players[0] == 'B':
           teamB.append((players[1], i))
        elif players[0] == 'A':
           teamA.append((players[1], i))
        else:
           print("incorrect team in array")
        i += 1   
        
    teamBSize = len(teamB)
    teamASize = len(teamA)
    averageChanceofWinning = [0] * (teamBSize + teamASize)
   #this calculates the probability of each individual players vs each player of the other team
   #the average for that players if found and then added to the averages of all the othe players on the A team
   #the probability of A team winning vs B team is then found by averaging the averages of the A team
    for playerA in teamA: 
        personalProbability = 0 
        for playerB in teamB:
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
    """ os.chdir('Desktop/robzScripts') """
    
    image_path = 'test_images/test.jpg'
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' does not exist")
        sys.exit(1)
    if len(API_KEYS['claude']) <= 10:
        print("Error: Invalid API key")
        sys.exit(1)
    
    # This function parses the image and returns a dictionary with the game results
    # Example output:
    """ == GAME RESULTS ===

    ALLIES (169 VP)
    ----------------------------------------
    Starfy          Score: 1435
    ShadowFalcon    Score: 931
    MrCoffee        Score: 36
    Bapoivre        Score: 12

    AXIS (167 VP)
    ----------------------------------------
    The Grinch      Score: 828
    Danielo1375     Score: 220
    Nick            Score: 164
    Mawcin_ka       Score: 49

    WINNER: ALLIES
    ======================================== """
    
    game_result_dictionary = parse_game_score(image_path)
    
    print("\n=== GAME RESULTS ===")
    print(f"\nALLIES ({game_result_dictionary['teams']['ALLIES']['victory_points']} VP)")
    print("-" * 40)
    for player in game_result_dictionary['teams']['ALLIES']['players']:
        print(f"{player['name']:<15} Score: {player['score']}")
        
    print(f"\nAXIS ({game_result_dictionary['teams']['AXIS']['victory_points']} VP)")  
    print("-" * 40)
    for player in game_result_dictionary['teams']['AXIS']['players']:
        print(f"{player['name']:<15} Score: {player['score']}")
        
    print(f"\nWINNER: {game_result_dictionary['winner']}")
    print("=" * 40 + "\n")

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
