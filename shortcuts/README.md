# shortcuts フォルダ

このフォルダには、モニタ復帰時に起動したいアプリのショートカットを配置します。

例：

```text
shortcuts\antigravity.lnk
```

`.lnk` ファイルはPC環境依存のためGit管理しません。
必要なPCごとに手動で作成してください。

ショートカットの相対パスは `config\switchbot_config.json` の `wake_shortcut` で指定します。
