#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk
import os, sys, json, datetime

sys.path.insert(0, os.path.dirname(__file__))
from lockscreen import load_config, save_config, DEFAULT_CONFIG

CSS_SETTINGS = """
.preview-box {
    background-color:
    border-radius: 12px;
    padding: 20px;
    min-height: 100px;
}
.preview-clock {
    font-family: "Comic Sans MS", cursive;
    font-size: 36px;
    font-weight: 700;
    color: rgba(255,255,255,0.9);
}
.preview-date {
    font-family: "Comic Sans MS", cursive;
    font-size: 12px;
    color: rgba(255,255,255,0.5);
}
.section-title {
    font-size: 11px;
    font-weight: 700;
    color: rgba(255,255,255,0.4);
    letter-spacing: 1.5px;
}
"""


STRINGS = {
    'ru': {
        'window_title':         'Fancy Lock Screen — Настройки',
        'preview_btn':          '▶  Превью',

        'days':   ['ПОНЕДЕЛЬНИК','ВТОРНИК','СРЕДА','ЧЕТВЕРГ','ПЯТНИЦА','СУББОТА','ВОСКРЕСЕНЬЕ'],
        'months': ['ЯНВАРЯ','ФЕВРАЛЯ','МАРТА','АПРЕЛЯ','МАЯ','ИЮНЯ',
                   'ИЮЛЯ','АВГУСТА','СЕНТЯБРЯ','ОКТЯБРЯ','НОЯБРЯ','ДЕКАБРЯ'],

        'lang_group':           'Язык',
        'lang_row_title':       'Язык интерфейса',
        'lang_row_sub':         'Выберите язык настроек',
        'lang_ru':              'Русский',
        'lang_en':              'English',

        'bg_group':             'Фон',
        'bg_static_title':      'Статичное изображение',
        'bg_static_sub':        'JPG, PNG, WebP — оставьте пустым для чёрного фона',
        'choose':               'Выбрать…',
        'dim_title':            'Затемнение',
        'dim_sub':              '0% — без затемнения, 100% — полностью чёрный',

        'live_group':           'Живые обои (видео / GIF)',
        'live_enable_title':    'Включить живые обои',
        'live_enable_sub':      'Требуется GStreamer (gir1.2-gst-plugins-base-1.0)',
        'live_file_title':      'Файл видео / GIF',
        'live_file_sub':        'MP4, WebM, MKV, GIF…',
        'live_vol_title':       'Громкость',
        'live_vol_sub':         '0% — без звука, 100% — полная громкость',

        'tod_group':            'Фон по времени суток',
        'tod_enable_title':     'Менять фон по времени суток',
        'tod_enable_sub':       'Перекрывает статичный фон. Затемнение подбирается автоматически.',
        'tod_morning':          'Утро (06:00–11:59)',
        'tod_day':              'День (12:00–17:59)',
        'tod_evening':          'Вечер (18:00–21:59)',
        'tod_night':            'Ночь (22:00–05:59)',

        'fx_group':             'Эффекты',
        'blur_title':           'Frosted glass (размытие под карточками)',
        'blur_sub':             'Cairo blur — может немного снижать производительность',

        'w_group':              'Виджеты — включить/выключить',
        'w_spotify_title':      'Spotify',
        'w_spotify_sub':        'Текущий трек через MPRIS DBus',
        'w_vscodium_title':     'VSCodium',
        'w_vscodium_sub':       'Последний изменённый файл',
        'w_sysmon_title':       'Системный монитор',
        'w_sysmon_sub':         'CPU и RAM из /proc',
        'w_notif_title':        'Уведомления',
        'w_notif_sub':          'Перехват через DBus',
        'w_weather_title':      'Погода',
        'w_weather_sub':        'OpenWeatherMap API',
        'w_media_title':        'Медиа-виджет',
        'w_media_sub':          'GIF, WebM, MP4 и другие форматы',
        'w_vscode_path_title':  'Папка проекта VSCodium',
        'w_vscode_path_sub':    'Пусто = автоматически из истории',
        'w_vscode_placeholder': 'Автоматически',

        'media_group':          'Медиа-виджет',
        'media_file_title':     'Файл для медиа-виджета',
        'media_file_sub':       'GIF, WebM, MP4, MKV, AVI, MOV…',

        'weather_group':        'Погода — OpenWeatherMap',
        'weather_api_title':    'API ключ',
        'weather_api_sub':      'Бесплатно на openweathermap.org → API keys',
        'weather_api_ph':       'Вставьте API ключ…',
        'weather_city_title':   'Город',
        'weather_city_sub':     'Например: Moscow, London, Berlin',
        'weather_test_btn':     'Проверить',
        'weather_toast_no_key': 'Введите API ключ!',
        'weather_toast_err':    'Ошибка: ',

        'sys_group':            'Интеграция с системой',
        'install_title':        'Установить как системный скринсейвер',
        'install_sub':          'Заменит стандартный локскрин GNOME',
        'install_btn':          'Установить',
        'uninstall_btn':        'Отключить',
        'toast_installed':      'Установлено! Перезайдите в сессию для активации.',
        'toast_uninstalled':    'Стандартный локскрин восстановлен.',

        'dialog_bg':            'Фоновое изображение',
        'dialog_live':          'Файл живых обоев',
        'dialog_media':         'Медиа-файл для виджета',
        'dialog_folder':        'Папка проекта VSCodium',
        'filter_images':        'Изображения',
        'filter_video':         'Видео / GIF',
        'filter_media':         'Медиа (GIF, видео)',
        'filter_tod':           'Изображение — ',
        'tooltip_clear':        'Убрать',
    },
    'en': {
        'window_title':         'Fancy Lock Screen — Settings',
        'preview_btn':          '▶  Preview',

        'days':   ['MONDAY','TUESDAY','WEDNESDAY','THURSDAY','FRIDAY','SATURDAY','SUNDAY'],
        'months': ['JANUARY','FEBRUARY','MARCH','APRIL','MAY','JUNE',
                   'JULY','AUGUST','SEPTEMBER','OCTOBER','NOVEMBER','DECEMBER'],

        'lang_group':           'Language',
        'lang_row_title':       'Interface language',
        'lang_row_sub':         'Choose the settings language',
        'lang_ru':              'Русский',
        'lang_en':              'English',

        'bg_group':             'Background',
        'bg_static_title':      'Static image',
        'bg_static_sub':        'JPG, PNG, WebP — leave empty for black background',
        'choose':               'Choose…',
        'dim_title':            'Dimming',
        'dim_sub':              '0% — no dimming, 100% — fully black',

        'live_group':           'Live wallpaper (video / GIF)',
        'live_enable_title':    'Enable live wallpaper',
        'live_enable_sub':      'Requires GStreamer (gir1.2-gst-plugins-base-1.0)',
        'live_file_title':      'Video / GIF file',
        'live_file_sub':        'MP4, WebM, MKV, GIF…',
        'live_vol_title':       'Volume',
        'live_vol_sub':         '0% — muted, 100% — full volume',

        'tod_group':            'Time-of-day background',
        'tod_enable_title':     'Change background by time of day',
        'tod_enable_sub':       'Overrides static background. Dimming is set automatically.',
        'tod_morning':          'Morning (06:00–11:59)',
        'tod_day':              'Day (12:00–17:59)',
        'tod_evening':          'Evening (18:00–21:59)',
        'tod_night':            'Night (22:00–05:59)',

        'fx_group':             'Effects',
        'blur_title':           'Frosted glass (blur under cards)',
        'blur_sub':             'Cairo blur — may slightly reduce performance',

        'w_group':              'Widgets — enable / disable',
        'w_spotify_title':      'Spotify',
        'w_spotify_sub':        'Current track via MPRIS DBus',
        'w_vscodium_title':     'VSCodium',
        'w_vscodium_sub':       'Last modified file',
        'w_sysmon_title':       'System monitor',
        'w_sysmon_sub':         'CPU and RAM from /proc',
        'w_notif_title':        'Notifications',
        'w_notif_sub':          'Intercepted via DBus',
        'w_weather_title':      'Weather',
        'w_weather_sub':        'OpenWeatherMap API',
        'w_media_title':        'Media widget',
        'w_media_sub':          'GIF, WebM, MP4 and other formats',
        'w_vscode_path_title':  'VSCodium project folder',
        'w_vscode_path_sub':    'Empty = auto-detect from history',
        'w_vscode_placeholder': 'Auto-detect',

        'media_group':          'Media widget',
        'media_file_title':     'Media widget file',
        'media_file_sub':       'GIF, WebM, MP4, MKV, AVI, MOV…',

        'weather_group':        'Weather — OpenWeatherMap',
        'weather_api_title':    'API key',
        'weather_api_sub':      'Free at openweathermap.org → API keys',
        'weather_api_ph':       'Paste API key…',
        'weather_city_title':   'City',
        'weather_city_sub':     'E.g.: Moscow, London, Berlin',
        'weather_test_btn':     'Test',
        'weather_toast_no_key': 'Please enter an API key!',
        'weather_toast_err':    'Error: ',

        'sys_group':            'System integration',
        'install_title':        'Set as system screen locker',
        'install_sub':          'Replaces the default GNOME lock screen',
        'install_btn':          'Install',
        'uninstall_btn':        'Disable',
        'toast_installed':      'Installed! Re-login to activate.',
        'toast_uninstalled':    'Default lock screen restored.',

        'dialog_bg':            'Background image',
        'dialog_live':          'Live wallpaper file',
        'dialog_media':         'Media widget file',
        'dialog_folder':        'VSCodium project folder',
        'filter_images':        'Images',
        'filter_video':         'Video / GIF',
        'filter_media':         'Media (GIF, video)',
        'filter_tod':           'Image — ',
        'tooltip_clear':        'Clear',
    },
}


class SettingsWindow(Adw.ApplicationWindow):

    def __init__(self, app):
        super().__init__(application=app)
        self.config = load_config()
        self._lang = self.config.get('language', 'ru')
        self.set_default_size(620, 860)
        self.set_resizable(True)
        self._apply_css()
        self._build_ui()

    def _t(self, key):
        """Return translated string for current language."""
        return STRINGS[self._lang].get(key, STRINGS['ru'].get(key, key))

    def _apply_css(self):
        prov = Gtk.CssProvider()
        prov.load_from_string(CSS_SETTINGS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


    def _build_ui(self):
        self.set_title(self._t('window_title'))

        header = Adw.HeaderBar()
        preview_btn = Gtk.Button(label=self._t('preview_btn'))
        preview_btn.add_css_class('suggested-action')
        preview_btn.connect('clicked', self._on_preview)
        header.pack_end(preview_btn)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)

        clamp = Adw.Clamp(maximum_size=580)
        scroll.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        box.set_margin_top(16)
        box.set_margin_bottom(24)
        box.set_margin_start(12)
        box.set_margin_end(12)
        clamp.set_child(box)

        prev_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        prev_box.add_css_class('preview-box')
        prev_box.set_halign(Gtk.Align.CENTER)
        now = datetime.datetime.now()
        self._prev_clock = Gtk.Label(label=now.strftime('%H:%M:%S'))
        self._prev_clock.add_css_class('preview-clock')
        prev_box.append(self._prev_clock)
        days = self._t('days')
        months = self._t('months')
        self._prev_date = Gtk.Label(
            label=f"{days[now.weekday()]}, {now.day} {months[now.month-1]}")
        self._prev_date.add_css_class('preview-date')
        prev_box.append(self._prev_date)
        box.append(prev_box)
        GLib.timeout_add(1000, self._tick_preview)

        lang_group = Adw.PreferencesGroup(title=self._t('lang_group'))
        box.append(lang_group)

        lang_row = Adw.ActionRow(
            title=self._t('lang_row_title'),
            subtitle=self._t('lang_row_sub'))
        lang_group.add(lang_row)

        lang_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        lang_row.add_suffix(lang_box)

        self._btn_ru = Gtk.ToggleButton(label=self._t('lang_ru'))
        self._btn_en = Gtk.ToggleButton(label=self._t('lang_en'),
                                         group=self._btn_ru)
        if self._lang == 'en':
            self._btn_en.set_active(True)
        else:
            self._btn_ru.set_active(True)
        self._btn_ru.connect('toggled', self._on_lang_toggled)
        self._btn_en.connect('toggled', self._on_lang_toggled)
        lang_box.append(self._btn_ru)
        lang_box.append(self._btn_en)

        bg_group = Adw.PreferencesGroup(title=self._t('bg_group'))
        box.append(bg_group)

        img_row = Adw.ActionRow(
            title=self._t('bg_static_title'),
            subtitle=self._t('bg_static_sub'))
        bg_group.add(img_row)
        img_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        img_row.add_suffix(img_box)
        cur = self.config.get('background_image', '')
        self._img_btn = Gtk.Button(label=os.path.basename(cur) if cur else self._t('choose'))
        self._img_btn.add_css_class('suggested-action')
        self._img_btn.connect('clicked', self._choose_image)
        img_box.append(self._img_btn)
        clear_btn = Gtk.Button(icon_name='edit-clear-symbolic',
                               tooltip_text=self._t('tooltip_clear'))
        clear_btn.connect('clicked', lambda _: (
            self.config.update({'background_image': ''}),
            self._img_btn.set_label(self._t('choose')),
            save_config(self.config)))
        img_box.append(clear_btn)

        dim_row = Adw.ActionRow(title=self._t('dim_title'),
                                subtitle=self._t('dim_sub'))
        bg_group.add(dim_row)
        dim_adj = Gtk.Adjustment(lower=0, upper=100, step_increment=1, page_increment=5,
                                 value=round(self.config.get('dim_level', 0.45) * 100))
        dim_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=dim_adj,
                              draw_value=True, digits=0, value_pos=Gtk.PositionType.RIGHT,
                              width_request=200, valign=Gtk.Align.CENTER)
        dim_scale.connect('value-changed', lambda s: (
            self.config.update({'dim_level': s.get_value() / 100}),
            save_config(self.config)))
        dim_row.add_suffix(dim_scale)

        live_group = Adw.PreferencesGroup(title=self._t('live_group'))
        box.append(live_group)

        live_en_row = Adw.SwitchRow(title=self._t('live_enable_title'),
                                    subtitle=self._t('live_enable_sub'))
        live_en_row.set_active(self.config.get('live_wallpaper_enabled', False))
        live_en_row.connect('notify::active', lambda r, _: (
            self.config.update({'live_wallpaper_enabled': r.get_active()}),
            save_config(self.config)))
        live_group.add(live_en_row)

        live_file_row = Adw.ActionRow(title=self._t('live_file_title'),
                                      subtitle=self._t('live_file_sub'))
        live_group.add(live_file_row)
        live_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        live_file_row.add_suffix(live_box)
        cur_live = self.config.get('live_wallpaper', '')
        self._live_btn = Gtk.Button(label=os.path.basename(cur_live) if cur_live else self._t('choose'))
        self._live_btn.connect('clicked', self._choose_live)
        live_box.append(self._live_btn)
        live_clear = Gtk.Button(icon_name='edit-clear-symbolic')
        live_clear.connect('clicked', lambda _: (
            self.config.update({'live_wallpaper': ''}),
            self._live_btn.set_label(self._t('choose')),
            save_config(self.config)))
        live_box.append(live_clear)

        live_vol_row = Adw.ActionRow(title=self._t('live_vol_title'),
                                     subtitle=self._t('live_vol_sub'))
        live_group.add(live_vol_row)
        vol_adj = Gtk.Adjustment(lower=0, upper=100, step_increment=1, page_increment=5,
                                 value=round(self.config.get('live_wallpaper_volume', 0.0) * 100))
        vol_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=vol_adj,
                              draw_value=True, digits=0, value_pos=Gtk.PositionType.RIGHT,
                              width_request=200, valign=Gtk.Align.CENTER)
        vol_scale.connect('value-changed', lambda s: (
            self.config.update({'live_wallpaper_volume': s.get_value() / 100}),
            save_config(self.config)))
        live_vol_row.add_suffix(vol_scale)

        tod_group = Adw.PreferencesGroup(title=self._t('tod_group'))
        box.append(tod_group)

        tod_en_row = Adw.SwitchRow(
            title=self._t('tod_enable_title'),
            subtitle=self._t('tod_enable_sub'))
        tod_en_row.set_active(self.config.get('tod_enabled', False))
        tod_en_row.connect('notify::active', lambda r, _: (
            self.config.update({'tod_enabled': r.get_active()}),
            save_config(self.config)))
        tod_group.add(tod_en_row)

        tod_times = [
            ('tod_morning_image', self._t('tod_morning')),
            ('tod_day_image',     self._t('tod_day')),
            ('tod_evening_image', self._t('tod_evening')),
            ('tod_night_image',   self._t('tod_night')),
        ]
        self._tod_btns = {}
        for key, label in tod_times:
            row = Adw.ActionRow(title=label)
            tod_group.add(row)
            rbox = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
            row.add_suffix(rbox)
            cur_v = self.config.get(key, '')
            btn = Gtk.Button(label=os.path.basename(cur_v) if cur_v else self._t('choose'))
            btn.connect('clicked', self._make_tod_chooser(key, btn))
            rbox.append(btn)
            clr = Gtk.Button(icon_name='edit-clear-symbolic')
            clr.connect('clicked', self._make_tod_clear(key, btn))
            rbox.append(clr)
            self._tod_btns[key] = btn

        fx_group = Adw.PreferencesGroup(title=self._t('fx_group'))
        box.append(fx_group)

        blur_row = Adw.SwitchRow(
            title=self._t('blur_title'),
            subtitle=self._t('blur_sub'))
        blur_row.set_active(self.config.get('frosted_blur', True))
        blur_row.connect('notify::active', lambda r, _: (
            self.config.update({'frosted_blur': r.get_active()}),
            save_config(self.config)))
        fx_group.add(blur_row)

        w_group = Adw.PreferencesGroup(title=self._t('w_group'))
        box.append(w_group)

        for active_key, title_key, sub_key in [
            ('show_spotify',       'w_spotify_title', 'w_spotify_sub'),
            ('show_vscodium',      'w_vscodium_title','w_vscodium_sub'),
            ('show_sysmon',        'w_sysmon_title',  'w_sysmon_sub'),
            ('show_notifications', 'w_notif_title',   'w_notif_sub'),
            ('show_weather',       'w_weather_title', 'w_weather_sub'),
            ('show_media_widget',  'w_media_title',   'w_media_sub'),
        ]:
            row = Adw.SwitchRow(title=self._t(title_key), subtitle=self._t(sub_key))
            row.set_active(self.config.get(active_key, True))
            row.connect('notify::active', self._make_switch_cb(active_key))
            w_group.add(row)

        path_row = Adw.ActionRow(title=self._t('w_vscode_path_title'),
                                 subtitle=self._t('w_vscode_path_sub'))
        w_group.add(path_row)
        path_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        path_row.add_suffix(path_box)
        self._path_entry = Gtk.Entry(
            text=self.config.get('vscodium_project_path', ''),
            placeholder_text=self._t('w_vscode_placeholder'), width_chars=24)
        self._path_entry.connect('changed', lambda e: (
            self.config.update({'vscodium_project_path': e.get_text()}),
            save_config(self.config)))
        path_box.append(self._path_entry)
        browse_btn = Gtk.Button(icon_name='folder-open-symbolic')
        browse_btn.connect('clicked', self._choose_folder)
        path_box.append(browse_btn)

        media_group = Adw.PreferencesGroup(title=self._t('media_group'))
        box.append(media_group)

        media_file_row = Adw.ActionRow(
            title=self._t('media_file_title'),
            subtitle=self._t('media_file_sub'))
        media_group.add(media_file_row)
        media_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        media_file_row.add_suffix(media_box)
        cur_media = self.config.get('media_widget_file', '')
        self._media_btn = Gtk.Button(
            label=os.path.basename(cur_media) if cur_media else self._t('choose'))
        self._media_btn.add_css_class('suggested-action')
        self._media_btn.connect('clicked', self._choose_media_file)
        media_box.append(self._media_btn)
        media_clear = Gtk.Button(icon_name='edit-clear-symbolic',
                                 tooltip_text=self._t('tooltip_clear'))
        media_clear.connect('clicked', lambda _: (
            self.config.update({'media_widget_file': ''}),
            self._media_btn.set_label(self._t('choose')),
            save_config(self.config)))
        media_box.append(media_clear)

        weather_group = Adw.PreferencesGroup(title=self._t('weather_group'))
        box.append(weather_group)

        api_row = Adw.ActionRow(
            title=self._t('weather_api_title'),
            subtitle=self._t('weather_api_sub'))
        weather_group.add(api_row)
        api_box = Gtk.Box(spacing=6, valign=Gtk.Align.CENTER)
        api_row.add_suffix(api_box)
        self._api_entry = Gtk.Entry(
            text=self.config.get('weather_api_key', ''),
            placeholder_text=self._t('weather_api_ph'),
            visibility=False,
            width_chars=28)
        self._api_entry.set_icon_from_icon_name(
            Gtk.EntryIconPosition.SECONDARY, 'view-conceal-symbolic')
        self._api_entry.connect('icon-press',
            lambda e, _: e.set_visibility(not e.get_visibility()))
        self._api_entry.connect('changed', lambda e: (
            self.config.update({'weather_api_key': e.get_text()}),
            save_config(self.config)))
        api_box.append(self._api_entry)

        city_row = Adw.ActionRow(title=self._t('weather_city_title'),
                                 subtitle=self._t('weather_city_sub'))
        weather_group.add(city_row)
        self._city_entry = Gtk.Entry(
            text=self.config.get('weather_city', 'Moscow'),
            placeholder_text='Moscow',
            width_chars=18,
            valign=Gtk.Align.CENTER)
        self._city_entry.connect('changed', lambda e: (
            self.config.update({'weather_city': e.get_text()}),
            save_config(self.config)))
        city_row.add_suffix(self._city_entry)

        test_weather_btn = Gtk.Button(label=self._t('weather_test_btn'),
                                      valign=Gtk.Align.CENTER)
        test_weather_btn.connect('clicked', self._test_weather)
        city_row.add_suffix(test_weather_btn)

        sys_group = Adw.PreferencesGroup(title=self._t('sys_group'))
        box.append(sys_group)

        install_row = Adw.ActionRow(
            title=self._t('install_title'),
            subtitle=self._t('install_sub'))
        sys_group.add(install_row)
        install_btn = Gtk.Button(label=self._t('install_btn'), valign=Gtk.Align.CENTER)
        install_btn.add_css_class('suggested-action')
        install_btn.connect('clicked', self._install_as_locker)
        install_row.add_suffix(install_btn)
        uninst_btn = Gtk.Button(label=self._t('uninstall_btn'), valign=Gtk.Align.CENTER)
        uninst_btn.add_css_class('destructive-action')
        uninst_btn.connect('clicked', self._uninstall_locker)
        install_row.add_suffix(uninst_btn)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.append(header)
        root.append(scroll)
        self.set_content(root)


    def _on_lang_toggled(self, btn):
        if not btn.get_active():
            return
        new_lang = 'en' if btn == self._btn_en else 'ru'
        if new_lang == self._lang:
            return
        self._lang = new_lang
        self.config['language'] = new_lang
        save_config(self.config)
        self._build_ui()


    def _make_switch_cb(self, key):
        def cb(row, _):
            self.config.update({key: row.get_active()})
            save_config(self.config)
        return cb

    def _make_tod_chooser(self, key, btn):
        def cb(_btn):
            dialog = Gtk.FileDialog(title=self._t('filter_tod') + key)
            dialog.set_initial_folder(Gio.File.new_for_path(os.path.expanduser('~')))
            filt = Gtk.FileFilter()
            filt.set_name(self._t('filter_images'))
            for mt in ('image/jpeg','image/png','image/webp'):
                filt.add_mime_type(mt)
            store = Gio.ListStore.new(Gtk.FileFilter)
            store.append(filt)
            dialog.set_filters(store)
            def done(d, res):
                try:
                    f = d.open_finish(res)
                    path = f.get_path()
                    self.config[key] = path
                    save_config(self.config)
                    btn.set_label(os.path.basename(path))
                except Exception:
                    pass
            dialog.open(self, None, done)
        return cb

    def _make_tod_clear(self, key, btn):
        def cb(_):
            self.config[key] = ''
            save_config(self.config)
            btn.set_label(self._t('choose'))
        return cb

    def _choose_image(self, _btn):
        dialog = Gtk.FileDialog(title=self._t('dialog_bg'))
        dialog.set_initial_folder(Gio.File.new_for_path(os.path.expanduser('~')))
        filt = Gtk.FileFilter()
        filt.set_name(self._t('filter_images'))
        for mt in ('image/jpeg','image/png','image/webp'):
            filt.add_mime_type(mt)
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(filt)
        dialog.set_filters(store)
        dialog.open(self, None, self._on_image_chosen)

    def _on_image_chosen(self, dialog, result):
        try:
            f = dialog.open_finish(result)
            path = f.get_path()
            self.config['background_image'] = path
            save_config(self.config)
            self._img_btn.set_label(os.path.basename(path))
        except Exception:
            pass

    def _choose_live(self, _btn):
        dialog = Gtk.FileDialog(title=self._t('dialog_live'))
        dialog.set_initial_folder(Gio.File.new_for_path(os.path.expanduser('~')))
        filt = Gtk.FileFilter()
        filt.set_name(self._t('filter_video'))
        for mt in ('video/mp4','video/webm','video/x-matroska',
                   'image/gif','video/avi','video/quicktime'):
            filt.add_mime_type(mt)
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(filt)
        dialog.set_filters(store)
        def done(d, res):
            try:
                f = d.open_finish(res)
                path = f.get_path()
                self.config['live_wallpaper'] = path
                save_config(self.config)
                self._live_btn.set_label(os.path.basename(path))
            except Exception:
                pass
        dialog.open(self, None, done)

    def _choose_media_file(self, _btn):
        dialog = Gtk.FileDialog(title=self._t('dialog_media'))
        dialog.set_initial_folder(Gio.File.new_for_path(os.path.expanduser('~')))
        filt = Gtk.FileFilter()
        filt.set_name(self._t('filter_media'))
        for mt in ('image/gif', 'video/mp4', 'video/webm', 'video/x-matroska',
                   'video/avi', 'video/quicktime', 'video/x-msvideo'):
            filt.add_mime_type(mt)
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(filt)
        dialog.set_filters(store)
        def done(d, res):
            try:
                f = d.open_finish(res)
                path = f.get_path()
                self.config['media_widget_file'] = path
                save_config(self.config)
                self._media_btn.set_label(os.path.basename(path))
            except Exception:
                pass
        dialog.open(self, None, done)

    def _choose_folder(self, _btn):
        dialog = Gtk.FileDialog(title=self._t('dialog_folder'))
        dialog.select_folder(self, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog, result):
        try:
            f = dialog.select_folder_finish(result)
            path = f.get_path()
            self.config['vscodium_project_path'] = path
            save_config(self.config)
            self._path_entry.set_text(path)
        except Exception:
            pass

    def _test_weather(self, _btn):
        api_key = self.config.get('weather_api_key', '')
        city = self.config.get('weather_city', 'Moscow')
        if not api_key:
            self._show_toast(self._t('weather_toast_no_key'))
            return
        import threading
        def fetch():
            try:
                import urllib.request, urllib.parse
                city_enc = urllib.parse.quote(city)
                url = (f'https://api.openweathermap.org/data/2.5/weather'
                       f'?q={city_enc}&appid={api_key}&units=metric&lang=ru')
                with urllib.request.urlopen(url, timeout=6) as r:
                    data = __import__('json').loads(r.read())
                temp = round(data['main']['temp'])
                desc = data['weather'][0]['description']
                name = data.get('name', city)
                GLib.idle_add(self._show_toast, f'{name}: {temp}°C, {desc}')
            except Exception as e:
                GLib.idle_add(self._show_toast, self._t('weather_toast_err') + str(e))
        threading.Thread(target=fetch, daemon=True).start()

    def _tick_preview(self):
        now = datetime.datetime.now()
        self._prev_clock.set_label(now.strftime('%H:%M:%S'))
        return GLib.SOURCE_CONTINUE

    def _on_preview(self, _btn):
        script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'lockscreen.py'))
        import subprocess
        subprocess.Popen(['python3', script])

    def _install_as_locker(self, _btn):
        script_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), 'lockscreen.py'))
        wrapper = os.path.expanduser('~/.local/bin/fancy-lockscreen')
        os.makedirs(os.path.dirname(wrapper), exist_ok=True)
        with open(wrapper, 'w') as f:
            f.write(f'#!/bin/bash\nexec python3 "{script_path}" "$@"\n')
        os.chmod(wrapper, 0o755)
        os.system(f'gsettings set org.gnome.desktop.screensaver lock-command "{wrapper}"')
        desktop_dir = os.path.expanduser('~/.config/autostart')
        os.makedirs(desktop_dir, exist_ok=True)
        with open(os.path.join(desktop_dir, 'fancy-lockscreen.desktop'), 'w') as f:
            f.write(f'[Desktop Entry]\nName=Fancy Lock Screen\nExec={wrapper}\nType=Application\n')
        self._show_toast(self._t('toast_installed'))

    def _uninstall_locker(self, _btn):
        for p in [
            os.path.expanduser('~/.local/bin/fancy-lockscreen'),
            os.path.expanduser('~/.config/autostart/fancy-lockscreen.desktop'),
        ]:
            if os.path.exists(p): os.remove(p)
        os.system('gsettings reset org.gnome.desktop.screensaver lock-command')
        self._show_toast(self._t('toast_uninstalled'))

    def _show_toast(self, msg):
        dialog = Adw.AlertDialog(heading='Fancy Lock Screen', body=msg)
        dialog.add_response('ok', 'OK')
        dialog.present(self)


class SettingsApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.fancy-lockscreen.settings',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        SettingsWindow(self).present()


if __name__ == '__main__':
    sys.exit(SettingsApp().run(sys.argv))

