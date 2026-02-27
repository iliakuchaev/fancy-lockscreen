#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/fancy-lockscreen"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🔒 Fancy Lock Screen — Install"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🔍 Checking dependencies..."

python3 -c "import gi; gi.require_version('Gtk','4.0')" 2>/dev/null \
    && echo "  ✓ GTK4 (PyGObject)" \
    || { echo "  ✗ PyGObject not found. Install: sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1"; exit 1; }

python3 -c "import dbus" 2>/dev/null \
    && echo "  ✓ dbus-python" \
    || { echo "  ✗ dbus-python not found. Install: sudo apt install python3-dbus"; exit 1; }

echo ""

echo "📁 Copying files to $INSTALL_DIR ..."
mkdir -p "$INSTALL_DIR"
cp -r "$SCRIPT_DIR"/. "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/lockscreen.py"
chmod +x "$INSTALL_DIR/settings.py"

mkdir -p "$BIN_DIR"

cat > "$BIN_DIR/fancy-lockscreen" << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/lockscreen.py" "\$@"
EOF
chmod +x "$BIN_DIR/fancy-lockscreen"

cat > "$BIN_DIR/fancy-lockscreen-settings" << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/settings.py" "\$@"
EOF
chmod +x "$BIN_DIR/fancy-lockscreen-settings"

echo "  ✓ ~/.local/bin/fancy-lockscreen"
echo "  ✓ ~/.local/bin/fancy-lockscreen-settings"

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_DIR/fancy-lockscreen-settings.desktop" << EOF
[Desktop Entry]
Name=Fancy Lock Screen — Settings
Comment=Settings for Fancy Lock Screen
Exec=$BIN_DIR/fancy-lockscreen-settings
Icon=system-lock-screen
Terminal=false
Type=Application
Categories=Settings;GNOME;
EOF

echo "  ✓ App menu shortcut created"

if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
    echo ""
    echo "⚠️  ~/.local/bin is not in PATH. Add to ~/.bashrc or ~/.zshrc:"
    echo "   export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Installation complete!"
echo ""
echo "  Commands:"
echo "    fancy-lockscreen             — run lock screen"
echo "    fancy-lockscreen-settings    — open settings"
echo ""
echo "  In settings press 'Install' to replace"
echo "  the default GNOME lock screen."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
