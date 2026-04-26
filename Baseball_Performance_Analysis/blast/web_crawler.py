import requests
import pandas as pd
import time
import random
import json

# ==========================================
# 1. 貼上你剛剛抓到的完美 Headers
# ==========================================
headers = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    # 注意：請將 Bearer Token 存放在環境變數或安全位置，不要直接寫在程式碼中
    "authorization": "Bearer YOUR_TOKEN_HERE",
    "cookie": "YOUR_COOKIE_HERE",
    "referer": "https://baseball-academy.blastconnect.com/insights",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest"
}

# ==========================================
# 2. 直接貼上整包 Session 的 JSON 回傳結果
# 請把整段 JSON 貼在三個雙引號 """ 中間
# ==========================================
sessions_json_raw = """
{
    "data": [
        {
            "group": "2026-03-25",
            "sessions": [
                {
                    "id": 4474096,
                    "name": "\u6253\u597d\u73a9",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474097,
                    "name": "020",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474098,
                    "name": "021",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474099,
                    "name": "007",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474100,
                    "name": "018",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474101,
                    "name": "011",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474102,
                    "name": "008",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474103,
                    "name": "002",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474104,
                    "name": "038",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474105,
                    "name": "030",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474106,
                    "name": "024",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474107,
                    "name": "028",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474108,
                    "name": "037",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474109,
                    "name": "001",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474110,
                    "name": "026",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474111,
                    "name": "035",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474112,
                    "name": "027",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474113,
                    "name": "014",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474114,
                    "name": "031",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474115,
                    "name": "005",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474116,
                    "name": "003",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474117,
                    "name": "040",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474118,
                    "name": "022",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474119,
                    "name": "006",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474120,
                    "name": "004",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474121,
                    "name": "025",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474122,
                    "name": "041",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474123,
                    "name": "034",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474124,
                    "name": "036",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474125,
                    "name": "033",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474126,
                    "name": "012",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474127,
                    "name": "010",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474128,
                    "name": "013",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474129,
                    "name": "017",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474130,
                    "name": "039",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474131,
                    "name": "019",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474132,
                    "name": "009",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474133,
                    "name": "029",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474134,
                    "name": "015",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474135,
                    "name": "032",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474136,
                    "name": "016",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474137,
                    "name": "Wed, Mar 25 at 4:16\u202fPM",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474138,
                    "name": "Test2",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474139,
                    "name": "Test",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                },
                {
                    "id": 4474140,
                    "name": "\u6e2c\u8a66",
                    "session_type_id": null,
                    "date": "2026-03-25",
                    "initiated_by_you": true,
                    "participants": [
                        {
                            "id": 533499,
                            "name": "\u7d39\u8fb0 \u674e"
                        }
                    ]
                }
            ]
        }
    ]
}
"""

# 自動解析 JSON 並建立 {ID: Name} 對照表
session_dict = {}
try:
    parsed_json = json.loads(sessions_json_raw)
    # 歷遍所有日期群組 (group) 裡面的 sessions
    for group in parsed_json.get('data', []):
        for session in group.get('sessions', []):
            session_dict[session['id']] = session['name']
    print(f"成功載入 Session 列表！共找到 {len(session_dict)} 位球員。")
except Exception as e:
    print(f"JSON 解析失敗，請檢查格式是否完整貼上: {e}")

# ==========================================
# 3. 設定撈取資料的 API 網址 (per_page 設為 100)
# ==========================================
base_api_url = "https://baseball-academy.blastconnect.com/api/v3/insights/533499/metrics?action_type=swing&context_constraint[]=all&context_environment[]=all&context_pitch_location[]=all&context_pitch_type[]=all&context_slap_type[]=all&date[]=2026-03-11&date[]=2026-03-25&impact_type=impact&order=descending&page=1&per_page=100&score=true&sort_by=swing&sport=baseball&swing_type=swings_with_impact&videos_only=false"

all_swings_data = []

print("開始安全抓取資料，請耐心等候...\n")

for session_id, player_name in session_dict.items():
    print(f"正在撈取球員: {player_name} (Session: {session_id})...", end="")
    
    # 組合網址，把 session_id 塞進去
    target_url = f"{base_api_url}&sessions[]={session_id}"
    
    try:
        response = requests.get(target_url, headers=headers)
        response.raise_for_status() 
        
        json_data = response.json()
        swings = json_data.get('data', {}).get('data', [])
        
        # 解析每一顆球的資料
        for swing in swings:
            metrics = swing.get('metrics', {})
            
            swing_record = {
                "球員編號": player_name,
                "日期時間": f"{swing.get('created_at', {}).get('date', '')} {swing.get('created_at', {}).get('time', '')}",
                "Bat Path Angle": metrics.get('bat_path_angle', {}).get('value', ''),
                "Swing Speed (mph)": metrics.get('swing_speed', {}).get('value', ''),
                "Blast Factor": metrics.get('blast_factor_2', {}).get('value', ''),
                "Connection": metrics.get('connection', {}).get('value', ''),
                "Early Connection": metrics.get('early_connection', {}).get('value', ''),
                "Body Rotation (%)": metrics.get('body_rotation', {}).get('value', ''),
                "Body Tilt Angle": metrics.get('body_tilt_angle', {}).get('value', ''),
                "Commit Time (sec)": metrics.get('commit_time', {}).get('value', ''),
                "On Plane (%)": metrics.get('on_plane', {}).get('value', ''),
                "Peak Speed": metrics.get('peak_speed', {}).get('value', ''),
                "Peak Hand Speed": metrics.get('peak_hand_speed', {}).get('value', ''),
                "Planar Efficiency (%)": metrics.get('planar_efficiency', {}).get('value', ''),
                "Power (kW)": metrics.get('power', {}).get('value', ''),
                "Rotational Accel (g)": metrics.get('rotational_acceleration', {}).get('value', ''),
                "Time to Contact (sec)": metrics.get('time_to_contact', {}).get('value', ''),
                "Vertical Bat Angle": metrics.get('vertical_bat_angle', {}).get('value', ''),
            }
            all_swings_data.append(swing_record)
        print(f" 完成 (共 {len(swings)} 筆)")
            
    except Exception as e:
        print(f" 失敗! 錯誤訊息: {e}")

    # ==========================================
    # 安全守則：隨機暫停 1.5 到 3 秒鐘，假裝是人類
    # ==========================================
    sleep_time = random.uniform(1.5, 3.0)
    time.sleep(sleep_time)

# ==========================================
# 4. 輸出成 CSV 報表
# ==========================================
if all_swings_data:
    df = pd.DataFrame(all_swings_data)
    df = df.sort_values(by=['球員編號', '日期時間'])
    
    output_filename = "blast_baseball_swings.csv"
    # 用 utf-8-sig 讓 Excel 開起來不會變亂碼
    df.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print(f"\n✅ 抓取大功告成！總共取得 {len(df)} 筆揮棒紀錄。")
    print(f"檔案已儲存為: {output_filename}")
else:
    print("\n沒有抓到任何資料，請確認 Token 是否過期。")