import os
import math
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import json
import cv2
import subprocess
import imageio_ffmpeg

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
            # 忽略備份檔案與臨時轉檔檔案
            if "_backup" in f.lower() or "temp_" in f.lower():
                continue
            
            name, ext = os.path.splitext(f)
            full_path = os.path.join(folder_path, f)
            
            # 檢查標註檔
            json_path = os.path.join(folder_path, f"{name}_labels.json")
            is_annotated = os.path.exists(json_path)
            
            # 為了相容以前可能存在的 _h264 標註檔
            if not is_annotated:
                h264_json_path = os.path.join(folder_path, f"{name}_h264_labels.json")
                is_annotated = os.path.exists(h264_json_path)
                
            fps = 30.0
            codec_str = ""
            try:
                cap = cv2.VideoCapture(full_path)
                if cap.isOpened():
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    if math.isnan(fps) or fps <= 0:
                        fps = 30.0
                    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
                    if fourcc > 0:
                        try:
                            codec_str = fourcc.to_bytes(4, 'little').decode('utf-8', 'ignore').strip()
                        except Exception:
                            codec_str = ""
                cap.release()
            except Exception:
                pass
            
            # 瀏覽器支援的編碼檢查
            # 必須是 .mp4 格式，且為相容的 H.264 / AVC 或是其他網頁編碼
            is_supported = False
            if ext.lower() == '.mp4':
                if codec_str:
                    supported_codecs = {'avc1', 'h264', 'hvc1', 'hev1', 'vp09', 'av01'}
                    is_supported = codec_str.lower() in supported_codecs
                else:
                    # 找不到 codec_str，則保守假設支援
                    is_supported = True
            
            video_files.append({
                "filename": f,
                "path": full_path,
                "fps": fps,
                "is_annotated": is_annotated,
                "codec": codec_str,
                "is_supported": is_supported
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
    import traceback
    folder_path = os.path.abspath(folder_path)
    if not os.path.isdir(folder_path):
         raise HTTPException(status_code=400, detail=f"目錄不存在或無效: {folder_path}")
    
    base_name = os.path.splitext(data.video_filename)[0]
    json_path = os.path.join(folder_path, f"{base_name}_labels.json")
    
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data.model_dump(), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("=== 儲存標註時發生異常 ===")
        traceback.print_exc()
        print("========================")
        raise HTTPException(
            status_code=500, 
            detail=f"寫入標註檔案失敗。原因: {type(e).__name__}: {str(e)}"
        )
        
    return {"status": "success", "file": json_path}

@app.get("/api/annotations")
def load_annotations(folder_path: str, filename: str):
    folder_path = os.path.abspath(folder_path)
    base_name = os.path.splitext(filename)[0]
    json_path = os.path.join(folder_path, f"{base_name}_labels.json")
    
    # Fallback to original file labels if _h264 labels don't exist yet
    if not os.path.exists(json_path) and base_name.lower().endswith("_h264"):
        orig_base = base_name[:-5]
        fallback_json_path = os.path.join(folder_path, f"{orig_base}_labels.json")
        if os.path.exists(fallback_json_path):
            json_path = fallback_json_path
            
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

@app.post("/api/transcode")
def transcode_video(path: str):
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    dir_name = os.path.dirname(path)
    base_name = os.path.basename(path)
    name, ext = os.path.splitext(base_name)
    
    # 建立安全刪除函式，解決 Windows 檔案鎖定問題
    def safe_remove(file_path, retries=5, delay=0.5):
        import gc
        import time
        for i in range(retries):
            try:
                gc.collect()  # 強制執行垃圾回收以釋放未完全關閉的影片串流 file handles
                if os.path.exists(file_path):
                    os.remove(file_path)
                return True
            except PermissionError:
                if i < retries - 1:
                    time.sleep(delay)
                else:
                    raise
        return False
    
    # 臨時轉檔路徑
    temp_output_path = os.path.join(dir_name, f"temp_{name}.mp4")
    # 最終儲存路徑（統一為 .mp4，不加 _h264）
    final_path = os.path.join(dir_name, f"{name}.mp4")
    
    # 如果臨時檔已存在，先刪除以防衝突
    if os.path.exists(temp_output_path):
        try:
            safe_remove(temp_output_path)
        except Exception:
            pass
            
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    
    cmd = [
        ffmpeg_path,
        '-i', path,
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-y', temp_output_path
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"轉碼失敗: {result.stderr}")
            
        # 轉碼成功，替換舊檔案
        # 1. 刪除原來的影片檔（使用 safe_remove 排除播放器鎖定）
        if os.path.exists(path):
            try:
                safe_remove(path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"無法刪除原始影片檔案 (可能被播放器鎖定): {str(e)}")
        
        # 2. 如果 final_path 仍存在且與 path 不同，刪除之
        if os.path.exists(final_path) and final_path != path:
            try:
                safe_remove(final_path)
            except Exception:
                pass
                
        # 3. 將臨時檔重新命名為 final_path
        os.rename(temp_output_path, final_path)
        
        # 4. 如果有舊的 _h264 標註檔案，拷貝一份為標準檔名標註檔
        orig_json = os.path.join(dir_name, f"{name}_labels.json")
        h264_json = os.path.join(dir_name, f"{name}_h264_labels.json")
        if os.path.exists(h264_json) and not os.path.exists(orig_json):
            try:
                import shutil
                shutil.copy(h264_json, orig_json)
            except Exception:
                pass
                
        return {"status": "success", "new_path": final_path}
    except Exception as e:
        if os.path.exists(temp_output_path):
            try:
                safe_remove(temp_output_path)
            except Exception:
                pass
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
