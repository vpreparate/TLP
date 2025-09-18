#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Эта шняга в самом верху говорит компу:
«Эй, запускай меня через Python3»
и что файлик в кодировке UTF-8,
чтобы кириллица и смайлы норм проходили."""
"""Подрубаем стандартные библиотеки:

sys/os — для работы с файлами и путями,

re — для регулярок,

time — чтобы таймеры и задержки юзать,

random — чтобы числа рандомные брать,

bisect — чтобы правильно вставлять в отсортированные списки,

webbrowser — открывать браузер из кода,

hashlib — для хешей, типа md5/sha."""
import sys, os, re, time, random, bisect, webbrowser, hashlib
"""Импортируем partial, чтоб делать такие функции,
где часть аргументов уже зафиксирована, удобно как закладка на функцию."""
from functools import partial
"""Тут просто математика: синусы, косинусы, корни, все дела."""
import math
"""Подрубаем виджеты PyQt5, чтобы строить интерфейс:
окна, кнопки, метки, списки, диалоги, чекбоксы и всякую мелочёвку для UI."""
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout,
    QFileDialog, QListWidget, QListWidgetItem, QStyle, QSizePolicy, QDialog,
    QCheckBox, QToolButton, QAbstractItemView
)
"""QAudioProbe нужен, чтобы слушать аудиопоток
и ловить его данные, типа анализировать звук в реальном времени."""
from PyQt5.QtMultimedia import QAudioProbe
"""Core штуки:

Qt — константы, флаги,

QTimer — таймеры для периодических задач,

QFileSystemWatcher — следим за изменениями файлов,

QUrl — ссылки,

QSize, QPoint, QRectF — размеры и координаты,

QEvent — события, типа клики мышью."""
from PyQt5.QtCore import Qt, QTimer, QFileSystemWatcher, QUrl, QSize, QPoint, QRectF, QEvent
"""Графика:

QFontDatabase и QFont — шрифты,

QPainter — рисуем на виджетах,

QLinearGradient, QColor, QBrush — цвета и градиенты,

QFontMetrics — размеры текста,

QPen — линия, контур для рисования."""
from PyQt5.QtGui import QFontDatabase, QFont, QPainter, QLinearGradient, QColor, QBrush, QFontMetrics, QPen
# --- set VLC path ---
"""Определяем, где лежит скрипт (BASEDIR),
и строим путь до папки с VLC, если она рядом с этим файлом."""
BASEDIR = os.path.abspath(os.path.dirname(__file__))
VLC_DIR = os.path.join(BASEDIR, "vlc")
"""Проверяем: есть ли папка vlc.
Если есть — подрубаем её в PATH, чтобы Python мог найти libvlc.
Потом проверяем папку с плагинами VLC, ставим её в VLC_PLUGIN_PATH.
Если папки нет — просто предупреждаем, что будем юзать системный VLC."""
if os.path.isdir(VLC_DIR):
    os.environ["PATH"] = VLC_DIR + os.pathsep + os.environ.get("PATH", "")
    plugins = os.path.join(VLC_DIR, "plugins")
    if os.path.isdir(plugins):
        os.environ["VLC_PLUGIN_PATH"] = plugins
    else:
        os.environ["VLC_PLUGIN_PATH"] = VLC_DIR
else:
    print("Warning: 'vlc' folder not found next to script. Using system libvlc if available.")

"""Пробуем импортировать python-vlc.
Если фигня — выкидываем ошибку и показываем, че именно не так."""
try:
    import vlc
except Exception as e:
    print("python-vlc import error:", e)
    raise


# более строгая RE — границы слова, 1-2 цифры часа/минуты
TIME_RE = re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?)\b')
URL_RE = re.compile(r'(https?://\S+|t\.me/\S+|tg://\S+)', re.IGNORECASE)
EXT_RE = re.compile(r'\.(mp3|wav|flac|ogg|m4a|aac)$', re.IGNORECASE)
LEADING_NUM_RE = re.compile(r'^\s*\d+\s*[-._:)\]]*\s*', re.UNICODE)



'''
Это типа «чистим название трека».
Берём сырой текст и вычищаем всё лишнее.
'''
def clean_title(raw):
    '''
Если вообще ничего нет (None),
то возвращаем пустую строку.
Типа «ничего нет — и ладно, поехали дальше».
    '''
    if raw is None:
        return ''
    '''
Убираем пробелы в начале и конце строки. Чтобы не было лишних пустот.
    '''
    s = raw.strip()
    s = re.sub(URL_RE, '', s)                     # убираем URL
    s = re.sub(EXT_RE, '', s)                     # убираем расширения (.mp3 и т.д.)
    s = re.sub(LEADING_NUM_RE, '', s)             # убираем ведущие номера "1 -"
    s = re.sub(r'^\s*[-_.:)\]]+\s*', '', s)       # убираем ведущие разделители
    '''
В конце ещё раз подчищаем лишние пробелы, тире, точки,
нижние подчёркивания, табы. Всё чисто и по кайфу.
    '''
    return s.strip(" -_.\t")

'''
Функция для перевода времени вроде «1:23:45» в миллисекунды.
'''
def parse_time_to_ms(tstr):
    '''
Сначала убираем пробелы и режем строку по :.
Например, "1:23:45" -> ["1","23","45"].
    '''
    parts = tstr.strip().split(':')
    '''
Пробуем превратить всё в числа.
Если что-то пошло не так — вернём 0. Чтобы программа не падала.
    '''
    try:
        parts = list(map(int, parts))
    except Exception:
        return 0
    '''
Если только «минуты:секунды» — часа нет, ставим 0.
Иначе берём все три: часы, минуты, секунды.
    '''
    if len(parts) == 2:
        h = 0; m, s = parts
    else:
        h, m, s = parts
        '''
Считаем полное количество секунд и умножаем на 1000,
чтобы получить миллисекунды.
        '''
    return ((h*60 + m)*60 + s) * 1000

def parse_tracklist(path):
    """Строгий парсер: возвращает entries в порядке файла.
    Каждый entry содержит: uid, line_no, raw, title, display,
    time_ms, url (если есть).
    """
    '''
Собираем результат в список.
    '''
    entries = []
    '''
Если файла нет — возвращаем пустой список.
Типа «треки не найдены, но программа жива».
    '''
    if not os.path.exists(path):
        return entries
    '''
Читаем файл построчно и убираем символы переноса строк в конце каждой строки.
    '''
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        raw_lines = [l.rstrip('\n') for l in f]
        '''
Перебираем строки. Если строка пустая — пропускаем.
        '''
    for line_no, raw in enumerate(raw_lines, start=1):
        orig = raw
        if not orig or not orig.strip():
            continue

        # Найти все возможные совпадения времени в строке
        matches = list(TIME_RE.finditer(orig))
        if not matches:
            # нет таймкода — пропускаем (или можно логировать)
            continue

        # Выбрать "лучший" матч — предпочтение тем, которые ближе к концу строки
        best = None
        best_score = -10**9
        L = len(orig)
        '''
Это хитроватая логика: выбираем таймкод,
который ближе к концу строки и не вписан в текст.
Если рядом буквы или символы _ -, добавляем штраф.
        '''
        for m in matches:
            start, end = m.start(), m.end()
            closeness = L - end
            prev_ch = orig[start-1] if start>0 else ' '
            next_ch = orig[end] if end < L else ' '
            penalty = 0
            if prev_ch.isalnum() or prev_ch in ['_', '-']:
                penalty += 200
            if next_ch.isalnum() or next_ch in ['_', '-']:
                penalty += 200
            score = -closeness - penalty
            if score > best_score:
                best_score = score
                best = m

                '''
Если лучший матч не нашли — берём последний найденный таймкод.
                '''
        m = best
        if m is None:
            m = matches[-1]
            '''
Переводим выбранный таймкод в миллисекунды.
            '''
        time_ms = parse_time_to_ms(m.group(1))
        '''
Ищем ссылку в строке.
Если это t.me/... — добавляем https://. Иначе оставляем как есть.
        '''
        u = URL_RE.search(orig)
        url = None
        if u:
            url_raw = u.group(1).strip()
            if url_raw.lower().startswith('t.me/'):
                url = 'https://' + url_raw
            else:
                url = url_raw

                '''
Вырезаем таймкод и ссылку из строки, чистим остаток через clean_title.
                '''
        title_part = orig[:m.start()] + orig[m.end():]
        if u:
            title_part = title_part.replace(u.group(1), '')
        title_part = clean_title(title_part)

        '''
Если название получилось пустым — ставим «Track H:M:S» как заглушку.
        '''
        display = title_part if title_part else f"Track {ms_to_hms(time_ms)}"

        '''
Создаём уникальный идентификатор трека по строке, таймкоду и хэшу.
        '''
        raw_hash = hashlib.sha1(orig.encode('utf-8')).hexdigest()[:8]
        uid = f"line{line_no}:{time_ms}:{raw_hash}"

        '''
Собираем всё в словарь и добавляем в список треков.
        '''
        entries.append({
            'uid': uid,
            'line_no': line_no,
            'raw': orig,
            'title': title_part,
            'display': display,
            'time_ms': time_ms,
            'url': url
        })
        '''
Возвращаем список всех треков.
        '''
    return entries

'''
Переводим миллисекунды обратно в «часы:минуты:секунды».
'''
def ms_to_hms(ms):
    '''
Считаем целые секунды из миллисекунд, минимум 0.
    '''
    s = max(0, int(ms // 1000))
    '''
Берём часы и вычитаем их из секунд.
    '''
    h = s // 3600; s -= h*3600
    '''
Берём минуты и оставляем остаток в секундах.
    '''
    m = s // 60; s -= m*60
    '''
Формируем строку. Если есть часы — показываем h:mm:ss, иначе только m:ss.
    '''
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

'''
Создаётся класс MarqueeLabel,
наследуется от QLabel.
То есть это надпись,
но с кастомным поведением — будет бегущая строка, понял?
'''
class MarqueeLabel(QLabel):
    '''
Конструктор: при старте можем задать текст и родительский виджет.
Если ничего не дали — пусто.
    '''
    def __init__(self, text='', parent=None):
        """
Запускаем конструктор от QLabel,
чтоб всё как обычно работало у базовой надписи.
        """
        super().__init__(text, parent)
        """
_offset — это на сколько текст сдвинут влево/вправо.
_dir — направление движения: 1 — вправо, -1 — влево.
        """
        self._offset = 0.0; self._dir = 1
        '''
Таймер, который будет тикать и двигать текст.
Каждое срабатывание вызывает метод _tick.
        '''
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick)
        '''
Ещё один таймер, который один раз стартует через задержку
и запускает движение текста.
        '''
        self._start = QTimer(self); self._start.setSingleShot(True); self._start.timeout.connect(self._start_run)
        """
Таймер для паузы.
Он один раз ждёт и потом снова включает движение после паузы.
        """
        self._pause = QTimer(self); self._pause.setSingleShot(True); self._pause.timeout.connect(self._resume)
        '''
Настройки:
скорость обновления (40 мс),
шаг смещения текста (2 пикселя),
пауза между сменами направления (800 мс).
        '''
        self._speed = 40; self._step = 2; self._pause_ms = 800
        '''
Флажок _running — идёт ли анимация. _text_width — ширина текста.
        '''
        self._running = False; self._text_width = 0
        """
Размерный режим: растягиваемся по горизонтали, но фиксированы по вертикали.
Текст прижат к левому краю и по центру вертикали.
        """
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self.setAlignment(Qt.AlignVCenter|Qt.AlignLeft)
        '''
Функция, чтоб задать новый текст.
        '''
    def setText(self, text):
        """
Вызываем обычный setText.
Потом берём метрики шрифта и считаем ширину текста в пикселях.
        """
        super().setText(text); fm = QFontMetrics(self.font()); self._text_width = fm.horizontalAdvance(text)
        """
Сбрасываем сдвиг, направление в начало.
Останавливаем старые таймеры и запускаем новый старт через 200 мс.
        """
        self._offset = 0.0; self._dir = 1; self._timer.stop(); self._pause.stop(); self._start.start(200)
        '''
Если текст влезает в ширину виджета,
то анимация не нужна (_running=False), просто обновляем отрисовку.
        '''
        if self._text_width <= max(0, self.width()-10): self._running=False; self.update()

        '''
Метод, который срабатывает при изменении размера окна/виджета.
        '''
    def resizeEvent(self, ev):
        """
Вызов стандартного обработчика. Потом пересчитываем ширину текста.
        """
        super().resizeEvent(ev); fm = QFontMetrics(self.font()); self._text_width = fm.horizontalAdvance(self.text())
        """
Если текст помещается в ширину, то стопаем анимацию,
сбрасываем сдвиг и просто показываем как есть.
        """
        """
Если не помещается — запускаем таймер старта через 150 мс.
        """
        if self._text_width <= max(0, self.width()-10): self._timer.stop(); self._running=False; self._offset=0; self.update()
        else: self._start.start(150)
        
        """
Метод, который реально запускает движение текста.
        """
    def _start_run(self):
        """
Если текст больше ширины виджета — включаем флаг _running
и стартуем таймер движения.
        """
        if self._text_width > max(0, self.width()-10): self._running=True; self._timer.start(self._speed)

        """
Метод, который возобновляет движение после паузы.
        """
    def _resume(self):
        """
Если анимация должна идти, но таймер не работает — запускаем снова.
        """
        if self._running and not self._timer.isActive(): self._timer.start(self._speed)

        """
Метод, который срабатывает на каждый тик таймера и двигает текст.
        """
    def _tick(self):
        """
Если движение выключено — выходим.
        """
        if not self._running: return
        """
visible — сколько пикселей реально видно.
max_off — максимальное смещение текста, чтоб показать весь.
        """
        visible = max(0, self.width()-10); max_off = max(0, self._text_width-visible)
        """
Если двигаемся вправо (или влево по сути, тут направление условное).
        """
        if self._dir>0:
            """
Двигаем текст на шаг вперёд.
            """
            self._offset += self._step
            """
Если дошли до края — ставим смещение на максимум, стопаем таймер,
запускаем паузу и меняем направление на обратное.
            """
            if self._offset >= max_off: self._offset = max_off; self._timer.stop(); self._pause.start(self._pause_ms); self._dir=-1
            """
Если направление обратное — двигаем текст назад.
            """
        else:
            self._offset -= self._step
            """
Если дошли до начала — сбрасываем смещение, стопаем таймер,
пауза и разворот в другую сторону.
            """
            if self._offset <= 0: self._offset = 0; self._timer.stop(); self._pause.start(self._pause_ms); self._dir=1
            """
Обновляем виджет, чтобы перерисовать с новым смещением.
            """
        self.update()

        """
Метод, который отвечает за отрисовку текста.
        """
    def paintEvent(self, ev):
        """
Создаём художника (QPainter),
включаем сглаживание текста, чтоб он красивый был.
        """
        painter = QPainter(self); painter.setRenderHint(QPainter.TextAntialiasing)
        """
Берём прямоугольник внутри виджета
и делаем отступы слева/справа по 6 пикселей.
Обрезаем рисование внутри этого прямоугольника.
        """
        rect = self.contentsRect().adjusted(6,0,-6,0); painter.setClipRect(rect)
        """
Берём метрики шрифта, сам текст,
и считаем координату Y, чтоб текст по центру вертикали лег.
        """
        fm = QFontMetrics(self.font()); text = self.text(); y = rect.top() + (rect.height()+fm.ascent()-fm.descent())//2
        """
Выбираем цвет (голубовато-белый),
рисуем текст со смещением _offset. Закрываем рисование.
        """
        painter.setPen(QColor(200,255,255)); painter.drawText(rect.left()-int(self._offset), y, text); painter.end()


'''
Тут мы объявляем класс TrackListItemWidget,
и он наследуется от QWidget.
То есть это будет кастомный виджет в Qt, типа своя коробочка для инфы.
'''
class TrackListItemWidget(QWidget):
    '''
Конструктор класса.
Сюда передают entry (данные про трек),
шрифт font_family (если не задали — потом дефолт будет),
и parent — родительский виджет.
    '''
    def __init__(self, entry, font_family=None, parent=None):
        '''
Запускаем инициализацию родительского класса QWidget, чтоб не было косяков.
        '''
        super().__init__(parent)
        '''
Подтягиваем нужные модули прямо тут:
QHBoxLayout (горизонтальная разметка)
и QToolButton (кнопочка такая миниатюрная).
        '''
        from PyQt5.QtWidgets import QHBoxLayout, QToolButton
        '''
Создаём горизонтальную компоновку h.

setContentsMargins(8,4,8,4) — отступы слева, сверху, справа и снизу
(8px,4px,8px,4px).

setSpacing(8) — расстояние между элементами 8px.
Короче, чтоб не было всё впритык.
        '''
        h = QHBoxLayout(self); h.setContentsMargins(8,4,8,4); h.setSpacing(8)
        '''
Тут если шрифт не задан, то будет использоваться стандартный — Segoe UI.
        '''
        font_name = font_family or 'Segoe UI'
        '''
Создаём QLabel для названия трека. Текст берём из entry['display'].
Дальше сразу задаём шрифт (font_name, размер 10).
        '''
        self.title = QLabel(entry['display']); self.title.setFont(QFont(font_name,10))
        '''
Красим текст в голубоватый цвет #dffcff.
setSizePolicy(Expanding, Preferred) — говорит,
что по горизонтали будет растягиваться,
а по вертикали ведёт себя как обычно.
        '''
        self.title.setStyleSheet("color:#dffcff;"); self.title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        '''
Если навести мышкой — будет всплывающая подсказка:
или entry['title'], или fallback entry['display'].
setWordWrap(False) — текст не переносится на новую строку.
        '''
        self.title.setToolTip(entry.get('title', entry['display'])); self.title.setWordWrap(False)
        '''
Мышка клики сквозь этот лейбл не ловит, типа он прозрачный для событий.
        '''
        self.title.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        '''
Добавляем title в горизонтальный лэйаут.
        '''
        h.addWidget(self.title)
        '''
Ещё один QLabel, только для времени трека.

Текст = время в формате чч:мм:сс, функция ms_to_hms переводит миллисекунды.

Шрифт = тот же, размер 9.

setFixedWidth(78) — фикс ширина 78px.

setAlignment — текст справа и по центру вертикали.
        '''
        self.time = QLabel(ms_to_hms(entry['time_ms'])); self.time.setFont(QFont(font_name,9)); self.time.setFixedWidth(78); self.time.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        '''
Красим текст времени в полупрозрачный голубой и делаем жирненький.
        '''
        self.time.setStyleSheet("color: rgba(200,220,255,0.95); font-weight:600;")
        '''
Тоже делаем время некликабельным, чтоб мышка его игнорила.
        '''
        self.time.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        '''
Добавляем метку времени в лэйаут.
        '''
        h.addWidget(self.time)
        '''
Если в entry есть ключ url, значит у трека есть ссылка.
        '''
        if entry.get('url'):
            '''
Создаём кнопочку.

На ней значок ⤴.

setAutoRaise(True) — она будет выглядеть как иконка без рамки.

Размер фиксированный 24x22.

Tooltip = сама ссылка.
            '''
            tb = QToolButton(); tb.setText('⤴'); tb.setAutoRaise(True); tb.setFixedSize(24,22); tb.setToolTip(entry['url'])
            '''
Кидаем кнопку в лэйаут и вешаем событие:
при клике откроется браузер по ссылке.
            '''
            h.addWidget(tb); tb.clicked.connect(partial(webbrowser.open, entry['url']))
            '''
Это такой маленький индикатор (12x12),
круглый (border-radius:6px), полупрозрачный белый фон. Типа маркер трека.
            '''
        self.marker = QLabel(); self.marker.setFixedSize(12,12); self.marker.setStyleSheet("background: rgba(255,255,255,12); border-radius:6px;")
        '''
Тоже мышка его не трогает.
        '''
        self.marker.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        '''
И в итоге добавляем этот маркер в лэйаут.
        '''
        h.addWidget(self.marker)

'''
тут мы мутим класс TracklistDialog, он унаследован от QDialog. Типа своё окно под треклист делаем.
'''
class TracklistDialog(QDialog):
    '''
это конструктор.
Сюда можно закинуть ссылку на плеер (player_ref),
шрифт (font_family) и родителя (parent).
    '''
    def __init__(self, player_ref=None, font_family=None, parent=None):
        '''
вызываем конструктор предков. Говорим Qt: сделай окно и держи его всегда поверх всех остальных.
        '''
        super().__init__(parent, Qt.Window | Qt.WindowStaysOnTopHint)
        '''
заголовок окна пишем "Tracklist". Запоминаем ссылку на плеер и какой шрифт юзать.
        '''
        self.setWindowTitle("Tracklist"); self.player_ref = player_ref; self.font_family = font_family
        """
— тут красоту наводим: стиль прописываем.
Фон окна — градиент тёмный, текст голубенький.
Список прозрачный без рамок.
Кнопки — полупрозрачные, скруглённые.
        """
        self.setStyleSheet("""QDialog{ background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #05060a, stop:1 #0c0f13); color: #dffcff; }
QListWidget{ background: transparent; border:none; } QPushButton{ background: rgba(255,255,255,6); border-radius:6px; }""")
        '''
делаем вертикальный лэйаут (раскладку). Отступы 8 пикселей, расстояние между элементами 6.
        '''
        layout = QVBoxLayout(self); layout.setContentsMargins(8,8,8,8); layout.setSpacing(6)
        '''
верхняя панелька горизонтальная (будут кнопки и чекбоксы рядом).
        '''
        hdr = QHBoxLayout()
        '''
чекбокс "Авто-фоллоу". По умолчанию включен — всегда подсвечивает играющий трек.
        '''
        self.follow_cb = QCheckBox('Auto-Follow — автоматически выделять текущий трек'); self.follow_cb.setChecked(True)
        '''
стиль чекбокса: текст салатовый.
        '''
        self.follow_cb.setStyleSheet("QCheckBox{ color: #8ef6a7; }")
        '''
второй чекбокс: "Подогнать по всем трекам". Текст голубенький.
        '''
        self.fit_cb = QCheckBox('Fit all — расширить окно, чтобы показать все треки'); self.fit_cb.setStyleSheet("QCheckBox{ color: #87cfff; }")
        '''
добавляем оба чекбокса в верхнюю панельку.
        '''
        hdr.addWidget(self.follow_cb); hdr.addWidget(self.fit_cb)
        '''
вставляем растяжку (чтоб кнопка была справа). Кнопка "Close" — при клике прячет окно.
        '''
        hdr.addStretch(); self.close_btn = QPushButton('Close'); self.close_btn.clicked.connect(self.hide); hdr.addWidget(self.close_btn)
        '''
закидываем верхнюю панельку в главный вертикальный лэйаут.
        '''
        layout.addLayout(hdr)
        '''
создаём список треков. Можно выбрать только один трек. Скролл плавный по пикселям.
        '''
        self.listw = QListWidget(); self.listw.setSelectionMode(QAbstractItemView.SingleSelection); self.listw.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        '''
сортировку отключаем, треки идут в том порядке, как есть.
        '''
        self.listw.setSortingEnabled(False)
        '''
тащить мышкой элементы нельзя.
        '''
        self.listw.setDragEnabled(False)
        '''
и перетаскивать тоже нельзя.
        '''
        self.listw.setDragDropMode(QAbstractItemView.NoDragDrop)
        '''
клики по элементам списка вешаем на свои функции:
одинарный _on_item_clicked, двойной _on_item_double. Потом список добавляем в лэйаут.
        '''
        self.listw.itemClicked.connect(self._on_item_clicked); self.listw.itemDoubleClicked.connect(self._on_item_double); layout.addWidget(self.listw)
        """
— делаем флаг user_interacting, типа юзер шарит мышкой или нет.
Таймер на одноразовый запуск — через 2.2 секунды сбрасывает это состояние.
        """
        self.user_interacting = False; self._interaction_timer = QTimer(self); self._interaction_timer.setSingleShot(True); self._interaction_timer.timeout.connect(self._clear_user_interaction)
        '''
на вьюшку списка вешаем фильтр событий (ловим скролл/мышку).
Если скроллбар двигается — считаем что юзер лазит.
        '''
        self.listw.viewport().installEventFilter(self); self.listw.verticalScrollBar().valueChanged.connect(self._on_user_interaction)
        '''
стандартная высота одного элемента списка.
        '''
        self._item_h = 26

        """
— фильтр событий: если юзер крутит колесо, жмёт мышкой или двигает её по списку — включаем "юзер взаимодействует".
Остальное отправляем дальше в Qt.
        """
    def eventFilter(self, obj, ev):
        if obj is self.listw.viewport() and ev.type() in (QEvent.Wheel, QEvent.MouseButtonPress, QEvent.MouseMove):
            self._on_user_interaction()
        return super().eventFilter(obj, ev)

    '''
отмечаем, что юзер активен, и запускаем таймер на 2.2 секунды. После этого сбросится.
    '''
    def _on_user_interaction(self, *a):
        self.user_interacting = True; self._interaction_timer.start(2200)

        '''
функция сброса: "юзер больше не трогает".
        '''
    def _clear_user_interaction(self): self.user_interacting = False
    '''
просто возвращает, активен ли юзер сейчас.
    '''
    def is_user_interacting(self): return self.user_interacting

    '''
функция для загрузки треков в список. Принимает список треков и шрифт.
    '''
    def set_tracks(self, tracks, font_family=None):
        '''
запоминаем IDшник прошлого трека, который был выделен.
        '''
        prev_uid = None
        '''
пытаемся взять UID текущего выделенного трека. Если что-то пошло не так — UID = None.
        '''
        try:
            cur_row = self.listw.currentRow()
            if cur_row >= 0:
                prev_uid = self.listw.item(cur_row).data(Qt.UserRole)
        except Exception:
            prev_uid = None

            '''
чистим список. Запоминаем шрифт: либо новый, либо старый.
            '''
        self.listw.clear(); self.font_family = font_family or self.font_family
        '''
если есть шрифт — юзаем его, если нет — дефолтный Segoe UI.
        '''
        if self.font_family: self.listw.setFont(QFont(self.font_family,10))
        else: self.listw.setFont(QFont('Segoe UI',10))
        '''
— идём по трекам.
Создаём элемент списка, в него кидаем UID трека.
Для показа делаем свой виджет TrackListItemWidget.
Размер подгоняем, засовываем в список и вешаем виджет.
        '''
        for t in tracks:
            it = QListWidgetItem(); it.setData(Qt.UserRole, t['uid'])
            w = TrackListItemWidget(t, font_family=self.font_family, parent=self.listw)
            it.setSizeHint(w.sizeHint()); self.listw.addItem(it); self.listw.setItemWidget(it, w)
            '''
если в списке есть треки, то берём высоту первого виджета и обновляем _item_h.
            '''
        if self.listw.count()>0:
            wd = self.listw.itemWidget(self.listw.item(0)); self._item_h = wd.sizeHint().height() + self.listw.spacing()
            '''
если до обновления был выделен какой-то трек — выделяем его снова.
            '''
        if prev_uid:
            self.select_by_uid(prev_uid)

            '''
— делаем ресайз окна под все треки.
Смотрим размеры экрана, вычисляем желаемую высоту и ширину (чтоб в экран влезло).
Если что-то пошло не так — просто забиваем.
            '''
    def fit_to_all(self, n_items):
        try:
            app = QApplication.instance(); screen = app.primaryScreen().availableGeometry()
            desired_h = min(screen.height()-160, max(300, n_items*self._item_h + 80))
            desired_w = min(1200, screen.width()-200)
            self.resize(desired_w, desired_h)
        except Exception:
            pass

        """
— при клике по треку: берём его UID.
Если он есть и плеер подключен, то:

отмечаем взаимодействие,

плеер прыгает на этот трек,

в списке выделяем этот элемент.
        """
    def _on_item_clicked(self, item):
        uid = item.data(Qt.UserRole)
        if uid and self.player_ref:
            self._on_user_interaction()
            self.player_ref.seek_to_uid(uid, play=True)
            for r in range(self.listw.count()):
                if self.listw.item(r).data(Qt.UserRole) == uid:
                    self.listw.setCurrentRow(r); break


                    '''
двойной клик: прыгаем на трек и сразу скрываем окно.
                    '''
    def _on_item_double(self, item):
        uid = item.data(Qt.UserRole)
        if uid and self.player_ref:
            self.player_ref.seek_to_uid(uid, play=True); self.hide()


            '''
— функция выделяет трек по его UID.
Если UID пустой — снимаем выделение.
Если нашли — выделяем и скроллим к нему.
Если не нашли — тоже снимаем выделение.
            '''
    def select_by_uid(self, uid):
        if uid is None:
            self.listw.setCurrentRow(-1); return
        for r in range(self.listw.count()):
            if self.listw.item(r).data(Qt.UserRole) == uid:
                self.listw.setCurrentRow(r); self.listw.scrollToItem(self.listw.item(r), QAbstractItemView.PositionAtCenter); return
        self.listw.setCurrentRow(-1)


'''
делаем класс, типа свой виджет-приборчик.
Будет рисовать бары,
как в плеере — полоски дергаются под музло.
'''
class BarsEqualizer(QWidget):
    '''
запускаем конструктор. Можно передать родителя, и сколько баров надо, по дефолту 24.
    '''
    def __init__(self, parent=None, bars=24):
        '''
подтягиваем движуху от предков (QWidget), чтоб всё по фэншую работало.
        '''
        super().__init__(parent)
        '''
фиксируем высоту всей этой темы, чтоб не растягивалась, типа панелька низкая.
        '''
        self.setFixedHeight(36)
        '''
сохраняем, сколько у нас баров вообще.
        '''
        self._bars_n = bars
        '''
делаем список значений для баров (их высоты). Все изначально по 0.02 — чуть-чуть подняты.
        '''
        self._bars = [0.02]*self._bars_n
        '''
цель для каждого бара: к чему он будет стремиться. Тоже на старте по 0.02.
        '''
        self._target = [0.02]*self._bars_n
        '''
флаг, играет музло или нет.
        '''
        self._playing = False
        '''
флаг, есть ли реальные уровни звука или пока бутафория.
        '''
        self._has_audio_levels = False
        '''
Тут хитрый мув: создаём таймер, который каждые 40 мс вызывает функцию _tick.
Короче, он постоянно подкачивает значения баров, чтоб анимация жила.
Без него полоски бы просто стояли колом.
        '''
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick); self.timer.start(40)


        '''
метод, ставим флаг: играет музло или нет.
        '''
    def set_playing(self, playing):
        '''
запоминаем, что за состояние (True/False).
        '''
        self._playing = bool(playing)
        """
Если музло стопнулось — сбрасываем цели всех баров на минимум (0.02).
И говорим: "нет уровней звука".
        """
        if not self._playing:
            self._target = [0.02]*self._bars_n
            self._has_audio_levels = False

            '''
метод, чтоб подкинуть уровни звука извне.
            '''
    def set_levels(self, levels):
        '''
если уровней нет — выходим.
        '''
        if not levels:
            return
        '''
преобразуем в список (чтоб удобно гонять).
        '''
        L = list(levels)
        '''
если данных меньше, чем баров, надо растянуть.
        '''
        if len(L) < self._bars_n:
            '''
Тут растягиваем список: берём пропорциональные индексы и дублируем значения,
чтоб баров стало столько, сколько нужно.
            '''
            import math
            new = []
            for i in range(self._bars_n):
                idx = int(i * len(L) / self._bars_n)
                new.append(L[idx])
            L = new
            '''
если уровней больше, чем баров — надо ужать
            '''
        elif len(L) > self._bars_n:
            """
Короче, через numpy делим список на куски по числу баров.
Берём среднее по каждому куску, чтоб плавненько вышло.
Если где-то ошибка — просто обрезаем лишнее.
            """
            import numpy as _np
            try:
                arr = _np.array(L)
                parts = _np.array_split(arr, self._bars_n)
                L = [float(p.mean()) if len(p)>0 else 0.0 for p in parts]
            except Exception:
                L = L[:self._bars_n]
                '''
выставляем цели для баров, но ограничиваем от 0.02 до 1.0 (не меньше, не больше).
                '''
        self._target = [max(0.02, min(1.0, float(x))) for x in L[:self._bars_n]]
        '''
говорим: да, теперь у нас есть реальные уровни звука.
        '''
        self._has_audio_levels = True

        '''
приватный метод, вызывается таймером — обновляет бары
        '''
    def _tick(self):
        """
Если есть реальные уровни — бары подтягиваются к целям.
Типа плавная анимация: разница умножается на коэффициент (0.22),
и мы двигаем бар ближе к цели.
        """
        if self._has_audio_levels:
            for i in range(self._bars_n):
                self._bars[i] += (self._target[i] - self._bars[i]) * 0.22
                """
А если реальных уровней нет:
– если музло идёт, то бары качаются синусом (имитация).
– если стоп — все падают в минимум.
Двигаются они плавно, с коэффициентом 0.12.
                """
        else:
            for i in range(self._bars_n):
                if self._playing:
                    target = 0.15 + 0.85 * (0.5 + 0.5 * abs(math.sin(time.monotonic()*1.2 + i*0.3)))
                else:
                    target = 0.02
                self._bars[i] += (target - self._bars[i]) * 0.12
                '''
перерисовываем виджет, чтоб всё на экране обновилось.
                '''
        self.update()

        '''
метод рисовки, срабатывает при апдейте.
        '''
    def paintEvent(self, ev):
        '''
создаём художника (QPainter) и берём размеры области.
        '''
        painter = QPainter(self); r = self.rect()
        '''
включаем сглаживание, чтоб бары были плавные, не рваные.
        '''
        painter.setRenderHint(QPainter.Antialiasing)
        '''
отключаем обводку, оставляем только заливку.
        '''
        painter.setPen(Qt.NoPen)
        '''
считаем, сколько пикселей на бар (с промежутками). Минимум — 3
        '''
        spacing = max(3, int(r.width() / (self._bars_n * 1.8)))
        '''
считаем общую ширину и центрируем по горизонтали.
        '''
        total_w = self._bars_n * spacing
        offset_x = max(0, (r.width() - total_w) / 2.0)
        """
Цикл по всем барам:
– считаем высоту бара (не меньше 3 пикселей).
– X — где рисовать по горизонтали.
– Y — снизу вверх.
        """
        for i, v in enumerate(self._bars):
            bar_h = max(3, v * r.height())
            x = r.left() + offset_x + i*spacing
            y = r.bottom() - bar_h
            """
Делаем градиент: сверху голубой-бирюзовый,
посередине фиолетовый,
внизу синий.
Короче, неончик чисто.
            """
            grad = QLinearGradient(x, y, x, r.bottom())
            grad.setColorAt(0.0, QColor(120,255,255,200))
            grad.setColorAt(0.6, QColor(200,30,255,180))
            grad.setColorAt(1.0, QColor(40,120,255,160))
            '''
задаём кисть градиентом и рисуем скруглённый бар.
            '''
            painter.setBrush(QBrush(grad))
            painter.drawRoundedRect(QRectF(x, y, spacing*0.85, bar_h), 3.0, 3.0)
            '''
завершаем рисование, отпускаем художника.
            '''
        painter.end()


'''
Короче, мы мутим класс NeonBanner,
он наследуется от QWidget — это типа панелька в Qt, на ней всё рисуем.
'''
class NeonBanner(QWidget):
    """
Это конструктор.
Как только баннер рождается, сюда залетаем.
Можно родителя передать, но не обязательно.
    """
    def __init__(self, parent=None):
        """
Тут зовём батю (родительский класс QWidget),
чтоб всё работало по феншую, без этого баннер охренеет и не взлетит.
        """
        super().__init__(parent)
        """
Фиксируем размер таблички: 200 ширина, 46 высота.
Типа не растягивается, чёткий прямоугольничек.
        """
        self.setFixedSize(200,46)
        '''
Надпись, которая будет сиять
        '''
        self.text = "@YMBAND"
        """
Эффект выбираем — с нуля начинаем. Типа какой будет стиль анимации.
        """
        self.effect_index = 0
        """
Массив эффектов: глюки, смена цветов, плавное исчезновение. Переключаем по кругу.
        """
        self.effects = [self._effect_glitch, self._effect_color_cycle, self._effect_fade]
        """
Фаза тика, короче, счётчик для анимации, чтоб было плавное движение.
        """
        self._tick_phase = 0.0
        """
Сдвиг текста, если типа бегущая строка. Ну чтоб буквы двигались.
        """
        self._marq_offset = 0
        """
Прозрачность: 1.0 — полностью видно, меньше — типа поддымилось.
        """
        self._alpha = 1.0
        """
Уровень звука, брат. Когда музыка играет, баннер сияет ярче.
        """
        self._audio_level = 0.0
        """
Схватил мышкой баннер или нет.
Если тащим — True.
А drag_off — это смещение, чтоб правильно таскать.
        """
        self._dragging = False; self._drag_off = None
        """
Заводим таймер, тик каждые 60 мс.
При каждом тике вызываем _tick, а тот уже гонит анимацию.
        """
        self._timer = QTimer(self); self._timer.timeout.connect(self._tick); self._timer.start(60)
        """
Второй таймер — каждые 6 сек меняем эффект
(глюки → радуга → затухание). Типа не заскучаешь.
        """
        self._switch_timer = QTimer(self); self._switch_timer.setSingleShot(False); self._switch_timer.timeout.connect(self._next_effect); self._switch_timer.start(6000)

        """
Метод: устанавливаем уровень звука от 0.0 до 1.0.
        """
    def set_audio_level(self, level):
        """
Ставим звук в нормальные рамки:
не ниже 0 и не выше 1.
Если там мусор прилетит — тупо игнорим, чтоб не упал скрипт.
        """
        try:
            self._audio_level = max(0.0, min(1.0, float(level)))
        except Exception:
            pass

        """
Если кликнули мышкой, сюда залетаем.
        """
    def mousePressEvent(self, ev):
        """
Если левой кнопкой — значит тащим баннер.
Сохраняем смещение, чтоб двигался ровно, как будто тащишь табличку в падике.
        """
        if ev.button() == Qt.LeftButton:
            self._dragging = True; self._drag_off = ev.globalPos() - self.frameGeometry().topLeft(); ev.accept()
            """
Если не левая кнопка — отправляем батю обрабатывать, нам пофиг.
            """
        else:
            super().mousePressEvent(ev)

            """
Когда двигаем мышью.
            """
    def mouseMoveEvent(self, ev):
        """
Если мы реально тащим, то двигаем баннер по экрану за мышкой.
        """
        if self._dragging and self._drag_off is not None:
            self.move(ev.globalPos() - self._drag_off); ev.accept()
            """
Если не тащим — стандартное поведение.
            """
        else:
            super().mouseMoveEvent(ev)

            """
Когда отпустил мышь.
            """
    def mouseReleaseEvent(self, ev):
        """
Всё, тащить перестали. Сбросили флаги.
        """
        self._dragging = False; self._drag_off = None; super().mouseReleaseEvent(ev)

        """
Меняем эффектчик на следующий.
        """
    def _next_effect(self):
        """
Прибавляем один, если дошли до конца — возвращаемся к первому. Типа карусель эффектов.
        """
        self.effect_index = (self.effect_index + 1) % len(self.effects)

        """
Этот метод вызывается таймером, чтоб обновлять анимацию.
        """
    def _tick(self):
        """
— Счётчик фазы анимации чуть растёт, чтоб движение было.
— Сдвиг для текста крутится по кругу.
— Альфу подгоняем к единице плавно.
— update() говорит: «перерисуй баннер!»
        """
        self._tick_phase += 0.08
        self._marq_offset = (self._marq_offset + 1) % (len(self.text) * 8 + 80)
        self._alpha += (1.0 - self._alpha) * 0.06
        self.update()

        """
Здесь происходит весь рисовочный движ.
        """
    def paintEvent(self, ev):
        """
Берём художника (painter) и говорим: рисуй красиво, без зубчиков.
        """
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing)
        """
Берём прямоугольник, где рисовать (наш баннер).
        """
        r = self.rect()
        """
Фон градиентный: сверху чёрный с синевой, снизу фиолетовый. Тёмный неончик.
        """
        grad = QLinearGradient(r.left(), r.top(), r.right(), r.bottom()); grad.setColorAt(0, QColor(12,14,18,220)); grad.setColorAt(1, QColor(18,14,36,200))
        """
Заливаем фон градиентом, рисуем прямоугольник с закруглёнными углами.
        """
        painter.setBrush(QBrush(grad)); painter.setPen(Qt.NoPen); painter.drawRoundedRect(QRectF(r), 8.0, 8.0)
        """
Если звук чуть-чуть есть, добавляем сияние.
        """
        if self._audio_level > 0.02:
            """
Готовим блестяшку: горизонтальный градиент, яркость зависит от громкости.
            """
            shimmer = QLinearGradient(r.left(), r.top(), r.right(), r.top())
            base_alpha = int(80 + 175 * min(1.0, self._audio_level*1.5))
            """
Основной цвет — голубоватый неон.
            """
            hsv_color = QColor(80, 220, 255, base_alpha)
            """
— По краям сияет нежно.
— В центре бахает розово-фиолетовым, если музон качает.
            """
            shimmer.setColorAt(0.0, QColor(80,220,255, base_alpha//3))
            shimmer.setColorAt(max(0.1, min(1.0, 0.2 + 0.6 * self._audio_level)), QColor(255,80,200, base_alpha))
            shimmer.setColorAt(1.0, QColor(80,220,255, base_alpha//3))
            """
Рисуем внутреннюю подсветку (типа глоу-эффект).
            """
            painter.setBrush(QBrush(shimmer))
            painter.drawRoundedRect(QRectF(r.left()+2, r.top()+2, r.width()-4, r.height()-4), 6.0, 6.0)
            """
Пробуем вызвать выбранный эффект (глюк, цветокрут, затухание).
            """
        try:
            self.effects[self.effect_index](painter, r)
            """
Если эффекты отвалились — рисуем просто текст светло-голубым цветом по центру.
Типа запасной вариант, чтоб баннер не умер.
            """
        except Exception:
            painter.setPen(QColor(200,255,255,int(230*self._alpha)))
            fm = QFontMetrics(QFont('Segoe UI', 18, QFont.Bold))
            y = r.top() + (r.height() + fm.ascent() - fm.descent()) // 2
            painter.drawText(r.left()+10, y, self.text)
            """
Закрываем художника, всё нарисовано.
            """
        painter.end()

        """
— Рисуем текст базовым цветом.
— Иногда сверху бахаем красным или синим сдвинутым текстом (рандомно).
— Это выглядит как глюки на старом телеке.
        """
    def _effect_glitch(self, painter, r):
        font = QFont('Segoe UI', 16, QFont.Bold); painter.setFont(font)
        fm = QFontMetrics(font); y = r.top() + (r.height() + fm.ascent() - fm.descent()) // 2
        base_x = r.left()+10
        painter.setPen(QColor(220,255,255,200)); painter.drawText(base_x, y, self.text)
        if random.random() > 0.6 * (1.0 - self._audio_level):
            painter.setPen(QColor(255,80,80,160)); painter.drawText(base_x+random.randint(-4,4), y+random.randint(-3,3), self.text)
        if random.random() > 0.6 * (1.0 - self._audio_level):
            painter.setPen(QColor(80,255,255,160)); painter.drawText(base_x+random.randint(-4,4), y+random.randint(-3,3), self.text)

            """
— Цвет текста крутится по кругу (hue меняется от времени).
— Короче радуга-переход, как в клубе.
            """
    def _effect_color_cycle(self, painter, r):
        hue = int((self._tick_phase * 60) % 360)
        c = QColor.fromHsl(hue, 200, 140, int(220*self._alpha))
        painter.setPen(c); font = QFont('Segoe UI', 16, QFont.Bold); painter.setFont(font)
        fm = QFontMetrics(font); y = r.top() + (r.height() + fm.ascent() - fm.descent()) // 2
        painter.drawText(r.left()+12, y, self.text)

        """
— Прозрачность текста прыгает по синусоиде.
— С музыкой — ещё сильнее.
— Выглядит как мерцающий неон.
        """
    def _effect_fade(self, painter, r):
        alpha = int(160 + 80 * math.sin(self._tick_phase*1.2) + 80*self._audio_level)
        painter.setPen(QColor(200,255,255, alpha))
        font = QFont('Segoe UI', 16, QFont.Bold); painter.setFont(font)
        fm = QFontMetrics(font); y = r.top() + (r.height() + fm.ascent() - fm.descent()) // 2
        painter.drawText(r.left()+12, y, self.text)


'''
тут мутим класс,
типа наша киберпанковая приблуда,
и она унаследована от QWidget.
Это значит — мы делаем своё окошко в проге.
'''
class CyberDeckWidget(QWidget):
    '''
    запускаем движуху при создании объекта, типа конструктор.
    '''
    def __init__(self):
        '''
вызываем батю-конструктор, чтоб всё по фэншую от QWidget подтянулось.
        '''
        super().__init__()
        """
— тут говорим: "окно будет без рамки,
всегда сверху и выглядит как инструмент".
По сути, чтоб оно как неоновая приблуда поверх всего висело.
        """
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        '''
делаем окошко чуть прозрачным, чтоб выглядело по киберпанку, типа стекло с подсветкой.
        '''
        self.setWindowOpacity(0.92)
        '''
ищем, где рядом с этим файлом лежит папочка vlc.
        '''
        vlc_path = os.path.join(os.path.dirname(__file__), 'vlc')
        '''
проверка: есть ли такая папка вообще.
        '''
        if os.path.isdir(vlc_path):
            '''
если есть, то запускаем VLC плеер и указываем,
где у него плагины валяются. Типа "подгружай отсюда, братан".
            '''
            self.vlc_instance = vlc.Instance(["--plugin-path=" + os.path.join(vlc_path, 'plugins')])
            '''
если папки нема, то запускаем VLC на дефолтных настройках.
            '''
        else:
            self.vlc_instance = vlc.Instance()
            '''
создаём реальный плеер, который треки шпилить будет.
            '''
        self.player = self.vlc_instance.media_player_new()
        """
— пробуем сразу врубить громкость на 85%.
Если чё-то сломалось (например, звука нет) — тупо игнорим.
        """
        try:
            self.player.audio_set_volume(85)
        except Exception:
            pass
        '''
шрифт пока пустой, не знаем какой будет.
        '''
        self.font_family = None
        '''
смотрим, есть ли в папке кастомный шрифт custom.ttf.
        '''
        script_dir = os.path.dirname(os.path.abspath(__file__)); font_path = os.path.join(script_dir, 'custom.ttf')
        '''
проверяем, реально ли он там есть.
        '''
        if os.path.exists(font_path):
            '''
пробуем подключить этот шрифт к системе Qt.
            '''
            try:
                fid = QFontDatabase.addApplicationFont(font_path)
                """
— если всё чётко загрузилось,
берём первую фамилию шрифта и сохраняем, чтоб в интерфейсе юзать.
                """
                if fid != -1:
                    families = QFontDatabase.applicationFontFamilies(fid)
                    if families:
                        self.font_family = families[0]
                        '''
если шрифт не подрубился, остаёмся без него.
                        '''
            except Exception:
                self.font_family = None

        # tracks / mapping
        '''
тут у нас список треков и карта "уникальный айди → индекс трека". Типа быстро находить будем.
        '''
        self.tracks = []; self.trackmap = {}  # uid -> index (file-order)
        '''
путь к треклисту пока пустой.
        '''
        self.tracklist_path = None
        """
— ставим "смотрящего" (QFileSystemWatcher), чтоб палил:
если файл треклиста поменялся или папка двинулась — вызываем метод _on_tracklist_changed.
Типа автоподгрузка.
        """
        self.watcher = QFileSystemWatcher(); self.watcher.fileChanged.connect(self._on_tracklist_changed); self.watcher.directoryChanged.connect(self._on_tracklist_changed)
        '''
делаем отдельное окно для треклиста (диалог).
        '''
        self.tl_window = TracklistDialog(player_ref=self, font_family=self.font_family)
        '''
позиция трека, время последнего тика и текущий айди трека. Всё по нулям.
        '''
        self.effective_pos = 0.0; self.last_tick_time = time.monotonic(); self.current_uid = None
        '''
флажок, чтоб иногда игнорить автосинхру (например, после ручного переключения).
        '''
        self._suppress_until = 0.0

        """
— тут хитрость: VLC иногда врёт и отдаёт меньшую длительность.
Поэтому мы кэшируем "самую большую известную длительность",
чтоб не прыгало туда-сюда.
        """
        self._last_known_duration = 0
        self._media_changed = False

        # build UI
        '''
        строим всё визуальное оформление.
        '''
        self._build_ui()

        # equalizer / neon
        """
— у нас есть переменная hue (оттенок),
и таймер, который каждые 120 мс гоняет _on_tick.
Это чтоб фон переливался неоновыми цветами.
        """
        self.hue = 260; self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self._on_tick); self.anim_timer.start(120)
        '''
второй таймер, который каждые 80 мс обновляет позицию трека.
        '''
        self.display_timer = QTimer(self); self.display_timer.timeout.connect(self._tick_position); self.display_timer.start(80)

        '''
настройки для перетаскивания окна мышкой.
        '''
        self._dragging=False; self._drag_off=None
        '''
берём размер экрана, чтоб вписать наше окошко нормально.
        '''
        app = QApplication.instance(); screen = app.primaryScreen().availableGeometry(); full_w = screen.width()-60
        '''
выставляем размеры окна и ставим его в позицию (30,60). Высота фиксированная
        '''
        self._normal_width = min(980, full_w); self._expanded=False; self.setFixedWidth(self._normal_width); self.setFixedHeight(170); self.move(30,60)

        # audio probe & numpy (optional)
        '''
пока думаем, что numpy (библиотека для математики) у нас нет.
        '''
        self._have_numpy = False
        '''
— пробуем импортнуть numpy.
Если получилось — отлично, включим эквалайзер на звуке.
Если нет — значит будем только "для красоты" показывать.
        '''
        try:
            import numpy as _np
            self._np = _np; self._have_numpy = True
        except Exception:
            self._np = None; self._have_numpy = False
            '''
пока думаем, что пробник звука (QAudioProbe) нам недоступен.
            '''
        self._audio_probe_available = False
        '''
если вообще доступен этот класс — пробуем замутить.
        '''
        if QAudioProbe is not None:
            '''
создаём пробника, флаг "ок" пока ложный.
            '''
            try:
                self.probe = QAudioProbe()
                ok = False
                '''
пробуем воткнуть пробника прямо в плеер.
                '''
                try:
                    ok = self.probe.setSource(self.player)
                    '''
— если напрямую не вышло — пробуем через mediaObject().
Если и так облом — ставим False.
                    '''
                except Exception:
                    try:
                        ok = self.probe.setSource(self.player.mediaObject())
                    except Exception:
                        ok = False
                        '''
если всё норм, цепляем сигнал: когда буфер звука есть, вызываем _on_audio_buffer.
                        '''
                if ok:
                    try:
                        self.probe.audioBufferProbed.connect(self._on_audio_buffer)
                        self._audio_probe_available = True
                        '''
если косяк — отключаем.
                        '''
                    except Exception:
                        self._audio_probe_available = False
                else:
                    self._audio_probe_available = False
                    '''
если вообще всё сломалось — пишем "нет пробника".
                    '''
            except Exception:
                self._audio_probe_available = False

                '''
— если у нас нет ни numpy, ни аудио-пробника,
пишем сообщение: "эквалайзер будет чисто декоративный, без настоящего звука".
                '''
        if not self._audio_probe_available or not self._have_numpy:
            print("Info: audio-reactive equalizer disabled (QAudioProbe or numpy not available). Using decorative mode.")

            '''
тут мутим весь интерфейс.
            '''
    def _build_ui(self):
        '''
общий лэйаут, типа "скелет".
        '''
        main = QHBoxLayout(self); main.setContentsMargins(14,14,14,14); main.setSpacing(10)
        '''
слева колоночка кнопок.
        '''
        left = QVBoxLayout(); left.setSpacing(8)
        '''
кнопка загрузки микса (mp3). Иконка папки.
        '''
        self.load_mix_btn = QPushButton(); self.load_mix_btn.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon)); self.load_mix_btn.setFixedSize(44,44); self.load_mix_btn.clicked.connect(self.load_mix); left.addWidget(self.load_mix_btn)
        '''
кнопка загрузки треклиста (txt).
        '''
        self.load_tl_btn = QPushButton(); self.load_tl_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView)); self.load_tl_btn.setFixedSize(44,44); self.load_tl_btn.clicked.connect(self.load_tracklist); left.addWidget(self.load_tl_btn)
        '''
добавляем пустое место и кидаем всё в общий макет.
        '''
        left.addStretch(); main.addLayout(left)
        '''
жирная кнопка плей/пауза, центр сцены.
        '''
        self.play_btn = QPushButton(); self.play_btn.setFixedSize(96,96); self.play_btn.clicked.connect(self.toggle_play); main.addWidget(self.play_btn)
        '''
центральная часть, тут название трека, таймер и эквалайзер.
        '''
        center = QVBoxLayout(); center.setContentsMargins(0,0,0,0)
        font_name = self.font_family or 'Segoe UI'
        '''
бегущая строка с названием трека.
        '''
        self.track_label = MarqueeLabel('No track loaded'); self.track_label.setFont(QFont(font_name,18,QFont.Bold)); self.track_label.setFixedHeight(56); self.track_label.setStyleSheet('color:#dffcff;'); center.addWidget(self.track_label)
        '''
время: текущая позиция и длительность.
        '''
        self.timer_label = QLabel('0:00'); self.timer_label.setFont(QFont(font_name,10)); self.timer_label.setStyleSheet('color: rgba(220,240,255,0.95);'); center.addWidget(self.timer_label)
        '''
полоски-эквалайзер.
        '''
        self.equalizer = BarsEqualizer(); center.addWidget(self.equalizer)
        main.addLayout(center)
        '''
справа кнопки "открыть список", "расширить", плюс неоновый баннер.
        '''
        right = QVBoxLayout(); right.setSpacing(8)
        self.open_list_btn = QPushButton(); self.open_list_btn.setIcon(self.style().standardIcon(QStyle.SP_FileDialogListView)); self.open_list_btn.setFixedSize(40,40); self.open_list_btn.clicked.connect(self.toggle_tracklist_window); right.addWidget(self.open_list_btn)
        self.expand_btn = QToolButton(); self.expand_btn.setText('⤢'); self.expand_btn.setFixedSize(36,36); self.expand_btn.clicked.connect(self.toggle_expand_x); right.addWidget(self.expand_btn)
        self.neon = NeonBanner(); right.addWidget(self.neon)
        right.addStretch(); main.addLayout(right)
        '''
стиль кнопок, чтоб не выглядели как унылый виндовс.
        '''
        self.setStyleSheet("""QPushButton{ background: transparent; border-radius:12px; color: #eafcff; } QPushButton:hover{ background: rgba(255,255,255,8); }""")
        self.play_btn.setProperty('big','1'); self.play_btn.setStyleSheet("""QPushButton[big='1']{ border-radius:48px;
background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(140,20,255,255), stop:0.5 rgba(20,220,255,200), stop:1 rgba(255,40,120,220));
color:white; font-weight:700; }""")
        '''
обновляем иконку play/pause.
        '''
        self._update_play_icon()
        
    def paintEvent(self, ev): #рисуем фон.
        painter = QPainter(self); r = self.rect()
        '''
неоновые градиенты, чтоб переливалось.
        '''
        g = QLinearGradient(r.topLeft(), r.bottomRight()); h = (self.hue%360)
        c1 = QColor.fromHsl((h)%360, 220, 80, 240); c2 = QColor.fromHsl((h+60)%360,210,80,220); c3 = QColor.fromHsl((h+140)%360,200,70,200)
        g.setColorAt(0.0, c1); g.setColorAt(0.5, c2); g.setColorAt(1.0, c3)
        painter.setRenderHint(QPainter.Antialiasing); painter.setBrush(QBrush(g)); painter.setPen(Qt.NoPen); painter.drawRoundedRect(QRectF(r),14.0,14.0)
        inner = r.adjusted(8,8,-8,-8); glow = QLinearGradient(inner.topLeft(), inner.bottomLeft()); glow.setColorAt(0.0, QColor(255,255,255,12)); glow.setColorAt(1.0, QColor(0,0,0,60))
        '''
рисуем круглые рамки и подсветку.
        '''
        painter.setBrush(QBrush(glow)); painter.drawRoundedRect(QRectF(inner),10.0,10.0)
        pen = QPen(QColor(120,255,255,90)); pen.setWidth(2); painter.setPen(pen); painter.setBrush(Qt.NoBrush); painter.drawRoundedRect(QRectF(inner.adjusted(2,2,-2,-2)),10.0,10.0)

        '''
kаждую сотку миллисекунд двигаем оттенок → фон меняется
        '''
    def _on_tick(self):
        self.hue += 2; self.update()

    def _on_player_position_changed(self, pos=None):
        self._sync_effective_pos()

        '''
— эти методы следят за тем, где мы в треке и как долго он идёт.
— _tick_position ещё и обновляет таймер, иконки, эквалайзер.
        '''
    def _sync_effective_pos(self):
        try:
            pos = self.player.get_time()
            if pos is None:
                pos = 0
        except Exception:
            pos = 0
        self.effective_pos = float(pos); self.last_tick_time = time.monotonic(); self._update_ui_after_position()

    def _tick_position(self):
        # Poll VLC player for accurate position/duration
        try:
            qt_pos = float(self.player.get_time() or 0)
        except Exception:
            qt_pos = 0.0
        try:
            qt_dur_raw = int(self.player.get_length() or 0)
        except Exception:
            qt_dur_raw = 0

        # Conservative duration caching: only update cached duration if new value is greater
        if qt_dur_raw and qt_dur_raw > 0:
            # if media just changed we accept any new value
            if self._media_changed or qt_dur_raw >= self._last_known_duration:
                self._last_known_duration = qt_dur_raw
                self._media_changed = False
            # otherwise ignore smaller durations (prevents mysterious decreases)
        # if backend returns 0/None, keep using last known duration
        display_dur = int(self._last_known_duration)

        # clamp position to known duration to avoid odd displays
        if display_dur and qt_pos > display_dur:
            qt_pos = float(display_dur)

        pos_display = int(qt_pos)

        self._update_play_icon()
        self.timer_label.setText(f"{ms_to_hms(pos_display)}")
        if time.monotonic() > self._suppress_until:
            self._autosync(pos_display)
        self.equalizer.set_playing(getattr(self.player, 'is_playing', lambda: False)())
        self._update_list_markers()

        '''
меняет иконку кнопки на play/pause в зависимости от состояния.
        '''
    def _update_play_icon(self):
        try:
            if getattr(self.player, 'is_playing', lambda: False)():
                icon = self.style().standardIcon(QStyle.SP_MediaPause)
            else:
                icon = self.style().standardIcon(QStyle.SP_MediaPlay)
            self.play_btn.setIcon(icon); self.play_btn.setIconSize(QSize(40,40))
        except Exception:
            pass

        '''
если играет → ставим на паузу.
— если молчит → запускаем.
        '''
    def toggle_play(self):
        try:
            if getattr(self.player, 'is_playing', lambda: False)():
                self.player.pause()
            else:
                self.player.play()
        except Exception:
            try:
                self.player.play()
            except Exception:
                pass
        self._update_play_icon()
        self.equalizer.set_playing(getattr(self.player, 'is_playing', lambda: False)())


        '''
открываем mp3, кидаем его в плеер, отмечаем что трек поменялся.
— через 300 мс запускаем проигрывание.
        '''
    def load_mix(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open mix (mp3)', '', 'Audio Files (*.mp3);;All Files (*)')
        if path:
            self._mix_path = path
            try:
                media = self.vlc_instance.media_new(path)
                self.player.set_media(media)
            except Exception:
                try:
                    media = self.vlc_instance.media_new_path(path)
                    self.player.set_media(media)
                except Exception:
                    pass
            # mark media changed so duration cache is refreshed on next good reading
            self._media_changed = True; self._last_known_duration = 0
            QTimer.singleShot(300, lambda: (self._sync_effective_pos(), self.player.play(), self._update_play_icon()))

            '''
— открываем файл с треклистом, следим за ним.
— если он меняется, подгружаем заново.
— в reload_tracklist — обновляем список и выбираем трек, если совпадает UID.
            '''
    def load_tracklist(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Open tracklist (txt)', '', 'Text Files (*.txt);;All Files (*)')
        if path:
            self.set_tracklist_path(path)

    def set_tracklist_path(self, path):
        if not path or not os.path.exists(path):
            return
        try:
            prev_files = list(self.watcher.files()); prev_dirs = list(self.watcher.directories())
            if prev_files: self.watcher.removePaths(prev_files)
            if prev_dirs: self.watcher.removePaths(prev_dirs)
        except Exception:
            pass
        self.tracklist_path = path
        try:
            self.watcher.addPath(path); self.watcher.addPath(os.path.dirname(path))
        except Exception:
            pass
        self.reload_tracklist()

    def reload_tracklist(self):
        prev_uid = self.current_uid
        if not self.tracklist_path:
            self.tracks = []; self.trackmap = {}
        else:
            self.tracks = parse_tracklist(self.tracklist_path)
            self.trackmap = {t['uid']: idx for idx, t in enumerate(self.tracks)}
        self.tl_window.set_tracks(self.tracks, font_family=self.font_family)
        if prev_uid and prev_uid in self.trackmap:
            self.current_uid = prev_uid
            if self.tl_window.isVisible() and self.tl_window.follow_cb.isChecked() and not self.tl_window.is_user_interacting():
                self.tl_window.select_by_uid(self.current_uid)
        if self.tl_window.fit_cb.isChecked():
            self.tl_window.fit_to_all(len(self.tracks))

    def _on_tracklist_changed(self, _):
        QTimer.singleShot(350, self.reload_tracklist)

        '''
— если окно треклиста открыто → прячем.
— если закрыто → красиво открываем снизу или сверху, чтоб влезло в экран.
        '''
    def toggle_tracklist_window(self):
        if self.tl_window.isVisible():
            self.tl_window.hide(); return
        app = QApplication.instance(); screen = app.primaryScreen().availableGeometry(); max_h = screen.height()-160
        if self.tl_window.fit_cb.isChecked():
            self.tl_window.fit_to_all(len(self.tracks))
        else:
            desired_h = min(max_h, max(300, len(self.tracks)*self.tl_window._item_h + 80)); desired_w = min(1200, screen.width()-200)
            self.tl_window.resize(desired_w, desired_h)
        main_geo = self.geometry(); x = max(10, min(screen.width()-self.tl_window.width()-10, main_geo.left())); y = main_geo.bottom()+10
        if y + self.tl_window.height() > screen.height()-10: y = max(10, main_geo.top() - self.tl_window.height() - 10)
        self.tl_window.move(QPoint(x,y)); self.tl_window.show(); self.tl_window.raise_(); self.tl_window.activateWindow()
        if self.current_uid and self.tl_window.follow_cb.isChecked() and not self.tl_window.is_user_interacting():
            self.tl_window.select_by_uid(self.current_uid)


            '''
ручная перемотка по миллисекундам или по треку (UID).
— сразу обновляем надпись, синхру и иконки.
            '''
    def seek_ms(self, ms, play=True):
        try:
            ms_int = int(ms)
        except Exception:
            ms_int = 0
        try:
            self.player.set_time(ms_int)
        except Exception:
            try:
                self.player.set_time(int(ms_int))
            except Exception:
                pass
        self.effective_pos = float(ms_int); self.last_tick_time = time.monotonic()
        if play:
            try:
                self.player.play()
            except Exception:
                pass
        # update immediately and suppress autosync a bit longer to avoid race
        self._suppress_until = time.monotonic() + 2.2
        self._update_play_icon()
        QTimer.singleShot(140, lambda: (self._sync_effective_pos(), self._update_ui_after_position()))

    def seek_to_uid(self, uid, play=True):
        if uid not in self.trackmap:
            return
        idx = self.trackmap[uid]; track = self.tracks[idx]
        self.current_uid = uid
        # show immediately
        self.track_label.setText(track['display'])
        # mark media/time change suppression to avoid immediate autosync override
        self._suppress_until = time.monotonic() + 2.2
        # reflect selection in dialog if visible
        if self.tl_window and self.tl_window.isVisible():
            self.tl_window.select_by_uid(uid)
        # perform seek
        self.seek_ms(track['time_ms'], play=play)
        # update markers immediately
        self._update_list_markers()

        '''
— автопереключение текущего трека по позиции проигрывания.
— меняет надпись и синхрит с треклистом.
        '''
    def _autosync(self, pos_display):
        if not self.tracks:
            self.current_uid = None; return
        idx = None
        for i, t in enumerate(self.tracks):
            if t['time_ms'] <= pos_display:
                idx = i
        if idx is None:
            new_uid = None
        else:
            new_uid = self.tracks[idx]['uid']
        # only update if changed
        if new_uid != self.current_uid:
            self.current_uid = new_uid
            # update label immediately when autosync changes current
            if self.current_uid and self.current_uid in self.trackmap:
                self.track_label.setText(self.tracks[self.trackmap[self.current_uid]]['display'])
            else:
                self.track_label.setText('No track')
        if self.tl_window.isVisible() and self.tl_window.follow_cb.isChecked() and not self.tl_window.is_user_interacting():
            self.tl_window.select_by_uid(self.current_uid)

            '''
обновляет текст времени и название трека (с учётом suppression-флага).
            '''
    def _update_ui_after_position(self):
        try:
            qt_pos = float(self.player.get_time() or 0)
        except Exception:
            qt_pos = 0.0
        # prefer cached duration
        display_dur = int(self._last_known_duration)
        pos_display = int(qt_pos)
        self.timer_label.setText(f"{ms_to_hms(pos_display)}")
        if self.current_uid and time.monotonic() <= self._suppress_until:
            if self.current_uid in self.trackmap:
                self.track_label.setText(self.tracks[self.trackmap[self.current_uid]]['display'])
        else:
            self._autosync(pos_display)
        self._update_list_markers()


        '''
разворачивает окно на всю ширину экрана или обратно.
        '''
    def toggle_expand_x(self):
        app = QApplication.instance(); screen = app.primaryScreen().availableGeometry()
        if not self._expanded:
            self.setFixedWidth(screen.width()-40); self._expanded=True
        else:
            self.setFixedWidth(self._normal_width); self._expanded=False
        self.track_label.resize(self.track_label.width(), self.track_label.height()); self.track_label.update()

        '''
ищет, был ли клик по кнопке (чтоб окно не уехало при клике).
        '''
    def _find_ancestor_button(self, widget):
        w = widget
        from PyQt5.QtWidgets import QToolButton
        while w:
            if isinstance(w, QPushButton) or isinstance(w, QToolButton):
                return w
            w = w.parentWidget()
        return None

    '''
позволяют таскать окно мышкой, как чемоданчик с района.
    '''
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos()); btn = self._find_ancestor_button(child)
            if btn:
                QApplication.sendEvent(btn, event); self._dragging=False; return
            self._dragging=True; self._drag_off = event.globalPos() - self.frameGeometry().topLeft(); event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and self._drag_off is not None:
            new_pos = event.globalPos() - self._drag_off; self.move(new_pos); event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._dragging=False; self._drag_off=None; super().mouseReleaseEvent(event)

        '''
обновляет подсветку треков в списке:
текущий — голубой, выбранный — зелёный, остальные бледные.
        '''
    def _update_list_markers(self):
        try:
            if not self.tl_window or self.tl_window.listw.count() == 0:
                return
            sel_uid = None
            cur_row = self.tl_window.listw.currentRow()
            if cur_row >= 0:
                sel_uid = self.tl_window.listw.item(cur_row).data(Qt.UserRole)
            for r in range(self.tl_window.listw.count()):
                it = self.tl_window.listw.item(r)
                widget = self.tl_window.listw.itemWidget(it)
                uid = it.data(Qt.UserRole)
                if widget and hasattr(widget, 'marker'):
                    if uid == self.current_uid:
                        widget.marker.setStyleSheet("background: rgba(80,240,255,220); border-radius:6px;")
                    elif sel_uid is not None and uid == sel_uid:
                        widget.marker.setStyleSheet("background: rgba(140,255,150,220); border-radius:6px;")
                    else:
                        widget.marker.setStyleSheet("background: rgba(255,255,255,14); border-radius:6px;")
        except Exception:
            pass

        '''
— тут вся магия звука:

Берём байты из буфера.

Конвертим в numpy массив.

Если стерео → сводим в моно.

Считаем спектр через FFT.

Режем на группы → делаем уровни для эквалайзера.

Считаем громкость RMS → кидаем её в неоновую подсветку.
        '''
    def _on_audio_buffer(self, audio_buffer):
        if not self._have_numpy:
            return
        try:
            ba = audio_buffer.data()
            raw_bytes = bytes(ba)
            if not raw_bytes:
                return
            np = self._np
            try:
                data = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            except Exception:
                return
            ch = 1
            try:
                ch = audio_buffer.format().channelCount()
            except Exception:
                ch = 1
            if ch > 1:
                try:
                    data = data.reshape(-1, ch)
                    data = data.mean(axis=1)
                except Exception:
                    pass
            if data.size < 64:
                return
            if data.size > 8192:
                data = data[:8192]
            window = np.hanning(len(data))
            spec = np.abs(np.fft.rfft(data * window))
            spec = spec + 1e-8
            log_spec = 20.0 * np.log10(spec)
            log_spec = log_spec - log_spec.min()
            if log_spec.max() > 0:
                log_spec = log_spec / log_spec.max()
            else:
                log_spec = log_spec * 0.0
            bands = np.array_split(log_spec, self.equalizer._bars_n)
            levels = [float(b.mean()) if len(b)>0 else 0.0 for b in bands]
            levels = [max(0.02, min(1.0, l)) for l in levels]
            self.equalizer.set_levels(levels)
            rms = np.sqrt(np.mean(np.square(data)))
            global_level = min(1.0, rms / 3000.0)
            self.neon.set_audio_level(global_level)
        except Exception:
            return

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = CyberDeckWidget(); w.show()
    test_path = os.path.join(os.path.dirname(__file__), "tracklist.txt")
    if os.path.exists(test_path):
        w.set_tracklist_path(test_path)
    sys.exit(app.exec_())
