import json
import os
from loguru import logger

from config.app_config.py import ELO_JSON_DATABASE_PATH





def change_player_name(json_file_path, old_name, new_name):
    try:
        # Load the JSON data from the file
        with open(json_file_path, "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                logger.error(f"Error: The file '{json_file_path}' contains invalid JSON.")
                return
    except FileNotFoundError:
        logger.error(f"Error: The file '{json_file_path}' was not found.")
        return
    except IOError:
        logger.error(f"Error: An I/O error occurred while trying to read '{json_file_path}'.")
        return

    # Find the player and change their name
    player_found = False
    try:
        for player in data["Players"]:
            if player["PlayerName"] == old_name:
                # Change the player's name
                player["PlayerName"] = new_name

                # Ensure past names is a list, initialize if needed
                if "past names" not in player or not isinstance(player["past names"], list):
                    player["past names"] = []

                # Add old_name to past names if not already present
                if old_name not in player["past names"]:
                    player["past names"].append(old_name)

                player_found = True
                logger.info(f"Player name changed from '{old_name}' to '{new_name}', and '{old_name}' added to past names.")
                break

        if not player_found:
            logger.error(f"Error: Player with name '{old_name}' not found in the JSON data.")

    except KeyError:
        logger.error("Error: Expected keys ('Players', 'PlayerName', or 'past names') were not found in the JSON structure.")
        return

    # Save the modified data back to the JSON file
    try:
        with open(json_file_path, "w") as file:
            json.dump(data, file, indent=4)
    except IOError:
        logger.error(f"Error: An I/O error occurred while trying to write to '{json_file_path}'.")


def add_past_name(json_file_path, player_name, past_name):
    try:
        # Load the JSON data from the file
        with open(json_file_path, "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                logger.error(f"Error: The file '{json_file_path}' contains invalid JSON.")
                return
    except FileNotFoundError:
        logger.error(f"Error: The file '{json_file_path}' was not found.")
        return
    except IOError:
        logger.error(f"Error: An I/O error occurred while trying to read '{json_file_path}'.")
        return

    # Find the player and add the past name
    player_found = False
    try:
        for player in data["Players"]:
            if player["PlayerName"] == player_name:
                # Ensure past names is a list, initialize if needed
                if "past names" not in player or not isinstance(player["past names"], list):
                    player["past names"] = []

                # Add past_name to past names if not already present
                if past_name not in player["past names"]:
                    player["past names"].append(past_name)
                    logger.info(f"'{past_name}' added to the past names of '{player_name}'.")
                else:
                    logger.info(f"'{past_name}' is already listed as a past name for '{player_name}'.")

                player_found = True
                break

        if not player_found:
            logger.error(f"Error: Player with name '{player_name}' not found in the JSON data.")

    except KeyError:
        logger.error("Error: Expected keys ('Players', 'PlayerName', or 'past names') were not found in the JSON structure.")
        return

    # Save the modified data back to the JSON file
    try:
        with open(json_file_path, "w") as file:
            json.dump(data, file, indent=4)
    except IOError:
        logger.error(f"Error: An I/O error occurred while trying to write to '{json_file_path}'.")


def main():
    # Get the directory of the current script and build the path to the JSON file
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(script_dir, ELO_JSON_DATABASE_PATH)

        # Prompt the user for an action
        action = input("Choose an action (1 to change name, 2 to add past name): ")

        if action == "1":
            old_name = input("Enter the player's current (old) name: ")
            new_name = input("Enter the player's new name: ")

            # Check if the file exists
            if os.path.exists(json_file_path):
                change_player_name(json_file_path, old_name, new_name)
            else:
                logger.error(f"Error: '{json_file_path}' does not exist.")

        elif action == "2":
            player_name = input("Enter the player's current name: ")
            past_name = input("Enter the past name to add: ")

            # Check if the file exists
            if os.path.exists(json_file_path):
                add_past_name(json_file_path, player_name, past_name)
            else:
                logger.error(f"Error: '{json_file_path}' does not exist.")
        else:
            logger.error("Invalid action selected.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()