import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D


# ────────────────────────────────────────────────────────────────────────────
# LAYOUT EVENT AGGREGATION: Show start-end periods for consecutive layout events
# ────────────────────────────────────────────────────────────────────────────
def extract_node_id(details_str):
    """Extract nodeId from details JSON string"""
    if pd.isna(details_str):
        return None
    # Extract nodeId using regex
    match = re.search(r"'nodeId'\s*:\s*'([^']+)'", str(details_str))
    if not match:
        match = re.search(r'"nodeId"\s*:\s*"([^"]+)"', str(details_str))
    return match.group(1) if match else None


def aggregate_layout_events(df, time_gap_threshold=5.0):
    """Aggregate truly consecutive layout events by nodeId to show start-end periods
    
    Args:
        df: DataFrame with events
        time_gap_threshold: Maximum seconds between events to consider them consecutive
    """
    layout_event_names = [
        "layout.node.moved",
        "layoutboard.node.resizable.resized", 
        "`layoutboard.node.resizable`",
    ]
    
    aggregated = []
    
    # Process each id_group separately
    for id_group in df["id_group"].unique():
        group_df = df[df["id_group"] == id_group].copy()
        group_df = group_df.sort_values("timestamp").reset_index(drop=True)
        
        # Find consecutive sequences of layout events for each nodeId
        i = 0
        while i < len(group_df):
            row = group_df.iloc[i]
            
            # Skip non-layout events
            if row["event"] not in layout_event_names:
                i += 1
                continue
                
            # Extract nodeId for this layout event
            node_id = extract_node_id(row["details"])
            if pd.isna(node_id):
                i += 1
                continue
            
            # Start a consecutive sequence
            sequence_start = i
            sequence_events = [row]
            
            # Look ahead to find consecutive layout events for same nodeId
            j = i + 1
            while j < len(group_df):
                next_row = group_df.iloc[j]
                
                # If it's not a layout event for the same node, break
                if (next_row["event"] not in layout_event_names or 
                    extract_node_id(next_row["details"]) != node_id):
                    break
                    
                # Check time gap
                time_diff = (next_row["timestamp"] - sequence_events[-1]["timestamp"]).total_seconds()
                if time_diff > time_gap_threshold:
                    break
                    
                sequence_events.append(next_row)
                j += 1
            
            # Process the found sequence
            if len(sequence_events) == 1:
                # Single event, keep as is
                event_row = sequence_events[0]
                aggregated.append({
                    "id_group": id_group,
                    "nodeId": node_id,
                    "event": f"layout.{event_row['event'].split('.')[1]}.{event_row['event'].split('.')[2]}",
                    "timestamp": event_row["timestamp"],
                    "seq_idx": None,
                    "is_start": True,
                    "is_end": True,
                    "duration": 0,
                    "event_count": 1,
                })
            else:
                # Multiple consecutive events, create start-end pair
                first = sequence_events[0]
                last = sequence_events[-1]
                duration = (last["timestamp"] - first["timestamp"]).total_seconds()
                
                # Start marker
                aggregated.append({
                    "id_group": id_group,
                    "nodeId": node_id,
                    "event": "layout.start",
                    "timestamp": first["timestamp"],
                    "seq_idx": None,
                    "is_start": True,
                    "is_end": False,
                    "duration": duration,
                    "event_count": len(sequence_events),
                })
                
                # End marker  
                aggregated.append({
                    "id_group": id_group,
                    "nodeId": node_id,
                    "event": "layout.end",
                    "timestamp": last["timestamp"],
                    "seq_idx": None,
                    "is_start": False,
                    "is_end": True,
                    "duration": duration,
                    "event_count": len(sequence_events),
                })
            
            # Move to next event after this sequence
            i = sequence_start + len(sequence_events)
    
    return pd.DataFrame(aggregated)


# ====== 설정 ======
INPUT_CSV = "csv_log/OOPT_filtered_all.csv"  # 원본 CSV 경로
OUTPUT_CSV = "csv_log/OOPT_filtered_all.csv"  # 수정본 저장 경로

# 매핑 사전
label_map = {
    "class_instances_reset": "class.instances_reset",
    "instance_created_from_detection": "instance.created_from_detection",
    "layout_board.new_box_positioned": "instance.created_from_text",
}

# ====== 실행 ======
df = pd.read_csv(INPUT_CSV)

# 'event'라는 컬럼이 있다고 가정
df["event"] = df["event"].replace(label_map)

df.to_csv(OUTPUT_CSV, index=False)

# df_all = df.copy()
# df = df_all.copy()

if "timestamp" in df.columns:
    if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["id_group", "timestamp"]).copy()
else:
    df = df.sort_values(["id_group"]).copy()

# Separate layout and non-layout events
non_layout_events = df[
    ~df["event"].isin(["layout.node.moved", "layoutboard.node.resizable.resized"])
].copy()
layout_aggregated = aggregate_layout_events(df)

# Combine and assign sequence indices
all_events = []

for id_group in sorted(df["id_group"].unique()):
    # Get non-layout events for this group
    group_non_layout = non_layout_events[
        non_layout_events["id_group"] == id_group
    ].copy()
    group_layout = layout_aggregated[layout_aggregated["id_group"] == id_group].copy()

    # Combine and sort by timestamp
    group_events = []

    for _, row in group_non_layout.iterrows():
        group_events.append(
            {
                "id_group": id_group,
                "event": row["event"],
                "timestamp": row["timestamp"],
                "is_layout": False,
                "is_start": False,
                "is_end": False,
                "duration": 0,
                "event_count": 1,
            }
        )

    for _, row in group_layout.iterrows():
        group_events.append(
            {
                "id_group": id_group,
                "event": row["event"],
                "timestamp": row["timestamp"],
                "is_layout": True,
                "is_start": row["is_start"],
                "is_end": row["is_end"],
                "duration": row["duration"],
                "event_count": row["event_count"],
            }
        )

    # Sort by timestamp and assign sequence indices
    group_events.sort(key=lambda x: x["timestamp"])
    for i, event in enumerate(group_events):
        event["seq_idx"] = i
        all_events.append(event)

# Create final dataframe
df_final = pd.DataFrame(all_events)
df_final = df_final[
    (df_final["event"] != "layout.node.moved")
    & (df_final["event"] != "layout.node.resizable")
]


print(f"Total events after aggregation: {len(df_final)}")
print(
    f"Layout start/end pairs: {len(df_final[df_final['event'].str.startswith('layout.')])}"
)

# ────────────────────────────────────────────────────────────────────────────
# VISUALIZATION SETUP WITH IMPROVED COLORS AND GROUPING
# ────────────────────────────────────────────────────────────────────────────

# Updated color scheme with layout events
base_colors = {
    "class": plt.cm.Blues,  # Class events - Blue
    "instance": plt.cm.Reds,  # Instance events - Red
    "object": plt.cm.Greens,  # Object events - Green
    "layout": plt.cm.Greys,  # Layout events - Orange (NEW)
    "api": plt.cm.Greys,  # API events - Grey
    "other": plt.cm.Purples,  # Other events - Purple
}

# Categorize events with improved grouping
event_types = sorted(df_final["event"].unique())
event_to_group = {}
for ev in event_types:
    if ev == "api.generate_image.succeeded":
        event_to_group[ev] = "api"
    elif ev.startswith("layout."):
        event_to_group[ev] = "layout"
    elif ev.startswith("class"):
        event_to_group[ev] = "class"
    elif ev.startswith("instance"):
        event_to_group[ev] = "instance"
    elif ev.startswith("object_node"):
        event_to_group[ev] = "object"
    else:
        event_to_group[ev] = "other"

# Assign colors
event_to_color = {}
for group in set(event_to_group.values()):
    group_events = [ev for ev, g in event_to_group.items() if g == group]
    cmap = base_colors[group]
    n = len(group_events)
    colors = [cmap(x) for x in np.linspace(0.9, 0.3, max(n, 1))]
    for i, ev in enumerate(group_events):
        event_to_color[ev] = colors[i] if n > 1 else cmap(0.7)

# Enhanced marker mapping with same color but different shapes for instance creation
marker_map = {
    # Class events
    "class.created": "s",
    "class.updated": "s",
    "class.instances_reset": "s",
    # Instance events - SAME COLOR, DIFFERENT SHAPES
    "instance.created_from_class": "s",  # Diamond
    "instance.created_from_text": "o",  # Circle
    "instance.created_from_detection": "^",  # Triangle
    "instance.updated": "s",  # Square
    # Layout events - distinct markers
    "layout.start": "s",  # Start marker
    "layout.end": "s",  # End marker
    "layout.moved": "s",  # Individual move
    "layout.resized": "v",  # Individual resize
    # Object events
    "object_node.extract.confirmed": "s",  # Hexagon
    # API events
    "api.generate_image.succeeded": "*",  # Star
}

alpha_map = {
    "instance.created_from_class": 0.95,
    "instance.created_from_text": 0.95,
    "instance.created_from_detection": 0.95,
    "instance.updated": 0.65,
    "layout.start": 0.7,
    "layout.end": 0.7,
    "api.generate_image.succeeded": 1,
}

# Make instance creation events same color
instance_creation_color = base_colors["instance"](0.7)
for event in [
    "instance.created_from_class",
    "instance.created_from_text",
    "instance.created_from_detection",
]:
    if event in event_to_color:
        event_to_color[event] = instance_creation_color

# Make instance creation events same color
layout_color = base_colors["layout"](0.7)
for event in ["layout.start", "layout.end", "layout.moved", "layout.resized"]:
    if event in event_to_color:
        event_to_color[event] = layout_color

import matplotlib.pyplot as plt
import pandas as pd

# df_all = pd.read_csv("csv_log/OOPT_filtered_all.csv")

df_all = df_final.copy()

# 각 id_group별로 첫 이벤트를 0초로 맞추기
if "timestamp" in df_all.columns:
    if not pd.api.types.is_datetime64_any_dtype(df_all["timestamp"]):
        df_all["timestamp"] = pd.to_datetime(df_all["timestamp"])
    df_all["time_norm"] = df_all.groupby("id_group")["timestamp"].transform(
        lambda x: (x - x.min()).dt.total_seconds()
    )
    x = df_all["time_norm"]
else:
    x = df_all.index

# id_group별로 y축 배치
id_groups_sorted = sorted(df_all["id_group"].unique())
id_group_to_y = {id_: i for i, id_ in enumerate(id_groups_sorted)}
y = df_all["id_group"].map(id_group_to_y)

import numpy as np

plt.figure(figsize=(20, max(6, len(id_groups_sorted) * 0.7)))
rng = np.random.default_rng(42)

legend_elems = []  # legend 수동 구성

for ev in event_types:
    mask = df_all["event"] == ev
    group = [g for e, g in zip(event_types, event_to_group) if e == ev][0]
    y_jitter = y[
        mask
    ]  # .to_numpy(dtype=float) + rng.uniform(-0.05, 0.05, size=mask.sum())

    # 기본 스타일
    scatter_args = dict(
        x=x[mask],
        y=y_jitter,
        color=event_to_color[ev],
        marker="o",
        s=50,
        alpha=0.7,
        edgecolors="none",
        linewidths=0,
    )

    # # 강조 이벤트
    # if ev in ['class.created', 'class.updated',
    #           'instance.created_from_class', 'instance.updated']:
    #     scatter_args.update(dict(
    #         s=50,
    #         edgecolors='k',
    #         linewidths=0.8,
    #         # # # # zorder=5
    #     ))

    plt.scatter(**scatter_args)

    # legend entry 생성
    legend_elems.append(
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=event_to_color[ev],
            #    markeredgecolor=('k' if ev in ['class.created','class.updated',
            #                                   'instance.created_from_class','instance.updated'] else 'none'),
            markersize=(
                6
                if ev
                in [
                    "class.created",
                    "class.updated",
                    "instance.created_from_class",
                    "instance.updated",
                ]
                else 6
            ),
            label=ev,
        )
    )

plt.xlabel("Time (seconds from first event in each id_group)")
plt.ylabel("id_group (2~7)")
plt.yticks(list(id_group_to_y.values()), list(id_group_to_y.keys()))
plt.title("Event Timeline by id_group (all events, created/updated emphasized)")

plt.legend(
    handles=legend_elems, bbox_to_anchor=(1.02, 1), loc="upper left", title="Events"
)
plt.tight_layout()
plt.show()
plt.tight_layout()
plt.show()
