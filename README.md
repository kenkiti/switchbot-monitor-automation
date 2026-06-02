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

タスクスケジューラへの登録・再登録は、管理者権限のPowerShellで実行してください。

通常のPowerShellで実行すると、既存タスクの削除時に次のようなエラーが出る場合があります。

```text
Unregister-ScheduledTask : アクセスが拒否されました。
```

タスク登録スクリプトは、`C:\SwitchBot\.venv\Scripts\pythonw.exe` が存在する場合、それを優先して使用します。
`.venv` が存在しない場合は、システムにインストール済みの `pythonw.exe` / `python.exe` を使用します。

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

## 動作確認

タスク登録後、以下を実行して `SwitchBot_ON` と `SwitchBot_OFF` が `Running` になっていることを確認します。

```powershell
cd C:\SwitchBot
powershell -ExecutionPolicy Bypass -File .\scripts\Check_SwitchBot_Status.ps1
```

期待する状態：

```text
TaskName       : SwitchBot_ON
State          : Running

TaskName       : SwitchBot_OFF
State          : Running
```

Pythonプロセスにも、以下の2つが表示されていれば正常です。

```text
pythonw.exe ... C:\SwitchBot\src\SwitchBot_ON.py
pythonw.exe ... C:\SwitchBot\src\SwitchBot_OFF.py
```

ログも確認できます。

```powershell
Get-Content .\logs\SwitchBot_ON.log -Tail 30
Get-Content .\logs\SwitchBot_OFF.log -Tail 30
```

`SwitchBot_ON.log` に `BLE SCANNER STARTED` が出ていれば、BLE監視側が起動しています。

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
- `.lnk` ショートカットファイルはPC環境ごとに異なるため、各PCで手動作成してください。
- CSVログは長期運用で肥大化しやすいため、通常は `enable_csv_log: false` を推奨します。

## ライセンス

MIT License
