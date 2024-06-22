import json


def load_config(file_path):
    """
    Loads the configuration from a JSON file.

    Args:
        file_path (str): The path to the configuration file.

    Returns:
        dict: The configuration dictionary.
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Invalid JSON format in file: {file_path}")
        return {}
