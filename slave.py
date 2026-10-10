"""
Slave - PC check tool (Windows)  |  TR / EN / RU / UK
Developed by killeremperor

Two tools in one app:
  1) Browse Tool       : searches files with Everything (es.exe or HTTP server)
  2) Data usage check  : shows per-application data usage and filters it with its own lists

Config system:
  - Each tool has its OWN configs (Browse configs and Data usage configs are separate)
  - "Default" config = built-in list, cannot be edited or deleted
  - Create new / Load / Edit / Delete your own configs
  - Everything is stored in slave_config.json next to this file

Requirements for Browse Tool (one is enough):
  1) Everything + es.exe next to this file / in PATH / in the Everything folder
     (Everything is started automatically when it is installed but not running)
  2) or Everything > Options > HTTP Server enabled (port 8080)

Run: python slave_scanner.py
"""

import ctypes
import hashlib
import hmac
import importlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.parse
import urllib.request
import wave
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

try:
    import winsound
except ImportError:
    winsound = None

Image = ImageFilter = ImageTk = None
PIL_OK = False
PIL_ERR = ""


def try_import_pil():
    global Image, ImageFilter, ImageTk, PIL_OK, PIL_ERR
    try:
        importlib.invalidate_caches()
        from PIL import Image as _I, ImageFilter as _F, ImageTk as _T
        Image, ImageFilter, ImageTk = _I, _F, _T
        PIL_OK, PIL_ERR = True, ""
    except Exception as e:
        PIL_OK, PIL_ERR = False, f"{type(e).__name__}: {e}"
    return PIL_OK


try_import_pil()

AUTHOR = "killeremperor"
CREDIT = f"developed by {AUTHOR}"
DEFAULT_CFG = "Default"
DEFAULT_NAMES = [
    "Potassium", "Volt", "Matcha", "Velocity", "Real", "Solara", "Xeno", "Wave",
    "Serotonin", "Lumen", "Macsploit", "Severe", "Delta", "Madium", "Vega X",
    "Seliware", "Aimmy", "Exoliner",
    "Mapper", "bootstrapper", "loader", "loader.exe", "updater", "updater.exe",
    "loader.zip", "vexor", "matrix", "imgui", "ronix", "drift", "drift_executor",
    "photon", "bauix",
]
DATA_DEFAULT_NAMES = list(DEFAULT_NAMES)
MAX_RESULTS = 300
HTTP_URL = "http://127.0.0.1:8080"
PER_ROW = 6
AUTO_SECONDS = 5
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "slave_config.json")

SYS_RE = re.compile(r"^[a-z]:\\(windows|program files\\windowsapps)\\", re.I)
LANGS = ("tr", "en", "ru", "uk")

TXT = {
    "tr": {
        "status_ready": "hazır", "status_error": "hata",
        "status_scanning": "taranıyor · {0} ({1}/{2})",
        "scan": "Tara", "stop": "Durdur",
        "logs_title": "LOGS", "close": "Kapat", "copy": "Kopyala", "clear": "Temizle",
        "tab_browse": "Browse Tool", "tab_data": "Data usage check",
        "cfg_label": "CONFIG (yükle)", "cfg_new": "Yeni oluştur", "cfg_edit": "Listeyi düzenle",
        "cfg_del": "Sil",
        "names_head": "ARANACAK İSİMLER", "names_hint": "kutu açık = bu config'te aranır",
        "all_on": "Hepsini aç", "all_off": "Hepsini kapat",
        "search": "Ara",
        "entry_hint": "«Ara» sadece yazdığını arar (hiçbir config'e eklemez) · birden fazlası için virgülle ayır · liste değiştirmek için «Listeyi düzenle»",
        "ck_sys": "Windows sistem klasörlerini gizle",
        "ck_whole": "Tam kelime eşleşmesi (yeniden tarar)",
        "col_kw": "İsim", "col_name": "Dosya", "col_path": "Konum", "col_size": "Boyut", "col_date": "Tarih",
        "show": "Klasörde göster", "copy_path": "Yolu kopyala", "export": "TXT'ye aktar",
        "summary": "{0} sonuç gösteriliyor  ·  toplam {1}",
        "notice_none": "Aranacak isim seçili değil.\n\nYukarıdan bir ismi aç ya da bir şey yazıp 'Ara'ya bas.",
        "notice_nomatch": "Hiçbir eşleşme bulunamadı.",
        "notice_setup": ("Everything'e ulaşılamadı.\n\n"
                         "1) Everything programını aç (arka planda çalışıyor olmalı)\n"
                         "2) es.exe'yi (voidtools.com → ES komut satırı aracı) bu programın klasörüne koy\n"
                         "    ya da Everything → Seçenekler → HTTP Sunucusu'nu aç (port 8080)\n\n"
                         "Sonra sağ üstteki 'Tara' düğmesine bas.\n"
                         "Ayrıntı için Logs panelinden bak."),
        "ed_title_new": "Yeni config", "ed_title_edit": "Config düzenle",
        "ed_name": "Config adı", "ed_add_label": "Listeye yeni isim ekle (birden fazlası için virgül)",
        "ed_add": "Ekle", "ed_remove": "Seçileni sil", "ed_save": "Kaydet", "ed_cancel": "İptal",
        "ed_copy": "Mevcut listeden başla", "ed_names": "İsimler ({0})",
        "ed_readonly": "Default config değiştirilemez.\n«Yeni oluştur» ile kendi configini yapabilirsin.",
        "err_name_empty": "Config adı boş olamaz.",
        "err_name_exists": "Bu isimde bir config zaten var.",
        "del_confirm": "'{0}' configi silinsin mi?", "del_default": "Default config silinemez.",
        "log_cfg_loaded": "Config yüklendi: {0}", "log_cfg_saved": "Config kaydedildi: {0}",
        "log_cfg_deleted": "Config silindi: {0}",
        "d_refresh": "Yenile", "d_auto": "Otomatik yenile ({0} sn)",
        "d_only_list": "Sadece config listesindekiler",
        "d_search_hint": "Yaz ve filtrele (virgülle ayır) · boş bırakırsan config listesi kullanılır",
        "d_note": "Değerler uygulamanın başlatıldığından beri okuduğu/yazdığı toplam veridir (ağ + disk). Hız = son yenilemeden beri.",
        "dc_app": "Uygulama", "dc_inst": "Adet", "dc_read": "Okunan", "dc_write": "Yazılan",
        "dc_other": "Diğer", "dc_total": "Toplam", "dc_rate": "Hız", "dc_conn": "Bağlantı", "dc_path": "Konum",
        "d_summary": "{0} uygulama  ·  toplam {1}",
        "d_nomatch": "Eşleşen uygulama yok.",
        "d_nowin": "Bu özellik sadece Windows'ta çalışır.",
        "log_data_start": "Veri kullanımı okunuyor...",
        "log_data_done": "Veri kullanımı okundu: {0} uygulama ({1}s)",
        "log_data_err": "Veri kullanımı okunamadı: {0}",
        "log_stop_req": "Durdurma istendi.",
        "log_scan_start": "Tarama başladı. İsimler: {0}",
        "log_whole": " (tam kelime)",
        "log_es": "es.exe: {0}", "log_es_none": "bulunamadı, HTTP sunucusu denenecek",
        "log_stopped": "Tarama durduruldu.",
        "log_searching": "Everything'de aranıyor: {0}",
        "log_unexpected": "{0}: beklenmeyen hata {1}",
        "log_found": "{0}: {1} sonuç ({2}s, {3})",
        "log_done": "Tarama bitti: {0} · toplam {1}",
        "log_skip": "Tarama atlandı: hiçbir isim seçili değil.",
        "log_all_on": "Tüm isimler açıldı.", "log_all_off": "Tüm isimler kapatıldı.",
        "log_quick": "Hızlı arama: {0}",
        "log_busy": "Tarama sürüyor, bitince tekrar dene.",
        "log_logs_copied": "Loglar panoya kopyalandı.",
        "log_path_copied": "Yol kopyalandı: {0}",
        "log_shown": "Klasörde gösterildi: {0}",
        "log_open_err": "Klasör açılamadı: {0}",
        "log_saved": "Sonuçlar kaydedildi: {0}",
        "log_save_err": "Kaydedilemedi: {0}",
        "log_ev_running": "Everything zaten çalışıyor.",
        "log_ev_started": "Everything otomatik başlatıldı.",
        "log_ev_missing": "Everything kurulu değil ya da bulunamadı.",
        "export_title": "Slave tarama sonuçları - {0}",
        "file_type": "Metin dosyası",
        "splash_sub": "PC KONTROL ARACI",
        "splash_steps": ["çekirdek başlatılıyor", "arama motoru aranıyor", "configler yükleniyor", "hazır"],
        "ap_title": "Görünüm", "ap_theme": "Renk teması", "ap_bg": "Arka plan görseli",
        "ap_pick": "Görsel seç", "ap_remove": "Görseli kaldır", "ap_blur": "Bulanıklık",
        "ap_none": "Görsel yok · varsayılan: hareketli mavi arka plan",
        "ap_hint": "Görsel eklenince otomatik bulanıklaştırılır, yazılar rahat okunur.",
        "ap_opacity": "Arayüz opaklığı",
        "ap_opacity_hint": "Düşürünce arka plan görseli arayüzün arkasından görünür (görsel seçiliyken çalışır).",
        "th_blue": "Mavi", "th_red": "Kırmızı", "th_black": "Siyah",
        "th_white": "Beyaz", "th_purple": "Mor", "th_green": "Yeşil",
        "img_type": "Görseller", "log_look": "Görünüm güncellendi.",
        "gate_sub": "PC KONTROL ARACI", "gate_pass": "PASSCODE", "gate_enter": "Giriş",
        "gate_wrong": "Yanlış passcode.", "gate_tick": "Devam etmek için onay kutusunu işaretle.",
        "gate_consent": "Uygulamanın amacının ne olduğunu ve neleri görebildiğini biliyorum ve yaşanacaklardan ben sorumluyum.",
        "gate_discord": "Passcode'un yok mu? Passcode almak için Discord sunucumuza katıl.",
        "ap_need_pil": "Pillow bulunamadı.\n\nUygulama şu Python ile çalışıyor:\n{0}\n\nHata: {1}\n\n(pip, başka bir Python'a yüklemiş olabilir.) Şimdi bu Python'a yüklensin mi?",
        "ap_install": "Pillow'u yükle", "ap_installing": "Yükleniyor...",
        "ap_install_ok": "Pillow yüklendi.", "ap_install_fail": "Yükleme başarısız:\n{0}",
    },
    "en": {
        "status_ready": "ready", "status_error": "error",
        "status_scanning": "scanning · {0} ({1}/{2})",
        "scan": "Scan", "stop": "Stop",
        "logs_title": "LOGS", "close": "Close", "copy": "Copy", "clear": "Clear",
        "tab_browse": "Browse Tool", "tab_data": "Data usage check",
        "cfg_label": "CONFIG (load)", "cfg_new": "Create new", "cfg_edit": "Edit list",
        "cfg_del": "Delete",
        "names_head": "NAMES TO SEARCH", "names_hint": "box on = searched in this config",
        "all_on": "All on", "all_off": "All off",
        "search": "Search",
        "entry_hint": "«Search» looks up only what you typed (not added to any config) · separate several with commas · use «Edit list» to change a config's list",
        "ck_sys": "Hide Windows system folders",
        "ck_whole": "Whole word match (rescans)",
        "col_kw": "Name", "col_name": "File", "col_path": "Location", "col_size": "Size", "col_date": "Date",
        "show": "Show in folder", "copy_path": "Copy path", "export": "Export TXT",
        "summary": "{0} results shown  ·  {1} total",
        "notice_none": "No names selected.\n\nTurn a name on above, or type something and press 'Search'.",
        "notice_nomatch": "No matches found.",
        "notice_setup": ("Can't reach Everything.\n\n"
                         "1) Open Everything (it must be running in the background)\n"
                         "2) Put es.exe (voidtools.com → ES command line tool) in this program's folder\n"
                         "    or enable Everything → Options → HTTP Server (port 8080)\n\n"
                         "Then press the 'Scan' button at the top right.\n"
                         "See the Logs panel for details."),
        "ed_title_new": "New config", "ed_title_edit": "Edit config",
        "ed_name": "Config name", "ed_add_label": "Add new name to list (comma for several)",
        "ed_add": "Add", "ed_remove": "Remove selected", "ed_save": "Save", "ed_cancel": "Cancel",
        "ed_copy": "Start from current list", "ed_names": "Names ({0})",
        "ed_readonly": "The Default config cannot be changed.\nUse «Create new» to make your own config.",
        "err_name_empty": "Config name cannot be empty.",
        "err_name_exists": "A config with this name already exists.",
        "del_confirm": "Delete config '{0}'?", "del_default": "The Default config cannot be deleted.",
        "log_cfg_loaded": "Config loaded: {0}", "log_cfg_saved": "Config saved: {0}",
        "log_cfg_deleted": "Config deleted: {0}",
        "d_refresh": "Refresh", "d_auto": "Auto refresh ({0}s)",
        "d_only_list": "Only names in the config list",
        "d_search_hint": "Type to filter (comma separated) · if empty, the config list is used",
        "d_note": "Values are the total data an app has read/written since it started (network + disk). Rate = since the last refresh.",
        "dc_app": "App", "dc_inst": "Count", "dc_read": "Read", "dc_write": "Written",
        "dc_other": "Other", "dc_total": "Total", "dc_rate": "Rate", "dc_conn": "Connections", "dc_path": "Location",
        "d_summary": "{0} apps  ·  total {1}",
        "d_nomatch": "No matching apps.",
        "d_nowin": "This feature only works on Windows.",
        "log_data_start": "Reading data usage...",
        "log_data_done": "Data usage read: {0} apps ({1}s)",
        "log_data_err": "Could not read data usage: {0}",
        "log_stop_req": "Stop requested.",
        "log_scan_start": "Scan started. Names: {0}",
        "log_whole": " (whole word)",
        "log_es": "es.exe: {0}", "log_es_none": "not found, trying HTTP server",
        "log_stopped": "Scan stopped.",
        "log_searching": "Searching Everything: {0}",
        "log_unexpected": "{0}: unexpected error {1}",
        "log_found": "{0}: {1} results ({2}s, {3})",
        "log_done": "Scan finished: {0} · total {1}",
        "log_skip": "Scan skipped: no names selected.",
        "log_all_on": "All names turned on.", "log_all_off": "All names turned off.",
        "log_quick": "Quick search: {0}",
        "log_busy": "A scan is running, try again when it finishes.",
        "log_logs_copied": "Logs copied to clipboard.",
        "log_path_copied": "Path copied: {0}",
        "log_shown": "Shown in folder: {0}",
        "log_open_err": "Could not open folder: {0}",
        "log_saved": "Results saved: {0}",
        "log_save_err": "Could not save: {0}",
        "log_ev_running": "Everything is already running.",
        "log_ev_started": "Everything was started automatically.",
        "log_ev_missing": "Everything is not installed or could not be found.",
        "export_title": "Slave scan results - {0}",
        "file_type": "Text file",
        "splash_sub": "PC CHECK TOOL",
        "splash_steps": ["starting core", "locating search engine", "loading configs", "ready"],
        "ap_title": "Appearance", "ap_theme": "Color theme", "ap_bg": "Background image",
        "ap_pick": "Choose image", "ap_remove": "Remove image", "ap_blur": "Blur",
        "ap_none": "No image · default: moving blue background",
        "ap_hint": "Images are blurred automatically so the text stays readable.",
        "ap_opacity": "Interface opacity",
        "ap_opacity_hint": "Lower it to let the background image show through the interface (needs a background image).",
        "th_blue": "Blue", "th_red": "Red", "th_black": "Black",
        "th_white": "White", "th_purple": "Purple", "th_green": "Green",
        "img_type": "Images", "log_look": "Appearance updated.",
        "gate_sub": "PC CHECK TOOL", "gate_pass": "PASSCODE", "gate_enter": "Enter",
        "gate_wrong": "Wrong passcode.", "gate_tick": "Tick the checkbox to continue.",
        "gate_consent": "I know what this application is for and what it can see, and I take responsibility for whatever happens.",
        "gate_discord": "You don't have the passcode? Join our Discord server to get the passcode.",
        "ap_need_pil": "Pillow was not found.\n\nThe app is running with this Python:\n{0}\n\nError: {1}\n\n(pip may have installed it into a different Python.) Install it into this Python now?",
        "ap_install": "Install Pillow", "ap_installing": "Installing...",
        "ap_install_ok": "Pillow installed.", "ap_install_fail": "Installation failed:\n{0}",
    },
    "ru": {
        "status_ready": "готово", "status_error": "ошибка",
        "status_scanning": "сканирование · {0} ({1}/{2})",
        "scan": "Скан", "stop": "Стоп",
        "logs_title": "LOGS", "close": "Закрыть", "copy": "Копировать", "clear": "Очистить",
        "tab_browse": "Browse Tool", "tab_data": "Data usage check",
        "cfg_label": "КОНФИГ (загрузить)", "cfg_new": "Создать", "cfg_edit": "Изменить список",
        "cfg_del": "Удалить",
        "names_head": "ИМЕНА ДЛЯ ПОИСКА", "names_hint": "галочка = ищется в этом конфиге",
        "all_on": "Включить все", "all_off": "Выключить все",
        "search": "Искать",
        "entry_hint": "«Искать» ищет только введённое (в конфиги не добавляет) · несколько имён через запятую · список конфига меняется через «Изменить список»",
        "ck_sys": "Скрыть системные папки Windows",
        "ck_whole": "Только целое слово (пересканирует)",
        "col_kw": "Имя", "col_name": "Файл", "col_path": "Расположение", "col_size": "Размер", "col_date": "Дата",
        "show": "Показать в папке", "copy_path": "Копировать путь", "export": "Экспорт в TXT",
        "summary": "Показано: {0}  ·  всего {1}",
        "notice_none": "Не выбрано ни одного имени.\n\nВключите имя выше или введите текст и нажмите «Искать».",
        "notice_nomatch": "Совпадений не найдено.",
        "notice_setup": ("Не удаётся подключиться к Everything.\n\n"
                         "1) Запустите Everything (он должен работать в фоне)\n"
                         "2) Положите es.exe (voidtools.com → ES, консольная утилита) в папку программы\n"
                         "    или включите Everything → Параметры → HTTP-сервер (порт 8080)\n\n"
                         "Затем нажмите «Скан» справа вверху.\n"
                         "Подробности — на панели Logs."),
        "ed_title_new": "Новый конфиг", "ed_title_edit": "Изменить конфиг",
        "ed_name": "Имя конфига", "ed_add_label": "Добавить имя в список (несколько через запятую)",
        "ed_add": "Добавить", "ed_remove": "Удалить выбранное", "ed_save": "Сохранить", "ed_cancel": "Отмена",
        "ed_copy": "Начать с текущего списка", "ed_names": "Имена ({0})",
        "ed_readonly": "Конфиг Default изменить нельзя.\nСоздайте свой через «Создать».",
        "err_name_empty": "Имя конфига не может быть пустым.",
        "err_name_exists": "Конфиг с таким именем уже существует.",
        "del_confirm": "Удалить конфиг '{0}'?", "del_default": "Конфиг Default удалить нельзя.",
        "log_cfg_loaded": "Конфиг загружен: {0}", "log_cfg_saved": "Конфиг сохранён: {0}",
        "log_cfg_deleted": "Конфиг удалён: {0}",
        "d_refresh": "Обновить", "d_auto": "Автообновление ({0} с)",
        "d_only_list": "Только имена из списка конфига",
        "d_search_hint": "Введите для фильтра (через запятую) · если пусто — список конфига",
        "d_note": "Значения — всего данных, прочитанных/записанных приложением с момента запуска (сеть + диск). Скорость — с прошлого обновления.",
        "dc_app": "Приложение", "dc_inst": "Кол-во", "dc_read": "Прочитано", "dc_write": "Записано",
        "dc_other": "Прочее", "dc_total": "Всего", "dc_rate": "Скорость", "dc_conn": "Соединения", "dc_path": "Расположение",
        "d_summary": "Приложений: {0}  ·  всего {1}",
        "d_nomatch": "Подходящих приложений нет.",
        "d_nowin": "Эта функция работает только в Windows.",
        "log_data_start": "Чтение данных об использовании...",
        "log_data_done": "Данные прочитаны: {0} приложений ({1}с)",
        "log_data_err": "Не удалось прочитать данные: {0}",
        "log_stop_req": "Запрошена остановка.",
        "log_scan_start": "Сканирование началось. Имена: {0}",
        "log_whole": " (целое слово)",
        "log_es": "es.exe: {0}", "log_es_none": "не найден, пробуем HTTP-сервер",
        "log_stopped": "Сканирование остановлено.",
        "log_searching": "Поиск в Everything: {0}",
        "log_unexpected": "{0}: непредвиденная ошибка {1}",
        "log_found": "{0}: {1} результатов ({2}с, {3})",
        "log_done": "Сканирование завершено: {0} · всего {1}",
        "log_skip": "Сканирование пропущено: имена не выбраны.",
        "log_all_on": "Все имена включены.", "log_all_off": "Все имена выключены.",
        "log_quick": "Быстрый поиск: {0}",
        "log_busy": "Идёт сканирование, повторите после завершения.",
        "log_logs_copied": "Логи скопированы в буфер обмена.",
        "log_path_copied": "Путь скопирован: {0}",
        "log_shown": "Показано в папке: {0}",
        "log_open_err": "Не удалось открыть папку: {0}",
        "log_saved": "Результаты сохранены: {0}",
        "log_save_err": "Не удалось сохранить: {0}",
        "log_ev_running": "Everything уже запущен.",
        "log_ev_started": "Everything запущен автоматически.",
        "log_ev_missing": "Everything не установлен или не найден.",
        "export_title": "Результаты сканирования Slave - {0}",
        "file_type": "Текстовый файл",
        "splash_sub": "ИНСТРУМЕНТ ПРОВЕРКИ ПК",
        "splash_steps": ["запуск ядра", "поиск движка", "загрузка конфигов", "готово"],
        "ap_title": "Оформление", "ap_theme": "Цветовая тема", "ap_bg": "Фоновое изображение",
        "ap_pick": "Выбрать изображение", "ap_remove": "Убрать изображение", "ap_blur": "Размытие",
        "ap_none": "Нет изображения · по умолчанию: движущийся синий фон",
        "ap_hint": "Изображение автоматически размывается, текст остаётся читаемым.",
        "ap_opacity": "Прозрачность интерфейса",
        "ap_opacity_hint": "Уменьшите, чтобы фоновое изображение проступало сквозь интерфейс (нужно фоновое изображение).",
        "th_blue": "Синий", "th_red": "Красный", "th_black": "Чёрный",
        "th_white": "Белый", "th_purple": "Фиолетовый", "th_green": "Зелёный",
        "img_type": "Изображения", "log_look": "Оформление обновлено.",
        "gate_sub": "ИНСТРУМЕНТ ПРОВЕРКИ ПК", "gate_pass": "PASSCODE", "gate_enter": "Войти",
        "gate_wrong": "Неверный passcode.", "gate_tick": "Поставьте галочку, чтобы продолжить.",
        "gate_consent": "Я знаю, для чего это приложение и что оно может видеть, и беру на себя ответственность за последствия.",
        "gate_discord": "Нет passcode? Вступите в наш Discord-сервер, чтобы получить passcode.",
        "ap_need_pil": "Pillow не найден.\n\nПриложение запущено в этом Python:\n{0}\n\nОшибка: {1}\n\n(pip мог установить его в другой Python.) Установить в этот Python сейчас?",
        "ap_install": "Установить Pillow", "ap_installing": "Установка...",
        "ap_install_ok": "Pillow установлен.", "ap_install_fail": "Не удалось установить:\n{0}",
    },
    "uk": {
        "status_ready": "готово", "status_error": "помилка",
        "status_scanning": "сканування · {0} ({1}/{2})",
        "scan": "Скан", "stop": "Стоп",
        "logs_title": "LOGS", "close": "Закрити", "copy": "Копіювати", "clear": "Очистити",
        "tab_browse": "Browse Tool", "tab_data": "Data usage check",
        "cfg_label": "КОНФІГ (завантажити)", "cfg_new": "Створити", "cfg_edit": "Змінити список",
        "cfg_del": "Видалити",
        "names_head": "ІМЕНА ДЛЯ ПОШУКУ", "names_hint": "галочка = шукається в цьому конфігу",
        "all_on": "Увімкнути все", "all_off": "Вимкнути все",
        "search": "Шукати",
        "entry_hint": "«Шукати» шукає лише введене (до конфігів не додає) · кілька імен через кому · список конфігу змінюється через «Змінити список»",
        "ck_sys": "Сховати системні папки Windows",
        "ck_whole": "Лише ціле слово (пересканує)",
        "col_kw": "Ім'я", "col_name": "Файл", "col_path": "Розташування", "col_size": "Розмір", "col_date": "Дата",
        "show": "Показати в папці", "copy_path": "Копіювати шлях", "export": "Експорт у TXT",
        "summary": "Показано: {0}  ·  усього {1}",
        "notice_none": "Не вибрано жодного імені.\n\nУвімкніть ім'я вище або введіть текст і натисніть «Шукати».",
        "notice_nomatch": "Збігів не знайдено.",
        "notice_setup": ("Не вдається підключитися до Everything.\n\n"
                         "1) Запустіть Everything (він має працювати у фоні)\n"
                         "2) Покладіть es.exe (voidtools.com → ES, консольна утиліта) у папку програми\n"
                         "    або увімкніть Everything → Параметри → HTTP-сервер (порт 8080)\n\n"
                         "Потім натисніть «Скан» праворуч угорі.\n"
                         "Докладніше — на панелі Logs."),
        "ed_title_new": "Новий конфіг", "ed_title_edit": "Змінити конфіг",
        "ed_name": "Ім'я конфігу", "ed_add_label": "Додати ім'я до списку (кілька через кому)",
        "ed_add": "Додати", "ed_remove": "Видалити вибране", "ed_save": "Зберегти", "ed_cancel": "Скасувати",
        "ed_copy": "Почати з поточного списку", "ed_names": "Імена ({0})",
        "ed_readonly": "Конфіг Default змінити не можна.\nСтворіть свій через «Створити».",
        "err_name_empty": "Ім'я конфігу не може бути порожнім.",
        "err_name_exists": "Конфіг з таким ім'ям уже існує.",
        "del_confirm": "Видалити конфіг '{0}'?", "del_default": "Конфіг Default видалити не можна.",
        "log_cfg_loaded": "Конфіг завантажено: {0}", "log_cfg_saved": "Конфіг збережено: {0}",
        "log_cfg_deleted": "Конфіг видалено: {0}",
        "d_refresh": "Оновити", "d_auto": "Автооновлення ({0} с)",
        "d_only_list": "Лише імена зі списку конфігу",
        "d_search_hint": "Введіть для фільтра (через кому) · якщо порожньо — список конфігу",
        "d_note": "Значення — усього даних, прочитаних/записаних застосунком від запуску (мережа + диск). Швидкість — від останнього оновлення.",
        "dc_app": "Застосунок", "dc_inst": "К-сть", "dc_read": "Прочитано", "dc_write": "Записано",
        "dc_other": "Інше", "dc_total": "Усього", "dc_rate": "Швидкість", "dc_conn": "З'єднання", "dc_path": "Розташування",
        "d_summary": "Застосунків: {0}  ·  усього {1}",
        "d_nomatch": "Відповідних застосунків немає.",
        "d_nowin": "Ця функція працює лише у Windows.",
        "log_data_start": "Читання даних про використання...",
        "log_data_done": "Дані прочитано: {0} застосунків ({1}с)",
        "log_data_err": "Не вдалося прочитати дані: {0}",
        "log_stop_req": "Запитано зупинку.",
        "log_scan_start": "Сканування розпочато. Імена: {0}",
        "log_whole": " (ціле слово)",
        "log_es": "es.exe: {0}", "log_es_none": "не знайдено, пробуємо HTTP-сервер",
        "log_stopped": "Сканування зупинено.",
        "log_searching": "Пошук в Everything: {0}",
        "log_unexpected": "{0}: непередбачена помилка {1}",
        "log_found": "{0}: {1} результатів ({2}с, {3})",
        "log_done": "Сканування завершено: {0} · усього {1}",
        "log_skip": "Сканування пропущено: імена не вибрано.",
        "log_all_on": "Усі імена увімкнено.", "log_all_off": "Усі імена вимкнено.",
        "log_quick": "Швидкий пошук: {0}",
        "log_busy": "Триває сканування, повторіть після завершення.",
        "log_logs_copied": "Логи скопійовано в буфер обміну.",
        "log_path_copied": "Шлях скопійовано: {0}",
        "log_shown": "Показано в папці: {0}",
        "log_open_err": "Не вдалося відкрити папку: {0}",
        "log_saved": "Результати збережено: {0}",
        "log_save_err": "Не вдалося зберегти: {0}",
        "log_ev_running": "Everything уже запущено.",
        "log_ev_started": "Everything запущено автоматично.",
        "log_ev_missing": "Everything не встановлено або не знайдено.",
        "export_title": "Результати сканування Slave - {0}",
        "file_type": "Текстовий файл",
        "splash_sub": "ІНСТРУМЕНТ ПЕРЕВІРКИ ПК",
        "splash_steps": ["запуск ядра", "пошук рушія", "завантаження конфігів", "готово"],
        "ap_title": "Оформлення", "ap_theme": "Колірна тема", "ap_bg": "Фонове зображення",
        "ap_pick": "Вибрати зображення", "ap_remove": "Прибрати зображення", "ap_blur": "Розмиття",
        "ap_none": "Немає зображення · за замовчуванням: рухомий синій фон",
        "ap_hint": "Зображення автоматично розмивається, текст лишається читабельним.",
        "ap_opacity": "Прозорість інтерфейсу",
        "ap_opacity_hint": "Зменште, щоб фонове зображення проступало крізь інтерфейс (потрібне фонове зображення).",
        "th_blue": "Синій", "th_red": "Червоний", "th_black": "Чорний",
        "th_white": "Білий", "th_purple": "Фіолетовий", "th_green": "Зелений",
        "img_type": "Зображення", "log_look": "Оформлення оновлено.",
        "gate_sub": "ІНСТРУМЕНТ ПЕРЕВІРКИ ПК", "gate_pass": "PASSCODE", "gate_enter": "Увійти",
        "gate_wrong": "Хибний passcode.", "gate_tick": "Поставте галочку, щоб продовжити.",
        "gate_consent": "Я знаю, для чого цей застосунок і що він може бачити, і беру на себе відповідальність за наслідки.",
        "gate_discord": "Немає passcode? Приєднайтеся до нашого Discord-сервера, щоб отримати passcode.",
        "ap_need_pil": "Pillow не знайдено.\n\nЗастосунок запущено в цьому Python:\n{0}\n\nПомилка: {1}\n\n(pip міг встановити його в інший Python.) Встановити в цей Python зараз?",
        "ap_install": "Встановити Pillow", "ap_installing": "Встановлення...",
        "ap_install_ok": "Pillow встановлено.", "ap_install_fail": "Не вдалося встановити:\n{0}",
    },
}


def sys_lang():
    try:
        pid = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0xFF
        return {0x1F: "tr", 0x19: "ru", 0x22: "uk"}.get(pid, "en")
    except Exception:
        return "en"


def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def split_names(text):
    return [s.strip() for s in text.replace(";", ",").split(",") if s.strip()]


class EverythingError(Exception):
    pass


def find_es():
    here = os.path.dirname(os.path.abspath(__file__))
    home = os.path.expanduser("~")
    cands = [
        shutil.which("es"), shutil.which("es.exe"),
        os.path.join(here, "es.exe"),
        r"C:\Program Files\Everything\es.exe",
        r"C:\Program Files (x86)\Everything\es.exe",
        r"C:\Program Files\Everything 1.5a\es.exe",
        os.path.join(home, "Desktop", "es.exe"),
        os.path.join(home, "Downloads", "es.exe"),
    ]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


EVERYTHING_EXES = ("Everything.exe", "Everything64.exe")


def everything_running():
    if os.name != "nt":
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for exe in EVERYTHING_EXES:
        try:
            r = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"],
                               capture_output=True, timeout=15, creationflags=flags)
        except Exception:
            return False
        if exe.lower() in r.stdout.decode("utf-8", "replace").lower():
            return True
    return False


def find_everything():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    for exe in EVERYTHING_EXES:
        cands += [shutil.which(exe), os.path.join(here, exe)]
        for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
                     os.environ.get("LOCALAPPDATA")):
            if base:
                cands += [os.path.join(base, "Everything", exe),
                          os.path.join(base, "Everything 1.5a", exe),
                          os.path.join(base, "Programs", "Everything", exe)]
    for c in cands:
        if c and os.path.isfile(c):
            return c
    return None


def start_everything():
    if os.name != "nt":
        return "missing"
    if everything_running():
        return "running"
    path = find_everything()
    if not path:
        return "missing"
    try:
        subprocess.Popen([path, "-startup"], cwd=os.path.dirname(path),
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError:
        return "missing"
    return "started"


def boot_sound_file():
    path = os.path.join(tempfile.gettempdir(), "slave_boot_v2.wav")
    if os.path.isfile(path):
        return path
    rate, total = 22050, 3.0
    n = int(rate * total)
    buf = [0.0] * n
    two_pi = 2 * math.pi

    def tone(start, freq, length, amp):
        i0 = int(start * rate)
        for i in range(int(length * rate)):
            if i0 + i >= n:
                break
            t = i / rate
            env = min(1.0, t / 0.04) * math.exp(-t * 3.0)
            buf[i0 + i] += amp * env * (math.sin(two_pi * freq * t)
                                        + 0.12 * math.sin(two_pi * freq * 2 * t))

    for start, freq in ((0.20, 739.99), (0.65, 880.0), (1.10, 587.33)):
        tone(start, freq, 1.2, 0.30)
    for freq in (293.66, 440.0, 739.99):
        tone(1.75, freq, 1.25, 0.22)
    fade = int(0.5 * rate)
    for i in range(fade):
        buf[n - 1 - i] *= i / fade
    peak = max(1e-6, max(abs(v) for v in buf))
    scale = 0.2 * 32767 / peak
    tmp = path + ".tmp"
    with wave.open(tmp, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<%dh" % n, *[int(v * scale) for v in buf]))
    os.replace(tmp, path)
    return path


def play_boot_sound():
    if winsound is None:
        return
    try:
        winsound.PlaySound(boot_sound_file(), winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass


def _decode_lines(raw):
    encs = ["utf-8"]
    try:
        encs += [f"cp{ctypes.windll.kernel32.GetOEMCP()}", f"cp{ctypes.windll.kernel32.GetACP()}"]
    except Exception:
        pass
    best, best_score = None, -1
    for enc in encs:
        try:
            lines = [l.strip() for l in raw.decode(enc).splitlines() if l.strip()]
        except Exception:
            continue
        score = sum(os.path.exists(l) for l in lines[:50])
        if score > best_score:
            best, best_score = lines, score
    if best is None:
        best = [l.strip() for l in raw.decode("utf-8", "replace").splitlines() if l.strip()]
    return best


def everything_term(name):
    if " " in name.strip():
        return "*" + name.strip().replace(" ", "?") + "*"
    return name


def search_es(es, name, whole_word):
    cmd = [es, "-n", str(MAX_RESULTS)] + (["-w"] if whole_word else []) + [everything_term(name)]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise EverythingError("es.exe did not respond within 60 seconds.")
    except OSError as e:
        raise EverythingError(f"could not run es.exe: {e}")
    if r.returncode != 0:
        msg = (r.stdout + r.stderr).decode("utf-8", "replace").strip()
        raise EverythingError(f"es.exe error code {r.returncode}: {msg or 'Everything may not be running.'}")
    return _decode_lines(r.stdout)


def search_http(name, whole_word):
    q = ("ww:" if whole_word else "") + everything_term(name)
    params = urllib.parse.urlencode(
        {"search": q, "json": 1, "count": MAX_RESULTS, "path_column": 1})
    try:
        with urllib.request.urlopen(f"{HTTP_URL}/?{params}", timeout=15) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        raise EverythingError(f"HTTP server unreachable ({HTTP_URL}): {e}")
    return [os.path.join(it.get("path", ""), it.get("name", "")) for it in data.get("results", [])]


def search_everything(name, whole_word):
    errors = []
    es = find_es()
    if es:
        try:
            return search_es(es, name, whole_word), "es.exe"
        except EverythingError as e:
            errors.append(str(e))
    else:
        errors.append("es.exe not found.")
    try:
        return search_http(name, whole_word), "HTTP"
    except EverythingError as e:
        errors.append(str(e))
    raise EverythingError("\n".join(errors))


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def file_info(path):
    try:
        st = os.stat(path)
        isdir = os.path.isdir(path)
        return (isdir, "—" if isdir else human(st.st_size),
                datetime.fromtimestamp(st.st_mtime).strftime("%d.%m.%Y %H:%M"))
    except OSError:
        return (False, "—", "—")


PS_SCRIPT = r"""
$ErrorActionPreference = 'SilentlyContinue'
$paths = @{}
Get-Process | ForEach-Object { $paths[[string]$_.Id] = $_.Path }
$conn = @{}
Get-NetTCPConnection -State Established | Group-Object OwningProcess | ForEach-Object { $conn[[string]$_.Name] = $_.Count }
$rows = Get-CimInstance Win32_PerfRawData_PerfProc_Process |
  Where-Object { $_.Name -ne '_Total' -and $_.Name -ne 'Idle' } |
  ForEach-Object {
    [pscustomobject]@{
      name  = $_.Name
      pid   = $_.IDProcess
      read  = [double]$_.IOReadBytesPersec
      write = [double]$_.IOWriteBytesPersec
      other = [double]$_.IOOtherBytesPersec
      path  = $paths[[string]$_.IDProcess]
      conns = [int]$conn[[string]$_.IDProcess]
    }
  }
ConvertTo-Json -InputObject @($rows) -Compress
"""


def fetch_usage():
    if os.name != "nt":
        raise RuntimeError("Windows only")
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command",
             "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + PS_SCRIPT],
            capture_output=True, timeout=90,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise RuntimeError("PowerShell did not respond within 90 seconds.")
    except OSError as e:
        raise RuntimeError(f"could not run PowerShell: {e}")
    out = r.stdout.decode("utf-8", "replace").strip()
    if not out:
        raise RuntimeError(r.stderr.decode("utf-8", "replace").strip() or "empty output")
    try:
        data = json.loads(out)
    except ValueError as e:
        raise RuntimeError(f"unreadable output: {e}")
    if isinstance(data, dict):
        data = [data]
    agg = {}
    for d in data:
        nm = re.sub(r"#\d+$", "", d.get("name") or "")
        if not nm:
            continue
        a = agg.setdefault(nm.lower(), {"app": nm, "inst": 0, "read": 0.0, "write": 0.0,
                                        "other": 0.0, "conn": 0, "path": ""})
        a["inst"] += 1
        a["read"] += d.get("read") or 0
        a["write"] += d.get("write") or 0
        a["other"] += d.get("other") or 0
        a["conn"] += d.get("conns") or 0
        if not a["path"] and d.get("path"):
            a["path"] = d["path"]
    for a in agg.values():
        a["total"] = a["read"] + a["write"]
    return list(agg.values())


GREEN = "#3fb950"
AMBER = "#e3a008"
RED = "#f85149"


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def lerp(c1, c2, t):
    t = max(0.0, min(1.0, t))
    a, b = _hex(c1), _hex(c2)
    return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


THEMES = {
    "blue":   dict(BG="#0a0e14", PANEL="#10161f", CARD="#161d29", LINE="#243044", FG="#e6edf3",
                   MUTED="#6b7787", ACCENT="#2fb8ff", ACCENT2="#7c5cff", ONACC="#001018"),
    "red":    dict(BG="#100a0b", PANEL="#181012", CARD="#221619", LINE="#3d2429", FG="#f3e8e9",
                   MUTED="#8a6b70", ACCENT="#ff4d5a", ACCENT2="#ff9a5c", ONACC="#1a0003"),
    "black":  dict(BG="#050505", PANEL="#0d0d0d", CARD="#161616", LINE="#2b2b2b", FG="#f2f2f2",
                   MUTED="#7d7d7d", ACCENT="#e8e8e8", ACCENT2="#8c8c8c", ONACC="#050505"),
    "white":  dict(BG="#e9edf3", PANEL="#ffffff", CARD="#f1f4f9", LINE="#cdd5e0", FG="#1a2230",
                   MUTED="#6b7787", ACCENT="#1a73e8", ACCENT2="#7c5cff", ONACC="#ffffff"),
    "purple": dict(BG="#0c0a14", PANEL="#141022", CARD="#1d1730", LINE="#322a4d", FG="#ece8f6",
                   MUTED="#7d7396", ACCENT="#a78bfa", ACCENT2="#f472b6", ONACC="#120a24"),
    "green":  dict(BG="#08110d", PANEL="#0e1a14", CARD="#14251c", LINE="#244134", FG="#e4f2ea",
                   MUTED="#6b8778", ACCENT="#34d399", ACCENT2="#2fb8ff", ONACC="#00180e"),
}
THEME_ORDER = ["blue", "red", "black", "white", "purple", "green"]


def set_theme(key):
    global BG, PANEL, CARD, LINE, FG, MUTED, ACCENT, ACCENT2, ONACC
    global HOVER, HOVER2, ROW_ALT, SEL, DANGER, DANGER_H, LIGHT
    th = THEMES.get(key, THEMES["blue"])
    BG, PANEL, CARD, LINE = th["BG"], th["PANEL"], th["CARD"], th["LINE"]
    FG, MUTED, ACCENT, ACCENT2, ONACC = th["FG"], th["MUTED"], th["ACCENT"], th["ACCENT2"], th["ONACC"]
    LIGHT = sum(_hex(BG)) > 450
    HOVER = lerp(ACCENT, "#ffffff", 0.3) if not LIGHT else lerp(ACCENT, "#000000", 0.15)
    HOVER2 = lerp(ACCENT2, "#ffffff", 0.3) if not LIGHT else lerp(ACCENT2, "#000000", 0.15)
    ROW_ALT = lerp(CARD, FG, 0.04)
    SEL = lerp(CARD, ACCENT, 0.3)
    DANGER = lerp(CARD, RED, 0.25)
    DANGER_H = lerp(CARD, RED, 0.42)


set_theme("blue")


def glass(c):
    if LIGHT:
        return lerp(c, "#000000", 0.14), c, lerp(c, "#ffffff", 0.35)
    return lerp(c, "#ffffff", 0.30), c, lerp(c, "#ffffff", 0.17)


def set_alpha(win, a):
    try:
        win.attributes("-alpha", a)
    except tk.TclError:
        pass


def rounded_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def flow_layout(frame, items, cell_w, padx=0):
    state = {"cols": 0}

    def regrid(_e=None):
        width = frame.winfo_width()
        cols = max(1, width // cell_w) if width > 1 else PER_ROW
        if cols == state["cols"]:
            return
        state["cols"] = cols
        for i, wd in enumerate(items):
            r, c = divmod(i, cols)
            wd.grid(row=r, column=c, sticky="w", pady=1, padx=(0, padx))

    frame.bind("<Configure>", regrid)
    regrid()


class RoundButton(tk.Canvas):
    def __init__(self, parent, text, command, bg, fg, hover, width=100, height=34,
                 font=("Segoe UI", 10, "bold"), parent_bg=None):
        super().__init__(parent, width=width, height=height, bg=parent_bg or PANEL,
                         highlightthickness=0, bd=0, cursor="hand2")
        self.command, self.bg_c, self.fg_c, self.hover_c = command, bg, fg, hover
        self.enabled = True
        r = height // 2
        self.r_border = rounded_rect(self, 1, 1, width - 1, height - 1, max(2, r - 1), fill="", outline="")
        self.r_base = rounded_rect(self, 2, 2, width - 2, height - 2, max(2, r - 2), fill="", outline="")
        gh = int(height * 0.55)
        self.r_gloss = rounded_rect(self, 5, 3, width - 5, gh, max(2, (gh - 3) // 2), fill="", outline="")
        self.label = self.create_text(width / 2, height / 2, text=text, fill=fg, font=font)
        self._paint(bg)
        self.bind("<Enter>", lambda e: self.enabled and self._paint(self.hover_c))
        self.bind("<Leave>", lambda e: self._paint(self.bg_c if self.enabled else LINE))
        self.bind("<Button-1>", lambda e: self.enabled and self.command())

    def _paint(self, color):
        border, base, gloss = glass(color)
        self.itemconfig(self.r_border, fill=border)
        self.itemconfig(self.r_base, fill=base)
        self.itemconfig(self.r_gloss, fill=gloss)

    def set_enabled(self, enabled):
        self.enabled = enabled
        self._paint(self.bg_c if enabled else LINE)
        self.itemconfig(self.label, fill=self.fg_c if enabled else MUTED)
        self.config(cursor="hand2" if enabled else "arrow")

    def set_text(self, text, fg=None):
        self.itemconfig(self.label, text=text)
        if fg:
            self.fg_c = fg
            self.itemconfig(self.label, fill=fg)

    def set_colors(self, bg, fg, hover):
        self.bg_c, self.fg_c, self.hover_c = bg, fg, hover
        self._paint(bg)
        self.itemconfig(self.label, fill=fg)


class Splash:
    W, H = 520, 340
    TOTAL = 2.8

    def __init__(self, root, on_done, lang="en"):
        self.on_done = on_done
        self.steps = TXT[lang]["splash_steps"]
        W, H = self.W, self.H
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        try:
            self.win.attributes("-topmost", True)
        except tk.TclError:
            pass
        x = (root.winfo_screenwidth() - W) // 2
        y = (root.winfo_screenheight() - H) // 2
        self.win.geometry(f"{W}x{H}+{x}+{y}")
        self.win.configure(bg=BG)
        set_alpha(self.win, 0.0)
        cv = self.cv = tk.Canvas(self.win, width=W, height=H, bg=BG, highlightthickness=0)
        cv.pack()
        cx, cy = W // 2, 120
        self.glow = [cv.create_oval(cx - r, cy - r, cx + r, cy + r, outline="", fill=BG)
                     for r in (72, 58, 46)]
        self.arcs = [cv.create_arc(cx - r, cy - r, cx + r, cy + r, start=0, extent=ext,
                                   style="arc", outline=col, width=w)
                     for r, w, col, ext in ((54, 4, ACCENT, 110), (42, 3, ACCENT2, 80),
                                            (30, 2, LINE, 140))]
        self.core = cv.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill=ACCENT, outline="")
        word, spacing = "SLAVE", 34
        x0 = cx - spacing * (len(word) - 1) / 2
        self.letters = [cv.create_text(x0 + i * spacing, 218, text=ch, fill=BG,
                                       font=("Segoe UI", 30, "bold"))
                        for i, ch in enumerate(word)]
        self.sub = cv.create_text(cx, 256, text=TXT[lang]["splash_sub"], fill=BG,
                                  font=("Segoe UI", 9))
        self.credit = cv.create_text(cx, 14, text=CREDIT, fill=BG, font=("Segoe UI", 8))
        self.bar = (110, W - 110, 296)
        cv.create_line(self.bar[0], self.bar[2], self.bar[1], self.bar[2],
                       fill=LINE, width=3, capstyle="round")
        self.fill = cv.create_line(self.bar[0], self.bar[2], self.bar[0], self.bar[2],
                                   fill=ACCENT, width=3, capstyle="round")
        self.step_txt = cv.create_text(cx, 318, text="", fill=MUTED, font=("Segoe UI", 9))
        self.t0 = time.time()
        threading.Thread(target=play_boot_sound, daemon=True).start()
        self._tick()

    def _tick(self):
        t = time.time() - self.t0
        if t < 0.4:
            set_alpha(self.win, t / 0.4)
        elif t > self.TOTAL:
            set_alpha(self.win, max(0.0, 1 - (t - self.TOTAL) / 0.35))
        else:
            set_alpha(self.win, 1.0)
        if t > self.TOTAL + 0.35:
            self.win.destroy()
            self.on_done()
            return
        cv = self.cv
        for arc, sp in zip(self.arcs, (200, -140, 90)):
            cv.itemconfig(arc, start=(t * sp) % 360)
        pulse = 0.5 + 0.5 * math.sin(t * 4)
        for oval, base in zip(self.glow, (0.04, 0.07, 0.11)):
            cv.itemconfig(oval, fill=lerp(BG, ACCENT, base * (0.6 + 0.8 * pulse)))
        cv.itemconfig(self.core, fill=lerp(ACCENT, "#ffffff", 0.3 * pulse))
        for i, item in enumerate(self.letters):
            cv.itemconfig(item, fill=lerp(BG, FG, (t - 0.5 - i * 0.12) / 0.3))
        cv.itemconfig(self.sub, fill=lerp(BG, MUTED, (t - 1.4) / 0.5))
        cv.itemconfig(self.credit, fill=lerp(BG, MUTED, (t - 0.8) / 0.5))
        p = min(1.0, max(0.0, (t - 0.3) / (self.TOTAL - 0.5)))
        p = 1 - (1 - p) ** 2
        bx1, bx2, by = self.bar
        cv.coords(self.fill, bx1, by, bx1 + (bx2 - bx1) * p, by)
        cv.itemconfig(self.step_txt, text=self.steps[min(3, int(p * 4))])
        self.win.after(16, self._tick)


class ConfigEditor:
    def __init__(self, app, tool, name, names, is_new, readonly, on_save):
        self.app, self.tool, self.on_save = app, tool, on_save
        self.is_new, self.readonly = is_new, readonly
        self.names = list(names)
        t = app.t
        w = self.win = tk.Toplevel(app.root)
        w.title(t("ed_title_new" if is_new else "ed_title_edit"))
        w.configure(bg=BG)
        w.geometry("470x560")
        w.minsize(400, 480)
        w.transient(app.root)
        w.grab_set()
        lab = dict(bg=BG, fg=MUTED, font=("Segoe UI", 8, "bold"))
        ent = dict(bg=CARD, fg=FG, insertbackground=FG, relief="flat", font=("Segoe UI", 10),
                   highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT,
                   readonlybackground=CARD, disabledbackground=CARD, disabledforeground=MUTED)

        tk.Label(w, text=t("ed_name").upper(), **lab).pack(anchor="w", padx=16, pady=(16, 3))
        self.name_var = tk.StringVar(value=name)
        self.name_e = tk.Entry(w, textvariable=self.name_var, **ent)
        self.name_e.pack(fill="x", padx=16, ipady=6)
        if not is_new:
            self.name_e.config(state="readonly")

        if is_new:
            self.copy_var = tk.BooleanVar(value=False)
            tk.Checkbutton(w, text=t("ed_copy"), variable=self.copy_var, command=self._copy_current,
                           bg=BG, fg=MUTED, selectcolor=CARD, activebackground=BG,
                           activeforeground=FG, font=("Segoe UI", 9), highlightthickness=0,
                           bd=0, cursor="hand2").pack(anchor="w", padx=14, pady=(8, 0))

        if readonly:
            tk.Label(w, text=t("ed_readonly"), bg=BG, fg=AMBER, font=("Segoe UI", 9),
                     justify="left").pack(anchor="w", padx=16, pady=(10, 0))
        else:
            tk.Label(w, text=t("ed_add_label").upper(), **lab).pack(anchor="w", padx=16, pady=(14, 3))
            row = tk.Frame(w, bg=BG)
            row.pack(fill="x", padx=16)
            self.add_e = tk.Entry(row, **ent)
            self.add_e.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
            self.add_e.bind("<Return>", lambda e: self.add())
            self.add_e.focus_set()
            RoundButton(row, t("ed_add"), self.add, ACCENT2, "#ffffff", HOVER2,
                        width=90, height=32, parent_bg=BG).pack(side="left")

        self.count_lbl = tk.Label(w, bg=BG, **{k: v for k, v in lab.items() if k != "bg"})
        self.count_lbl.pack(anchor="w", padx=16, pady=(14, 3))
        lf = tk.Frame(w, bg=BG)
        lf.pack(fill="both", expand=True, padx=16)
        self.lb = tk.Listbox(lf, bg=CARD, fg=FG, selectbackground=SEL, selectforeground=FG,
                             relief="flat", font=("Segoe UI", 10), highlightthickness=1,
                             highlightbackground=LINE, activestyle="none", selectmode="extended")
        sb = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sb.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.lb.bind("<Delete>", lambda e: self.remove())

        bot = tk.Frame(w, bg=BG)
        bot.pack(fill="x", padx=16, pady=14)
        if not readonly:
            RoundButton(bot, t("ed_remove"), self.remove, CARD, FG, LINE, width=130, height=34,
                        parent_bg=BG).pack(side="left")
            RoundButton(bot, t("ed_save"), self.save, ACCENT, ONACC, HOVER, width=100,
                        height=34, parent_bg=BG).pack(side="right")
            RoundButton(bot, t("ed_cancel"), w.destroy, CARD, FG, LINE, width=90, height=34,
                        parent_bg=BG).pack(side="right", padx=8)
        else:
            RoundButton(bot, t("close"), w.destroy, CARD, FG, LINE, width=90, height=34,
                        parent_bg=BG).pack(side="right")
        self._fill()

    def _fill(self):
        self.lb.delete(0, "end")
        for n in self.names:
            self.lb.insert("end", n)
        self.count_lbl.config(text=self.app.t("ed_names", len(self.names)).upper())

    def _add_names(self, items):
        for s in items:
            if not any(s.lower() == n.lower() for n in self.names):
                self.names.append(s)

    def _copy_current(self):
        if self.copy_var.get():
            self._add_names(self.tool.names)
            self._fill()

    def add(self):
        self._add_names(split_names(self.add_e.get()))
        self.add_e.delete(0, "end")
        self._fill()
        self.lb.see("end")

    def remove(self):
        for i in sorted(self.lb.curselection(), reverse=True):
            del self.names[i]
        self._fill()

    def save(self):
        t = self.app.t
        nm = self.name_var.get().strip()
        if self.is_new:
            if not nm:
                messagebox.showerror("Slave", t("err_name_empty"), parent=self.win)
                return
            if nm.lower() in [c.lower() for c in self.tool.cfgs]:
                messagebox.showerror("Slave", t("err_name_exists"), parent=self.win)
                return
        self.win.destroy()
        self.on_save(nm, list(self.names))


class ToolCfg:
    def __init__(self, app, key, default_names, data):
        self.app, self.key, self.default_names = app, key, list(default_names)
        data = data if isinstance(data, dict) else {}
        cfgs = data.get("configs") if isinstance(data.get("configs"), dict) else {}
        old_def = cfgs.get(DEFAULT_CFG) if isinstance(cfgs.get(DEFAULT_CFG), dict) else {}
        cfgs[DEFAULT_CFG] = {"names": None,
                             "disabled": [n for n in old_def.get("disabled", []) if n in self.default_names]}
        for k, v in list(cfgs.items()):
            if k != DEFAULT_CFG:
                if not isinstance(v, dict) or not isinstance(v.get("names"), list):
                    del cfgs[k]
                else:
                    v.setdefault("disabled", [])
        self.cfgs = cfgs
        self.active = data.get("active") if data.get("active") in cfgs else DEFAULT_CFG
        self.names, self.enabled = [], {}
        self.combo = None
        self.sel_fr = None
        self.on_load = lambda: None
        self.on_toggle = lambda: None
        self.apply()

    def apply(self):
        c = self.cfgs[self.active]
        self.names = list(self.default_names) if c.get("names") is None else list(c["names"])
        dis = set(c.get("disabled", []))
        self.enabled = {n: tk.BooleanVar(value=n not in dis) for n in self.names}

    def store_disabled(self):
        if self.active in self.cfgs:
            self.cfgs[self.active]["disabled"] = [n for n in self.names if not self.enabled[n].get()]

    def data_out(self):
        self.store_disabled()
        return {"active": self.active, "configs": self.cfgs}

    def busy(self):
        return self.key == "browse" and self.app.scanning

    def build_ui(self, card):
        app = self.app
        bar = tk.Frame(card, bg=PANEL)
        bar.pack(fill="x", padx=12, pady=(10, 0))
        lc = tk.Label(bar, bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold"))
        lc.pack(side="left", padx=(0, 8))
        app.reg(lambda: lc.config(text=app.t("cfg_label")))
        self.combo = ttk.Combobox(bar, state="readonly", width=26, style="Dark.TCombobox",
                                  font=("Segoe UI", 10))
        self.combo.pack(side="left", ipady=3, padx=(0, 10))
        self.combo.bind("<<ComboboxSelected>>", self._picked)
        for key, cmd, bg, fg, hov, w in (
                ("cfg_new", self.new, ACCENT2, "#ffffff", HOVER2, 120),
                ("cfg_edit", self.edit, CARD, FG, LINE, 130),
                ("cfg_del", self.delete, DANGER, RED, DANGER_H, 80)):
            b = RoundButton(bar, "", cmd, bg, fg, hov, width=w, height=32, parent_bg=PANEL)
            b.pack(side="left", padx=(0, 8))
            app.reg(lambda b=b, k=key: b.set_text(app.t(k)))

        head = tk.Frame(card, bg=PANEL)
        head.pack(fill="x", padx=12, pady=(12, 0))
        l1 = tk.Label(head, bg=PANEL, fg=MUTED, font=("Segoe UI", 8, "bold"))
        l1.pack(side="left")
        l2 = tk.Label(head, bg=PANEL, fg=MUTED, font=("Segoe UI", 8))
        l2.pack(side="left", padx=8)
        app.reg(lambda: l1.config(text=app.t("names_head")))
        app.reg(lambda: l2.config(text=app.t("names_hint")))
        for key, val in (("all_off", False), ("all_on", True)):
            b = RoundButton(head, "", lambda v=val: self.set_all(v), CARD, FG, LINE,
                            width=120, height=26, font=("Segoe UI", 8, "bold"), parent_bg=PANEL)
            b.pack(side="right", padx=(6, 0))
            app.reg(lambda b=b, k=key: b.set_text(app.t(k)))
        self.sel_fr = tk.Frame(card, bg=PANEL)
        self.sel_fr.pack(fill="x", padx=12, pady=(2, 10))
        self.refresh_combo()
        self.build_checks()

    def refresh_combo(self):
        order = [DEFAULT_CFG] + sorted((k for k in self.cfgs if k != DEFAULT_CFG), key=str.lower)
        self.combo.config(values=order)
        self.combo.set(self.active)

    def build_checks(self):
        for w in self.sel_fr.winfo_children():
            w.destroy()
        items = [tk.Checkbutton(self.sel_fr, text=name, variable=self.enabled[name],
                                command=self.toggled, width=14, anchor="w",
                                **self.app.ck(PANEL)) for name in self.names]
        flow_layout(self.sel_fr, items, 142)

    def toggled(self):
        self.app.save_config()
        self.on_toggle()

    def set_all(self, value):
        for v in self.enabled.values():
            v.set(value)
        self.app.save_config()
        self.on_toggle()
        self.app.dlog("INFO", "log_all_on" if value else "log_all_off")

    def _picked(self, _e=None):
        name = self.combo.get()
        if name == self.active:
            return
        if self.busy():
            self.combo.set(self.active)
            self.app.dlog("WARN", "log_busy")
            return
        self.load(name)

    def load(self, name, log="log_cfg_loaded"):
        if name not in self.cfgs:
            return
        self.store_disabled()
        self.active = name
        self.apply()
        self.refresh_combo()
        self.build_checks()
        self.on_load()
        self.app.save_config()
        self.app.dlog("OK", log, name)

    def new(self):
        if self.busy():
            self.app.dlog("WARN", "log_busy")
            return
        ConfigEditor(self.app, self, "", [], True, False, self.saved)

    def edit(self):
        if self.busy():
            self.app.dlog("WARN", "log_busy")
            return
        ConfigEditor(self.app, self, self.active, self.names, False,
                     self.active == DEFAULT_CFG, self.saved)

    def saved(self, name, names):
        old = self.cfgs.get(name, {})
        self.cfgs[name] = {"names": names, "disabled": [d for d in old.get("disabled", []) if d in names]}
        if name == self.active:
            self.active = None
        self.load(name, "log_cfg_saved")

    def delete(self):
        if self.active == DEFAULT_CFG:
            messagebox.showinfo("Slave", self.app.t("del_default"))
            return
        if self.busy():
            self.app.dlog("WARN", "log_busy")
            return
        name = self.active
        if messagebox.askyesno(self.app.t("cfg_del"), self.app.t("del_confirm", name)):
            del self.cfgs[name]
            self.active = None
            self.load(DEFAULT_CFG)
            self.app.dlog("INFO", "log_cfg_deleted", name)


class AppearanceDialog:
    def __init__(self, app, geo=None):
        self.app = app
        t = app.t
        w = self.win = tk.Toplevel(app.root)
        w.title(t("ap_title"))
        w.configure(bg=BG)
        w.geometry(geo or "460x800")
        w.resizable(False, False)
        w.transient(app.root)
        lab = dict(bg=BG, fg=MUTED, font=("Segoe UI", 8, "bold"))

        tk.Label(w, text=t("ap_theme").upper(), **lab).pack(anchor="w", padx=18, pady=(18, 8))
        grid = tk.Frame(w, bg=BG)
        grid.pack(anchor="w", padx=18)
        for i, key in enumerate(THEME_ORDER):
            r, c = divmod(i, 3)
            cell = tk.Frame(grid, bg=BG)
            cell.grid(row=r, column=c, padx=(0, 12), pady=(0, 8))
            th = THEMES[key]
            sel = key == app.theme
            cv = tk.Canvas(cell, width=124, height=66, bg=BG, highlightthickness=0, cursor="hand2")
            rounded_rect(cv, 2, 2, 122, 64, 14, fill=ACCENT if sel else th["LINE"], outline="")
            rounded_rect(cv, 4, 4, 120, 62, 12, fill=th["BG"], outline="")
            rounded_rect(cv, 14, 13, 110, 25, 5, fill=th["CARD"], outline="")
            rounded_rect(cv, 14, 36, 70, 54, 9, fill=th["ACCENT"], outline="")
            rounded_rect(cv, 17, 38, 67, 44, 3, fill=lerp(th["ACCENT"], "#ffffff", 0.3), outline="")
            cv.create_oval(84, 36, 102, 54, fill=th["ACCENT2"], outline="")
            cv.pack()
            cv.bind("<Button-1>", lambda e, k=key: app.apply_look(theme=k))
            tk.Label(cell, text=t("th_" + key), bg=BG, fg=FG if sel else MUTED,
                     font=("Segoe UI", 9, "bold" if sel else "normal")).pack(pady=(3, 0))

        tk.Label(w, text=t("ap_bg").upper(), **lab).pack(anchor="w", padx=18, pady=(14, 6))
        name = os.path.basename(app.bg_image) if app.bg_image else t("ap_none")
        tk.Label(w, text=name, bg=BG, fg=FG if app.bg_image else MUTED, font=("Segoe UI", 9),
                 anchor="w", wraplength=420, justify="left").pack(anchor="w", padx=18)
        row = tk.Frame(w, bg=BG)
        row.pack(anchor="w", padx=18, pady=8)
        RoundButton(row, t("ap_pick"), self.pick, ACCENT, ONACC, HOVER, width=150, height=34,
                    parent_bg=BG).pack(side="left", padx=(0, 8))
        RoundButton(row, t("ap_remove"), lambda: app.apply_look(image=""), CARD, FG, LINE,
                    width=150, height=34, parent_bg=BG).pack(side="left")

        tk.Label(w, text=t("ap_blur").upper(), **lab).pack(anchor="w", padx=18, pady=(10, 0))
        self.sc = tk.Scale(w, from_=0, to=30, orient="horizontal", length=410, bg=BG, fg=FG,
                           troughcolor=CARD, highlightthickness=0, bd=0, activebackground=ACCENT,
                           font=("Segoe UI", 9))
        self.sc.set(app.bg_blur)
        self.sc.pack(anchor="w", padx=18)
        self.sc.bind("<ButtonRelease-1>", lambda e: app.apply_look(blur=int(self.sc.get())))

        tk.Label(w, text=t("ap_opacity").upper(), **lab).pack(anchor="w", padx=18, pady=(10, 0))
        self.op = tk.Scale(w, from_=40, to=100, orient="horizontal", length=410, bg=BG, fg=FG,
                           troughcolor=CARD, highlightthickness=0, bd=0, activebackground=ACCENT,
                           font=("Segoe UI", 9))
        self.op.set(app.ui_opacity)
        self.op.config(command=lambda v: app.set_opacity(int(float(v)), save=False))
        self.op.pack(anchor="w", padx=18)
        self.op.bind("<ButtonRelease-1>", lambda e: app.set_opacity(int(self.op.get())))
        tk.Label(w, text=t("ap_hint") + "\n" + t("ap_opacity_hint"), bg=BG, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=420, justify="left").pack(
            anchor="w", padx=18, pady=(4, 0))
        if not PIL_OK:
            tk.Label(w, text=f"Pillow: {PIL_ERR}\nPython: {sys.executable}", bg=BG, fg=AMBER,
                     font=("Segoe UI", 8), wraplength=420, justify="left").pack(
                anchor="w", padx=18, pady=(8, 4))
            self.inst_btn = RoundButton(w, t("ap_install"), self.install_pil, ACCENT2, "#ffffff",
                                        HOVER2, width=170, height=34, parent_bg=BG)
            self.inst_btn.pack(anchor="w", padx=18)
        bot = tk.Frame(w, bg=BG)
        bot.pack(fill="x", side="bottom", padx=18, pady=14)
        RoundButton(bot, t("close"), w.destroy, CARD, FG, LINE, width=90, height=34,
                    parent_bg=BG).pack(side="right")

    def _alive(self):
        try:
            return self.win.winfo_exists()
        except tk.TclError:
            return False

    def install_pil(self):
        app = self.app
        t = app.t
        self.inst_btn.set_text(t("ap_installing"))
        self.inst_btn.set_enabled(False)

        def done(ok, out):
            parent = self.win if self._alive() else app.root
            if ok and try_import_pil():
                messagebox.showinfo("Slave", t("ap_install_ok"), parent=parent)
                app.apply_look()
            else:
                if self._alive():
                    self.inst_btn.set_text(t("ap_install"))
                    self.inst_btn.set_enabled(True)
                messagebox.showerror("Slave", t("ap_install_fail", out or PIL_ERR), parent=parent)

        def work():
            try:
                r = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pillow"],
                                   capture_output=True, text=True, timeout=300,
                                   creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                ok, out = r.returncode == 0, (r.stdout + r.stderr).strip()[-600:]
            except Exception as e:
                ok, out = False, str(e)
            app.root.after(0, done, ok, out)

        threading.Thread(target=work, daemon=True).start()

    def pick(self):
        t = self.app.t
        if not PIL_OK:
            if messagebox.askyesno("Slave", t("ap_need_pil", sys.executable, PIL_ERR),
                                   parent=self.win):
                self.install_pil()
            return
        fn = filedialog.askopenfilename(
            parent=self.win,
            filetypes=[(t("img_type"), "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("*", "*.*")])
        if fn:
            self.app.apply_look(image=fn)


class Veil:
    MAX_ALPHA = 0.6

    def __init__(self, app):
        self.app = app
        self.win = None
        self.label = None
        self.photo = None

    def _create(self):
        w = tk.Toplevel(self.app.root)
        w.overrideredirect(True)
        w.transient(self.app.root)
        w.configure(bg=BG)
        self.label = tk.Label(w, bd=0, highlightthickness=0, bg=BG, anchor="nw")
        self.label.pack(fill="both", expand=True)
        set_alpha(w, 0.0)
        w.geometry("1x1+0+0")
        w.update_idletasks()
        if os.name == "nt":
            try:
                user32 = ctypes.windll.user32
                hwnd = user32.GetParent(w.winfo_id()) or w.winfo_id()
                style = user32.GetWindowLongW(hwnd, -20)
                user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20 | 0x80 | 0x8000000)
            except Exception:
                pass
        self.win = w

    def hide(self):
        if self.win is not None:
            try:
                self.win.withdraw()
            except tk.TclError:
                pass

    def sync(self):
        app = self.app
        try:
            show = (app.bg_on and app.ui_opacity < 100 and app._bg_photo is not None
                    and app.root.state() == "normal")
            if not show:
                self.hide()
                return
            main = app.main
            W, H = main.winfo_width(), main.winfo_height()
            if W < 20 or H < 20:
                self.hide()
                return
            if self.win is None:
                self._create()
            if self.photo is not app._bg_photo:
                self.photo = app._bg_photo
                self.label.config(image=self.photo)
            self.win.geometry(f"{W}x{H}+{main.winfo_rootx()}+{main.winfo_rooty()}")
            set_alpha(self.win, min(self.MAX_ALPHA, (100 - app.ui_opacity) / 100.0))
            if self.win.state() == "withdrawn":
                self.win.deiconify()
        except tk.TclError:
            pass


KW_X = dict(fill="x", padx=12, pady=(10, 0))
KW_EXP = dict(fill="both", expand=True, padx=12, pady=(10, 0))
KW_BAR = dict(fill="x", padx=12, pady=10)
BLOB_SPECS = [
    (0.20, 0.30, 0.10, 0.08, 0.21, 0.17, 0.0, 260),
    (0.75, 0.25, 0.08, 0.12, 0.15, 0.23, 1.7, 300),
    (0.55, 0.75, 0.12, 0.08, 0.19, 0.13, 3.1, 280),
    (0.90, 0.80, 0.07, 0.10, 0.25, 0.20, 4.4, 220),
    (0.35, 0.90, 0.09, 0.07, 0.17, 0.27, 5.2, 200),
]
BLOB_RINGS = 8


class SlaveApp:
    PW = 400

    def __init__(self, root):
        self.root = root
        root.title("Slave")
        height = max(640, min(900, root.winfo_screenheight() - 90))
        root.geometry(f"1200x{height}")
        root.minsize(900, 620)

        cfg = load_config()
        self.lang = cfg.get("lang") if cfg.get("lang") in LANGS else sys_lang()
        self.theme = cfg.get("theme") if cfg.get("theme") in THEMES else "blue"
        set_theme(self.theme)
        root.configure(bg=BG)
        self.bg_image = cfg.get("bg_image") if isinstance(cfg.get("bg_image"), str) else ""
        try:
            self.bg_blur = max(0, min(30, int(cfg.get("bg_blur", 14))))
        except (TypeError, ValueError):
            self.bg_blur = 14
        try:
            self.ui_opacity = max(40, min(100, int(cfg.get("ui_opacity", 100))))
        except (TypeError, ValueError):
            self.ui_opacity = 100
        self._tr = []

        tools = cfg.get("tools") if isinstance(cfg.get("tools"), dict) else {}
        self.bcfg = ToolCfg(self, "browse", DEFAULT_NAMES, tools.get("browse"))
        self.dcfg = ToolCfg(self, "data", DATA_DEFAULT_NAMES, tools.get("data"))
        self.bcfg.on_load = self._b_loaded
        self.dcfg.on_load = self._d_render
        self.dcfg.on_toggle = self._d_render
        self.temp = []

        self.results = {}
        self.row_path = {}
        self.chips = {}
        self.filter = None
        self.scanning = False
        self.stop = False
        self.status = ("status_ready",)
        self.engine = "—"
        self.log_lines = []
        self.logs_open = False
        self._log_w = 0
        self._slide_id = 0
        self._t0 = time.time()
        self.notice_state = None
        self.d_notice_state = None
        self.page = "browse"
        self.data_rows, self.data_prev, self.data_busy = [], {}, False
        self.dsort = ("total", True)
        self.var_whole = tk.BooleanVar(value=bool(cfg.get("whole", False)))
        self.var_sys = tk.BooleanVar(value=bool(cfg.get("hide_sys", True)))
        self.var_dauto = tk.BooleanVar(value=False)
        self.var_donly = tk.BooleanVar(value=bool(cfg.get("data_only_list", True)))

        self.ap_dialog = None
        self._bg_job = None
        self._bg_key = None
        self._bg_photo = None
        self._src_path = None
        self._src = None
        self.bg_on = False
        self.veil = Veil(self)

        self._build_ui()
        root.bind("<Configure>", self._root_cfg, add="+")
        root.bind("<Unmap>", lambda e: e.widget is root and self.veil.hide(), add="+")
        root.bind("<Map>", lambda e: e.widget is root and root.after(60, self.veil.sync), add="+")
        self._animate()
        self.root.after(AUTO_SECONDS * 1000, self._d_auto_tick)

    @property
    def names(self):
        return self.bcfg.names

    @property
    def enabled(self):
        return self.bcfg.enabled

    def ck(self, bg):
        return dict(bg=bg, fg=MUTED, selectcolor=CARD, activebackground=bg, activeforeground=FG,
                    font=("Segoe UI", 9), highlightthickness=0, bd=0, cursor="hand2")

    def t(self, key, *a):
        s = TXT[self.lang].get(key) or TXT["en"][key]
        return s.format(*a) if a else s

    def reg(self, fn):
        self._tr.append(fn)
        fn()

    def apply_lang(self):
        for fn in self._tr:
            fn()
        self._refresh_scan_btn()
        for code, b in self.btn_lang.items():
            if code == self.lang:
                b.set_colors(ACCENT2, "#ffffff", HOVER2)
            else:
                b.set_colors(CARD, MUTED, LINE)
        if self.notice_state:
            key, color = self.notice_state
            self.notice.config(text=self.t(key), fg=color)
        if self.d_notice_state:
            key, color = self.d_notice_state
            self.dnotice.config(text=self.t(key), fg=color)
        self._render()
        self._d_render()

    def set_lang(self, code):
        self.lang = code
        self.apply_lang()
        self.save_config()

    def _refresh_scan_btn(self):
        if self.scanning:
            self.btn_scan.set_text(self.t("stop"))
            self.btn_scan.set_colors(DANGER, RED, DANGER_H)
        else:
            self.btn_scan.set_text(self.t("scan"))
            self.btn_scan.set_colors(ACCENT, ONACC, HOVER)

    def save_config(self):
        data = {
            "lang": self.lang,
            "theme": self.theme,
            "bg_image": self.bg_image,
            "bg_blur": self.bg_blur,
            "ui_opacity": self.ui_opacity,
            "tools": {"browse": self.bcfg.data_out(), "data": self.dcfg.data_out()},
            "whole": self.var_whole.get(),
            "hide_sys": self.var_sys.get(),
            "data_only_list": self.var_donly.get(),
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def _build_ui(self):
        self._tr = []
        self.chips = {}
        self.page_cards = {}
        self.bg_on = False
        self._bg_key = None
        self.root.configure(bg=BG)
        self._build_style()
        self._build_logpanel()
        self._build_bgitems()
        self._build_header()
        self._build_tabs()
        self._build_browse()
        self._build_data()
        self.apply_lang()
        self.show_page(self.page)
        if self.notice_state:
            self._show_notice(*self.notice_state)
        if self.d_notice_state:
            self._d_show_notice(*self.d_notice_state)
        if self.logs_open:
            self.btn_logs.set_text("Logs", FG)
        self.main.bind("<Configure>", self._on_main_cfg)
        self.root.after(60, self._load_bg)

    def rebuild(self):
        self.logpanel.destroy()
        self.main.destroy()
        self._build_ui()

    def apply_look(self, theme=None, image=None, blur=None):
        if theme is not None:
            self.theme = theme
            set_theme(theme)
        if image is not None:
            self.bg_image = image
        if blur is not None:
            self.bg_blur = blur
        self.save_config()
        geo = None
        if self.ap_dialog and self.ap_dialog.win.winfo_exists():
            geo = self.ap_dialog.win.geometry()
            self.ap_dialog.win.destroy()
        self.rebuild()
        self.dlog("INFO", "log_look")
        if geo:
            self.open_appearance(geo)

    def set_opacity(self, value, save=True):
        self.ui_opacity = max(40, min(100, int(value)))
        if save:
            self.save_config()
        self.veil.sync()

    def open_appearance(self, geo=None):
        if self.ap_dialog and self.ap_dialog.win.winfo_exists():
            self.ap_dialog.win.lift()
            return
        self.ap_dialog = AppearanceDialog(self, geo if isinstance(geo, str) else None)

    def _build_style(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=FG,
                     rowheight=28, borderwidth=0, font=("Segoe UI", 10))
        st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.configure("Treeview.Heading", background=PANEL, foreground=MUTED, relief="flat",
                     font=("Segoe UI", 9, "bold"), borderwidth=0, padding=(8, 6))
        st.map("Treeview", background=[("selected", SEL)], foreground=[("selected", FG)])
        st.map("Treeview.Heading", background=[("active", PANEL)])
        st.configure("Vertical.TScrollbar", background=LINE, troughcolor=PANEL, bordercolor=PANEL,
                     arrowcolor=MUTED, lightcolor=LINE, darkcolor=LINE)
        st.configure("Dark.TCombobox", fieldbackground=CARD, background=LINE, foreground=FG,
                     arrowcolor=MUTED, bordercolor=LINE, lightcolor=CARD, darkcolor=CARD,
                     selectbackground=CARD, selectforeground=FG)
        st.map("Dark.TCombobox", fieldbackground=[("readonly", CARD)],
               foreground=[("readonly", FG)], selectbackground=[("readonly", CARD)],
               selectforeground=[("readonly", FG)])
        self.root.option_add("*TCombobox*Listbox.background", CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)
        self.root.option_add("*TCombobox*Listbox.selectBackground", SEL)
        self.root.option_add("*TCombobox*Listbox.selectForeground", FG)

    def _build_bgitems(self):
        cv = self.main
        self.bg_item = cv.create_image(0, 0, anchor="nw")
        self.blobs = []
        for _spec in BLOB_SPECS:
            ids = []
            for k in range(BLOB_RINGS):
                ids.append(cv.create_oval(0, 0, 0, 0, outline="",
                                          fill=lerp(BG, ACCENT, 0.03 + k * 0.012)))
            self.blobs.append(ids)

    def _root_cfg(self, e):
        if e.widget is self.root:
            self.root.after_idle(self.veil.sync)

    def _on_main_cfg(self, e):
        if e.widget is not self.main:
            return
        if self._bg_job:
            try:
                self.root.after_cancel(self._bg_job)
            except Exception:
                pass
        self._bg_job = self.root.after(130, self._load_bg)

    def _load_bg(self):
        self._bg_job = None
        cv = self.main
        W, H = cv.winfo_width(), cv.winfo_height()
        if W < 20 or H < 20:
            return
        path = self.bg_image
        use = bool(path) and PIL_OK and os.path.isfile(path)
        if use:
            key = (path, self.bg_blur, W, H, BG)
            if key != self._bg_key:
                try:
                    self._bg_photo = self._make_bg(path, W, H)
                    self._bg_key = key
                except Exception as e:
                    self.dlog_raw("ERROR", f"background: {e}")
                    use = False
        self.bg_on = use
        if use:
            cv.itemconfig(self.bg_item, image=self._bg_photo, state="normal")
        else:
            cv.itemconfig(self.bg_item, state="hidden")
        for ids in self.blobs:
            for oid in ids:
                cv.itemconfig(oid, state="hidden" if use else "normal")
        self.veil.sync()

    def _make_bg(self, path, W, H):
        if self._src_path != path:
            img = Image.open(path).convert("RGB")
            img.thumbnail((2400, 2400))
            self._src, self._src_path = img, path
        img = self._src
        iw, ih = img.size
        s = max(W / iw, H / ih)
        img = img.resize((max(W, int(iw * s) + 1), max(H, int(ih * s) + 1)),
                         getattr(Image, "Resampling", Image).LANCZOS)
        l, tp = (img.width - W) // 2, (img.height - H) // 2
        img = img.crop((l, tp, l + W, tp + H))
        if self.bg_blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(self.bg_blur))
        img = Image.blend(img, Image.new("RGB", (W, H), BG), 0.35)
        return ImageTk.PhotoImage(img)

    def _build_header(self):
        self.hdr = tk.Canvas(self.main, height=64, bg=PANEL, highlightthickness=0)
        self.hdr.pack(fill="x", padx=12, pady=(12, 0))
        self.orb_glow = self.hdr.create_oval(0, 0, 0, 0, fill=PANEL, outline="")
        self.orb = self.hdr.create_oval(26, 24, 42, 40, fill=GREEN, outline="")
        self.hdr.create_text(62, 24, text="S L A V E", anchor="w", fill=FG,
                             font=("Segoe UI", 15, "bold"))
        self.hdr.create_text(190, 27, text=CREDIT, anchor="w", fill=MUTED, font=("Segoe UI", 8))
        self.sub_txt = self.hdr.create_text(62, 46, text="", anchor="w", fill=MUTED,
                                            font=("Segoe UI", 9))
        self.btn_scan = RoundButton(self.hdr, "", self.toggle_scan, ACCENT, ONACC, HOVER,
                                    width=92, height=32)
        self.btn_logs = RoundButton(self.hdr, "Logs", self.toggle_logs, CARD, FG, LINE,
                                    width=76, height=32)
        self.btn_look = RoundButton(self.hdr, "🖌", self.open_appearance, CARD, FG, LINE,
                                    width=44, height=32, font=("Segoe UI", 12))
        self.w_scan = self.hdr.create_window(0, 32, window=self.btn_scan, anchor="e")
        self.w_logs = self.hdr.create_window(0, 32, window=self.btn_logs, anchor="e")
        self.w_look = self.hdr.create_window(0, 32, window=self.btn_look, anchor="e")
        self.btn_lang, self.w_lang = {}, {}
        for code in LANGS:
            b = RoundButton(self.hdr, code.upper(), lambda c=code: self.set_lang(c), CARD, MUTED,
                            LINE, width=44, height=30, font=("Segoe UI", 9, "bold"))
            self.btn_lang[code] = b
            self.w_lang[code] = self.hdr.create_window(0, 32, window=b, anchor="e")
        self.hdr.bind("<Configure>", self._layout_header)

    def _layout_header(self, e):
        x = e.width - 16
        self.hdr.coords(self.w_scan, x, 32)
        x -= 92 + 10
        self.hdr.coords(self.w_logs, x, 32)
        x -= 76 + 8
        self.hdr.coords(self.w_look, x, 32)
        x -= 44 + 16
        for i, code in enumerate(LANGS):
            self.hdr.coords(self.w_lang[code], x - (len(LANGS) - 1 - i) * 50, 32)

    def _build_tabs(self):
        tabs = tk.Frame(self.main, bg=PANEL)
        tabs.pack(fill="x", padx=12, pady=(10, 0))
        self.tab_btn = {}
        for key, w in (("browse", 130), ("data", 170)):
            b = RoundButton(tabs, "", lambda k=key: self.show_page(k), CARD, MUTED, LINE,
                            width=w, height=34, parent_bg=PANEL)
            b.pack(side="left", padx=(12, 0), pady=10)
            self.tab_btn[key] = b
            self.reg(lambda b=b, k=key: b.set_text(self.t("tab_" + k)))

    def show_page(self, key):
        self.page = key
        for lst in self.page_cards.values():
            for w, _ in lst:
                w.pack_forget()
        for w, kw in self.page_cards[key]:
            w.pack(**kw)
        for k, b in self.tab_btn.items():
            if k == key:
                b.set_colors(ACCENT, ONACC, HOVER)
            else:
                b.set_colors(CARD, MUTED, LINE)
        if key == "data" and not self.data_rows and not self.data_busy:
            self.d_refresh()

    def _build_browse(self):
        cA = tk.Frame(self.main, bg=PANEL)
        self.bcfg.build_ui(cA)

        cB = tk.Frame(self.main, bg=PANEL)
        self.chips_fr = tk.Frame(cB, bg=PANEL)
        self.chips_fr.pack(fill="x", padx=12, pady=(10, 4))
        row = tk.Frame(cB, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(6, 2))
        self.entry = tk.Entry(row, bg=CARD, fg=FG, insertbackground=FG, relief="flat",
                              font=("Segoe UI", 10), highlightthickness=1,
                              highlightbackground=LINE, highlightcolor=ACCENT)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.entry.bind("<Return>", lambda e: self.quick_search())
        b = RoundButton(row, "", self.quick_search, ACCENT, ONACC, HOVER,
                        width=100, height=32, parent_bg=PANEL)
        b.pack(side="left")
        self.reg(lambda: b.set_text(self.t("search")))
        hint = tk.Label(cB, bg=PANEL, fg=MUTED, font=("Segoe UI", 8), anchor="w",
                        justify="left", wraplength=950)
        hint.pack(fill="x", padx=14)
        self.reg(lambda: hint.config(text=self.t("entry_hint")))
        opts = tk.Frame(cB, bg=PANEL)
        opts.pack(fill="x", padx=12, pady=(6, 10))
        c1 = tk.Checkbutton(opts, variable=self.var_sys, command=self._sys_changed, **self.ck(PANEL))
        c1.pack(side="left")
        c2 = tk.Checkbutton(opts, variable=self.var_whole, command=self._whole_changed, **self.ck(PANEL))
        c2.pack(side="left", padx=16)
        self.reg(lambda: c1.config(text=self.t("ck_sys")))
        self.reg(lambda: c2.config(text=self.t("ck_whole")))

        self.tree_fr = tk.Frame(self.main, bg=PANEL)
        inner = tk.Frame(self.tree_fr, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        cols = ("kw", "name", "path", "size", "date")
        self.tree = ttk.Treeview(inner, columns=cols, show="headings", selectmode="browse")
        for c, w, anchor in (("kw", 80, "w"), ("name", 210, "w"), ("path", 400, "w"),
                             ("size", 80, "e"), ("date", 130, "w")):
            self.tree.heading(c, text=c, anchor=anchor)
            self.tree.column(c, width=w, anchor=anchor, stretch=(c == "path"))
        self.reg(lambda: [self.tree.heading(c, text=self.t("col_" + c)) for c in cols])
        self.tree.tag_configure("odd", background=ROW_ALT)
        self.tree.tag_configure("even", background=CARD)
        sb = ttk.Scrollbar(inner, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", lambda e: self.show_in_folder())
        self.notice = tk.Label(self.tree_fr, bg=CARD, fg=MUTED, font=("Segoe UI", 11),
                               justify="center")

        bar = tk.Frame(self.main, bg=PANEL, height=64)
        bar.pack_propagate(False)
        for key, cmd, w in (("show", self.show_in_folder, 158),
                            ("copy_path", self.copy_path, 150),
                            ("export", self.export_txt, 132)):
            b = RoundButton(bar, "", cmd, CARD, FG, LINE, width=w, height=36)
            b.pack(side="left", padx=(14, 0))
            self.reg(lambda b=b, k=key: b.set_text(self.t(k)))
        self.summary = tk.Label(bar, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
        self.summary.pack(side="right", padx=16)

        self.page_cards["browse"] = [(cA, KW_X), (cB, KW_X), (self.tree_fr, KW_EXP), (bar, KW_BAR)]
        self._build_chips()

    def _b_loaded(self):
        self.temp, self.results, self.filter = [], {}, None
        self._hide_notice()
        self._build_chips()
        self._render()

    def _build_chips(self):
        for w in self.chips_fr.winfo_children():
            w.destroy()
        self.chips = {}
        items = []
        for name in self.names + self.temp:
            b = RoundButton(self.chips_fr, name, lambda n=name: self.set_filter(n), CARD, MUTED,
                            LINE, width=136, height=28, font=("Segoe UI", 9, "bold"),
                            parent_bg=PANEL)
            self.chips[name] = b
            items.append(b)
        flow_layout(self.chips_fr, items, 144, padx=8)
        self._render()

    def _build_data(self):
        cA = tk.Frame(self.main, bg=PANEL)
        self.dcfg.build_ui(cA)

        cB = tk.Frame(self.main, bg=PANEL)
        row = tk.Frame(cB, bg=PANEL)
        row.pack(fill="x", padx=12, pady=(10, 2))
        self.dentry = tk.Entry(row, bg=CARD, fg=FG, insertbackground=FG, relief="flat",
                               font=("Segoe UI", 10), highlightthickness=1,
                               highlightbackground=LINE, highlightcolor=ACCENT)
        self.dentry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 8))
        self.dentry.bind("<KeyRelease>", lambda e: self._d_render())
        b = RoundButton(row, "", self.d_refresh, ACCENT, ONACC, HOVER,
                        width=100, height=32, parent_bg=PANEL)
        b.pack(side="left")
        self.reg(lambda: b.set_text(self.t("d_refresh")))
        hint = tk.Label(cB, bg=PANEL, fg=MUTED, font=("Segoe UI", 8), anchor="w")
        hint.pack(fill="x", padx=14)
        self.reg(lambda: hint.config(text=self.t("d_search_hint")))
        opts = tk.Frame(cB, bg=PANEL)
        opts.pack(fill="x", padx=12, pady=(6, 10))
        c1 = tk.Checkbutton(opts, variable=self.var_donly, command=self._d_only_changed, **self.ck(PANEL))
        c1.pack(side="left")
        c2 = tk.Checkbutton(opts, variable=self.var_dauto, **self.ck(PANEL))
        c2.pack(side="left", padx=16)
        self.reg(lambda: c1.config(text=self.t("d_only_list")))
        self.reg(lambda: c2.config(text=self.t("d_auto", AUTO_SECONDS)))

        fr = tk.Frame(self.main, bg=PANEL)
        inner = tk.Frame(fr, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=8, pady=8)
        self.dcols = ("app", "inst", "read", "write", "other", "total", "rate", "conn", "path")
        self.dtree = ttk.Treeview(inner, columns=self.dcols, show="headings", selectmode="browse")
        for c, w, anchor in (("app", 150, "w"), ("inst", 60, "e"), ("read", 90, "e"),
                             ("write", 90, "e"), ("other", 90, "e"), ("total", 90, "e"),
                             ("rate", 90, "e"), ("conn", 90, "e"), ("path", 300, "w")):
            self.dtree.column(c, width=w, anchor=anchor, stretch=(c == "path"))
        self.reg(lambda: [self.dtree.heading(c, text=self.t("dc_" + c),
                                             command=lambda c=c: self.d_sort(c))
                          for c in self.dcols])
        self.dtree.tag_configure("odd", background=ROW_ALT)
        self.dtree.tag_configure("even", background=CARD)
        sb = ttk.Scrollbar(inner, orient="vertical", command=self.dtree.yview)
        self.dtree.configure(yscrollcommand=sb.set)
        self.dtree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.dnotice = tk.Label(fr, bg=CARD, fg=MUTED, font=("Segoe UI", 11), justify="center")

        bar = tk.Frame(self.main, bg=PANEL, height=64)
        bar.pack_propagate(False)
        note = tk.Label(bar, bg=PANEL, fg=MUTED, font=("Segoe UI", 8), justify="left",
                        anchor="w", wraplength=620)
        note.pack(side="left", padx=16)
        self.reg(lambda: note.config(text=self.t("d_note")))
        self.dsummary = tk.Label(bar, text="", bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
        self.dsummary.pack(side="right", padx=16)

        self.page_cards["data"] = [(cA, KW_X), (cB, KW_X), (fr, KW_EXP), (bar, KW_BAR)]

    def _d_only_changed(self):
        self.save_config()
        self._d_render()

    def d_sort(self, col):
        asc_first = col in ("app", "path")
        if self.dsort[0] == col:
            self.dsort = (col, not self.dsort[1])
        else:
            self.dsort = (col, not asc_first)
        self._d_render()

    def d_refresh(self):
        if self.data_busy:
            return
        if os.name != "nt":
            self._d_show_notice("d_nowin", AMBER)
            return
        self.data_busy = True
        self.dlog("TOOL", "log_data_start")
        threading.Thread(target=self._d_worker, daemon=True).start()

    def _d_worker(self):
        t0 = time.time()
        try:
            rows = fetch_usage()
        except Exception as e:
            self.dlog("ERROR", "log_data_err", e)
            self.root.after(0, self._d_done, None, 0)
            return
        self.dlog("OK", "log_data_done", len(rows), f"{time.time() - t0:.1f}")
        self.root.after(0, self._d_done, rows, time.time())

    def _d_done(self, rows, now):
        self.data_busy = False
        if rows is None:
            return
        for r in rows:
            prev = self.data_prev.get(r["app"].lower())
            r["rate"] = max(0.0, (r["total"] - prev[0]) / max(now - prev[1], 0.001)) if prev else 0.0
            self.data_prev[r["app"].lower()] = (r["total"], now)
        self.data_rows = rows
        self._d_render()

    def _d_terms(self):
        typed = split_names(self.dentry.get())
        if typed:
            return typed
        if self.var_donly.get():
            return [n for n in self.dcfg.names if self.dcfg.enabled[n].get()]
        return None

    def _d_render(self):
        t = self.dtree
        t.delete(*t.get_children())
        terms = self._d_terms()
        rows = self.data_rows
        if terms is not None:
            low = [x.lower() for x in terms]
            rows = [r for r in rows if any(x in r["app"].lower() or x in r["path"].lower() for x in low)]
        key, desc = self.dsort
        keyf = (lambda r: r[key].lower()) if key in ("app", "path") else (lambda r: r[key])
        rows = sorted(rows, key=keyf, reverse=desc)
        for i, r in enumerate(rows):
            t.insert("", "end", tags=("odd" if i % 2 else "even",),
                     values=(r["app"], r["inst"], human(r["read"]), human(r["write"]),
                             human(r["other"]), human(r["total"]),
                             human(r["rate"]) + "/s" if r["rate"] else "—", r["conn"], r["path"]))
        self.dsummary.config(text=self.t("d_summary", len(rows), human(sum(r["total"] for r in rows))))
        if rows:
            self._d_hide_notice()
        elif self.data_rows:
            self._d_show_notice("d_nomatch", GREEN)

    def _d_show_notice(self, key, color=MUTED):
        self.d_notice_state = (key, color)
        self.dnotice.config(text=self.t(key), fg=color)
        self.dnotice.place(relx=0.5, rely=0.45, anchor="center")
        self.dnotice.lift()

    def _d_hide_notice(self):
        self.d_notice_state = None
        self.dnotice.place_forget()

    def _d_auto_tick(self):
        if self.var_dauto.get() and self.page == "data":
            self.d_refresh()
        self.root.after(AUTO_SECONDS * 1000, self._d_auto_tick)

    def quick_search(self):
        terms = []
        for s in split_names(self.entry.get()):
            s = next((n for n in self.names if n.lower() == s.lower()), s)
            if not any(s.lower() == o.lower() for o in terms):
                terms.append(s)
        if not terms:
            return
        if self.scanning:
            self.dlog("WARN", "log_busy")
            return
        self.temp = [x for x in terms if x not in self.names]
        self.entry.delete(0, "end")
        self.filter = None
        self._build_chips()
        self.dlog("INFO", "log_quick", ", ".join(terms))
        self.start_scan(names=terms)

    def _build_logpanel(self):
        PW = self.PW
        self.logpanel = tk.Frame(self.root, bg=PANEL, width=int(self._log_w))
        self.logpanel.pack(side="right", fill="y")
        self.logpanel.pack_propagate(False)
        self.main = tk.Canvas(self.root, bg=BG, highlightthickness=0, bd=0)
        self.main.pack(side="left", fill="both", expand=True)
        self.main.pack_propagate(False)

        inner = tk.Frame(self.logpanel, bg=PANEL, width=PW)
        inner.pack(side="left", fill="y")
        inner.pack_propagate(False)
        tk.Frame(inner, bg=LINE, width=1).pack(side="left", fill="y")
        body = tk.Frame(inner, bg=PANEL)
        body.pack(side="left", fill="both", expand=True)

        top = tk.Frame(body, bg=PANEL, height=64)
        top.pack(fill="x")
        top.pack_propagate(False)
        title = tk.Label(top, bg=PANEL, fg=FG, font=("Segoe UI", 12, "bold"))
        title.pack(side="left", padx=(14, 0))
        self.reg(lambda: title.config(text=self.t("logs_title")))
        small = ("Segoe UI", 9, "bold")
        for key, cmd, w, padx in (("close", self.toggle_logs, 76, (4, 12)),
                                  ("copy", self.copy_logs, 98, 4),
                                  ("clear", self.clear_logs, 84, 4)):
            b = RoundButton(top, "", cmd, CARD, FG, LINE, width=w, height=28, font=small)
            b.pack(side="right", padx=padx)
            self.reg(lambda b=b, k=key: b.set_text(self.t(k)))

        self.logbox = tk.Text(body, bg=BG, fg=FG, font=("Consolas", 9), wrap="word",
                              relief="flat", padx=10, pady=8, state="disabled", borderwidth=0,
                              highlightthickness=0, cursor="arrow", insertwidth=0, spacing1=2)
        self.logbox.pack(fill="both", expand=True)
        colors = {"INFO": MUTED, "TOOL": ACCENT, "OK": GREEN, "WARN": AMBER, "ERROR": RED}
        self.logbox.tag_config("ts", foreground=MUTED)
        for lvl, col in colors.items():
            self.logbox.tag_config(lvl, foreground=col)
            self.logbox.tag_config("b_" + lvl, foreground=col, font=("Consolas", 9, "bold"))
        for ts, level, text in self.log_lines:
            self._log_insert(ts, level, text)

    def toggle_logs(self):
        self.logs_open = not self.logs_open
        if self.logs_open:
            self.btn_logs.set_text("Logs", FG)
            self.logbox.see("end")
        self._slide_id += 1
        self._slide(self._slide_id, self.PW if self.logs_open else 0)

    def _slide(self, sid, target):
        if sid != self._slide_id:
            return
        diff = target - self._log_w
        cur = target if abs(diff) <= 3 else self._log_w + diff * 0.25 + (3 if diff > 0 else -3)
        cur = max(0, min(self.PW, cur))
        self._log_w = cur
        self.logpanel.config(width=int(cur))
        if cur != target:
            self.root.after(14, self._slide, sid, target)

    def dlog(self, level, key, *args):
        self.dlog_raw(level, self.t(key, *args))

    def dlog_raw(self, level, text):
        ts = datetime.now().strftime("%H:%M:%S")
        self.root.after(0, self._dlog_ui, ts, level, str(text))

    def _log_insert(self, ts, level, text):
        t = self.logbox
        t.config(state="normal")
        t.insert("end", ts + " ", "ts")
        t.insert("end", f"{level:<5} ", "b_" + level)
        t.insert("end", text + "\n", level)
        if int(t.index("end-1c").split(".")[0]) > 1500:
            t.delete("1.0", "400.0")
        t.see("end")
        t.config(state="disabled")

    def _dlog_ui(self, ts, level, text):
        self.log_lines.append((ts, level, text))
        if len(self.log_lines) > 1500:
            del self.log_lines[:400]
        self._log_insert(ts, level, text)
        if level == "ERROR" and not self.logs_open:
            self.btn_logs.set_text("Logs ●", RED)

    def clear_logs(self):
        self.log_lines = []
        self.logbox.config(state="normal")
        self.logbox.delete("1.0", "end")
        self.logbox.config(state="disabled")

    def copy_logs(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.logbox.get("1.0", "end"))
        self.dlog("INFO", "log_logs_copied")

    def _animate(self):
        try:
            self._tick()
        except tk.TclError:
            pass
        self.root.after(40, self._animate)

    def _tick(self):
        t = time.time() - self._t0
        busy = self.scanning or self.data_busy
        pulse = 0.5 + 0.5 * math.sin(t * (5.0 if busy else 1.6))
        col = AMBER if busy else GREEN
        r = 9 + 5 * pulse
        self.hdr.coords(self.orb_glow, 34 - r, 32 - r, 34 + r, 32 + r)
        self.hdr.itemconfig(self.orb_glow, fill=lerp(PANEL, col, 0.18 + 0.12 * pulse))
        self.hdr.itemconfig(self.orb, fill=col)
        dots = "." * (int(t * 3) % 4) if busy else ""
        cur = self.bcfg if self.page == "browse" else self.dcfg
        eng = f"  ·  Everything: {self.engine}" if self.page == "browse" else ""
        self.hdr.itemconfig(self.sub_txt,
                            text=f"{self.t(*self.status)}{dots}{eng}  ·  Config: {cur.active}")
        W = max(self.hdr.winfo_width(), 1)
        seg, n = 220, 22
        pos = (t * (760 if busy else 240)) % (W + seg) - seg
        self.hdr.delete("sweep")
        for i in range(n):
            x1 = pos + i * seg / n
            self.hdr.create_rectangle(x1, 61, x1 + seg / n + 1, 64, width=0, tags="sweep",
                                      fill=lerp(PANEL, ACCENT, math.sin(math.pi * i / (n - 1))))
        if not self.bg_on:
            cw, ch = self.main.winfo_width(), self.main.winfo_height()
            for (cx, cy, ax, ay, sx, sy, ph, rad), ids in zip(BLOB_SPECS, self.blobs):
                x = (cx + ax * math.sin(t * sx + ph)) * cw
                y = (cy + ay * math.cos(t * sy + ph)) * ch
                for k, oid in enumerate(ids):
                    rr = rad * (1 - k * 0.11)
                    self.main.coords(oid, x - rr, y - rr, x + rr, y + rr)

    def reveal(self):
        set_alpha(self.root, 0.0)
        self.root.deiconify()
        self.root.lift()

        def fade(a=0.0):
            a += 0.07
            set_alpha(self.root, min(a, 1.0))
            if a < 1.0:
                self.root.after(16, fade, a)
            else:
                self.veil.sync()
        fade()
        threading.Thread(target=self._boot, daemon=True).start()

    def _boot(self):
        state = start_everything()
        self.dlog("WARN" if state == "missing" else "OK", "log_ev_" + state)
        time.sleep(3.0 if state == "started" else 0.7)
        self.root.after(0, self.start_scan)

    def toggle_scan(self):
        if self.page == "data":
            self.d_refresh()
            return
        if self.scanning:
            self.stop = True
            self.dlog("WARN", "log_stop_req")
        else:
            self.start_scan()

    def _whole_changed(self):
        self.save_config()
        if not self.scanning:
            self.start_scan()

    def _sys_changed(self):
        self.save_config()
        self._render()

    def start_scan(self, names=None):
        if self.scanning:
            return
        if names is None:
            if self.temp:
                self.temp = []
                self._build_chips()
            names = [n for n in self.names if self.enabled[n].get()]
        if not names:
            self.results = {}
            self._render()
            self._show_notice("notice_none", AMBER)
            self.dlog("WARN", "log_skip")
            return
        self.scanning, self.stop = True, False
        self.results = {}
        self.filter = None
        self._hide_notice()
        self._render()
        self._refresh_scan_btn()
        threading.Thread(target=self._scan_worker, args=(self.var_whole.get(), names),
                         daemon=True).start()

    def _scan_worker(self, whole, names):
        es = find_es()
        self.dlog_raw("INFO", self.t("log_scan_start", ", ".join(names))
                      + (self.t("log_whole") if whole else ""))
        self.dlog("INFO", "log_es", es or self.t("log_es_none"))
        failed = False
        for i, name in enumerate(names, 1):
            if self.stop:
                self.dlog("WARN", "log_stopped")
                break
            self.status = ("status_scanning", name, i, len(names))
            self.dlog("TOOL", "log_searching", name)
            t0 = time.time()
            try:
                paths, engine = search_everything(name, whole)
            except EverythingError as e:
                self.dlog_raw("ERROR", f"{name}: {e}")
                if i == 1:
                    failed = True
                    self.root.after(0, self._show_notice, "notice_setup", AMBER)
                    break
                continue
            except Exception as e:
                self.dlog("ERROR", "log_unexpected", name, repr(e))
                continue
            infos = [(p, *file_info(p)) for p in paths]
            self.dlog("OK", "log_found", name, len(paths), f"{time.time() - t0:.1f}", engine)
            self.root.after(0, self._set_results, name, infos, engine)
        self.root.after(0, self._scan_done, failed)

    def _set_results(self, name, infos, engine):
        self.results[name] = infos
        self.engine = engine
        self._render()

    def _scan_done(self, failed):
        self.scanning = False
        self.status = ("status_error",) if failed else ("status_ready",)
        self._refresh_scan_btn()
        if failed:
            return
        counts = {n: len(self._visible(n)) for n in self.names + self.temp if n in self.results}
        total = sum(counts.values())
        self.dlog("OK", "log_done", ", ".join(f"{n}={c}" for n, c in counts.items()), total)
        if total == 0 and counts:
            self._show_notice("notice_nomatch", GREEN)

    def _visible(self, name):
        hide = self.var_sys.get()
        return [x for x in self.results.get(name, []) if not (hide and SYS_RE.match(x[0]))]

    def set_filter(self, name):
        self.filter = None if self.filter == name else name
        self._render()

    def _render(self):
        t = self.tree
        t.delete(*t.get_children())
        self.row_path.clear()
        shown = total = 0
        for name in self.names + self.temp:
            items = self._visible(name)
            total += len(items)
            chip = self.chips.get(name)
            active = self.filter == name
            if chip:
                if name in self.results:
                    chip.set_text(f"{name}  {len(items)}", fg=(ONACC if active else
                                                              (AMBER if items else MUTED)))
                else:
                    chip.set_text(name, fg=(ONACC if active else MUTED))
                if active:
                    chip.set_colors(ACCENT, ONACC, HOVER)
                else:
                    chip.set_colors(CARD, chip.fg_c, LINE)
            if self.filter and self.filter != name:
                continue
            for path, isdir, size, date in sorted(items, key=lambda x: x[0].lower()):
                folder, base = os.path.split(path)
                iid = t.insert("", "end", tags=("odd" if shown % 2 else "even",),
                               values=(name, ("📁 " if isdir else "") + base, folder, size, date))
                self.row_path[iid] = path
                shown += 1
        self.summary.config(text=self.t("summary", shown, total))
        if shown:
            self._hide_notice()

    def _show_notice(self, key, color=MUTED):
        self.notice_state = (key, color)
        self.notice.config(text=self.t(key), fg=color)
        self.notice.place(relx=0.5, rely=0.45, anchor="center")
        self.notice.lift()

    def _hide_notice(self):
        self.notice_state = None
        self.notice.place_forget()

    def _selected(self):
        sel = self.tree.selection()
        return self.row_path.get(sel[0]) if sel else None

    def show_in_folder(self):
        path = self._selected()
        if not path:
            return
        try:
            if os.name == "nt":
                subprocess.Popen(["explorer", f"/select,{path}"])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(path)])
            self.dlog("INFO", "log_shown", path)
        except Exception as e:
            self.dlog("ERROR", "log_open_err", e)

    def copy_path(self):
        path = self._selected()
        if path:
            self.root.clipboard_clear()
            self.root.clipboard_append(path)
            self.dlog("INFO", "log_path_copied", path)

    def export_txt(self):
        if not any(self.results.values()):
            return
        fn = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="slave_results.txt",
                                          filetypes=[(self.t("file_type"), "*.txt")])
        if not fn:
            return
        try:
            with open(fn, "w", encoding="utf-8") as f:
                f.write(self.t("export_title", f"{datetime.now():%d.%m.%Y %H:%M}") + "\n\n")
                for name in self.names + self.temp:
                    if name not in self.results:
                        continue
                    items = self._visible(name)
                    f.write(f"[{name}] ({len(items)})\n")
                    for path, *_ in sorted(items, key=lambda x: x[0].lower()):
                        f.write(f"  {path}\n")
                    f.write("\n")
            self.dlog("OK", "log_saved", fn)
        except OSError as e:
            self.dlog("ERROR", "log_save_err", e)


DISCORD_URL = "https://discord.gg/UdeMUMmVMB"
_PC_SALT = bytes.fromhex("6ae14b6c5c0081405fb566e736c12444")
_PC_HASH = "f0911f7b8ded6900f67f193ae3310d1fdbfc185d0ae493b92d268cbb55309b5f"
_PC_ITER = 200000

_DISCORD_PTS = [
    (20.32, 4.37), (15.45, 2.85), (14.82, 4.10), (13.5, 3.88), (12, 3.84), (10.5, 3.88),
    (9.33, 4.10), (8.71, 2.85), (3.83, 4.37), (1.6, 7.6), (0.4, 12.0), (0.10, 18.06),
    (2.2, 20.0), (6.09, 21.17), (7.31, 19.18), (5.43, 18.18), (5.30, 17.05), (6.3, 16.6),
    (9.0, 17.5), (12, 17.9), (15.0, 17.5), (18.3, 16.6), (19.25, 17.05), (19.1, 18.18),
    (17.3, 19.18), (18.5, 21.17), (21.8, 20.0), (23.9, 18.06), (23.6, 12.0), (22.4, 7.6),
]


def check_passcode(text):
    d = hashlib.pbkdf2_hmac("sha256", text.encode("utf-8"), _PC_SALT, _PC_ITER)
    return hmac.compare_digest(d.hex(), _PC_HASH)


class DiscordIcon(tk.Canvas):
    SIZE = 40

    def __init__(self, parent, bg):
        S = self.SIZE
        super().__init__(parent, width=S, height=S, bg=bg, highlightthickness=0, bd=0,
                         cursor="hand2")
        k = S / 26.0
        off = (S - 24 * k) / 2
        pts = []
        for x, y in _DISCORD_PTS:
            pts += [off + x * k, off + y * k]
        self.shape = self.create_polygon(pts, fill=MUTED, outline=MUTED, width=2, joinstyle="round")
        for cx in (8.02, 15.99):
            self.create_oval(off + (cx - 2.0) * k, off + (12.91 - 2.3) * k,
                             off + (cx + 2.0) * k, off + (12.91 + 2.3) * k, fill=bg, outline=bg)
        self.bind("<Enter>", lambda e: self.itemconfig(self.shape, fill="#5865F2", outline="#5865F2"))
        self.bind("<Leave>", lambda e: self.itemconfig(self.shape, fill=MUTED, outline=MUTED))
        self.bind("<Button-1>", lambda e: webbrowser.open(DISCORD_URL))


class PasscodeGate:
    def __init__(self, root, lang, on_ok):
        self.root, self.lang, self.on_ok = root, lang, on_ok
        self.items = []
        w = self.win = tk.Toplevel(root)
        w.title("Slave")
        w.configure(bg=BG)
        W, H = 480, 610
        w.geometry(f"{W}x{H}+{(w.winfo_screenwidth() - W) // 2}+{(w.winfo_screenheight() - H) // 3}")
        w.resizable(False, False)
        w.protocol("WM_DELETE_WINDOW", root.destroy)

        langbar = tk.Frame(w, bg=BG)
        langbar.pack(fill="x", padx=14, pady=(12, 0))
        self.lbtn = {}
        for code in reversed(LANGS):
            b = RoundButton(langbar, code.upper(), lambda c=code: self.set_lang(c), CARD, MUTED,
                            LINE, width=44, height=28, font=("Segoe UI", 9, "bold"), parent_bg=BG)
            b.pack(side="right", padx=(6, 0))
            self.lbtn[code] = b

        tk.Label(w, text="S L A V E", bg=BG, fg=FG, font=("Segoe UI", 24, "bold")).pack(pady=(14, 0))
        tk.Label(w, text=CREDIT, bg=BG, fg=MUTED, font=("Segoe UI", 8)).pack()
        self._label("gate_sub", dict(fg=MUTED, font=("Segoe UI", 9)), pady=(2, 18))

        self._label("gate_pass", dict(fg=MUTED, font=("Segoe UI", 8, "bold")), anchor="w",
                    padx=40, pady=(0, 4))
        self.var = tk.StringVar()
        self.entry = tk.Entry(w, textvariable=self.var, show="•", bg=CARD, fg=FG,
                              insertbackground=FG, relief="flat", font=("Segoe UI", 13),
                              highlightthickness=1, highlightbackground=LINE, highlightcolor=ACCENT)
        self.entry.pack(fill="x", padx=40, ipady=8)
        self.entry.bind("<Return>", lambda e: self.submit())
        self.entry.focus_set()
        self.err = tk.Label(w, text="", bg=BG, fg=RED, font=("Segoe UI", 9))
        self.err.pack(anchor="w", padx=40, pady=(6, 0))

        self._label("gate_discord", dict(fg=MUTED, font=("Segoe UI", 9), wraplength=400,
                                         justify="center"), pady=(8, 4))
        DiscordIcon(w, BG).pack()

        self.ok = tk.BooleanVar(value=False)
        row = tk.Frame(w, bg=BG)
        row.pack(fill="x", padx=36, pady=(22, 0))
        self.chk = tk.Checkbutton(row, variable=self.ok, command=self._tick_changed, bg=BG,
                                  fg=MUTED, selectcolor=CARD, activebackground=BG,
                                  activeforeground=FG, highlightthickness=0, bd=0,
                                  cursor="hand2", font=("Segoe UI", 9), justify="left",
                                  anchor="w", wraplength=380)
        self.chk.pack(anchor="w")
        self.items.append((self.chk, "gate_consent"))

        self.btn = RoundButton(w, "", self.submit, ACCENT, ONACC, HOVER, width=160, height=38,
                               parent_bg=BG)
        self.btn.pack(pady=22)
        self.btn.set_enabled(False)
        self.apply_lang()

    def _label(self, key, kw, anchor="center", padx=0, pady=0):
        lb = tk.Label(self.win, bg=BG, **kw)
        if anchor == "center":
            lb.pack(padx=padx, pady=pady)
        else:
            lb.pack(anchor=anchor, padx=padx, pady=pady)
        self.items.append((lb, key))
        return lb

    def t(self, key):
        return TXT[self.lang].get(key) or TXT["en"][key]

    def apply_lang(self):
        for wd, key in self.items:
            wd.config(text=self.t(key))
        self.btn.set_text(self.t("gate_enter"))
        for code, b in self.lbtn.items():
            if code == self.lang:
                b.set_colors(ACCENT2, "#ffffff", HOVER2)
            else:
                b.set_colors(CARD, MUTED, LINE)

    def set_lang(self, code):
        self.lang = code
        cfg = load_config()
        cfg["lang"] = code
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
        self.apply_lang()

    def _tick_changed(self):
        self.btn.set_enabled(self.ok.get())
        if self.ok.get():
            self.err.config(text="")

    def submit(self):
        if not self.ok.get():
            self.err.config(text=self.t("gate_tick"))
            return
        if check_passcode(self.var.get()):
            self.win.destroy()
            self.on_ok()
        else:
            self.err.config(text=self.t("gate_wrong"))
            self.var.set("")
            self.entry.focus_set()


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    root.withdraw()
    cfg = load_config()
    lang = cfg.get("lang") if cfg.get("lang") in LANGS else sys_lang()
    set_theme(cfg.get("theme") if cfg.get("theme") in THEMES else "blue")

    def start():
        app = SlaveApp(root)
        Splash(root, app.reveal, app.lang)

    PasscodeGate(root, lang, start)
    root.mainloop()


if __name__ == "__main__":
    main()