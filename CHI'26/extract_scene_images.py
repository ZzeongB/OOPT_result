import json
import shutil
from pathlib import Path

def extract_scene_images():
    """
    Study2-P{id}.log.patched 파일들을 분석하여 scene_saved 이벤트를 찾고,
    그 직전의 api.generate_image.succeeded 이벤트에서 이미지 경로를 추출하여
    참가자별 폴더에 이미지들을 복사한다.
    """
    log_dir = Path("log")
    output_base_dir = Path("extracted_scene_images")
    
    # 출력 디렉토리 생성
    output_base_dir.mkdir(exist_ok=True)
    
    # 참가자 ID 1-6
    for participant_id in range(1, 7):
        log_file = log_dir / f"Study2-P{participant_id}.log.patched"
        
        if not log_file.exists():
            print(f"Warning: {log_file} not found, skipping...")
            continue
            
        print(f"Processing {log_file}...")
        
        # 참가자별 출력 폴더 생성
        participant_dir = output_base_dir / f"P{participant_id}"
        participant_dir.mkdir(exist_ok=True)
        
        # 로그 파일 읽기
        events = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    # JSON 부분만 추출 (로그 레벨 제거)
                    json_start = line.find('{"timestamp"')
                    if json_start != -1:
                        json_str = line[json_start:]
                        event = json.loads(json_str)
                        events.append(event)
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # scene_saved 이벤트 찾기
        scene_saved_events = []
        for i, event in enumerate(events):
            if event.get("event") == "scene_saved":
                scene_saved_events.append((i, event))
        
        print(f"Found {len(scene_saved_events)} scene_saved events for P{participant_id}")
        
        # 각 scene_saved 이벤트에 대해 직전의 api.generate_image.succeeded 찾기
        image_paths = []
        for scene_idx, (event_idx, scene_event) in enumerate(scene_saved_events):
            # 역순으로 검색하여 가장 최근의 api.generate_image.succeeded 찾기
            for j in range(event_idx - 1, -1, -1):
                prev_event = events[j]
                if prev_event.get("event") == "api.generate_image.succeeded":
                    # 이미지 경로 추출
                    details = prev_event.get("details", {})
                    image_path = details.get("image_path")
                    if image_path:
                        image_paths.append({
                            'scene_index': scene_idx + 1,
                            'image_path': image_path,
                            'timestamp': scene_event.get("timestamp")
                        })
                        print(f"  Scene {scene_idx + 1}: {image_path}")
                    break
        
        # 이미지 파일들 복사
        copied_count = 0
        for img_info in image_paths:
            src_path = Path(img_info['image_path'])
            if src_path.exists():
                # 파일명에 scene 번호 추가
                file_ext = src_path.suffix
                file_name = f"scene_{img_info['scene_index']:02d}{file_ext}"
                dst_path = participant_dir / file_name
                
                try:
                    shutil.copy2(src_path, dst_path)
                    copied_count += 1
                    print(f"  Copied: {src_path} -> {dst_path}")
                except Exception as e:
                    print(f"  Error copying {src_path}: {e}")
            else:
                print(f"  Warning: Image file not found: {src_path}")
        
        print(f"Copied {copied_count} images for P{participant_id}\n")

if __name__ == "__main__":
    extract_scene_images()