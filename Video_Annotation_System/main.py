import os
import math
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import json
import cv2

app = FastAPI(title="Video Annotation System")

class Annotation(BaseModel):
    tag: str
    timestamp_sec: float
    frame_index: int
    shortcut: str

class VideoAnnotationData(BaseModel):
    video_filename: str
    fps: float
    annotations: List[Annotation]

@app.get("/api/videos")
def get_videos(folder_path: str):
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
        raise HTTPException(status_code=400, detail="Invalid directory path")
    
    supported_extensions = ('.mp4', '.avi', '.mov', '.mkv')
    video_files = []
    
    for f in os.listdir(folder_path):
        if f.lower().endswith(supported_extensions):
            full_path = os.path.join(folder_path, f)
            base_name = os.path.splitext(f)[0]
            json_path = os.path.join(folder_path, f"{base_name}_labels.json")
            is_annotated = os.path.exists(json_path)
            fps = 30.0
            try:
                cap = cv2.VideoCapture(full_path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    if math.isnan(fps) or fps <= 0:
                        fps = 30.0
                cap.release()
            except Exception:
                pass
            
            video_files.append({
                "filename": f,
                "path": full_path,
                "fps": fps,
                "is_annotated": is_annotated
            })
    return {"videos": video_files}

@app.get("/api/video_stream")
def video_stream(path: str, request: Request):
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    file_size = os.path.getsize(path)
    range_header = request.headers.get("Range", None)
    
    if range_header:
        byte1, byte2 = 0, None
        match = range_header.replace("bytes=", "").split("-")
        if match[0]:
            byte1 = int(match[0])
        if len(match) > 1 and match[1]:
            byte2 = int(match[1])
        
        byte2 = byte2 if byte2 else file_size - 1
        length = byte2 - byte1 + 1
        
        def file_iterator(file_path, offset, chunk_size):
            with open(file_path, "rb") as f:
                f.seek(offset)
                bytes_read = 0
                while bytes_read < chunk_size:
                    read_size = min(65536, chunk_size - bytes_read)
                    data = f.read(read_size)
                    if not data:
                        break
                    bytes_read += len(data)
                    yield data
                
        headers = {
            "Content-Range": f"bytes {byte1}-{byte2}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(file_iterator(path, byte1, length), status_code=206, headers=headers)
    else:
        return FileResponse(path)

@app.post("/api/annotations")
def save_annotations(data: VideoAnnotationData, folder_path: str):
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
         raise HTTPException(status_code=400, detail="Invalid directory path")
    
    base_name = os.path.splitext(data.video_filename)[0]
    json_path = os.path.join(folder_path, f"{base_name}_labels.json")
    
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)
        
    return {"status": "success", "file": json_path}

@app.get("/api/annotations")
def load_annotations(folder_path: str, filename: str):
    folder_path = os.path.abspath(folder_path)
    base_name = os.path.splitext(filename)[0]
    json_path = os.path.join(folder_path, f"{base_name}_labels.json")
    
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"annotations": []}

@app.get("/api/templates")
def load_templates():
    template_path = os.path.join(os.path.dirname(__file__), "templates.json")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "templates": [
            {
                "name": "棒球打擊範本",
                "tags": [
                    {"name": "預備", "shortcut": "1", "color": "#3b82f6"},
                    {"name": "抬腿", "shortcut": "2", "color": "#10b981"},
                    {"name": "轉體", "shortcut": "3", "color": "#f59e0b"},
                    {"name": "擊球", "shortcut": "4", "color": "#ef4444"},
                    {"name": "延伸", "shortcut": "5", "color": "#8b5cf6"}
                ]
            }
        ]
    }

class TagTemplate(BaseModel):
    name: str
    tags: List[dict]

class TemplatesData(BaseModel):
    templates: List[TagTemplate]

@app.post("/api/templates")
def save_templates(data: TemplatesData):
    template_path = os.path.join(os.path.dirname(__file__), "templates.json")
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)
    return {"status": "success"}

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
