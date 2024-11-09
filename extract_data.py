import math 
import base64
import json
from PIL import Image 
from anthropic import Anthropic
from llm_config import API_KEYS
from Elo_calculation import calculatePoints
from io import BytesIO
from collections import Counter
from difflib import SequenceMatcher  # For fuzzy string matching
from robz_elo_system import print_game_results
from robz_elo_system import NUM_ATTEMPTS

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

    Names that are similar (similarity ratio above the threshold) are placed in the same group.

    **Parameters:**
    - `names` (list of str): A list of names to group.
    - `threshold` (float): The similarity threshold between 0 and 1. Default is 0.8.

    **Returns:**
    - A list of groups, where each group is a list of similar names.

    **Example:**

    ```python
    names = ["John", "Jon", "Johnny", "Jane", "Janet"]
    groups = group_similar_names(names)
    print(groups)
    # Output: [['John', 'Jon', 'Johnny'], ['Jane', 'Janet']]
    ```
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
    Combines multiple parsed data dictionaries into a single consensus dictionary.

    This function goes through each piece of data (like the winner, team names, player names, and scores)
    and selects the most frequently occurring value among all the parsed data.

    **Parameters:**
    - `parsed_data_list` (list of dict): A list of dictionaries containing parsed game data.

    **Returns:**
    - A single dictionary representing the consensus of the input data.

    **How It Works:**
    - Collects all team names and uses them to organize the consensus.
    - For each team, it computes the consensus victory points and player information.
    - Uses `get_majority_value` to find the most common value.
    - Uses `group_similar_names` to group and consensus player names.

    **Example:**

    ```python
    parsed_data_list = [
        {
            'winner': 'Team A',
            'teams': {
                'Team A': {
                    'victory_points': 10,
                    'players': [{'name': 'Alice', 'score': 100}]
                },
                'Team B': {
                    'victory_points': 8,
                    'players': [{'name': 'Bob', 'score': 90}]
                }
            }
        },
        {
            'winner': 'Team A',
            'teams': {
                'Team A': {
                    'victory_points': 10,
                    'players': [{'name': 'Alicia', 'score': 100}]
                },
                'Team B': {
                    'victory_points': 8,
                    'players': [{'name': 'Robert', 'score': 90}]
                }
            }
        },
    ]

    consensus = compute_consensus(parsed_data_list)
    print(consensus)
    # Output:
    # {
    #   'winner': 'Team A',
    #   'teams': {
    #     'Team A': {
    #       'victory_points': 10,
    #       'players': [{'name': 'Alice', 'score': 100}]
    #     },
    #     'Team B': {
    #       'victory_points': 8,
    #       'players': [{'name': 'Bob', 'score': 90}]
    #     }
    #   }
    # }
    ```
    """
    consensus_data = {}

    # Collect all team names from parsed data
    team_names = set()
    for pd in parsed_data_list:
        if 'teams' in pd:
            team_names.update(pd['teams'].keys())

    # Consensus for 'winner'
    winner_values = [pd.get('winner') for pd in parsed_data_list if pd.get('winner') is not None]
    consensus_data['winner'] = get_majority_value(winner_values)

    consensus_data['teams'] = {}

    for team_name in team_names:
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

        consensus_data['teams'][team_name]['players'] = consensus_players

    return consensus_data

def parse_game_score(image_path, num_attempts=NUM_ATTEMPTS):
    """
    Parses a game score image using the Claude API and returns structured data.

    This function reads an image of a game score sheet, processes it, and sends it to the Claude API for parsing.
    It attempts to extract team names, player names, scores, and victory points.

    **Parameters:**
    - `image_path` (str): The file path to the game score image.
    - `num_attempts` (int): Number of times to send the image to Claude for consensus (default is `NUM_ATTEMPTS`).

    **Returns:**
    - A dictionary containing the consensus data extracted from the image. Includes team information and winner.

    **How It Works:**
    - Determines the media type based on the image file extension.
    - Reads and processes the image (resizing or cropping) to meet size constraints.
    - Encodes the image in base64 format.
    - Sends the image and a prompt to the Claude API.
    - Parses the JSON response and collects data from multiple attempts.
    - Computes consensus data using `compute_consensus`.

    **Example:**

    ```python
    result = parse_game_score('game_scores/score_sheet.jpg')
    if result:
        print("Parsed Data:")
        print(result)
    else:
        print("Failed to parse the game score.")
    ```
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

    1. **Extract the data from the image**, ensuring high accuracy in team names, player names, and scores.
       Implement fuzzy matching for team names and player names that may have up to one character difference
       (e.g., one letter off). Correct or account for such minor discrepancies.

    2. **Team Names**: The team names can be any of the following factions, generic names like "Team A" or "Team B", or any combination thereof.

       **Factions List**:
       - U.S. Army
       - Wehrmacht  
       - Red Army
       - Commonwealth
       - Imperial Japan
       - Kampfgruppe Ost
       - Waffen-SS
       - Guards Army

    3. **Data to Extract**:
       - For **each team**:
         - The **team's name**
         - **List of player names** under the 'Player' column (excluding entries that match the team name)
         - Team's total **victory points** from the 'Victory P.' column
         - Each player's individual **score** from the 'Score' column
         - Note: Team total scores should not be included as player scores or tracked as a player

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

    **Instructions:**
    - Provide only the JSON output and no additional text
    - Think step by step, analyze every part of the image carefully before providing the final JSON output
    - Do not include team total scores as individual player scores
    - Do not include entries where player name matches team name
    """

    parsed_data_list = []

    for attempt in range(num_attempts):
        try:
            print(f"\n{'='*50}")
            print(f"Attempt {attempt + 1}")
            print(f"{'='*50}")
            
            print(f'Parsing game score from: {image_path}')

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