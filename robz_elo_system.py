# Robz Elo system

import math 
import pandas as pd
import os
import base64
import json
import sys
from anthropic import Anthropic
from config import API_KEYS
from io import BytesIO
from collections import Counter
from difflib import SequenceMatcher  # For fuzzy string matching
from datetime import datetime  # Added import

# Configuration variable
NUM_ATTEMPTS = 5  # Number of times to send the image to Claude for consensus

def get_majority_value(values):
    """
    Returns the value that appears most frequently in the list.
    If there is a tie, returns one of the most common values.
    """
    counter = Counter(values)
    if not counter:
        return None
    most_common = counter.most_common()
    max_count = most_common[0][1]
    # Get all values with the highest count
    top_values = [val for val, count in most_common if count == max_count]
    return top_values[0]  # Return one of the top values

def similar(a, b):
    """Return a similarity ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()

def group_similar_names(names, threshold=0.8):
    """
    Groups similar names based on a similarity threshold.
    Returns a list of groups, where each group is a list of names.
    """
    groups = []
    for name in names:
        found_group = False
        for group in groups:
            if any(similar(name, member) >= threshold for member in group):
                group.append(name)
                found_group = True
                break
        if not found_group:
            groups.append([name])
    return groups

def compute_consensus(parsed_data_list):
    """
    Computes the consensus of a list of parsed_data dictionaries.
    Applies consensus to every part of the final dictionary.
    Preserves the original ordering of players.
    """
    consensus_data = {}

    # Consensus for 'winner'
    # Collect all 'winner' values from parsed_data_list
    winner_values = [pd.get('winner') for pd in parsed_data_list if pd.get('winner') is not None]
    # Compute the majority value
    consensus_data['winner'] = get_majority_value(winner_values)

    # Consensus for 'teams'
    consensus_data['teams'] = {}

    for team_name in ['ALLIES', 'AXIS']:
        # Collect all team data for this team
        team_data_list = [
            pd['teams'][team_name] for pd in parsed_data_list
            if 'teams' in pd and team_name in pd['teams']
        ]

        # Consensus for 'victory_points'
        victory_points_values = [
            team_data.get('victory_points') for team_data in team_data_list
            if team_data.get('victory_points') is not None
        ]
        consensus_victory_points = get_majority_value(victory_points_values)

        consensus_data['teams'][team_name] = {'victory_points': consensus_victory_points}

        # Consensus for 'players'
        # We will process players per position to preserve ordering
        # First, determine the maximum number of players
        max_players = max(len(team_data.get('players', [])) for team_data in team_data_list)
        consensus_players = []

        for position in range(max_players):
            # Collect names and scores at this position from all attempts
            names_at_position = []
            scores_at_position = []
            for team_data in team_data_list:
                players = team_data.get('players', [])
                if len(players) > position:
                    player = players[position]
                    name = player.get('name')
                    score = player.get('score')
                    if name is not None:
                        names_at_position.append(name)
                    if score is not None:
                        scores_at_position.append(score)
            # Compute consensus name and score for this position
            if names_at_position:
                # Group similar names
                grouped_names = group_similar_names(names_at_position)
                # Choose the largest group
                largest_group = max(grouped_names, key=lambda g: len(g))
                consensus_name = get_majority_value(largest_group)
            else:
                consensus_name = None
            consensus_score = get_majority_value(scores_at_position) if scores_at_position else None
            consensus_players.append({'name': consensus_name, 'score': consensus_score})
        # Assign the consensus players to the team
        consensus_data['teams'][team_name]['players'] = consensus_players

    return consensus_data

def parse_game_score(image_path, num_attempts=NUM_ATTEMPTS):
    """
    Uses Claude API to parse game score images and return structured data.
    """
    # Determine media type based on file extension
    media_type = "image/jpeg"  # default
    if image_path.lower().endswith(".png"):
        media_type = "image/png"
    elif image_path.lower().endswith(".webp"):
        media_type = "image/webp"
    elif image_path.lower().endswith(".gif"):
        media_type = "image/gif"

    client = Anthropic(api_key=API_KEYS['claude'])

    # Prepare the prompt with role assignment and instructions
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

    parsed_data_list = []

    for attempt in range(num_attempts):
        try:
            print(f"\n{'='*50}")
            print(f"Attempt {attempt + 1}")
            print(f"{'='*50}")

            # Read the original image using PIL
            original_image = Image.open(image_path)
            width, height = original_image.size
            
            print(f"Original Image: {width}x{height}")
            
            # Calculate max possible dimensions while maintaining aspect ratio
            aspect_ratio = width / height
            
            # Try to maximize size within token and dimension limits
            # tokens = (w * h)/750 <= 1200
            # w <= 1200
            # h = w/aspect_ratio
            
            # From token formula: w * (w/aspect_ratio) <= 1200 * 750
            max_width_from_tokens = int(math.sqrt(1200 * 750 * aspect_ratio))
            max_width = min(1200, max_width_from_tokens)
            max_height = int(max_width / aspect_ratio)

            # Only resize if original dimensions are smaller than max allowed
            if width < max_width and height < max_height:
                print("\nOriginal Image:")
                print(f"- Dimensions: {width}x{height}")
                print(f"- Aspect ratio: {aspect_ratio:.2f}")
                print(f"- Current tokens: {(width * height)/750:.0f}")
                
                print("\nMax Possible:")
                print(f"- Dimensions: {max_width}x{max_height}")
                print(f"- Max tokens: {(max_width * max_height)/750:.0f}")
                
                # Decrease by 10% for each subsequent attempt
                reduction_factor = 0.9 ** attempt
                new_width = int(max_width * reduction_factor)
                new_height = int(new_width / aspect_ratio)
                
                print("\nResized Image:")
                print(f"- Dimensions: {new_width}x{new_height}")
                print(f"- Reduction factor: {reduction_factor:.2f}")
                
                resized_image = original_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                """ # Save with proper extension
                save_path = f"attempt{attempt+1}.{original_image.format.lower()}"
                resized_image.save(save_path)
                print(f"\nSaved resized image to: {save_path}") """
            else:
                print(f"Image is at max dimensions. Cropping by {attempt * 10}%")
                
                # Calculate crop dimensions
                crop_factor = 0.9 ** attempt  # Reduce by 10% each attempt
                crop_width = int(width * crop_factor)
                crop_height = int(height * crop_factor)
                
                # Calculate margins to center the crop
                left = (width - crop_width) // 2
                top = (height - crop_height) // 2
                right = left + crop_width
                bottom = top + crop_height
                
                # Crop the image
                resized_image = original_image.crop((left, top, right, bottom))
                
            # Determine the format and set save parameters
            save_kwargs = {}
            format_lower = original_image.format.lower()

            if format_lower == 'jpeg' or format_lower == 'jpg':
                save_kwargs.update({'quality': 100, 'optimize': True, 'progressive': True})
            elif format_lower == 'png':
                save_kwargs.update({'compress_level': 0})
            elif format_lower == 'webp':
                save_kwargs.update({'quality': 100, 'method': 6})

            # Convert the resized image to bytes and encode in base64
            buffered = BytesIO()
            resized_image.save(buffered, format=original_image.format, **save_kwargs)
            image_data = base64.b64encode(buffered.getvalue()).decode("utf-8")

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
            print(f"Parsed Claude data (attempt {attempt+1}): {parsed_data}")
            parsed_data_list.append({
                'attempt': attempt + 1,
                'parsed_data': parsed_data,
                'error': None
            })

        except Exception as e:
            error_message = str(e)
            print(f"Error parsing game score on attempt {attempt+1}: {error_message}")
            parsed_data_list.append({
                'attempt': attempt + 1,
                'parsed_data': None,
                'error': error_message
            })
            continue

    if not parsed_data_list:
        print("No valid parsed data obtained.")
        return None

    # Combine parsed data using consensus mechanism
    valid_parsed_data = [pd['parsed_data'] for pd in parsed_data_list if pd['parsed_data'] is not None]
    consensus_data = compute_consensus(valid_parsed_data)
    # Include all attempt data in consensus_data for later analysis
    consensus_data['attempts_data'] = parsed_data_list

    print(f"Consensus data: {consensus_data}")
    return consensus_data

def playerProbability(enemyElo, playerElo):
    rcf = 1000  # Random chance factor
    subtractElo = (enemyElo - playerElo) / rcf
    probability  =  round(1 / (1 + pow(10, subtractElo)), 4)
    return probability 

<<<<<<< HEAD

def gamePrediction(playerDictionary):

=======
def gamePrediction(playerElo):
>>>>>>> 2f247e12f875a5477f155f181a9863b91ced78b6
    personalProbability  = 0 
    overallProbability = 0
    finalProbability = 0

<<<<<<< HEAD
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
=======
    # Adds the elo to the correct team
    i = 0
    for players in playerElo:
        if players[0] == 'B':
            teamB.append((players[1], i))
        elif players[0] == 'A':
            teamA.append((players[1], i))
        else:
            print("Incorrect team in array")
        i += 1   

    teamBSize = len(teamB)
    teamASize = len(teamA)
    averageChanceofWinning = [0] * (teamBSize + teamASize)

    # Calculates the probability of each individual player vs each player of the other team
>>>>>>> 2f247e12f875a5477f155f181a9863b91ced78b6
    for playerA in teamA: 
        personalProbability = 0 
        i = 0
        for playerB in teamB:
<<<<<<< HEAD
           p = playerProbability(playerB[1] , playerA[1])
           personalProbability += p #this calculates for every A players
           opposingProbability = abs(1 - p)/teamBSize
           averageChanceofWinning[i] += opposingProbability
           i += 1
=======
            p = playerProbability(playerB[0] , playerA[0])
            personalProbability += p  # For each A player
            opposingProbability  = abs(1 - p)/teamBSize
            averageChanceofWinning[playerB[1]] += opposingProbability  # For each B player
>>>>>>> 2f247e12f875a5477f155f181a9863b91ced78b6

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

<<<<<<< HEAD
    return playerDictionary





#when i find their probability i put it in the right index
def calculatePoints(playerDictionary):
   
    teamAScore = playerDictionary['ATeam']['Points']
    teamBScore = playerDictionary['BTeam']['Points']
=======
def calculatePoints(playerDictionary):
    teamAScore = round(playerDictionary['TeamAPoints'][0])
    teamBScore  = round(playerDictionary['TeamBPoints'][0])
    playerElo = list(zip(playerDictionary['team'], playerDictionary['playerElo']))
    playerInformation = list(zip(playerDictionary['playerElo'], 
                                 playerDictionary['gamesPlayed'], 
                                 playerDictionary['team'],))
>>>>>>> 2f247e12f875a5477f155f181a9863b91ced78b6

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

<<<<<<< HEAD
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
=======
    # Calculates the score gained or lost for each player
    for player in playerInformation:
        k = 50 / (1 + (player[1]/300))
        if winner == 'B':
            if player[2] == 'B':
                newRating = player[0] + ((k*pointFactor) * (1 - RB))
            elif player[2] == 'A':
                newRating = player[0] + ((k*pointFactor) * (0 - RA))
            else:
                print('Team is not A or B')
        elif winner == 'A':
            if player[2] == 'B':
                newRating = player[0] + ((k*pointFactor) * (0 - RB))
            elif player[2] == 'A':
                newRating = player[0] + ((k*pointFactor) * (1 - RA))
            else:
                print('Team is not A or B')
        else:
            print('No winner provided')
        newPlayerElo.append(round(newRating))
    return newPlayerElo, RB, RA, RP

def main():
    image_path = 'test_images/test2.jpg'  # Update the image path as needed
>>>>>>> 2f247e12f875a5477f155f181a9863b91ced78b6
    if not os.path.exists(image_path):
        print(f"Error: Image file '{image_path}' does not exist")
        sys.exit(1)
    if len(API_KEYS['claude']) <= 10:
        print("Error: Invalid API key")
        sys.exit(1)

<<<<<<< HEAD



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
   
=======
    # Parse the game score image
    game_result_dictionary = parse_game_score(image_path)

    if game_result_dictionary:
        user_corrections = {
            "edited": False,
            "edits": []
        }

        while True:
            print("\n=== GAME RESULTS ===")
            for team_name in ['ALLIES', 'AXIS']:
                team = game_result_dictionary['teams'][team_name]
                print(f"\n{team_name} ({team['victory_points']} VP)")
                print("-" * 40)
                for player in team['players']:
                    print(f"{player['name']:<15} Score: {player['score']}")

            print(f"\nWINNER: {game_result_dictionary['winner']}")
            print("=" * 40 + "\n")

            edit = input("Would you like to edit these results? (y/n): ").lower()
            if edit != 'y':
                break

            user_corrections['edited'] = True

            print("\nEditing options:")
            print("1. Edit team victory points")
            print("2. Edit player details")
            print("3. Change winner")

            choice = input("Enter your choice (1-3): ")

            if choice == '1':
                for team_name in ['ALLIES', 'AXIS']:
                    old_vp = game_result_dictionary['teams'][team_name]['victory_points']
                    try:
                        new_vp = int(input(f"Enter new victory points for {team_name}: "))
                        game_result_dictionary['teams'][team_name]['victory_points'] = new_vp
                        user_corrections['edits'].append({
                            "field": f"teams.{team_name}.victory_points",
                            "old_value": old_vp,
                            "new_value": new_vp
                        })
                    except ValueError:
                        print("Invalid input. Victory points must be a number.")

            elif choice == '2':
                team_name = input("Enter team to edit (ALLIES/AXIS): ").upper()
                if team_name not in ['ALLIES', 'AXIS']:
                    print("Invalid team name.")
                    continue

                print("\nCurrent players:")
                for i, player in enumerate(game_result_dictionary['teams'][team_name]['players']):
                    print(f"{i+1}. {player['name']} - Score: {player['score']}")

                try:
                    player_num = int(input("Enter player number to edit (1-4): ")) - 1
                    if 0 <= player_num < len(game_result_dictionary['teams'][team_name]['players']):
                        player = game_result_dictionary['teams'][team_name]['players'][player_num]
                        old_name = player['name']
                        old_score = player['score']

                        new_name = input("Enter new name (or press enter to keep current): ")
                        new_score = input("Enter new score (or press enter to keep current): ")

                        if new_name:
                            player['name'] = new_name
                            user_corrections['edits'].append({
                                "field": f"teams.{team_name}.players[{player_num}].name",
                                "old_value": old_name,
                                "new_value": new_name
                            })
                        if new_score:
                            try:
                                player['score'] = int(new_score)
                                user_corrections['edits'].append({
                                    "field": f"teams.{team_name}.players[{player_num}].score",
                                    "old_value": old_score,
                                    "new_value": int(new_score)
                                })
                            except ValueError:
                                print("Invalid score. Must be a number.")
                    else:
                        print("Invalid player number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")

            elif choice == '3':
                old_winner = game_result_dictionary['winner']
                new_winner = input("Enter new winner (ALLIES/AXIS): ").upper()
                if new_winner in ['ALLIES', 'AXIS']:
                    game_result_dictionary['winner'] = new_winner
                    user_corrections['edits'].append({
                        "field": "winner",
                        "old_value": old_winner,
                        "new_value": new_winner
                    })
                else:
                    print("Invalid team name.")

            else:
                print("Invalid choice.")

        # Prepare game entry data
        current_time = datetime.now()
        game_entry = {
            "game_id": current_time.isoformat(timespec='milliseconds'),
            "date": current_time.strftime('%Y-%m-%d'),
            "time": current_time.strftime('%H:%M:%S.%f')[:-3],  # up to milliseconds
            "image_file": os.path.basename(image_path),
            "consensus_data": game_result_dictionary,
            "user_corrections": user_corrections
        }

        # Load existing game data
        if os.path.exists('game_results.json'):
            with open('game_results.json', 'r') as file:
                game_results = json.load(file)
        else:
            game_results = []

        # Append new game entry
        game_results.append(game_entry)

        # Save updated game data
        with open('game_results.json', 'w') as file:
            json.dump(game_results, file, indent=2)

        print("Game results saved to 'game_results.json'.")

        # Process results into CSV (existing code)
        df = pd.read_csv("RobzElo.csv")
        dictionary = df.to_dict('list')
        newPlayerElo, RB, RA, RP = calculatePoints(dictionary)
        dictionary['new Elo'] = newPlayerElo
        dictionary['TeamBPoints'][1] = RB
        dictionary['TeamAPoints'][1] = RA
        dictionary['RP'] = RP
        data_frame = pd.DataFrame(dictionary)
        data_frame.to_csv('newElo.csv', index=False)

    else:
        print("Failed to parse game results.")
        return
>>>>>>> 2f247e12f875a5477f155f181a9863b91ced78b6

if __name__ == "__main__":
    main()