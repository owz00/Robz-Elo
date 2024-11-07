#robz Elo system
import math 
import pandas as pd
import os
import base64
import json
import sys
from anthropic import Anthropic
from config import API_KEYS
from io import BytesIO

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
        print(f"Error processing image file: {str(e)}")
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
    
    # Prepare the prompt with role assignment and few-shot examples
    prompt = """
    You are a data extraction assistant with perfect vision and excellent attention to detail. 
    Your task is to parse the provided game score sheet image and extract the information into 
    a structured JSON format. Please follow these instructions carefully:

    1. Extract the data from the image, ensuring high accuracy in player names and scores. 
       Implement fuzzy matching for player names that may have up to one character difference 
       (e.g., one letter off). Correct or account for such minor discrepancies.

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
      "winner": "<ALLIES or AXIS or TIE based on higher victory_points>"
    }

    4. Ensure all numeric values are integers.

    5. If any data is missing or cannot be read, indicate it with a null value in the JSON.

    6. The winner field should contain "ALLIES" if Allies victory points are higher, 
       "AXIS" if Axis victory points are higher, or "TIE" if they are equal.

    **Instructions:**

    - Provide only the JSON output and no additional text.
    - Think step by step, analyze every part of the image carefully before providing the final JSON output.
    """

    try:
        # Send image and prompt to Claude
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
        parsed_data = json.loads(message.content[0].text.strip())
        
        print(f"Parsed Claude data: {parsed_data}")
        
        return parsed_data

    except Exception as e:
        print(f"Error parsing game score: {str(e)}")
        return None
    
def playerProbability(enemyElo, playerElo):

    rcf = 1000 #random chance factor
    subtractElo = (enemyElo - playerElo) / rcf
    probability  =  round(1 / (1 + pow(10, subtractElo)), 4)

    return probability 


def gamePrediction(playerDictionary):

    personalProbability  = 0 
    overallProbability = 0
    finalProbability = 0

    teamA = playerDictionary['ATeam']['players']
    teamB = playerDictionary['BTeam']['players']
    teamBSize = len(teamB)
    teamASize = len(teamA)

    updateA = []
    updateB = []
    

    averageChanceofWinning = [0] * teamBSize
   #this calculates the probability of each individual players vs each player of the other team
   #the average for that players if found and then added to the averages of all the othe players on the A team
   #the probability of A team winning vs B team is then found by averaging the averages of the A team
    for playerA in teamA: 
        personalProbability = 0 
        i = 0
        for playerB in teamB:
           p = playerProbability(playerB[1] , playerA[1])
           personalProbability += p #this calculates for every A players
           opposingProbability = abs(1 - p)/teamBSize
           averageChanceofWinning[i] += opposingProbability
           i += 1

        overallProbability += personalProbability / teamBSize
        playerA = list(playerA)
        playerA.append(personalProbability / teamBSize)
        updateA.append(playerA)
       
    for playerB in teamB:
        playerB = list(playerB)
        playerB.append(averageChanceofWinning[teamB.index(playerB)])
        updateB.append(playerB)
       
     

    finalProbability = overallProbability / teamASize

    #teamAProbability = finalProbability
    #teamBProbability = abs(1 - finalProbability)

    playerDictionary['ATeam']['winProbability'] = finalProbability
    playerDictionary['BTeam']['winProbability'] = abs(1 - finalProbability)
    playerDictionary['ATeam']['players'] =  updateA
    playerDictionary['BTeam']['players'] =  updateB

    return playerDictionary





#when i find their probability i put it in the right index
def calculatePoints(playerDictionary):
   
    teamAScore = playerDictionary['ATeam']['Points']
    teamBScore = playerDictionary['BTeam']['Points']

    pointFactor = 2 + pow((math.log((abs(teamAScore - teamBScore)) + 1, 10)), 3)
    
    if teamAScore > teamBScore:
        winner = 'A'
    else:
        winner = 'B'
        
    newPlayerElo = []
    updatedPlayerDictionary = gamePrediction(playerDictionary)

    RA = updatedPlayerDictionary['ATeam']['winProbability']
    RB = updatedPlayerDictionary['BTeam']['winProbability']
    print(RA, RB)

   #this calculates the score gained or lost for each player
    for player in updatedPlayerDictionary['ATeam']['players']:
        k = 50 / (1 + (player[2]/300))
        if winner == 'A':
            newRating = player[1] + ((k*pointFactor) * (1 - RA))
        elif winner == 'B':
            newRating = player[1] + ((k*pointFactor) * (0 - RA))
        else:
            print("error")
        player.append(round(newRating))
    
    for player in updatedPlayerDictionary['BTeam']['players']:
        k = 50 / (1 + (player[2]/300))
        if winner == 'A':
            newRating = player[1] + ((k*pointFactor) * (0 - RA))
        elif winner == 'B':
            newRating = player[1] + ((k*pointFactor) * (1 - RA))
        else:
            print("error")
        player.append(round(newRating))

    return updatedPlayerDictionary




def orderData(data, eloDatabase):
    A_team = []
    B_team = []

     # Populate A_team with ALLIES players and B_team with AXIS players
    #find the players name in the databse
    #of no player exists make a new entry with 1200 as the default Elo
    #add spell checking in the future at this stage
    defaultUserElo = 1200
    defaultNumGames = 0

    for player in data['teams']['ALLIES']['players']:
        if player['name'] in eloDatabase['PlayerName']:
            playerIndex = eloDatabase['PlayerName'].index(player['name'])
            A_team.append(list((player['name'], eloDatabase['Starting Elo'][playerIndex], eloDatabase['games played'][playerIndex])))
        else:
            A_team.append(list((player['name'], defaultUserElo,  defaultNumGames)))

    for player in data['teams']['AXIS']['players']:
        if player['name'] in eloDatabase['PlayerName']:
            playerIndex = eloDatabase['PlayerName'].index(player['name'])
            B_team.append(list((player['name'], eloDatabase['Starting Elo'][playerIndex], eloDatabase['games played'][playerIndex])))
        else:
            B_team.append(list((player['name'], defaultUserElo,  defaultNumGames)))

        '''''
        # Output the results
        print("A Team (ALLIES):", A_team)
        print("B Team (AXIS):", B_team)
        '''''

    playerDictionary = {'ATeam':{'players':[], 'Points':[], 'winProbability':[]},
                            'BTeam':{'players':[], 'Points':[], 'winProbability':[]}
                            }
    
    playerDictionary['ATeam']['players'] = A_team
    playerDictionary['BTeam']['players'] = B_team
    playerDictionary['ATeam']['Points'] = data['teams']['ALLIES']['victory_points']
    playerDictionary['BTeam']['Points'] = data['teams']['AXIS']['victory_points']

    return playerDictionary


def prepareData(updatedDictionary, eloDatabase):
    #find the name in the database and give it a new elo in a new elo column 
    #add 1 to number of games played for the player 
    players = updatedDictionary['ATeam']['players'] + updatedDictionary['BTeam']['players']
     #after processing the data the elo database is updated
    for player in players:
        playerName = player[0]
        if playerName in eloDatabase['PlayerName']:
            playerIndex = eloDatabase['PlayerName'].index(playerName)
            newPlayerElo = player[4]
            eloDatabase['Starting Elo'][playerIndex] = newPlayerElo
            eloDatabase['games played'][playerIndex] +=  1
        else:
            print("player not in database")

    return eloDatabase


  

def main():

    #pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe' 
    os.chdir('Desktop/robzScripts/RobzElo') 
    image_path = 'test_images'
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' does not exist")
        sys.exit(1)
    if len(API_KEYS['claude']) <= 10:
        print("Error: Invalid API key")
        sys.exit(1)




    # Check if images can be listed in the directory
    try:
        image_files = os.listdir(image_path)
    except PermissionError:
        print(f"Error: Permission denied for directory '{image_path}'")
        sys.exit(1)
  
  
  
    for image_file in image_files:

        df = pd.read_csv("Elo Database.csv")
        eloDatabase = df.to_dict('list')

        data = parse_game_score(os.path.join(image_path, image_file))
        playerDictionary = orderData(data, eloDatabase)
        updatedDictionary = calculatePoints(playerDictionary)
        finalDictionary = prepareData(updatedDictionary, eloDatabase)
        print(finalDictionary)
        data_frame = pd.DataFrame(finalDictionary)
        data_frame.to_csv('Elo Database.csv', index=False) 
        print("database updated")
       
        """""
        data = {'teams': {'ALLIES': {'victory_points': 169, 'players': [{'name': 'Starfy', 'score': 1435}, 
                                                                         {'name': 'ShadowFalcon', 'score': 931}, 
                                                                         {'name': 'MrCoffee', 'score': 36}, 
                                                                         {'name': 'Bapouvre', 'score': 12}]}, 
                                                                         'AXIS': {'victory_points': 167, 'players': [
                                                                             {'name': 'The Grinch', 'score': 828}, 
                                                                             {'name': 'Danielo1375', 'score': 220}, 
                                                                             {'name': 'Nick', 'score': 164}, 
                                                                             {'name': 'Mawcin_ka', 'score': 49}]}}, 'winner': 'ALLIES'}
       """""
    # This function parses the image and returns a dictionary with the game results
    # Example output:
    """ === GAME RESULTS ===

        ALLIES (169 VP)
        ----------------------------------------
        Starly          Score: 1435
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
    
    #data = parse_game_score(image_path)

    """""
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
    """""
   

if __name__ == "__main__":
    main()
