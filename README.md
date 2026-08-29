# Minesweeper Neon Protocol — Rebuilt Edition

این نسخه از پایه بازنویسی شده تا مشکل eventهای Canvas، Settings و Sound برطرف شود.

## امکانات
- Main Menu
- Difficulty
- Custom Board
- Click / Right Click / Chord
- Hint
- Pause
- Undo / Redo
- Themes
- XP / Level / Coins
- Achievements
- Leaderboard
- Reset Progress
- Sound Effects
- ذخیره تنظیمات

## اجرا
```bash
python minesweeper_aaa.py
```

## Reset
از Main Menu یا Settings می‌توان `RESET PROGRESS` را انتخاب کرد. این گزینه XP، Level، Coins، Achievements و Leaderboard را پاک می‌کند.

## تبدیل به EXE
برای ویندوز می‌توان با PyInstaller نسخه مستقل ساخت:
```bash
pip install pyinstaller
pyinstaller --noconsole --onedir --name MinesweeperNeonProtocol --add-data "sounds;sounds" minesweeper_aaa.py
```
فایل اجرایی در پوشه `dist/MinesweeperNeonProtocol` ساخته می‌شود و روی سیستم مقصد به Python نیاز ندارد.
