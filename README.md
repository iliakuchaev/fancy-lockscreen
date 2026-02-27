Fancy Lock Screen

A beautiful, fully customizable lock screen for GNOME — built with GTK4 and Python.
Supports English and Russian interface. Replaces the default GNOME lock screen.

---

Features

- **Clock** — seconds-precise, styled font
- **Date** — localized (Russian / English)
- **Spotify** — current track, artist, album art, progress bar, EQ animation via DBus MPRIS
- **VSCodium** — last modified file with syntax-colored code snippet
- **Weather** — current + tomorrow via OpenWeatherMap API
- **System monitor** — CPU, RAM, Disk, Network, top processes
- **Notifications** — intercepted via DBus
- **Media widget** — looped GIF / MP4 / WebM (GStreamer)
- **Static background** — JPG / PNG / WebP
- **Time-of-day backgrounds** — different image per time period
- **Live wallpaper** — looped video background with volume control
- **Frosted glass** — Cairo blur under cards
- **Language switcher** — RU / EN in settings, applied instantly
- **Settings app** — separate Adwaita GUI, no config file editing needed

---

Dependencies


# Ubuntu / Debian
sudo apt install python3-gi python3-dbus \
     gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-gdkpixbuf-2.0 \
     gstreamer1.0-plugins-good gstreamer1.0-plugins-bad \
     gir1.2-gst-plugins-base-1.0 gir1.2-gstreamer-1.0

# Arch
sudo pacman -S python-gobject python-dbus gtk4 libadwaita \
     gstreamer gst-plugins-good gst-plugins-bad


**Optional** (for system monitor):

pip install psutil --break-system-packages


---

Installation

git clone https://github.com/YOUR_USERNAME/fancy-lockscreen.git
cd fancy-lockscreen
chmod +x install.sh
./install.sh


After install:

fancy-lockscreen-settings    # open settings, configure background, widgets, language
fancy-lockscreen             # test run

In settings, press **"Install"** under *System Integration* to replace the GNOME lock screen.  
Re-login to activate.

---

Customization

All styles are in the `CSS` variable inside `lockscreen.py` — standard GTK CSS:


.clock-label { font-size: 88px; color: rgba(100, 200, 255, 0.95); }
.card        { background-color: rgba(20, 0, 40, 0.8); }


To add a new widget, add a `_build_xxx_card()` method following the Spotify/VSCodium pattern.

---

Structure


fancy-lockscreen/
├── lockscreen.py      — main window, clock, widgets, unlock logic
├── settings.py        — settings GUI (GTK4 + Adwaita)
├── install.sh         — installer
├── setup.sh           — register as desktop app (for inhibit permission)
└── README.md

Config is stored at `~/.config/fancy-lockscreen/config.json`.

---

Uninstall

Open settings and press **"Disable"** — this restores the default GNOME lock screen.

To fully remove:
rm -rf ~/.local/share/fancy-lockscreen
rm ~/.local/bin/fancy-lockscreen ~/.local/bin/fancy-lockscreen-settings
rm ~/.local/share/applications/fancy-lockscreen-settings.desktop
rm -rf ~/.config/fancy-lockscreen
