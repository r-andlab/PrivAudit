import json
import os
from typing import Any, Dict, List, Union
from src.utils import Logger


class JsonManager:
    """Handles JSON file operations for storing email results."""
    
    def __init__(self, output_file: str):
        self.output_file = output_file
        self._initialize_json()
    
    def _initialize_json(self) -> None:
        """Creates or loads the JSON file."""
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w') as f:
                json.dump([], f, indent=2)

    def write_json(self, data: dict) -> None:
        """Appends a new dictionary to the JSON file without overwriting existing data."""
        try:
            with open(self.output_file, 'r') as f:
                existing_data = json.load(f)
            
            existing_data.append(data)
            
            with open(self.output_file, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            Logger.log(f"Error writing to JSON file {self.output_file}: {e}")
    
    def update_results(self, url: str, values: Union[List[str], Dict[str, Any]], keyword: str) -> None:
        """
        Updates or creates new entries in the JSON file.
        For dictionaries, directly updates the structure without using the keyword parameter.
        For lists, maintains the existing keyword-based structure.
        """
        try:
            # Load existing data
            with open(self.output_file, 'r') as f:
                data = json.load(f)
            
            # If URL doesn't exist, create it
            if url not in data:
                data[url] = {}
            
            # Handle dictionary type (keyword counts)
            if isinstance(values, dict):
                # Directly merge the dictionary structure
                for key, value in values.items():
                    if key not in data[url]:
                        Logger.log(f"Added new {key} to {url}.")
                        data[url][key] = value
                    else:
                        # If key exists, merge the nested structure
                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in data[url][key]:
                                    data[url][key][subkey] = subvalue
                                    Logger.log(f"Added new subkey.")
                                else:
                                    # Merge the innermost level (keyword counts)
                                    Logger.log(f"Merged values for subkey, avoiding duplicates.")
                                    if isinstance(subvalue, dict):
                                        for k, v in subvalue.items():
                                            if k not in data[url][key][subkey]:
                                                data[url][key][subkey][k] = v
                                            else:
                                                data[url][key][subkey][k] += v
                
                Logger.log(f"Updated dictionary structure for {url}.")
            
            # Handle list-type data (emails/phones)
            else:
                if keyword not in data[url]:
                    data[url][keyword] = list(values)
                    Logger.log(f"Added new {keyword} to {url}.")
                else:
                    # Merge the values avoiding duplicates
                    existing_values = set(data[url][keyword])
                    new_values = set(values)
                    merged_values = list(existing_values.union(new_values))
                    data[url][keyword] = merged_values
                    Logger.log(f"Merged values for {url} under {keyword}, avoiding duplicates.")
            
            # Write updated data back to the file
            with open(self.output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
        except Exception as e:
            Logger.log(f"Error updating JSON results: {str(e)}")