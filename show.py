import pygame
import os
import re
from pathlib import Path
import codecs
import locale
import sys

class MapVisualizer:
    def __init__(self):
        pygame.init()

        # Определение системной кодировки
        self.system_encoding = locale.getpreferredencoding()
        if sys.platform == 'win32':
            self.system_encoding = 'cp1251'

        # Находим рабочую директорию с файлами
        self.game_dir = self.find_game_directory()
        if not self.game_dir:
            raise FileNotFoundError("Не найдена директория с игровыми файлами")

        # Читаем размеры карты из ANT.DAT
        self.map_width, self.map_height = self.read_map_dimensions()

        # Читаем игровые константы
        self.read_game_constants()

        # Загружаем фоновое изображение с учетом регистра
        map_file = self.find_file('MAP.BMP')
        self.original_background = pygame.image.load(map_file)
        self.aspect_ratio = self.original_background.get_width() / self.original_background.get_height()
        
        # Создаем одну поверхность для всего содержимого
        self.canvas = self.original_background.copy()
        self.canvas_width = self.original_background.get_width()
        self.canvas_height = self.original_background.get_height()
        
        # Создаем начальную масштабированную канву
        self.scaled_canvas = self.canvas.copy()
        
        # Простое определение границ игрового поля
        width, height = self.original_background.get_width(), self.original_background.get_height()
        self.field_bounds = (0, 0, width, height)
        
        # Вычисляем размеры клетки отдельно по горизонтали и вертикали
        self.cell_width = width / self.map_width
        self.cell_height = height / self.map_height
        
        # Для элементов интерфейса используем высоту клетки
        self.cell_size = self.cell_height  # Изменено с min() на высоту клетки
        
        # Устанавливаем размер шрифта и высоту панели
        self.font = pygame.font.Font(None, int(self.cell_height * 0.7))  # 70% от высоты клетки
        self.panel_height = int(self.cell_height * 1.5)
        
        # Добавляем параметры для панели игроков
        self.player_panel_height = int(self.cell_height * 2)  # Высота панели игроков
        self.color_rect_width = 30  # Ширина цветного прямоугольника для каждого игрока
        self.color_rect_height = 20  # Высота цветного прямоугольника
        self.color_spacing = 5  # Расстояние между цветными прямоугольниками
        
        # Обновляем размеры окна с учетом обеих панелей
        self.screen_width = self.canvas_width
        self.screen_height = self.canvas_height + self.panel_height + self.player_panel_height
        
        # Позиции панелей
        self.panel_y = self.canvas_height
        self.player_panel_y = self.panel_y + self.panel_height
        
        # Инициализируем списки для хранения данных игроков
        self.current_players = []
        self.selected_player = None
        
        # Создаем окно с новыми размерами
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        
        # Словарь для игровых элементов
        self.game_objects = {
            'г': ('Гном', (139, 69, 19)),
            'в': ('Варвар', (165, 42, 42)),
            'э': ('Эльф', (34, 139, 34)),
            'о': ('Орк', (107, 142, 35)),
            'п': ('Пехота', (169, 169, 169)),
            'р': ('Рыцарь', (192, 192, 192)),
            'м': ('Маг', (138, 43, 226)),
            'з': ('Зомби', (85, 107, 47)),
            'д': ('Дракон', (178, 34, 34)),
            'ф': ('Корабль', (0, 0, 139)),
            'К': ('Крепость', (139, 0, 0)),
            'Г': ('Город', (128, 128, 128)),
            'З': ('Замок', (47, 79, 79)),
            'П': ('Поместье', (160, 82, 45)),
            'Б': ('Башня', (112, 128, 144)),
            'C': ('Медь', (184, 115, 51)),
            'S': ('Серебро', (192, 192, 192)),
            'G': ('Золото', (255, 215, 0)),
            'M': ('Мифрил', (173, 216, 230))
        }

        self.current_turn = 0
        self.max_turn = self.find_max_turn()
        
        # Загружаем данные игроков из нулевого хода
        print("Начинаем загрузку данных игроков...")
        self.load_initial_players()
        print(f"Загружено игроков: {len(self.current_players)}")
        
        self.cell_size = self.calculate_cell_size()
        self.font = pygame.font.Font(None, int(self.cell_height * 0.7))  # 70% от высоты клетки

        # Загружаем изображения пиктограмм с учетом регистра
        osnova_file = self.find_file('OSNOVA.BMP')
        rudnici_file = self.find_file('RUDNICI.BMP')
        self.army_icons = self.load_icons(osnova_file, 16)  # 16 иконок армий/строений
        self.mine_icons = self.load_icons(rudnici_file, 4)  # 4 иконки рудников
        
        # Словарь соответствия символов и индексов иконок
        self.icon_indices = {
            'л': 0,  # Личное войско
            'г': 1,  # Гном
            'в': 2,  # Варвар
            'э': 3,  # Эльф
            'о': 4,  # Орк
            'п': 5,  # Пехота
            'р': 6,  # Рыцарь
            'м': 7,  # Маг
            'з': 8,  # Зомби
            'д': 9,  # Дракон
            'ф': 10, # Корабль
            'К': 11, # Крепость
            'Г': 12, # Город
            'З': 13, # Замок
            'П': 14, # Поместье
            'Б': 15, # Башня
            'C': 0,  # Медь (индекс в mine_icons)
            'S': 1,  # Серебро
            'G': 2,  # Золото
            'M': 3   # Мифрил
        }

        # Поиск границ игрового поля
        self.left_border, self.cell_size = self.find_left_border()
        if self.left_border is None:
            self.left_border = 0
            # Используем старый способ вычисления размера клетки
            width, height = self.original_background.get_width(), self.original_background.get_height()
            self.cell_width = width / self.map_width
            self.cell_height = height / self.map_height
            self.cell_size = min(self.cell_width, self.cell_height)

        # Добавляем атрибут для хранения отладочной поверхности
        self.debug_surface = None
        
        # Находим границы игрового поля
        self.find_game_borders()

        # Вычисляем базовый размер клетки (до масштабирования)
        self.base_cell_width = self.cell_width
        self.base_cell_height = self.cell_height
        self.base_cell_size = min(self.base_cell_width, self.base_cell_height)

        # Создаем поверхность для подсветки клетки
        self.highlight_surface = pygame.Surface((self.cell_width, self.cell_height))
        self.highlight_surface.set_alpha(64)  # Полупрозрачность (0-255)
        self.highlight_surface.fill((255, 255, 255))  # Белый цвет
        
        # Скрываем курсор
        pygame.mouse.set_visible(True)  # Изначально показываем курсор

        # Шрифт для всплывающего окна
        self.tooltip_font = pygame.font.Font(None, int(self.cell_height * 1.1))  # 50% от высоты клетки

        # Добавляем атрибут для хранения объектов текущего хода
        self.current_turn_objects = []

    def read_game_constants(self):
        """Читает размеры поля из ANT.DAT и цвета игроков из нулевого хода"""
        # Чтение ANT.DAT
        try:
            ant_file = self.find_file('ANT.DAT')
            with open(ant_file, 'rb') as file:
                content = file.read()
                # Пробуем разные кодировки
                for encoding in ['cp1251', 'cp866', 'utf-8']:
                    try:
                        text = content.decode(encoding)
                        lines = text.split('\n')
                        self.map_width = int(lines[1].strip())
                        self.map_height = int(lines[2].strip())
                        break
                    except UnicodeDecodeError:
                        continue
        except Exception as e:
            print(f"Ошибка чтения ANT.DAT: {e}")
            self.map_width = 130  # Значения по умолчанию
            self.map_height = 57

        # Чтение цветов игроков из нулевого хода
        try:
            # Проверяем оба варианта именования нулевого хода
            turn0_file = None
            for name in ['Год0.svs', 'год0.svs', '®¤0.svs']:
                full_path = os.path.join(self.game_dir, name)
                if os.path.exists(full_path):
                    turn0_file = full_path
                    break

            if turn0_file:
                with open(turn0_file, 'rb') as f:
                    content = f.read()
                    # Пробуем разные кодировки
                    for encoding in ['cp1251', 'cp866', 'utf-8']:
                        try:
                            text = content.decode(encoding)
                            lines = text.split('\n')
                            self.player_colors = {}
                            
                            current_player = None
                            for line in lines:
                                input_string = line.strip()
                                print(f"New line: {input_string}")
                                if line.startswith('Player'):
                                    print(f"It's: {'Player!'}")
                                    continue
                                elif len(line.split()) >= 3:
                                    parts = line.split()
                                    if len(parts) >= 3 and parts[0].isdigit():
                                        # Строка с координатами и цветом игрока
                                        print(f"Digit Line: {parts}")
                                        try:
                                            color = int(parts[2])
                                            if current_player:
                                                self.player_colors[current_player] = color
                                                print(f"Цвет игрока: {color}")
                                        except ValueError:
                                            continue
                                else:
                                    # Строка с именем игрока
                                    input_string = line.strip()
                                    # Регулярное выражение для извлечения данных
                                    pattern = r'^(.*?)\s*\((.*?)\)\s*(.*)$'
                                    print(f"input_string: {input_string}")
                                    # Поиск совпадений
                                    match = re.match(pattern, input_string)
                                    
                                    if match:
                                        current_player = match.group(1).strip()
                                        player_name = match.group(2).strip()
                                        country_name = match.group(3).strip()
                                        
                                        print(f"Имя персонажа: {current_player}")
                                        print(f"Имя игрока: {player_name}")
                                        print(f"Название страны: {country_name}")
                                    else:
                                        print("Не удалось извлечь данные из строки.")
                        except UnicodeDecodeError:
                            continue
        except Exception as e:
            print(f"Ошибка чтения Год0.svs: {e}")
            self.player_colors = {}

    def load_turn_data(self, turn):
        """Загрузка данных хода"""
        try:
            # Ищем файл хода с учетом обоих вариантов именования
            turn_file = None
            
            # Проверяем все возможные варианты имени файла
            possible_names = [
                f'Год{turn}.svs',
                f'год{turn}.svs',
                f'®¤{turn}.svs'
            ]
            
            for name in possible_names:
                full_path = os.path.join(self.game_dir, name)
                if os.path.exists(full_path):
                    turn_file = full_path
                    break

            if not turn_file:
                return []

            with open(turn_file, 'rb') as file:
                content = file.read()
                # Пробуем разные кодировки
                for encoding in ['cp1251', 'cp866', 'utf-8']:
                    try:
                        text = content.decode(encoding)
                        lines = text.split('\n')
                        
                        objects = []
                        players_info = []  # Список для хранения информации об игроках
                        current_player = None
                        
                        for line in lines:
                            line = line.strip().rstrip(',').strip()
                            
                            if line.startswith('Player'):
                                if current_player:
                                    players_info.append(current_player)
                                current_player = {'objects': []}
                                continue
                            
                            if not line or line.startswith('END'):
                                continue
                            
                            # Проверяем, является ли строка информацией об игроке
                            if current_player is not None and len(line.split()) < 3:
                                # Парсим имя игрока и название страны
                                match = re.match(r'(.*?)\s*\((.*?)\)', line)
                                if match:
                                    current_player['name'] = match.group(1).strip()
                                    current_player['country'] = match.group(2).strip()
                                continue
                            
                            # Парсим координаты объекта
                            parts = [part.strip() for part in line.split() if part.strip()]
                            if len(parts) >= 3:
                                obj_type = parts[0]
                                if obj_type in self.game_objects:
                                    try:
                                        x = int(parts[1])
                                        y = int(parts[2])
                                        state = int(parts[3].rstrip(',')) if len(parts) > 3 else 0
                                        obj = (obj_type, x, y, state)
                                        objects.append(obj)
                                        if current_player:
                                            current_player['objects'].append(obj)
                                    except (ValueError, IndexError) as e:
                                        print(f"Ошибка парсинга строки '{line}': {e}")
                                else:
                                    # Пропускаем неизвестные типы объектов без вывода ошибки
                                    continue
                        
                        # Добавляем последнего игрока
                        if current_player:
                            players_info.append(current_player)
                        
                        # Сохраняем информацию об игроках
                        self.current_players = players_info
                        return objects
                    except UnicodeDecodeError:
                        continue
                        
        except Exception as e:
            print(f"Ошибка загрузки хода {turn}: {e}")
            return []

    def load_icons(self, filename, count):
        """Загружает и разделяет изображение на отдельные иконки"""
        try:
            image = pygame.image.load(filename)
            width = image.get_width() // count
            height = image.get_height()
            icons = []
            
            # Создаем маску для замены белого фона на прозрачный
            for i in range(count):
                icon = pygame.Surface((width, height), pygame.SRCALPHA)
                icon.blit(image, (-i * width, 0))
                
                # Делаем белый цвет прозрачным
                pixels = pygame.PixelArray(icon)
                pixels.replace((255, 255, 255), (0, 0, 0, 0))
                del pixels
                
                icons.append(icon)
            return icons
        except pygame.error as e:
            print(f"Ошибка загрузки {filename}: {e}")
            return []

    def draw_game_objects(self, objects):
        """Отрисовка игровых объектов"""
        # Сохраняем объекты текущего хода
        self.current_turn_objects = objects
        
        # Получаем коэффициенты масштабирования
        scale_x = self.scaled_canvas.get_width() / self.canvas_width
        scale_y = self.scaled_canvas.get_height() / self.canvas_height
        
        # Получаем смещение канвы для центрирования
        canvas_x = (self.screen_width - self.scaled_canvas.get_width()) // 2
        canvas_y = 0
        
        # Используем оригинальные размеры клеток для расчета позиций
        cell_width = self.field_bounds[2] / self.map_width
        cell_height = self.field_bounds[3] / self.map_height
        
        for obj_type, x, y, state in objects:
            # Рассчитываем координаты в оригинальном масштабе
            original_x = self.field_bounds[0] + (x - 1) * cell_width
            original_y = self.field_bounds[1] + (y - 1) * cell_height
            
            # Масштабируем координаты
            scaled_x = canvas_x + original_x * scale_x
            scaled_y = canvas_y + original_y * scale_y
            
            # Вычисляем центр клетки
            cell_center_x = scaled_x + (cell_width * scale_x) / 2
            cell_center_y = scaled_y + (cell_height * scale_y) / 2
            
            # Определяем тип объекта (строение или войско)
            is_building = obj_type in ['К', 'Г', 'З', 'П', 'Б', 'C', 'S', 'G', 'M']
            is_army = obj_type.islower()  # Все войска обозначаются строчными буквами
            
            # Используем разные размеры для армий и строений
            if is_building:
                icon_size = int(min(cell_width, cell_height) * scale_x)  # Полный размер клетки для строений
            else:
                icon_size = int(min(cell_width, cell_height) * scale_x * 0.8)  # 80% размера для армий
            
            # Получаем цвет игрока
            player_color = self.game_objects[obj_type][1]
            
            # Вычисляем координаты для отрисовки
            circle_center = (int(cell_center_x), int(cell_center_y))
            
            if is_army:  # Рисуем круг только для войск
                # Рисуем круг с цветом игрока
                pygame.draw.circle(self.screen, player_color, circle_center, icon_size // 2)
                
                # Определяем цвет обводки на основе яркости цвета игрока
                r, g, b = player_color
                brightness = (r + g + b) / 3
                outline_color = (0, 0, 0) if brightness > 127 else (255, 255, 255)
                
                # Рисуем обводку толщиной 1 пиксель
                pygame.draw.circle(self.screen, outline_color, circle_center, icon_size // 2, 1)
            else:  # Для строений рисуем прямоугольник с заливкой
                rect = pygame.Rect(
                    int(cell_center_x - icon_size // 2),
                    int(cell_center_y - icon_size // 2),
                    icon_size,
                    icon_size
                )
                pygame.draw.rect(self.screen, player_color, rect)
            
            # Определяем, какой набор иконок использовать
            if obj_type in ['C', 'S', 'G', 'M']:
                icons = self.mine_icons
            else:
                icons = self.army_icons
            
            # Получаем и отрисовываем иконку
            if obj_type in self.icon_indices:
                icon_index = self.icon_indices[obj_type]
                icon = icons[icon_index]
                scaled_icon = pygame.transform.scale(icon, (icon_size, icon_size))
                
                # Вычисляем позицию для центрирования иконки
                icon_x = int(cell_center_x - icon_size // 2)
                icon_y = int(cell_center_y - icon_size // 2)
                
                self.screen.blit(scaled_icon, (icon_x, icon_y))
            
            # Убираем отрисовку дополнительных обводок состояний
            # if state & 128:  # Столица/ЛВ
            #     pygame.draw.circle(self.screen, (255, 215, 0), circle_center, icon_size // 2 + 2, 2)
            # elif state & 32:  # Без АД
            #     pygame.draw.circle(self.screen, (128, 128, 128), circle_center, icon_size // 2 + 2, 2)
            # 
            # if state & 64:  # На воде
            #     pygame.draw.circle(self.screen, (0, 0, 255), circle_center, icon_size // 2 + 4, 2)

        # После отрисовки всех объектов добавляем подсветку текущей клетки
        mouse_pos = pygame.mouse.get_pos()
        self.draw_cell_highlight(mouse_pos)

    def draw_cell_highlight(self, mouse_pos):
        """Отрисовка подсветки клетки под курсором"""
        # Получаем коэффициенты масштабирования
        scale_x = self.scaled_canvas.get_width() / self.canvas_width
        scale_y = self.scaled_canvas.get_height() / self.canvas_height
        
        # Получаем смещение канвы для центрирования
        canvas_x = (self.screen_width - self.scaled_canvas.get_width()) // 2
        canvas_y = 0
        
        # Проверяем, находится ли курсор в пределах канвы
        canvas_rect = pygame.Rect(
            canvas_x, 
            0, 
            self.scaled_canvas.get_width(), 
            self.scaled_canvas.get_height()
        )
        
        if not canvas_rect.collidepoint(mouse_pos):
            pygame.mouse.set_visible(True)
            return
            
        pygame.mouse.set_visible(False)
        
        # Преобразуем координаты мыши в координаты внутри канвы
        field_x = (mouse_pos[0] - canvas_x) / scale_x
        field_y = mouse_pos[1] / scale_y
        
        # Получаем границы игрового поля
        field_left, field_top, field_width, field_height = self.field_bounds
        
        # Проверяем, находится ли курсор в пределах игрового поля
        if (field_left <= field_x <= field_left + field_width and 
            field_top <= field_y <= field_top + field_height):
            
            # Вычисляем индексы клетки (с учетом того, что игровые координаты начинаются с 1)
            cell_x = int((field_x - field_left) / self.base_cell_width)
            cell_y = int((field_y - field_top) / self.base_cell_height)
            
            # Проверяем, находится ли клетка в пределах сетки
            if 0 <= cell_x < self.map_width and 0 <= cell_y < self.map_height:
                # Рассчитываем координаты в оригинальном масштабе
                original_x = field_left + cell_x * self.base_cell_width
                original_y = field_top + cell_y * self.base_cell_height
                
                # Масштабируем координаты
                scaled_x = canvas_x + original_x * scale_x
                scaled_y = original_y * scale_y
                
                # Вычисляем размер иконки как для зданий
                icon_size = int(min(self.base_cell_width, self.base_cell_height) * scale_x)
                
                # Вычисляем центр клетки
                cell_center_x = scaled_x + (self.base_cell_width * scale_x) / 2
                cell_center_y = scaled_y + (self.base_cell_height * scale_y) / 2
                
                # Создаем прямоугольник для подсветки относительно центра клетки
                rect = pygame.Rect(
                    int(cell_center_x - icon_size // 2),
                    int(cell_center_y - icon_size // 2),
                    icon_size,
                    icon_size
                )
                
                # Создаем поверхность для подсветки
                highlight_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                highlight_surface.fill((255, 255, 255, 64))
                
                # Отрисовываем подсветку
                self.screen.blit(highlight_surface, rect)
                
                # Рисуем контур
                pygame.draw.rect(self.screen, (255, 255, 255), rect, 1)
                
                # Отрисовываем всплывающее окно только для подсвеченной клетки
                terrain_type = self.get_cell_terrain(cell_x, cell_y)
                self.draw_coordinates_tooltip((cell_center_x, cell_center_y), cell_x, cell_y, terrain_type)

    def draw_interface(self):
        """Отрисовка интерфейса управления"""
        # Отрисовка основной панели управления
        panel_rect = pygame.Rect(0, self.panel_y, self.screen_width, self.panel_height)
        pygame.draw.rect(self.screen, (200, 200, 200), panel_rect)
        
        # Отрисовка кнопок навигации
        button_width = 100
        button_height = 30
        button_margin = 10
        
        prev_button = pygame.Rect(button_margin, 
                                self.panel_y + (self.panel_height - button_height) // 2,
                                button_width, button_height)
        next_button = pygame.Rect(button_margin * 2 + button_width,
                                self.panel_y + (self.panel_height - button_height) // 2,
                                button_width, button_height)
        
        pygame.draw.rect(self.screen, (180, 180, 180), prev_button)
        pygame.draw.rect(self.screen, (180, 180, 180), next_button)
        
        # Отрисовка текста на кнопках
        prev_text = self.font.render("Пред", True, (0, 0, 0))
        next_text = self.font.render("След", True, (0, 0, 0))
        
        prev_text_rect = prev_text.get_rect(center=prev_button.center)
        next_text_rect = next_text.get_rect(center=next_button.center)
        
        self.screen.blit(prev_text, prev_text_rect)
        self.screen.blit(next_text, next_text_rect)
        
        # Отрисовка номера текущего хода
        turn_text = self.font.render(f"Ход: {self.current_turn}", True, (0, 0, 0))
        turn_rect = turn_text.get_rect(midleft=(button_margin * 3 + button_width * 2,
                                               self.panel_y + self.panel_height // 2))
        self.screen.blit(turn_text, turn_rect)
        
        # Отрисовка панели игроков
        player_panel_rect = pygame.Rect(0, self.player_panel_y, 
                                      self.screen_width, self.player_panel_height)
        pygame.draw.rect(self.screen, (220, 220, 220), player_panel_rect)
        
        # Отрисовка цветных прямоугольников игроков
        x = 10
        player_rects = []
        
        for player in self.current_players:
            color = player.get('color', 0)
            # Преобразуем число в RGB
            r = (color >> 16) & 255
            g = (color >> 8) & 255
            b = color & 255
            
            rect = pygame.Rect(x, self.player_panel_y + 5, 
                             self.color_rect_width, self.color_rect_height)
            pygame.draw.rect(self.screen, (r, g, b), rect)
            pygame.draw.rect(self.screen, (0, 0, 0), rect, 1)  # Рамка
            
            player_rects.append((rect, player))
            x += self.color_rect_width + self.color_spacing
        
        # Отображение информации о выбранном игроке
        if self.selected_player:
            info_y = self.player_panel_y + self.color_rect_height + 10
            name = self.selected_player.get('name', '')
            name_surface = self.font.render(f"Игрок: {name}", True, (0, 0, 0))
            self.screen.blit(name_surface, (10, info_y))
        
        # Возвращаем все интерактивные элементы
        return [prev_button, next_button] + [rect for rect, _ in player_rects]

    def handle_resize(self, width, height):
        """Обработка изменения размера окна"""
        # Сохраняем новые размеры окна
        self.screen_width = width
        self.screen_height = height
        
        # Пересоздаем окно
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        
        # Вычисляем новые размеры канвы с сохранением пропорций
        available_height = height - self.panel_height - self.player_panel_height
        canvas_height = available_height
        canvas_width = int(canvas_height * self.aspect_ratio)
        
        if canvas_width > width:
            canvas_width = width
            canvas_height = int(width / self.aspect_ratio)
        
        # Масштабируем канву
        self.scaled_canvas = pygame.transform.scale(self.canvas, (canvas_width, canvas_height))
        
        # Обновляем позиции панелей
        self.panel_y = canvas_height
        self.player_panel_y = self.panel_y + self.panel_height

    def draw_coordinates_tooltip(self, pos, cell_x, cell_y, terrain_type):
        """Отрисовка всплывающего окна с информацией о клетке"""
        # Получаем тип местности
        terrain_info = self.get_terrain_info(terrain_type)
        
        # Формируем список строк для отображения
        lines = []
        
        # Координаты и тип местности в первой строке
        coord_text = f"({cell_x + 1}-{cell_y + 1})"
        if terrain_info:
            coord_text += f" - {terrain_info}"
        lines.append(coord_text)
        
        # Добавляем информацию о строениях
        buildings = self.get_cell_buildings(cell_x, cell_y)
        if buildings:
            lines.append("")  # Пустая строка для разделения
            for building in buildings:
                owner = self.get_building_owner(cell_x, cell_y, building)
                if owner:
                    lines.append(f"{building} (Игрок {owner})")
                else:
                    lines.append(building)
        
        # Добавляем информацию о войсках
        armies = self.get_cell_armies(cell_x, cell_y)
        if armies:
            if not buildings:
                lines.append("")  # Пустая строка для разделения
            for army in armies:
                owner = self.get_army_owner(cell_x, cell_y, army)
                if owner:
                    lines.append(f"{army} (Игрок {owner})")
                else:
                    lines.append(army)
        
        # Вычисляем размеры окна
        padding = 5
        line_height = self.tooltip_font.get_height()
        max_width = 0
        
        # Получаем максимальную ширину текста
        for line in lines:
            text_surface = self.tooltip_font.render(line, True, (0, 0, 0))
            max_width = max(max_width, text_surface.get_width())
        
        tooltip_width = max_width + (padding * 2)
        tooltip_height = (len(lines) * line_height) + (padding * 2)
        
        # Определяем позицию окна относительно центра клетки
        tooltip_x = pos[0] + 10
        tooltip_y = pos[1] - tooltip_height - 10
        
        # Корректируем позицию, чтобы окно не выходило за пределы экрана
        if tooltip_x + tooltip_width > self.screen_width:
            tooltip_x = pos[0] - tooltip_width - 10
        if tooltip_x < 0:
            tooltip_x = 10
            
        if tooltip_y < 0:
            tooltip_y = pos[1] + 10
        if tooltip_y + tooltip_height > self.panel_y:
            tooltip_y = self.panel_y - tooltip_height - 10
        
        # Отрисовываем фон
        background_rect = pygame.Rect(tooltip_x, tooltip_y, tooltip_width, tooltip_height)
        pygame.draw.rect(self.screen, (255, 255, 255), background_rect)
        pygame.draw.rect(self.screen, (0, 0, 0), background_rect, 1)
        
        # Отрисовываем текст
        current_y = tooltip_y + padding
        for line in lines:
            text_surface = self.tooltip_font.render(line, True, (0, 0, 0))
            self.screen.blit(text_surface, (tooltip_x + padding, current_y))
            current_y += line_height

    def draw_canvas(self):
        """Отрисовка канвы"""
        # Очищаем экран
        self.screen.fill((255, 255, 255))
        
        # Вычисляем позицию для центрирования канвы
        x = (self.screen_width - self.scaled_canvas.get_width()) // 2
        y = 0  # Прижимаем к верхнему краю
        
        # Отрисовываем масштабированную канву
        self.screen.blit(self.scaled_canvas, (x, y))

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    # Запоминаем текущие размеры окна
                    self.handle_resize(event.w, event.h)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    button_rects = self.draw_interface()
                    
                    # Проверяем клик по кнопкам навигации
                    if button_rects[0].collidepoint(mouse_pos):  # Предыдущий ход
                        self.current_turn = max(0, self.current_turn - 1)
                    elif button_rects[1].collidepoint(mouse_pos):  # Следующий ход
                        self.current_turn = min(self.max_turn, self.current_turn + 1)
                    
                    # Проверяем клик по прямоугольникам игроков
                    for i in range(2, len(button_rects)):
                        if button_rects[i].collidepoint(mouse_pos):
                            self.selected_player = self.current_players[i-2]
                            break

            # Отрисовка всего интерфейса
            self.screen.fill((255, 255, 255))
            self.draw_canvas()
            turn_objects = self.load_turn_data(self.current_turn)
            self.draw_game_objects(turn_objects)
            self.draw_interface()
            
            pygame.display.flip()
        
        pygame.quit()

    def find_max_turn(self):
        max_turn = 0
        # Ищем файлы ходов в игровой директории с учетом обоих вариантов именования
        for file in os.listdir(self.game_dir):
            # Проверяем оба варианта именования
            year_match = re.search(r'[Гг]од(\d+)\.svs', file, re.IGNORECASE)
            alt_match = re.search(r'®¤(\d+)\.svs', file, re.IGNORECASE)
            
            if year_match:
                try:
                    turn = int(year_match.group(1))
                    max_turn = max(max_turn, turn)
                except ValueError:
                    continue
            elif alt_match:
                try:
                    turn = int(alt_match.group(1))
                    max_turn = max(max_turn, turn)
                except ValueError:
                    continue
        return max_turn

    def calculate_cell_size(self):
        # Учитываем границы карты при расчете размера клетки
        playable_width = self.original_background.get_width() - 2  # Вычитаем границы слева и справа
        playable_height = self.original_background.get_height() - 2  # Вычитаем границы сверху и снизу
        return min(playable_width / 120, playable_height / 60)

    def read_map_dimensions(self):
        try:
            ant_file = self.find_file('ANT.DAT')
            with open(ant_file, 'rb') as file:
                content = file.read()
                # Пробуем разные кодировки
                for encoding in ['cp1251', 'cp866', 'utf-8']:
                    try:
                        text = content.decode(encoding)
                        lines = text.split('\n')
                        
                        # Читаем заголовок и устанавливаем его в окно
                        title = lines[0].strip('[]').strip()
                        pygame.display.set_caption(title)
                        
                        # Читаем размеры карты
                        width = int(lines[1].strip())
                        height = int(lines[2].strip())
                        
                        return width, height
                    except UnicodeDecodeError:
                        continue
                
                raise UnicodeDecodeError("Не удалось декодировать файл ANT.DAT")
                
        except (FileNotFoundError, ValueError, IndexError) as e:
            print(f"Ошибка чтения карты: {e}")
            return 130, 57

    def find_game_directory(self):
        """Поиск директории с игровыми файлами"""
        # Проверяем текущую директорию
        if os.path.exists('ANT.DAT'):
            return '.'
            
        # Ищем в поддиректориях
        for dir_entry in os.scandir('.'):
            if dir_entry.is_dir():
                ant_path = os.path.join(dir_entry.path, 'ANT.DAT')
                if os.path.exists(ant_path):
                    return dir_entry.path
                    
        return None

    def find_file(self, filename):
        """Ищет файл независимо от регистра букв в имени"""
        # Проверяем в игровой директории
        game_path = os.path.join(self.game_dir, filename)
        if os.path.exists(game_path):
            return game_path
            
        # Ищем файл в разных регистрах
        for file in os.listdir(self.game_dir):
            if file.lower() == filename.lower():
                return os.path.join(self.game_dir, file)
                
        raise FileNotFoundError(f"Файл {filename} не найден")

    def draw_grid(self):
        """Отрисовывает сетку игрового поля"""
        if not hasattr(self, 'cell_width') or not hasattr(self, 'cell_height'):
            return

        left, top, width, height = self.field_bounds
        
        # Вертикальные линии
        for x in range(self.map_width + 1):
            x_pos = left + x * self.cell_width
            pygame.draw.line(self.debug_surface, 
                           (255, 0, 0),  # Красный цвет
                           (x_pos, top), 
                           (x_pos, top + height),
                           1)  # Толщина линии
        
        # Горизонтальные линии
        for y in range(self.map_height + 1):
            y_pos = top + y * self.cell_height
            pygame.draw.line(self.debug_surface,
                           (255, 0, 0),  # Красный цвет
                           (left, y_pos),
                           (left + width, y_pos),
                           1)  # Толщина линии

    def find_left_border(self):
        """Поиск левой границы игрового поля по черно-белому паттерну"""
        # Получаем массив пикселей
        pixel_array = pygame.surfarray.array3d(self.original_background)
        height = self.original_background.get_height()
        
        # Создаем копию фона для визуализации
        debug_surface = self.original_background.copy()
        
        # Начинаем с середины высоты изображения
        mid_height = height // 2
        scan_height = 5  # Высота области сканирования
        start_y = mid_height - scan_height // 2
        
        def is_black(color):
            return all(c < 30 for c in color)
            
        def is_white(color):
            return all(c > 225 for c in color)
            
        def find_pattern_in_row(y):
            black_count = 0
            white_count = 0
            pattern_start = None
            
            # Сканируем от 50-го пикселя к левому краю
            for x in range(50, -1, -1):
                color = tuple(pixel_array[x][y])  # Преобразуем в кортеж для вывода
                
                # Отрисовываем точку проверки
                debug_surface.set_at((x, y), (255, 0, 0))  # Красная точка
                self.screen.blit(debug_surface, (2, 2))
                pygame.display.flip()
                pygame.time.delay(10)  # Небольшая задержка для визуализации
                
                # Логируем проверку цвета
                is_black_pixel = is_black(color)
                is_white_pixel = is_white(color)
                # print(f"x={x}, y={y}, цвет={color}, ")
                # print(f"    черный={is_black_pixel} (нужно < 30 для всех компонент)")
                # print(f"    белый={is_white_pixel} (нужно > 225 для всех компонент)")
                
                if is_black_pixel:
                    black_count += 1
                    if 3 <= black_count <= 10:
                        # print(f"Найден черный паттерн длиной {black_count}")
                        # Отмечаем найденный паттерн зелеными точками
                        for i in range(x, x + black_count):
                            debug_surface.set_at((i, y), (0, 255, 0))
                        # Отрисовываем вертикальную салатовую линию на правой границе паттерна
                        border_x = x + black_count
                        for y_line in range(height):
                            debug_surface.set_at((border_x, y_line), (144, 238, 144))  # Салатовый цвет
                        self.screen.blit(debug_surface, (2, 2))
                        pygame.display.flip()
                        return border_x, black_count
                    if white_count > 0:
                        white_count = 0
                elif is_white_pixel:
                    white_count += 1
                    if 3 <= white_count <= 10:
                        # print(f"Найден белый паттерн длиной {white_count}")
                        # Отмечаем найденный паттерн зелеными точками
                        for i in range(x, x + white_count):
                            debug_surface.set_at((i, y), (0, 255, 0))
                        # Отрисовываем вертикальную салатовую линию на правой границе паттерна
                        border_x = x + white_count
                        for y_line in range(height):
                            debug_surface.set_at((border_x, y_line), (144, 238, 144))  # Салатовый цвет
                        self.screen.blit(debug_surface, (2, 2))
                        pygame.display.flip()
                        return border_x, white_count
                    if black_count > 0:
                        black_count = 0
        
        # Ищем паттерн в области сканирования
        for y in range(start_y, start_y + scan_height):
            border_x, segment_size = find_pattern_in_row(y)
            if border_x is not None:
                print(f"Найдена левая граница: x={border_x}, размер сегмента={segment_size}")
                return border_x, segment_size
        
        print("Левая граница не найдена")
        return None, None

    def find_game_borders(self):
        """Поиск всех границ игрового поля"""
        # Создаем копию фона для визуализации
        self.debug_surface = self.original_background.copy()
        
        # Находим все границы
        left_x, _ = self.find_left_border()
        right_x, _ = self.find_right_border()
        top_y, _ = self.find_top_border()
        bottom_y, _ = self.find_bottom_border()
        
        if all(x is not None for x in [left_x, right_x, top_y, bottom_y]):
            self.field_bounds = (left_x, top_y, right_x - left_x, bottom_y - top_y)
            print(f"Найдены границы поля: {self.field_bounds}")
            
            # Вычисляем размеры клеток и рисуем сетку
            if self.calculate_field_cells():
                self.draw_grid()
                # Обновляем канву с отладочной информацией
                self.canvas = self.debug_surface.copy()
                self.scaled_canvas = pygame.transform.scale(
                    self.canvas,
                    (self.scaled_canvas.get_width(), self.scaled_canvas.get_height())
                )
        else:
            print("Не удалось найти все границы поля")

    def find_right_border(self):
        """Поиск правой границы игрового поля"""
        pixel_array = pygame.surfarray.array3d(self.original_background)
        height = self.original_background.get_height()
        width = self.original_background.get_width()
        
        mid_height = height // 2
        scan_height = 5
        start_y = mid_height - scan_height // 2
        
        def is_black(color):
            return all(c < 30 for c in color)
            
        def is_white(color):
            return all(c > 225 for c in color)
        
        def find_pattern_in_row(y):
            black_count = white_count = 0
            
            # Сканируем от центра к правому краю (изменено направление)
            for x in range(width - 50, width):  # Начинаем с width-50 и идем к правому краю
                color = tuple(pixel_array[x][y])
                
                # Отрисовываем точку проверки
                self.debug_surface.set_at((x, y), (255, 0, 0))
                self.screen.blit(self.debug_surface, (2, 2))
                pygame.display.flip()
                pygame.time.delay(10)
                
                is_black_pixel = is_black(color)
                is_white_pixel = is_white(color)
                
                if is_black_pixel:
                    black_count += 1
                    if 3 <= black_count <= 10:
                        for i in range(x - black_count + 1, x + 1):  # Отмечаем паттерн
                            self.debug_surface.set_at((i, y), (0, 255, 0))
                        border_x = x - black_count + 1  # Граница - начало паттерна
                        for y_line in range(height):
                            self.debug_surface.set_at((border_x, y_line), (144, 238, 144))
                        return border_x, black_count
                    white_count = 0
                elif is_white_pixel:
                    white_count += 1
                    if 3 <= white_count <= 10:
                        for i in range(x - white_count + 1, x + 1):
                            self.debug_surface.set_at((i, y), (0, 255, 0))
                        border_x = x - white_count + 1
                        for y_line in range(height):
                            self.debug_surface.set_at((border_x, y_line), (144, 238, 144))
                        return border_x, white_count
                    black_count = 0
                else:
                    black_count = white_count = 0
            
            return None, None

        for y in range(start_y, start_y + scan_height):
            border_x, segment_size = find_pattern_in_row(y)
            if border_x is not None:
                return border_x, segment_size
        
        return None, None

    def find_top_border(self):
        """Поиск верхней границы игрового поля"""
        pixel_array = pygame.surfarray.array3d(self.original_background)
        width = self.original_background.get_width()
        
        mid_width = width // 2
        scan_width = 5
        start_x = mid_width - scan_width // 2
        
        def is_black(color):
            return all(c < 30 for c in color)
            
        def is_white(color):
            return all(c > 225 for c in color)
        
        def find_pattern_in_column(x):
            black_count = white_count = 0
            
            # Сканируем от центра к верхнему краю
            for y in range(50, 0, -1):
                color = tuple(pixel_array[x][y])
                self.debug_surface.set_at((x, y), (255, 0, 0))
                self.screen.blit(self.debug_surface, (2, 2))
                pygame.display.flip()
                pygame.time.delay(10)
                
                if is_black(color):
                    black_count += 1
                    if 3 <= black_count <= 10:
                        for i in range(y, y + black_count):  # Отмечаем паттерн
                            self.debug_surface.set_at((x, i), (0, 255, 0))
                        border_y = y + black_count  # Граница - конец паттерна
                        for x_line in range(width):
                            self.debug_surface.set_at((x_line, border_y), (144, 238, 144))
                        return border_y, black_count
                    white_count = 0
                elif is_white(color):
                    white_count += 1
                    black_count = 0
                    if 3 <= white_count <= 10:
                        for i in range(y, y + white_count):
                            self.debug_surface.set_at((x, i), (0, 255, 0))
                        border_y = y + white_count  # Граница - конец паттерна
                        for x_line in range(width):
                            self.debug_surface.set_at((x_line, border_y), (144, 238, 144))
                        return border_y, white_count
                    black_count = 0
                else:
                    black_count = white_count = 0
            return None, None

        for x in range(start_x, start_x + scan_width):
            border_y, segment_size = find_pattern_in_column(x)
            if border_y is not None:
                return border_y, segment_size
        
        return None, None

    def find_bottom_border(self):
        """Поиск нижней границы игрового поля"""
        pixel_array = pygame.surfarray.array3d(self.original_background)
        width = self.original_background.get_width()
        height = self.original_background.get_height()
        
        mid_width = width // 2
        scan_width = 5
        start_x = mid_width - scan_width // 2
        
        def is_black(color):
            return all(c < 30 for c in color)
            
        def is_white(color):
            return all(c > 225 for c in color)
        
        def find_pattern_in_column(x):
            black_count = white_count = 0
            
            # Сканируем от центра к нижнему краю (изменено направление)
            for y in range(height - 50, height):  # Начинаем с height-50 и идем к нижнему краю
                color = tuple(pixel_array[x][y])
                self.debug_surface.set_at((x, y), (255, 0, 0))
                self.screen.blit(self.debug_surface, (2, 2))
                pygame.display.flip()
                pygame.time.delay(10)
                
                if is_black(color):
                    black_count += 1
                    if 3 <= black_count <= 10:
                        for i in range(y - black_count + 1, y + 1):  # Отмечаем паттерн
                            self.debug_surface.set_at((x, i), (0, 255, 0))
                        border_y = y - black_count + 1  # Граница - начало паттерна
                        for x_line in range(width):
                            self.debug_surface.set_at((x_line, border_y), (144, 238, 144))
                        return border_y, black_count
                    white_count = 0
                elif is_white(color):
                    white_count += 1
                    black_count = 0
                    if 3 <= white_count <= 10:
                        for i in range(y - white_count + 1, y + 1):
                            self.debug_surface.set_at((x, i), (0, 255, 0))
                        border_y = y - white_count + 1
                        for x_line in range(width):
                            self.debug_surface.set_at((x_line, border_y), (144, 238, 144))
                        return border_y, white_count
                    black_count = 0
                else:
                    black_count = white_count = 0
            return None, None

        for x in range(start_x, start_x + scan_width):
            border_y, segment_size = find_pattern_in_column(x)
            if border_y is not None:
                return border_y, segment_size
        
        return None, None

    def calculate_field_cells(self):
        """Вычисляет размеры клеток на основе найденных границ поля"""
        if all(x is not None for x in self.field_bounds):
            left, top, width, height = self.field_bounds
            # Вычисляем размеры клеток
            self.cell_width = width / self.map_width
            self.cell_height = height / self.map_height
            print(f"Размеры клетки: {self.cell_width:.2f}x{self.cell_height:.2f} пикселей")
            return True
        return False

    def get_cell_terrain(self, cell_x, cell_y):
        """Получает тип местности в указанной клетке"""
        if hasattr(self, 'terrain_map') and self.terrain_map:
            if 0 <= cell_y < len(self.terrain_map) and 0 <= cell_x < len(self.terrain_map[0]):
                terrain_code = self.terrain_map[cell_y][cell_x]
                if terrain_code:
                    return self.get_terrain_type(terrain_code)
        return "неизвестно"

    def get_terrain_type(self, code):
        """Преобразует код местности в текстовое описание"""
        terrain_types = {
            'M': "горы",
            'F': "лес",
            'W': "вода",
            'P': "равнина",
            'S': "болото",
            'D': "пустыня"
        }
        return terrain_types.get(code, "неизвестно")

    def get_terrain_info(self, terrain_type):
        """Возвращает описание типа местности"""
        terrain_names = {
            "равнина": "Равнина",
            "лес": "Лес",
            "горы": "Горы",
            "вода": "Вода",
            "болото": "Болото",
            "пустыня": "Пустыня",
            "неизвестно": "Неизвестно"
        }
        return terrain_names.get(terrain_type, terrain_type)
    
    def get_cell_buildings(self, cell_x, cell_y):
        """Получает список строений в указанной клетке"""
        buildings = []
        for obj in self.current_turn_objects:
            if isinstance(obj, tuple) and len(obj) >= 3:
                obj_type, x, y = obj[:3]
                # Проверяем, является ли объект строением и находится ли в указанной клетке
                if (x-1, y-1) == (cell_x, cell_y) and obj_type in 'КГЗПБ':
                    building_name = self.game_objects.get(obj_type, [obj_type])[0]
                    buildings.append(building_name)
        return buildings
    
    def get_cell_armies(self, cell_x, cell_y):
        """Получает список армий в указанной клетке"""
        armies = []
        for obj in self.current_turn_objects:
            if isinstance(obj, tuple) and len(obj) >= 3:
                obj_type, x, y = obj[:3]
                # Проверяем, является ли объект армией и находится ли в указанной клетке
                if (x-1, y-1) == (cell_x, cell_y) and obj_type.lower() in 'гвэопрмзд':
                    army_name = self.game_objects.get(obj_type, [obj_type])[0]
                    armies.append(army_name)
        return armies
    
    def get_building_owner(self, cell_x, cell_y, building_name):
        """Получает владельца строения"""
        # Ищем владельца среди игроков
        for player in self.current_players:
            for obj in player.get('objects', []):
                if isinstance(obj, tuple) and len(obj) >= 3:
                    obj_type, x, y = obj[:3]
                    if (x-1, y-1) == (cell_x, cell_y) and self.game_objects.get(obj_type, [obj_type])[0] == building_name:
                        return player.get('name')
        return None
    
    def get_army_owner(self, cell_x, cell_y, army_name):
        """Получает владельца армии"""
        # Ищем владельца среди игроков
        for player in self.current_players:
            for obj in player.get('objects', []):
                if isinstance(obj, tuple) and len(obj) >= 3:
                    obj_type, x, y = obj[:3]
                    if (x-1, y-1) == (cell_x, cell_y) and self.game_objects.get(obj_type, [obj_type])[0] == army_name:
                        return player.get('name')
        return None

    def load_initial_players(self):
        """Загрузка начальных данных об игроках из нулевого хода"""
        try:
            # Проверяем оба варианта именования нулевого хода
            turn0_file = None
            for name in ['Год0.svs', 'год0.svs', '®¤0.svs']:
                full_path = os.path.join(self.game_dir, name)
                if os.path.exists(full_path):
                    turn0_file = full_path
                    break

            if turn0_file:
                with open(turn0_file, 'rb') as f:
                    content = f.read()
                    # Пробуем разные кодировки
                    for encoding in ['cp1251', 'cp866', 'utf-8']:
                        try:
                            text = content.decode(encoding)
                            lines = text.split('\n')
                            
                            current_player = None
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                    
                                if line.startswith('Player'):
                                    if current_player:
                                        self.current_players.append(current_player)
                                    current_player = {'name': '', 'color': 0, 'objects': []}
                                elif not line[0].isdigit() and current_player is not None:
                                    # Строка с именем игрока
                                    current_player['name'] = line
                                elif len(line.split()) >= 3 and current_player is not None:
                                    # Строка с данными игрока (координаты, казна, цвет)
                                    parts = line.split()
                                    try:
                                        current_player['color'] = int(parts[2])
                                    except (ValueError, IndexError):
                                        continue
                            
                            # Добавляем последнего игрока
                            if current_player:
                                self.current_players.append(current_player)
                            break
                        except UnicodeDecodeError:
                            continue
        except Exception as e:
            print(f"Ошибка загрузки данных игроков: {e}")

    def handle_click(self, pos):
        """Обработка клика мыши"""
        # ... существующий код ...
        
        # Проверяем клик по цветным прямоугольникам игроков
        for rect, player in player_rects:
            if rect.collidepoint(pos):
                if self.selected_player == player:
                    self.selected_player = None  # Повторный клик снимает выделение
                else:
                    self.selected_player = player
                return True
        
        return False

if __name__ == '__main__':
    visualizer = MapVisualizer()
    visualizer.run()
