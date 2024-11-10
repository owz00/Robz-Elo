def print_game_results(game_result_dictionary):
    """
    Prints the game results in a formatted manner.
    """
    print("\n=== GAME RESULTS ===")
    for team_name, team_info in game_result_dictionary['teams'].items():
        print(f"\n{team_name} ({team_info['victory_points']} VP)")
        print("-" * 40)
        for player in team_info['players']:
            print(f"{player['name']:<15} Score: {player['score']}")
    print(f"\nWINNER: {game_result_dictionary['winner']}")
    print("=" * 40 + "\n")