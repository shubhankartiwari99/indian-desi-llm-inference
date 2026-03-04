import json
import os
import logging
from typing import List, Dict, Any

LEADERBOARD_FILE = "data/benchmark_results.json"

def update_leaderboard(model_name: str, summary: Dict[str, Any]):
    """
    Updates or appends a model entry in the leaderboard.
    """
    try:
        os.makedirs(os.path.dirname(LEADERBOARD_FILE), exist_ok=True)
        if os.path.exists(LEADERBOARD_FILE):
            with open(LEADERBOARD_FILE, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
        else:
            data = []

        # Prepare new entry
        entry = {
            "model": model_name,
            "mean_confidence": summary.get("mean_confidence", 0.0),
            "mean_instability": summary.get("mean_instability", 0.0),
            "escalation_rate": summary.get("escalation_rate", 0.0),
            "mean_entropy": summary.get("mean_entropy", 0.0),
            "timestamp": summary.get("timestamp", "")
        }

        # Check if model already exists, if so update it, otherwise append
        updated = False
        for i, item in enumerate(data):
            if item.get("model") == model_name:
                data[i] = entry
                updated = True
                break
        
        if not updated:
            data.append(entry)

        with open(LEADERBOARD_FILE, "w") as f:
            json.dump(data, f, indent=2)
        
        logging.info(f"Leaderboard updated for model: {model_name}")
    except Exception as e:
        logging.error(f"Failed to update leaderboard: {e}")

def get_leaderboard() -> List[Dict[str, Any]]:
    """
    Retrieves the current leaderboard rankings.
    """
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            data = json.load(f)
        
        # Sort by confidence descending, then instability ascending
        data.sort(key=lambda x: (-x.get("mean_confidence", 0), x.get("mean_instability", 0)))
        return data
    except Exception as e:
        logging.error(f"Failed to read leaderboard: {e}")
        return []
