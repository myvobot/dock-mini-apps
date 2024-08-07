# minidock_webcam
Webcam app for the Vobot MiniDock

This is a sleek webcam application powered by the LVGL graphics library.
You can configure up to 5 webcams in the vobot's application settings screen.
This app provides a distraction-free interface for users to browse through 
user's configured webcams. With an encoder knob, users can effortlessly 
switch between different webcams, allowing them to 
watch different places of the earth in real time with ease.

Due to limited processing power, expect around 1 image per second. 
This obviously depends largely on the speed of your webcam and your network bandwidth.

Please note, that images cannot be scaled due to limited processing power. The URLs you provide must 
present a JPEG image (not MJPEG or any other format) in 320x240 pixels resolution.

# Installation

1. Create a new directory `webcam` inside the `apps` directory of your Minidock.
2. Copy all files and directories into this `webcam` directory.
3. Restart your Vobot Minidock.

For more details, please read [https://github.com/myvobot/dock-mini-apps/blob/main/README.md](https://github.com/myvobot/dock-mini-apps/blob/main/README.md)

# Development

Install `black` and `pre-commit` for the pre-commit-hooks.

On Mac you can use:
```bash
brew install black pre-commit
```

On other system, please use:
```bash
pip install black pre-commit
```

