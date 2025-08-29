import json
import os
from collections import defaultdict


def group_and_sort_prompts(directory):
    """
    Groups and sorts prompt files from a given directory.

    Args:
        directory (str): The path to the directory containing the prompt files.

    Returns:
        list: A list of sorted prompts.
    """
    all_prompts = []

    # List all files in the given directory
    try:
        files = os.listdir(directory)
    except FileNotFoundError:
        print(f"Error: Directory not found at '{directory}'")
        return None

    # Filter for .json files
    json_files = [f for f in files if f.endswith(".json")]

    # Process each json file
    for filename in json_files:
        # Extract participant_id, system_id, and target_id from the filename
        parts = filename.replace(".json", "").split("_")
        if len(parts) != 3:
            print(f"Warning: Skipping file with unexpected format: {filename}")
            continue

        participant_id = parts[0]
        system_id = parts[1]
        target_id = parts[2]  # e.g., 'target1'

        # Construct the full file path
        file_path = os.path.join(directory, filename)

        # Read the JSON content from the file
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {filename}")
            continue
        except IOError as e:
            print(f"Warning: Could not read file {filename}: {e}")
            continue

        # The data is a list of items, process each one
        if isinstance(data, list):
            for item in data:
                # Store the data
                all_prompts.append(
                    {
                        "participant_id": participant_id,
                        "system_id": system_id,
                        "target_id": target_id,
                        "data": item,
                    }
                )

    # Sort the data: by system_id, then participant_id (numeric), then target_id
    all_prompts.sort(
        key=lambda x: (
            x["system_id"],
            int(x["participant_id"].replace("P", "")),
            x["target_id"],
        )
    )

    # Create the final list
    final_list = []
    for prompt in all_prompts:
        new_item = {
            "participant_id": prompt["participant_id"],
            "system_id": prompt["system_id"],
        }
        # Merge the data from the JSON file's item
        new_item.update(prompt["data"])
        final_list.append(new_item)

    return final_list


if __name__ == "__main__":
    # Specify the directory containing the prompt files
    prompt_directory = "output_final/revised_prompt"

    # Get the data
    all_prompts = group_and_sort_prompts(prompt_directory)

    # Group prompts by system_id
    prompts_by_system = defaultdict(list)
    if all_prompts:
        for prompt in all_prompts:
            prompts_by_system[prompt["system_id"]].append(prompt)

    # Write each group to a separate file
    if prompts_by_system:
        for system_id, prompts in prompts_by_system.items():
            # Modify the label and assign new sequential IDs for each instance
            for i, prompt in enumerate(prompts, 1):
                prompt["id"] = i  # Assign new sequential ID
                if "instances" in prompt and isinstance(prompt["instances"], list):
                    for instance in prompt["instances"]:
                        if "textDescription" in instance:
                            instance["label"] = instance["textDescription"]

            filename = f"{system_id}.txt"
            with open(filename, "w") as f:
                json.dump(prompts, f, indent=4)
            print(f"Saved prompts for {system_id} to {filename}")
