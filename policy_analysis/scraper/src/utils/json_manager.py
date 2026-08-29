# Load existing data
import json
import os
from typing import Any, Dict, List, Union
from src.utils import Logger

class JsonManager:

    def __init__(self, output_file: str):
        self.output_file = output_file
        self._initialize_json()

    def _initialize_json(self) -> None:
        if not os.path.exists(self.output_file):
            with open(self.output_file, 'w') as f:
                json.dump([], f, indent=2)

    def write_json(self, data: dict) -> None:
        try:
            with open(self.output_file, 'r') as f:
                existing_data = json.load(f)

            existing_data.append(data)

            with open(self.output_file, 'w') as f:
                json.dump(existing_data, f, indent=2)

        except Exception as e:
            Logger.log(f"Error writing to JSON file {self.output_file}: {e}")

    def update_results(self, url: str, values: Union[List[str], Dict[str, Any]], keyword: str) -> None:
        try:

            with open(self.output_file, 'r') as f:
                data = json.load(f)

            if url not in data:
                data[url] = {}

            if isinstance(values, dict):

                for key, value in values.items():
                    if key not in data[url]:
                        Logger.log(f"Added new {key} to {url}.")
                        data[url][key] = value
                    else:

                        if isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if subkey not in data[url][key]:
                                    data[url][key][subkey] = subvalue
                                    Logger.log(f"Added new subkey.")
                                else:

                                    Logger.log(f"Merged values for subkey, avoiding duplicates.")
                                    if isinstance(subvalue, dict):
                                        for k, v in subvalue.items():
                                            if k not in data[url][key][subkey]:
                                                data[url][key][subkey][k] = v
                                            else:
                                                data[url][key][subkey][k] += v

                Logger.log(f"Updated dictionary structure for {url}.")

            else:
                if keyword not in data[url]:
                    data[url][keyword] = list(values)
                    Logger.log(f"Added new {keyword} to {url}.")
                else:

                    existing_values = set(data[url][keyword])
                    new_values = set(values)
                    merged_values = list(existing_values.union(new_values))
                    data[url][keyword] = merged_values
                    Logger.log(f"Merged values for {url} under {keyword}, avoiding duplicates.")

            with open(self.output_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            Logger.log(f"Error updating JSON results: {str(e)}")
