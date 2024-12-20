# Robz-Elo

An Elo rating system to track player ratings based on game results. This project processes game score sheets, extracts player names and scores, calculates updated Elo ratings, and maintains a database of player standings.

## Features

- **Automated Data Extraction**: Parses game score images and extracts data using OCR and AI assistance.
- **Elo Rating Calculation**: Updates player ratings based on game outcomes using a custom Elo calculation algorithm.
- **User Corrections**: Allows users to review and correct extracted data before finalizing.
- **Data Persistence**: Maintains a history of games and player ratings in CSV and JSON formats.

## Requirements

- Python 3.x
- [Anthropic API Key](https://www.anthropic.com/) (for AI-assisted data extraction)

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/owz00/Robz-Elo.git
   cd Robz-Elo
   ```

2. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up API Keys**

   Set the Anthropic API key in the `llm_config.py` file:

   ```python
   # configs/llm_config.py

   API_KEYS = {
       'claude': 'your-anthropic-api-key'
   }
   ```

4. **Prepare Image Data**

   Place your game score images in the designated folder. By default, images should be placed in `image_input`. You can change the path in the configuration.

## Usage

Run the main script to process game scores and update player ratings:

```bash
python robz_elo_system.py
```
