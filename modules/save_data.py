import pandas as pd
import json
import os
import json
from datetime import datetime  
from loguru import logger
from configs.app_config import ELO_JSON_DATABASE_PATH, GAME_RESULTS_JSON_PATH

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
            newPlayerElo = player[6]
            gamesPlayed = player[2] + 1  # Increment games played 
            gamesWon = player[3]
            gamesLost = player[4]

            if eloDatabase != []:
                # Check if the player exists in the eloDatabase
                player_data = next((p for p in eloDatabase["Players"] if p["PlayerName"] == playerName), None)

                if player_data:
                    # Update Elo and games played for existing player
                    player_data['Starting Elo'] = newPlayerElo
                    player_data['games played'] = gamesPlayed
                    player_data['Games Won'] = gamesWon
                    player_data['Games Lost'] = gamesLost


                    # Append new Elo to Elo History
                    player_data['Elo History'].append(newPlayerElo)
            
                else:
                    # Add new player to the database
                    new_player_data = {
                        'PlayerName': playerName,
                        'Starting Elo': newPlayerElo,
                        'games played': gamesPlayed,
                        'past names': [],  # Or handle if you need specific logic for past names
                        'Elo History': [newPlayerElo],  # Initialize Elo History with the first Elo value
                        'Games Won':  gamesWon,  
                        'Games Lost': gamesLost
                    }
                    eloDatabase["Players"].append(new_player_data)
                    logger.info(f"Added new player to database: {playerName}")
            else:
                new_player_data = {
                    'PlayerName': playerName,
                    'Starting Elo': newPlayerElo,
                    'games played': gamesPlayed,
                    'past names': [],  # Or handle if you need specific logic for past names
                    'Elo History': [newPlayerElo],  # Initialize Elo History with the first Elo value
                    'Games Won':  gamesWon,  
                    'Games Lost': gamesLost  
                    }
                
                eloDatabase["Players"].append(new_player_data)
                logger.info(f"Added new player to database: {playerName}")


    # Save updated database to JSON file
    with open(ELO_JSON_DATABASE_PATH, "w") as file:
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
    if os.path.exists(GAME_RESULTS_JSON_PATH):
        try:
            with open(GAME_RESULTS_JSON_PATH, 'r') as file:
                game_results = json.load(file)
        except json.JSONDecodeError:
            logger.error("Error: 'GAME_RESULTS_JSON_PATH' is corrupted. Overwriting file.")
            game_results = []
    else:
        game_results = []

    # Append new game entry
    game_results.append(game_entry)

    # Save updated game data
    try:
        with open(GAME_RESULTS_JSON_PATH, 'w') as file:
            json.dump(game_results, file, indent=2)
        logger.info(f"Game results saved to '{GAME_RESULTS_JSON_PATH}'.")
    except IOError as e:
        logger.error(f"Failed to save game results: {e}")



