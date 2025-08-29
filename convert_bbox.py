import json
import os
import re


def convert_bbox_format(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            input_filepath = os.path.join(input_dir, filename)

            # Create the new filename by removing the version and iteration numbers
            # e.g., P1_system1_target2_6.0_1.json -> P1_system1_target2.json
            base_name = re.sub(r"_\d+\.\d+_\d+\.json$", ".json", filename)
            output_filepath = os.path.join(output_dir, base_name)

            with open(input_filepath, "r") as f:
                data = json.load(f)

            new_regions = []
            for i, bbox in enumerate(data["region_bboxes"]):
                x_min, y_min, x_max, y_max = bbox

                # Convert normalized coordinates to 512x512 absolute coordinates
                x = int(x_min * 512)
                y = int(y_min * 512)
                width = int((x_max - x_min) * 512)
                height = int((y_max - y_min) * 512)

                new_regions.append(
                    {
                        "caption": data["region_captions"][i],
                        "boundingBox": {
                            "x": x,
                            "y": y,
                            "width": width,
                            "height": height,
                        },
                    }
                )

            new_data = {
                "global_caption": data["global_caption"],
                "regions": new_regions,
            }

            with open(output_filepath, "w") as f:
                json.dump(new_data, f, indent=2)

    print(f"Conversion complete. Files are saved in '{output_dir}'")


if __name__ == "__main__":
    input_directory = "output_final/prompt/"
    output_directory = "output_final/revised_prompt/"
    convert_bbox_format(input_directory, output_directory)
