# switchbot-monitor-automation

Windows monitor sleep/wake automation using SwitchBot Motion Sensor BLE and idle-time detection.

This project turns off a Windows monitor after user inactivity, then wakes it when a SwitchBot Motion Sensor Pro BLE counter reset is detected.

このプロジェクトは、Windowsの入力アイドル時間とSwitchBot人感センサーProのBLE広告を使い、PCモニタの自動OFF・自動復帰を行うためのスクリプト群です。

Repository: https://github.com/kenkiti/switchbot-monitor-automation

## 概要

Windowsの入力アイドル時間を監視して離席状態を記録し、SwitchBot人感センサーProのBLE広告を監視して復帰処理を行います。

## 主な機能

- モニタOFF判定は Windows の入力アイドル時間で行う
- モニタ復帰判定は SwitchBot 人感センサーPro の BLE カウンターリセットで行う
- `away_mode = true` のときだけ復帰処理を行う
- Plug の ON/OFF は復帰条件に使わない
- PS4コントローラー関連処理は使わない
- CSV詳細ログは通常無効
- BLE監視の長期固着対策として、1日1回タスクを再起動する

## 仕組み

`SwitchBot_OFF.py` がWindowsの入力アイドル時間を確認し、設定時間を超えるとモニタをOFFにして `away_mode` を有効化します。

`SwitchBot_ON.py` はBLE広告を監視します。対象センサーのカウンターリセットを検出し、かつ `away_mode = true` の場合に、入力イベントと設定済みショートカットによる復帰処理を実行します。

## フォルダ構成

```text
C:\SwitchBot
├─ README.md
├─ requirements.txt
├─ .gitignore
├─ src\
│  ├─ SwitchBot_ON.py
│  └─ SwitchBot_OFF.py
├─ scripts\
│  ├─ Register_SwitchBot_Tasks.ps1
│  ├─ Unregister_SwitchBot_Tasks.ps1
│  ├─ Stop_SwitchBot_Processes.ps1
│  ├─ Check_SwitchBot_Status.ps1
│  ├─ Watch_SwitchBot_Logs.ps1
│  ├─ Restart_SwitchBot_Tasks_Silent.ps1
│  ├─ Restart_SwitchBot_Tasks_Admin.ps1
│  └─ Register_SwitchBot_DailyRestart.ps1
├─ config\
│  ├─ switchbot_config.example.json
│  └─ switchbot_config.json
├─ state\
│  └─ switchbot_state.json
├─ logs\
│  ├─ SwitchBot_ON.log
│  ├─ SwitchBot_OFF.log
│  └─ Restart_SwitchBot_Tasks.log
└─ shortcuts\
   └─ antigravity.lnk
```

`Restart_SwitchBot_Tasks_Admin.ps1` は環境によって存在しない場合があります。

## 必要環境

- Windows
- Python 3
- PowerShell
- Bluetooth Low Energyを利用できるPC
- SwitchBot人感センサーPro

## セットアップ

```powershell
cd C:\SwitchBot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

実行用configを作成して編集します。

```powershell
Copy-Item .\config\switchbot_config.example.json .\config\switchbot_config.json
notepad .\config\switchbot_config.json
```

復帰時に起動するショートカットを利用する場合は、`shortcuts` フォルダへ手動で配置します。

## config設定

```json
{
  "target_mac": "AA:BB:CC:DD:EE:FF",
  "idle_minutes": 10,
  "enable_csv_log": false,
  "wake_shortcut": "shortcuts/antigravity.lnk",
  "daily_restart_time": "05:00"
}
```

- `target_mac`: SwitchBot人感センサーProのBLE MACアドレス
- `idle_minutes`: Windows操作がない状態を何分で離席扱いにするか
- `enable_csv_log`: BLE詳細CSVログを出力するかどうか。通常は `false` 推奨
- `wake_shortcut`: 復帰時に起動するショートカットのパス
- `daily_restart_time`: 毎日再起動タスクの時刻。現在はconfig上の記録用で、PowerShell側では固定値を使う場合があります

## タスクスケジューラ登録

仮想環境を有効化したPowerShellで実行してください。タスク名は `SwitchBot_ON`、`SwitchBot_OFF`、`SwitchBot_DailyRestart` です。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Register_SwitchBot_Tasks.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\Register_SwitchBot_DailyRestart.ps1
```

## 起動・停止・再起動

起動：

```powershell
Start-ScheduledTask -TaskName "SwitchBot_ON"
Start-ScheduledTask -TaskName "SwitchBot_OFF"
```

状態確認：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Check_SwitchBot_Status.ps1
```

停止：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Stop_SwitchBot_Processes.ps1
```

再起動：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Restart_SwitchBot_Tasks_Silent.ps1
```

## ログ確認

ログ監視：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Watch_SwitchBot_Logs.ps1
```

ログは `logs` フォルダに出力されます。CSV詳細ログは通常無効です。

## Git管理対象外ファイル

次のファイルは実行環境固有または実行時生成物のため、Git管理しません。

```text
config\switchbot_config.json
state\switchbot_state.json
logs\*.log
logs\*.csv
shortcuts\*.lnk
trash\
.venv\
__pycache__\
```

## 注意事項

- `config\switchbot_config.json` に実機MACアドレスを設定してください。
- 実機MACアドレスやローカルconfigをGitへ追加しないでください。
- ショートカットはPCごとに作成してください。
- タスク登録スクリプトは、登録時に解決されたPython実行ファイルを使用します。

## トラブルシュート

状態確認スクリプトを実行します。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Check_SwitchBot_Status.ps1
```

BLE監視が起動しない場合は、仮想環境を有効化して依存関係を再確認します。

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python .\src\SwitchBot_ON.py
```

ログ監視で状況を確認します。

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Watch_SwitchBot_Logs.ps1
```

## ライセンス

ライセンスを公開前に設定してください。
