# switchbot-monitor-automation

Windows monitor sleep/wake automation using SwitchBot Motion Sensor BLE and idle-time detection.

このプロジェクトは、Windowsの入力アイドル時間とSwitchBot人感センサーProのBLE広告を使い、PCモニタの自動OFF・自動復帰を行うためのスクリプト群です。

## 主な機能

- Windowsの入力アイドル時間が設定値を超えたら、モニタをOFFにする
- SwitchBot人感センサーProのBLEカウンターリセットを検出したら、モニタを復帰させる
- `away_mode` を使い、在席中の不要な復帰処理を防ぐ
- Windowsタスクスケジューラで常駐実行する
- BLE監視の長期固着を避けるため、1日1回タスクを自動再起動する

## 仕組み

- `SwitchBot_OFF.py`
  - Windowsの入力アイドル時間を確認する
  - モニタをOFFにする
  - `away_mode = true` にする

- `SwitchBot_ON.py`
  - SwitchBotのBLE広告を監視する
  - BLEカウンターリセットを検出する
  - `away_mode = true` のときだけモニタを復帰させる

## フォルダ構成

```text
C:\SwitchBot
├─ src\
│  ├─ SwitchBot_ON.py
│  └─ SwitchBot_OFF.py
├─ scripts\
├─ config\
│  └─ switchbot_config.example.json
├─ state\
├─ logs\
└─ shortcuts\
```

## 必要環境

- Windows
- Python 3.10 or later
- SwitchBot Motion Sensor Pro
- Bluetooth adapter supported by Windows
- PowerShell
- Windows Task Scheduler

## セットアップ

```powershell
cd C:\SwitchBot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create your local config file:

```powershell
Copy-Item .\config\switchbot_config.example.json .\config\switchbot_config.json
notepad .\config\switchbot_config.json
```

Example config:

```json
{
  "target_mac": "AA:BB:CC:DD:EE:FF",
  "idle_minutes": 10,
  "enable_csv_log": false,
  "wake_shortcut": "shortcuts/antigravity.lnk",
  "daily_restart_time": "05:00"
}
```

## タスクスケジューラ登録

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Register_SwitchBot_Tasks.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\Register_SwitchBot_DailyRestart.ps1
```

起動:

```powershell
Start-ScheduledTask -TaskName "SwitchBot_ON"
Start-ScheduledTask -TaskName "SwitchBot_OFF"
```

状態確認:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Check_SwitchBot_Status.ps1
```

停止:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Stop_SwitchBot_Processes.ps1
```

再起動:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Restart_SwitchBot_Tasks_Silent.ps1
```

ログ監視:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Watch_SwitchBot_Logs.ps1
```

## 補足

- 実機のSwitchBot MACアドレスは、`config\switchbot_config.json` にのみ記載してください。
- `config\switchbot_config.json` はローカル専用ファイルです。Gitにコミットしないでください。
- `.lnk` ショートカットファイルはPC環境ごとに異なるため、各PCで手動作成してください。
- CSVログは長期運用で肥大化しやすいため、通常は `enable_csv_log: false` を推奨します。

## ライセンス

MIT License
