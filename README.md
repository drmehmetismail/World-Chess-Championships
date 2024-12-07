# World Chess Championships

## Project Overview

This repository contains a set of Python scripts designed for analyzing World Chess Championships games and calculating missed points, game intelligence (GI), and other metrics. You can either use chess engines like Stockfish and Lc0 to annotate chess games and compute performance statistics or upload pre-annotated games from e.g. https://lichess.org/page/world-championships. 


## Requirements

### Installation
Use the following command to install the required dependencies:

```bash
pip install -r requirements.txt
```

### Dependencies
The following Python libraries are used:
- `pandas`: For handling and manipulating CSV data.
- `matplotlib`: For generating visualizations.
- `python-chess`: For parsing and analyzing chess game PGNs.

---

## Scripts and Usage

### 1. `csv_to_player_stats.py`
- **Purpose**: Generates player-specific statistics from a CSV file of chess games.
- **Input**: A CSV file containing game data.
- **Output**: Player-specific performance metrics and summaries.

### 2. `json_to_csv_converter.py`
- **Purpose**: Converts chess game data from JSON format to CSV format.
- **Input**: JSON files with game data.
- **Output**: CSV files with structured game data.

### 3. `lc0_pgn_annotator.py`
- **Purpose**: Annotates PGN files with move evaluations using the Lc0 chess engine.
- **Input**: PGN files.
- **Output**: Annotated PGNs with Lc0 pawn and wdl evaluations.

### 4. `pgn_evaluation_fast_analyzer_lc0.py`
- **Purpose**: Analyzes Lc0 annotated PGNs.
- **Input**: Annotated PGN files.
- **Output**: Metrics

### 5. `pgn_evaluation_fast_analyzer.py`
- **Purpose**: Analyzes Stockfish annotated PGNs.
- **Input**: Annotated PGN files.
- **Output**: Metrics

### 6. `pr_calculator.py`
- **Purpose**: Calculates performance ratings for players. Uses Complete Performance Rating (CPR) in case of perfect scores.

### 7. `stockfish_pgn_annotator.py`
- **Purpose**: Annotates PGN files with move evaluations using the Stockfish engine.
- **Input**: PGN files.
- **Output**: Annotated PGNs.

### 8. `summary_stats.py`
- **Purpose**: Generates summary statistics for a set of chess games.

### 9. `wcc_stats.py`
- **Purpose**: Focused on analyzing World Chess Championship data. Exports a graph of average missed points over the years.

### 10. `WCC_matches` folder
- As an example, this folder contains Magnus Carlsen's World Chess Championship matches, analyzed with Stockfish 17 at depth 27.
- It also contains two games analyzed with Leela Chess Zero with nodes_limit = 2500. This is for the sake of illustration, as no meaningful conclusions can be derived from these two games at this nodes level.
---

## Reference
- For more information, see https://doi.org/10.48550/arXiv.2302.13937
- For more super GM games, see https://github.com/drmehmetismail/Performance-Metrics
- For Engine vs Engine games (CCRL), see https://github.com/drmehmetismail/Engine-vs-engine-chess-stats
- For Lichess games by regular players, see https://github.com/drmehmetismail/Chess-Data-Processing

## Citation
Please cite the following paper if you find this helpful.
```
@article{ismail2023human,
  title={Human and Machine Intelligence in n-Person Games with Partial Knowledge: Theory and Computation},
  author={Ismail, Mehmet S},
  journal={arXiv preprint arXiv:2302.13937},
  year={2023}
}
```
