import pandas as pd
import json
import os
import json
from datetime import datetime  # Added import

#get the elo history, append anew value to array
def prepareData(updatedDictionary, eloDatabase):
    """
    Updates the eloDatabase DataFrame with the new Elo ratings and game counts
    from the updatedDictionary.
    """
    # After processing the data, the Elo database is updated
    for team_name in updatedDictionary.keys():
        
        players = updatedDictionary[team_name]['players']
        for player in players:
            playerName = player[0]
            newPlayerElo = player[4]
            gamesPlayed = player[2] + 1  # Increment games played 

            if playerName in eloDatabase['PlayerName'].values:
                playerIndex = eloDatabase.index[eloDatabase['PlayerName'] == playerName][0]
                eloDatabase.at[playerIndex, 'Starting Elo'] = newPlayerElo
                eloDatabase.at[playerIndex, 'games played'] = gamesPlayed

                 # Append new Elo to Elo History
                eloDatabase.at[playerIndex, 'Elo History'].append(newPlayerElo)
            
            else:
                # Add new player to the database
                new_player_data = pd.DataFrame({
                    'PlayerName': [playerName],
                    'Starting Elo': [newPlayerElo],
                    'games played': [gamesPlayed],
                    'past names': 'null',
                    'Elo History': [[newPlayerElo]]  # Initialize Elo History with the first Elo
                    
                })

                eloDatabase = pd.concat([eloDatabase, new_player_data], ignore_index=True)
                print(f"Added new player to database: {playerName}")

    """
    save to json
    """
    players_list = eloDatabase.to_dict(orient='records')
    final_structure = {"Players": players_list}
    with open("players_data.json", "w") as file:
        json.dump(final_structure, file, indent=4)

    return eloDatabase








def process_and_save_game_data(game_result_dictionary, user_corrections, image_file):
    """
    Processes the game data and saves it into a JSON file.
    """

    """""
    Save Games here
    """""
    # Prepare game entry data
    current_time = datetime.now()
    game_entry = {
        "game_id": current_time.isoformat(timespec='milliseconds'),
        "date": current_time.strftime('%Y-%m-%d'),
        "time": current_time.strftime('%H:%M:%S.%f')[:-3],  # up to milliseconds
        "image_file": os.path.basename(image_file),
        "consensus_data": game_result_dictionary,
        "user_corrections": user_corrections
    }

    # Load existing game data
    if os.path.exists('game_results.json'):
        try:
            with open('game_results.json', 'r') as file:
                game_results = json.load(file)
        except json.JSONDecodeError:
            print("Error: 'game_results.json' is corrupted. Overwriting file.")
            game_results = []
    else:
        game_results = []

    # Append new game entry
    game_results.append(game_entry)

    # Save updated game data
    try:
        with open('game_results.json', 'w') as file:
            json.dump(game_results, file, indent=2)
        print("Game results saved to 'game_results.json'.")
    except IOError as e:
        print(f"Failed to save game results: {e}")



