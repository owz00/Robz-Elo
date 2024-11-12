import pandas as pd
import json
import os
import json
from datetime import datetime  # Added import




def prepareData(updatedDictionary, eloDatabase):
    """
    Updates the eloDatabase dictionary with the new Elo ratings and game counts
    from the updatedDictionary.
    """
    # After processing the data, the Elo database is updated
    for team_name in updatedDictionary.keys():
        
        players = updatedDictionary[team_name]['players']
        for player in players:
            playerName = player[0]
            newPlayerElo = player[4]
            gamesPlayed = player[2] + 1  # Increment games played 

            if eloDatabase != []:
                # Check if the player exists in the eloDatabase
                player_data = next((p for p in eloDatabase["Players"] if p["PlayerName"] == playerName), None)

                if player_data:
                    # Update Elo and games played for existing player
                    player_data['Starting Elo'] = newPlayerElo
                    player_data['games played'] = gamesPlayed

                    # Append new Elo to Elo History
                    player_data['Elo History'].append(newPlayerElo)
            
                else:
                    # Add new player to the database
                    new_player_data = {
                        'PlayerName': playerName,
                        'Starting Elo': newPlayerElo,
                        'games played': gamesPlayed,
                        'past names': "null",  # Or handle if you need specific logic for past names
                        'Elo History': [newPlayerElo]  # Initialize Elo History with the first Elo value
                    }
                    eloDatabase["Players"].append(new_player_data)
                    print(f"Added new player to database: {playerName}")
            else:
                new_player_data = {
                    'PlayerName': playerName,
                    'Starting Elo': newPlayerElo,
                    'games played': gamesPlayed,
                    'past names': "null",  # Or handle if you need specific logic for past names
                    'Elo History': [newPlayerElo]  # Initialize Elo History with the first Elo value
                    }
                eloDatabase["Players"].append(new_player_data)
                print(f"Added new player to databaseee: {playerName}")


    # Save updated database to JSON file
    with open("players_data.json", "w") as file:
        json.dump(eloDatabase, file, indent=4)

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



