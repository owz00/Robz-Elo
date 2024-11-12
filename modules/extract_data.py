import math 
import base64
import json
import cv2
import numpy as np

from PIL import Image 
from anthropic import Anthropic
from io import BytesIO
from collections import Counter
from difflib import SequenceMatcher  
import os

from configs.llm_config import API_KEYS
from modules.elo_calculation import calculatePoints
from modules.utils import print_game_results

def order_data(data, eloDatabase):
    playerDictionary = {}

    for team_name, team_info in data['teams'].items():
        team_players = []
        for player in team_info['players']:
            player_name = player['name']
            if player_name in eloDatabase['PlayerName'].values:
                playerIndex = eloDatabase.index[eloDatabase['PlayerName'] == player_name][0]
                starting_elo = eloDatabase.at[playerIndex, 'Starting Elo']
                games_played = eloDatabase.at[playerIndex, 'games played']
                team_players.append([
                    player_name,
                    starting_elo,
                    games_played
                ])
            else:
                team_players.append([player_name, 1200, 0])  # Default Elo and games played

        playerDictionary[team_name] = {
            'players': team_players,
            'Points': data['teams'][team_name]['victory_points'],
            'winProbability': None  # Will be calculated later
        }

    return playerDictionary

def get_majority_value(values):
    """
    Returns the value that appears most frequently in the list.

    If there is a tie (multiple values with the same highest frequency), it returns one of them.

    **Parameters:**
    - `values` (list): A list of values (can be of any type that is hashable).

    **Returns:**
    - The most frequent value in the list. If the list is empty, returns `None`.

    **Example:**

    ```python
    values = [1, 2, 2, 3, 3, 3]
    result = get_majority_value(values)
    print(result)  # Output: 3

    values = ['apple', 'banana', 'apple', 'orange']
    result = get_majority_value(values)
    print(result)  # Output: 'apple'

    values = []
    result = get_majority_value(values)
    print(result)  # Output: None
    ```
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
    Groups similar names together based on a similarity threshold.
    """
    groups = []
    generic_team_names = {'TEAM A', 'TEAM B', 'ALLIES', 'AXIS'}  # Keep these names separate

    for name in names:
        name_upper = name.upper()
        # Check if name matches exactly any generic team name
        if name_upper in generic_team_names:
            groups.append([name])  # Treat as their own group
            continue

        found_group = False
        for group in groups:
            group_name_upper = group[0].upper()
            # Skip comparison with generic team names
            if group_name_upper in generic_team_names:
                continue
            if any(similar(name_upper, member.upper()) >= threshold for member in group):
                group.append(name)
                found_group = True
                break
        if not found_group:
            groups.append([name])
    return groups

def compute_consensus(parsed_data_list):
    """
    Combines multiple parsed data dictionaries into a single consensus dictionary,
    handling similar team names.
    """
    consensus_data = {}

    # Collect all team names from parsed data
    all_team_names = []
    for pd in parsed_data_list:
        if 'teams' in pd:
            all_team_names.extend(pd['teams'].keys())

    # Group similar team names
    grouped_team_names = group_similar_names(all_team_names, threshold=0.8)

    # Create a mapping from original team names to consensus names
    consensus_team_names = {}
    for group in grouped_team_names:
        # Choose the most common team name in the group as the consensus name
        consensus_name = get_majority_value(group)
        for name in group:
            consensus_team_names[name] = consensus_name

    # Update parsed data with consensus team names
    updated_parsed_data_list = []
    for pd in parsed_data_list:
        updated_pd = pd.copy()
        if 'teams' in pd:
            updated_teams = {}
            for team_name, team_data in pd['teams'].items():
                consensus_name = consensus_team_names.get(team_name, team_name)
                updated_teams[consensus_name] = team_data
            updated_pd['teams'] = updated_teams
        updated_parsed_data_list.append(updated_pd)

    # Consensus for 'winner'
    winner_values = [
        consensus_team_names.get(pd.get('winner'), pd.get('winner'))
        for pd in parsed_data_list if pd.get('winner') is not None
    ]
    consensus_data['winner'] = get_majority_value(winner_values)

    consensus_data['teams'] = {}

    # Collect unique consensus team names while preserving order
    seen_team_names = set()
    team_names = []
    for pd in updated_parsed_data_list:
        for team_name in pd.get('teams', {}).keys():
            if team_name not in seen_team_names:
                seen_team_names.add(team_name)
                team_names.append(team_name)

    for team_name in team_names:
        # Collect all team data for this team
        team_data_list = [
            pd['teams'][team_name] for pd in updated_parsed_data_list
            if 'teams' in pd and team_name in pd['teams']
        ]

        if not team_data_list:
            continue  # Skip if no data for this team

        # Consensus for 'victory_points'
        victory_points_values = [
            team_data.get('victory_points') for team_data in team_data_list
            if team_data.get('victory_points') is not None
        ]
        consensus_victory_points = get_majority_value(victory_points_values)

        # Consensus for 'players'
        max_players = max(len(team_data.get('players', [])) for team_data in team_data_list)
        consensus_players = []

        for position in range(max_players):
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
            if names_at_position:
                grouped_names = group_similar_names(names_at_position)
                largest_group = max(grouped_names, key=lambda g: len(g))
                consensus_name = get_majority_value(largest_group)
            else:
                consensus_name = None
            consensus_score = get_majority_value(scores_at_position) if scores_at_position else None
            consensus_players.append({'name': consensus_name, 'score': consensus_score})

        consensus_data['teams'][team_name] = {
            'victory_points': consensus_victory_points,
            'players': consensus_players
        }

    return consensus_data

def detect_scoreboard(image_path, save_cropped=True, cropped_folder="cropped_scoreboards"):
    """
    Detects, crops, and upscales the scoreboard from a game screenshot.

    This function processes an image to identify and extract the scoreboard area, 
    enhances its sharpness, and optionally saves the cropped image.

    **Parameters:**
    - `image_path` (str): The file path to the game screenshot.
    - `save_cropped` (bool): Whether to save the cropped scoreboard image.
    - `cropped_folder` (str): Directory to save the cropped images.

    **Returns:**
    - A PIL Image object of the upscaled and sharpened scoreboard.
    """
    # Read image using OpenCV
    img = cv2.imread(image_path)
    original_height, original_width = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Apply threshold to get black and white image
    _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Find the largest rectangular contour (likely to be the scoreboard)
    max_area = 0
    scoreboard_rect = None
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        aspect_ratio = float(w)/h
        
        # Filter based on area and aspect ratio
        if area > max_area and 1.2 < aspect_ratio < 2.5 and area > (original_height * original_width * 0.1):
            max_area = area
            scoreboard_rect = (x, y, w, h)
    
    if scoreboard_rect is None:
        print("Could not detect scoreboard, using original image")
        cropped = img
    else:
        # Crop the scoreboard without padding
        x, y, w, h = scoreboard_rect
        cropped = img[y:y+h, x:x+w]
    
    # Upscale the image using high-quality interpolation
    upscale_factor = 2  # Adjust this factor to control the upscaling
    new_width = cropped.shape[1] * upscale_factor
    new_height = cropped.shape[0] * upscale_factor
    upscaled = cv2.resize(cropped, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
    
    # Apply a sharpening filter
    sharpening_kernel = np.array([[0, -1, 0],
                                  [-1, 5,-1],
                                  [0, -1, 0]])
    sharpened = cv2.filter2D(upscaled, -1, sharpening_kernel)
    
    # Convert back to PIL Image
    pil_image = Image.fromarray(cv2.cvtColor(sharpened, cv2.COLOR_BGR2RGB))
    
    # Save cropped image if requested
    if save_cropped:
        if not os.path.exists(cropped_folder):
            os.makedirs(cropped_folder)
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        save_path = os.path.join(cropped_folder, f"{base_name}_upscaled.png")
        pil_image.save(save_path, format='PNG')
    
    return pil_image



def parse_game_score(image_path, num_attempts=1):
    """
    Parses a game score image using the Claude API and returns structured data.

    This function reads an image of a game score sheet, crops the scoreboard area, and sends it to the Claude API for parsing.
    It attempts to extract team names, player names, scores, and victory points.

    **Parameters:**
    - `image_path` (str): The file path to the game score image.
    - `num_attempts` (int): Number of times to send the image to Claude for consensus.

    **Returns:**
    - A dictionary containing the consensus data extracted from the image, including team information and winner.

    **How It Works:**
    - Detects and crops the scoreboard from the image.
    - Encodes the cropped image in base64 format.
    - Sends the image and a prompt to the Claude API for parsing.
    - Collects the parsed data from multiple attempts.
    - Computes consensus data using `compute_consensus`.
    - Includes all attempt data in the final consensus data for analysis.
    """
    # Detect and crop the scoreboard from the image
    cropped_image = detect_scoreboard(image_path)
    if cropped_image is None:
        print("Error: Unable to process image for scoreboard detection.")
        return None

    # Determine media type based on the image format (we'll use PNG for the cropped image)
    media_type = "image/png"

    client = Anthropic(api_key=API_KEYS['claude'])

    # Prepare the prompt with role assignment and instructions
    prompt = """
    You are a data extraction assistant with perfect vision and excellent attention to detail.
    Your task is to parse the provided game score sheet image and extract the information into
    a structured JSON format. Please follow these instructions carefully:

    1. **Extract the data from the image**, ensuring high accuracy in team names, player names, and scores.
       Implement fuzzy matching for team names and player names that may have up to one character difference
       (e.g., one letter off). Correct or account for such minor discrepancies.

    2. **Team Names**: The team names can be any of the following factions, generic names like "Team A" or "Team B", or any combination thereof.
       There must be exactly 2 teams per game.

       **Factions List**:
       - Team A
       - Team B
       - ALLIES
       - AXIS
       - USA
       - Wehrmacht
       - Soviet army
       - Commonwealth
       - Imperial Japan
       - Kampfgruppe Ost
       - Waffen-SS
       - Guards Army

    3. **Data to Extract**:
       - For **each of the 2 teams**:
         - The **team's name**
         - **List of player names** under the 'Player' column (excluding entries that match the team name)
         - Team's total **victory points** from the 'Victory P.' column
         - Each player's individual **score** from the 'Score' column
         - IMPORTANT: Team total scores should NOT be included as player scores. The team total score appears at the top of each team's section and should be ignored when extracting player scores.

    4. **Organize the data into the following JSON structure**:

    {
      "teams": {
        "<team_name_1>": {
          "victory_points": <integer>,
          "players": [
            {
              "name": "<player_name>",
              "score": <integer>
            },
            ...
          ]
        },
        "<team_name_2>": {
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
      "winner": "<team_name of the team with higher victory_points, or 'TIE' if they are equal>"
    }

    5. Ensure all numeric values are integers.

    6. If any data is missing or cannot be read, indicate it with a null value in the JSON.

    **Critical Instructions:**
    - Provide only the JSON output and no additional text
    - Think step by step, analyze every part of the image carefully before providing the final JSON output
    - Do not include team total scores as individual player scores - these appear at the top of each team's section
    - Do not include entries where player name matches team name
    - Do not include any additional keys or metadata beyond the specified JSON structure
    - Double check that player scores are individual scores from the Score column, not team totals
    - There must be exactly 2 teams in the output - no more, no less
    """

    parsed_data_list = []

    for attempt in range(num_attempts):
        try:
            print(f"\n{'='*50}")
            print(f"Attempt {attempt + 1}")
            print(f"{'='*50}")

            print('Parsing game score from the cropped scoreboard image.')

            # Convert the cropped image to bytes and encode in base64
            buffered = BytesIO()
            cropped_image.save(buffered, format='PNG')
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
            parsed_text = message.content[0].text.strip()
            parsed_data = json.loads(parsed_text)

            # Remove any 'attempts_data' key to prevent duplication
            if 'attempts_data' in parsed_data:
                del parsed_data['attempts_data']

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

    return consensus_data

def implement_user_corrections(game_result_dictionary, skip_edit_prompt):
    """
    Allows the user to implement corrections to the game dictionary.
    Returns the possibly modified game_result_dictionary, user_corrections dictionary,
    and updated skip_edit_prompt flag.
    """
    user_corrections = {
        "edited": False,
        "edits": []
    }

    # Check if the user has chosen to skip the editing prompt
    if skip_edit_prompt:
        print("Skipping edit prompt as per user preference.")
        return game_result_dictionary, user_corrections, skip_edit_prompt

    team_names = list(game_result_dictionary['teams'].keys())

    while True:
        edit = input("Would you like to edit these results? (y/n), or type 'never' to never be asked again: ").lower()
        if edit == 'never':
            # Update the skip_edit_prompt variable to skip prompt in the future
            skip_edit_prompt = True
            print("You will no longer be prompted to edit results during this session.")
            break
        elif edit != 'y':
            break

        user_corrections['edited'] = True

        print("\nEditing options:")
        print("1. Edit team victory points")
        print("2. Edit player details")
        print("3. Change winner")
        print("4. Add or remove player")
        print("5. Exit editing")

        choice = input("Enter your choice (1-5): ")

        if choice == '1':
            for team_name in team_names:
                old_vp = game_result_dictionary['teams'][team_name]['victory_points']
                try:
                    new_vp = int(input(f"Enter new victory points for {team_name} (current: {old_vp}): "))
                    game_result_dictionary['teams'][team_name]['victory_points'] = new_vp
                    user_corrections['edits'].append({
                        "field": f"teams.{team_name}.victory_points",
                        "old_value": old_vp,
                        "new_value": new_vp
                    })
                except ValueError:
                    print("Invalid input. Victory points must be a number.")

        elif choice == '2':
            team_name = input(f"Enter team to edit {team_names}: ").strip()
            if team_name not in team_names:
                print("Invalid team name.")
                continue

            print("\nCurrent players:")
            for i, player in enumerate(game_result_dictionary['teams'][team_name]['players']):
                print(f"{i+1}. {player['name']} - Score: {player['score']}")

            try:
                player_num = int(input("Enter player number to edit: ")) - 1
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
            new_winner = input(f"Enter new winner {team_names + ['TIE']}: ").strip()
            if new_winner in team_names or new_winner.upper() == 'TIE':
                game_result_dictionary['winner'] = new_winner
                user_corrections['edits'].append({
                    "field": "winner",
                    "old_value": old_winner,
                    "new_value": new_winner
                })
            else:
                print("Invalid team name.")

        elif choice == '4':
            team_name = input(f"Enter team to modify {team_names}: ").strip()
            if team_name not in team_names:
                print("Invalid team name.")
                continue

            action = input("Would you like to add or remove a player? (add/remove): ").lower()
            if action == 'add':
                new_name = input("Enter new player's name: ")
                try:
                    new_score = int(input("Enter new player's score: "))
                except ValueError:
                    print("Invalid score. Must be a number.")
                    continue

                game_result_dictionary['teams'][team_name]['players'].append({
                    'name': new_name,
                    'score': new_score
                })
                user_corrections['edits'].append({
                    "field": f"teams.{team_name}.players",
                    "action": "add",
                    "player": {'name': new_name, 'score': new_score}
                })

            elif action == 'remove':
                print("\nCurrent players:")
                for i, player in enumerate(game_result_dictionary['teams'][team_name]['players']):
                    print(f"{i+1}. {player['name']} - Score: {player['score']}")
                try:
                    player_num = int(input("Enter player number to remove: ")) - 1
                    if 0 <= player_num < len(game_result_dictionary['teams'][team_name]['players']):
                        removed_player = game_result_dictionary['teams'][team_name]['players'].pop(player_num)
                        user_corrections['edits'].append({
                            "field": f"teams.{team_name}.players",
                            "action": "remove",
                            "player": removed_player
                        })
                        print(f"Removed player: {removed_player['name']}")
                    else:
                        print("Invalid player number.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            else:
                print("Invalid action. Please choose 'add' or 'remove'.")

        elif choice == '5':
            break
        else:
            print("Invalid choice.")

        # Re-print game results after each edit
        print_game_results(game_result_dictionary)

    return game_result_dictionary, user_corrections, skip_edit_prompt