import json
import os

def change_player_name(json_file_path, old_name, new_name):
    try:
        # Load the JSON data from the file
        with open(json_file_path, "r") as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                print(f"Error: The file '{json_file_path}' contains invalid JSON.")
                return
    except FileNotFoundError:
        print(f"Error: The file '{json_file_path}' was not found.")
        return
    except IOError:
        print(f"Error: An I/O error occurred while trying to read '{json_file_path}'.")
        return

    # Find the player and change their name
    player_found = False
    try:
        for player in data["Players"]:
            if player["PlayerName"] == old_name:
                # Change the player's name
                player["PlayerName"] = new_name

                # Update past names
                if player["past names"] == "null":
                    # Initialize with a list containing the old name
                    player["past names"] = [old_name]
                elif isinstance(player["past names"], list):
                    # Append the old name to the past names list if it’s already a list
                    player["past names"].append(old_name)
                else:
                    # If it's not "null" or a list, convert to a list and add the old name
                    player["past names"] = [player["past names"], old_name]

                player_found = True
                print(f"Player name changed from '{old_name}' to '{new_name}', and '{old_name}' added to past names.")
                break

        if not player_found:
            print(f"Error: Player with name '{old_name}' not found in the JSON data.")

    except KeyError:
        print("Error: Expected keys ('Players', 'PlayerName', or 'past names') were not found in the JSON structure.")
        return

    # Save the modified data back to the JSON file
    try:
        with open(json_file_path, "w") as file:
            json.dump(data, file, indent=4)
    except IOError:
        print(f"Error: An I/O error occurred while trying to write to '{json_file_path}'.")

def main():
    # Get the directory of the current script and build the path to the JSON file
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(script_dir, "players_data.json")

        # Prompt the user for the old and new names
        old_name = input("Enter the player's current (old) name: ")
        new_name = input("Enter the player's new name: ")

        # Check if the file exists
        if os.path.exists(json_file_path):
            change_player_name(json_file_path, old_name, new_name)
        else:
            print(f"Error: '{json_file_path}' does not exist.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()