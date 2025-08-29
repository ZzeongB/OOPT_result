import json
import os
import re

import pandas as pd


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
            # This script reads the normalized region_bboxes from the first file
            # and overwrites the pixel-space boundingBox values in the second file (assumed 512x512 canvas).
            # It preserves all other fields in the second file and writes an updated JSON file next to it.

            # SRC_NORMALIZED = Path("/mnt/data/P1_system1_target2_6.0_1.json")
            # SRC_PIXEL_DOC = Path("/mnt/data/P1_system1_target2.json")
            # OUT_PATH = Path("/mnt/data/P1_system1_target2.bbox_overwritten.json")
            CANVAS_SIZE = 512

            # --- Load inputs ---
            with open(input_filepath, "r", encoding="utf-8") as f:
                norm_doc = json.load(f)

            with open(output_filepath, "r", encoding="utf-8") as f:
                pixel_doc = json.load(f)

            # The second file appears to be a list with one scene document; handle both list and dict just in case.
            if isinstance(pixel_doc, list):
                scenes = pixel_doc
            elif isinstance(pixel_doc, dict):
                scenes = [pixel_doc]
            else:
                raise TypeError(
                    "Unexpected structure in second file (should be list or dict)."
                )

            region_bboxes = norm_doc.get("region_bboxes", [])
            if not region_bboxes:
                raise ValueError("No 'region_bboxes' found in the first file.")

            # Safety: only update the first scene's instances, matching the provided example.
            scene = scenes[0]
            instances = scene.get("instances", [])

            if len(instances) != len(region_bboxes):
                # We'll still proceed but warn in the output table by truncating to the min length.
                print(
                    f"Warning: instances ({len(instances)}) != region_bboxes ({len(region_bboxes)}). Using min length."
                )
            n = min(len(instances), len(region_bboxes))

            # Helper to convert normalized [x1,y1,x2,y2] to pixel {x,y,width,height} on a 512x512 canvas
            def norm_to_pixel_bbox(bb, size=CANVAS_SIZE):
                x1, y1, x2, y2 = bb
                # Convert to pixel coordinates
                px1 = int(round(x1 * size))
                py1 = int(round(y1 * size))
                px2 = int(round(x2 * size))
                py2 = int(round(y2 * size))
                # Ensure proper ordering in case of any anomalies
                left, right = sorted([px1, px2])
                top, bottom = sorted([py1, py2])
                # Clamp to image bounds
                left = max(0, min(size, left))
                right = max(0, min(size, right))
                top = max(0, min(size, top))
                bottom = max(0, min(size, bottom))
                # Compute width/height (ensure non-negative)
                w = max(0, right - left)
                h = max(0, bottom - top)
                return {"x": left, "y": top, "width": w, "height": h}

            # Build a small audit table
            rows = []
            for i in range(n):
                inst = instances[i]
                old = inst.get("boundingBox", {})
                new = norm_to_pixel_bbox(region_bboxes[i], CANVAS_SIZE)
                inst["boundingBox"] = new  # overwrite in place
                rows.append(
                    {
                        "index": i,
                        "instance_id": inst.get("id"),
                        "label": inst.get("label"),
                        "old_x": old.get("x"),
                        "old_y": old.get("y"),
                        "old_w": old.get("width"),
                        "old_h": old.get("height"),
                        "x": new["x"],
                        "y": new["y"],
                        "w": new["width"],
                        "h": new["height"],
                    }
                )

            # Write out updated structure, preserving original list/dict shape
            updated = scenes if isinstance(pixel_doc, list) else scenes[0]
            with open(output_filepath, "w", encoding="utf-8") as f:
                json.dump(updated, f, ensure_ascii=False, indent=2)

            # Show audit as a table for quick verification
            df = pd.DataFrame(rows)

            print("Overwritten bounding boxes (old vs new)", df)

            print(f"Updated file written to: {output_filepath}")

    print(f"Conversion complete. Files are saved in '{output_dir}'")


if __name__ == "__main__":
    input_directory = "output_final/prompt/"
    output_directory = "output_final/revised_prompt/"
    convert_bbox_format(input_directory, output_directory)
