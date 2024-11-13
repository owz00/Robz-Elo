import math 
import base64
import json
import cv2
import numpy as np
import os

from PIL import Image 
from anthropic import Anthropic
from io import BytesIO
from collections import Counter
from difflib import SequenceMatcher 
from loguru import logger

from configs.llm_config import API_KEYS
from modules.elo_calculation import calculatePoints
from modules.utils import print_game_results


def order_data(data, eloDatabase):
    """
    Organizes player data from game results and Elo database.

    This function processes the input game data and matches each player with their corresponding
    Elo rating and games played from the Elo database. If a player is not found in the database,
    default values are used.

    **Parameters:**
    - `data` (dict): Game result data containing teams and players.
    - `eloDatabase` (dict): Database containing player Elo ratings and games played.

    **Returns:**
    - A dictionary with team names as keys. Each team contains:
      - `players`: A list of players with their name, starting Elo, and games played.
      - `Points`: The team's victory points.
      - `winProbability`: Placeholder for win probability calculation.

    **Example:**

    ```python
    data = {
        'teams': {
            'Team A': {
                'players': [{'name': 'Alice'}, {'name': 'Bob'}],
                'victory_points': 10
            }
        }
    }
    eloDatabase = {
        'Players': [
            {'PlayerName': 'Alice', 'Starting Elo': 1300, 'games played': 5},
            {'PlayerName': 'Bob', 'Starting Elo': 1250, 'games played': 3}
        ]
    }
    result = order_data(data, eloDatabase)
    print(result)
    # Output:
    # {
    #     'Team A': {
    #         'players': [
    #             ['Alice', 1300, 5],
    #             ['Bob', 1250, 3]
    #         ],
    #         'Points': 10,
    #         'winProbability': None
    #     }
    # }
    ```

    """
#for every player check to see if any other player in the database has the player name as a past name
#then if it does, set the player name the current name of the player whivh they are a past name of
#for playerName in playerNames:
  #for  player in eloDatabase:
        




    playerDictionary = {}

    for team_name, team_info in data['teams'].items():
        team_players = []

        for player in team_info['players']:
            current_player_name = find_name(player['name'], eloDatabase)
            if current_player_name:
                player_name = current_player_name
            else:    
                player_name = player['name']


            player_data = next((p for p in eloDatabase["Players"] if p["PlayerName"] == player_name), None)
            
            if player_data:
                starting_elo = player_data.get("Starting Elo", 1200)
                games_played = player_data.get("games played", 0)
            else:
                starting_elo = 1200
                games_played = 0

            team_players.append([
                player_name,
                starting_elo,
                games_played
            ])

        playerDictionary[team_name] = {
            'players': team_players,
            'Points': team_info['victory_points'],
            'winProbability': None
        }

    return playerDictionary


def find_name(incoming_name, eloDatabase):
    """
    returns the name of the player that has the incoming_name in their past names array
    """
    returned_names = []
    # Iterate through all players in the eloDatabase
    for player in eloDatabase['Players']:
        # Check if the incoming name is not already a player name
        if incoming_name in player['PlayerName']:
            return None
        # Check if the incoming name matches any name in the PastNames list
        if incoming_name in player['past names']:
            returned_names.append(player['PlayerName'])  # Return the current PlayerName if a match is found
            
    if len(returned_names) > 1:
        print(f"'multiple players have '{incoming_name}' in their past names list'")
        return None
    else:
        print(f"'{incoming_name}' changed to '{returned_names[0]}'")
        return returned_names[0]

    return None  # Return None if no match is found


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

    **Parameters:**
    - `names` (list of str): A list of names to be grouped.
    - `threshold` (float): A similarity threshold between 0 and 1. Names with a similarity ratio above this threshold are grouped together.

    **Returns:**
    - A list of lists, where each sublist contains names that are considered similar.

    **Example:**

    ```python
    names = ['Team Alpha', 'team alpha', 'Team Beta', 'TEAM BETA', 'Allies', 'Axis']
    result = group_similar_names(names, threshold=0.8)
    print(result)  # Output: [['Team Alpha', 'team alpha'], ['Team Beta', 'TEAM BETA'], ['Allies'], ['Axis']]
    ```
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
    Combines multiple parsed game data dictionaries into a single consensus dictionary, handling similar team names.

    This function processes multiple parsing attempts of game result data to create a consensus result.
    It groups similar team names, resolves discrepancies in victory points and player information,
    and outputs a unified game result. This helps in mitigating errors from individual parsing attempts,
    especially when data may have minor inconsistencies.

    **Parameters:**
    - `parsed_data_list` (list of dict): A list of dictionaries containing parsed game data from multiple attempts.

    **Returns:**
    - `consensus_data` (dict): A dictionary with consolidated game results, including consensus team names, victory points, players, and winner.

    **Example:**

    ```python
    parsed_data_list = [
        {
            "teams": {
                "Team Alpha": {
                    "victory_points": 15,
                    "players": [
                        {"name": "Alice", "score": 2000},
                        {"name": "Bob", "score": 1800}
                    ]
                },
                "Team Beta": {
                    "victory_points": 10,
                    "players": [
                        {"name": "Charlie", "score": 1900},
                        {"name": "David", "score": 1700}
                    ]
                }
            },
            "winner": "Team Alpha"
        },
        {
            "teams": {
                "Team Alfa": {  # Slight variation in team name
                    "victory_points": 15,
                    "players": [
                        {"name": "Alyce", "score": 2000},  # Slight variation in player name
                        {"name": "Bob", "score": 1800}
                    ]
                },
                "Team Beta": {
                    "victory_points": 12,  # Different victory points
                    "players": [
                        {"name": "Charlie", "score": 1900},
                        {"name": "Dave", "score": 1700}  # Slight variation in player name
                    ]
                }
            },
            "winner": "Team Alfa"
        },
        {
            "teams": {
                "Team Alpha": {
                    "victory_points": 15,
                    "players": [
                        {"name": "Alice", "score": 2000},
                        {"name": "Robert", "score": 1800}  # Slight variation in player name
                    ]
                },
                "Team Beta": {
                    "victory_points": 10,
                    "players": [
                        {"name": "Charlie", "score": 1900},
                        {"name": "David", "score": 1700}
                    ]
                }
            },
            "winner": "Team Alpha"
        }
    ]

    consensus_data = compute_consensus(parsed_data_list)
    print(json.dumps(consensus_data, indent=2))

    # Output:
    # {
    #   "winner": "Team Alpha",
    #   "teams": {
    #     "Team Alpha": {
    #       "victory_points": 15,
    #       "players": [
    #         {"name": "Alice", "score": 2000},
    #         {"name": "Bob", "score": 1800}
    #       ]
    #     },
    #     "Team Beta": {
    #       "victory_points": 10,
    #       "players": [
    #         {"name": "Charlie", "score": 1900},
    #         {"name": "David", "score": 1700}
    #       ]
    #     }
    #   }
    # }

    ```

    In this example, the function consolidates data from three parsing attempts:

    - **Team Names**: It recognizes that "Team Alpha" and "Team Alfa" are the same team by grouping similar names.
    - **Victory Points**: Resolves discrepancies in victory points for "Team Beta" by selecting the most frequent value (10).
    - **Player Names**: Handles slight variations in player names like "Alice" vs. "Alyce" and "David" vs. "Dave", choosing the most common names.
    - **Winner**: Determines the consensus winner as "Team Alpha" based on the majority of attempts.

    This consensus helps ensure accurate game results despite minor inconsistencies in individual parsing attempts.

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
        logger.warning("Could not detect scoreboard, using original image")
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
        logger.error("Error: Unable to process image for scoreboard detection.")
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
            logger.info(f"{'='*50}")
            logger.info(f"Attempt {attempt + 1}")
            logger.info(f"{'='*50}")

            logger.info('Parsing game score from the cropped scoreboard image.')

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

            logger.debug(f"Parsed Claude data (attempt {attempt+1}): {parsed_data}")
            parsed_data_list.append({
                'attempt': attempt + 1,
                'parsed_data': parsed_data,
                'error': None
            })

        except Exception as e:
            error_message = str(e)
            logger.error(f"Error parsing game score on attempt {attempt+1}: {error_message}")
            parsed_data_list.append({
                'attempt': attempt + 1,
                'parsed_data': None,
                'error': error_message
            })
            continue

    if not parsed_data_list:
        logger.error("No valid parsed data obtained.")
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

    This function provides an interactive prompt for the user to make corrections to the game results.
    The user can choose to edit team victory points, player details, change the winner, or add/remove players.
    The function also allows the user to skip the editing prompt for future sessions.

    **Parameters:**
    - `game_result_dictionary` (dict): The dictionary containing game results, including teams and players.
    - `skip_edit_prompt` (bool): Flag indicating whether to skip the editing prompt.

    **Returns:**
    - `game_result_dictionary` (dict): The possibly modified game result dictionary.
    - `user_corrections` (dict): A dictionary containing information about the edits made by the user.
    - `skip_edit_prompt` (bool): Updated flag indicating whether to skip the editing prompt in future sessions.

    **Example:**

    ```python
    game_result_dictionary = {
        'teams': {
            'Team A': {
                'players': [{'name': 'Alice', 'score': 10}, {'name': 'Bob', 'score': 15}],
                'victory_points': 26
            },
            'Team B': {
                'players': [{'name': 'Charlie', 'score': 20}, {'name': 'David', 'score': 5}],
                'victory_points': 25
            }
        },
        'winner': 'Team A'
    }
    skip_edit_prompt = False

    updated_game_result_dictionary, user_corrections, skip_edit_prompt = implement_user_corrections(game_result_dictionary, skip_edit_prompt)
    ```

    In this example, the user is prompted to make corrections to the game results. The function returns the updated game result dictionary, a dictionary of user corrections, and the updated skip edit prompt flag.
    """
    user_corrections = {
        "edited": False,
        "edits": []
    }

    # Check if the user has chosen to skip the editing prompt
    if skip_edit_prompt:
        logger.info("Skipping edit prompt as per user preference.")
        return game_result_dictionary, user_corrections, skip_edit_prompt

    team_names = list(game_result_dictionary['teams'].keys())

    while True:
        edit = input("Would you like to edit these results? (y/n), or type 'never' to never be asked again: ").lower()
        if edit == 'never':
            # Update the skip_edit_prompt variable to skip prompt in the future
            skip_edit_prompt = True
            logger.info("You will no longer be prompted to edit results during this session.")
            break
        elif edit != 'y':
            break

        user_corrections['edited'] = True

        logger.info("Editing options:")
        logger.info("1. Edit team victory points")
        logger.info("2. Edit player details")
        logger.info("3. Change winner")
        logger.info("4. Add or remove player")
        logger.info("5. Exit editing")

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
                    logger.error("Invalid input. Victory points must be a number.")

        elif choice == '2':
            team_name = input(f"Enter team to edit {team_names}: ").strip()
            if team_name not in team_names:
                logger.error("Invalid team name.")
                continue

            logger.info("Current players:")
            for i, player in enumerate(game_result_dictionary['teams'][team_name]['players']):
                logger.info(f"{i+1}. {player['name']} - Score: {player['score']}")

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
                            logger.error("Invalid score. Must be a number.")
                else:
                    logger.error("Invalid player number.")
            except ValueError:
                logger.error("Invalid input. Please enter a number.")

        elif choice == '3':
            old_winner = game_result_dictionary['winner']
            new_winner = input(f"Enter new winner {team_names}: ").strip()
            if new_winner in team_names:
                game_result_dictionary['winner'] = new_winner
                user_corrections['edits'].append({
                    "field": "winner",
                    "old_value": old_winner,
                    "new_value": new_winner
                })
            else:
                logger.error("Invalid team name.")

        elif choice == '4':
            team_name = input(f"Enter team to modify {team_names}: ").strip()
            if team_name not in team_names:
                logger.error("Invalid team name.")
                continue

            action = input("Would you like to add or remove a player? (add/remove): ").lower()
            if action == 'add':
                new_name = input("Enter new player's name: ")
                try:
                    new_score = int(input("Enter new player's score: "))
                except ValueError:
                    logger.error("Invalid score. Must be a number.")
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
                logger.info("Current players:")
                for i, player in enumerate(game_result_dictionary['teams'][team_name]['players']):
                    logger.info(f"{i+1}. {player['name']} - Score: {player['score']}")
                try:
                    player_num = int(input("Enter player number to remove: ")) - 1
                    if 0 <= player_num < len(game_result_dictionary['teams'][team_name]['players']):
                        removed_player = game_result_dictionary['teams'][team_name]['players'].pop(player_num)
                        user_corrections['edits'].append({
                            "field": f"teams.{team_name}.players",
                            "action": "remove",
                            "player": removed_player
                        })
                        logger.info(f"Removed player: {removed_player['name']}")
                    else:
                        logger.error("Invalid player number.")
                except ValueError:
                    logger.error("Invalid input. Please enter a number.")
            else:
                logger.error("Invalid action. Please choose 'add' or 'remove'.")

        elif choice == '5':
            break
        else:
            logger.error("Invalid choice.")

        # Re-print game results after each edit
        print_game_results(game_result_dictionary)

    return game_result_dictionary, user_corrections, skip_edit_prompt