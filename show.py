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

        # Читаем игровые константы
        self.read_game_constants()

        # Читаем размеры карты из ANT.DAT
        self.map_width, self.map_height = self.read_map_dimensions()

        # Загружаем фоновое изображение
        self.original_background = pygame.image.load('MAP.bmp')
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
        
        # Для элементов интерфейса используем минимальный размер
        self.cell_size = min(self.cell_width, self.cell_height)
        
        # Устанавливаем размер шрифта и высоту панели
        self.font = pygame.font.Font(None, int(self.cell_size))
        self.panel_height = int(self.cell_size * 1.5)
        
        # Инициализируем размеры окна
        self.screen_width = self.canvas_width
        self.screen_height = self.canvas_height + self.panel_height
        
        # Инициализируем позицию панели управления
        self.panel_y = self.canvas_height
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.RESIZABLE)
        
        # Установка заголовка окна с учетом кодировки
        pygame.display.set_caption("Визуализация карты")
        
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
        self.cell_size = self.calculate_cell_size()
        self.font = pygame.font.Font(None, 36)

        # Загружаем изображения пиктограмм
        self.army_icons = self.load_icons('OSNOVA.BMP', 16)  # 16 иконок армий/строений
        self.mine_icons = self.load_icons('RUDNICI.BMP', 4)  # 4 иконки рудников
        
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

    def read_game_constants(self):
        """Читает размеры поля из ANT.DAT и цвета игроков из нулевого хода"""
        # Чтение ANT.DAT
        try:
            with open('ANT.DAT', 'r', encoding=self.system_encoding) as f:
                lines = f.readlines()
                # Строка 2 - ширина поля
                # Строка 3 - высота поля
                self.map_width = int(lines[1].strip())
                self.map_height = int(lines[2].strip())
        except Exception as e:
            print(f"Ошибка чтения ANT.DAT: {e}")
            self.map_width = 0
            self.map_height = 0

        # Чтение цветов игроков из нулевого хода
        try:
            with open('Год0.svs', 'rb') as f:
                content = f.read().decode('cp1251')
                lines = content.split('\n')
                self.player_colors = {}
                
                current_player = None
                for line in lines:
                    if line.startswith('Player'):
                        continue
                    elif len(line.split()) >= 3:
                        parts = line.split()
                        if len(parts) >= 3 and parts[0].isdigit():
                            # Строка с координатами и цветом игрока
                            try:
                                color = int(parts[2])
                                if current_player:
                                    self.player_colors[current_player] = color
                            except ValueError:
                                continue
                    else:
                        # Строка с именем игрока
                        current_player = line.strip()
        except Exception as e:
            print(f"Ошибка чтения Год0.svs: {e}")
            self.player_colors = {}

    def load_turn_data(self, turn):
        filename = f'Год{turn}.svs'
        objects = []
        players_info = []  # Список для хранения информации об игроках
        current_player = None
        
        try:
            with open(filename, 'rb') as file:
                content = file.read()
                text = content.decode('cp1251')
                lines = text.split('\n')
                
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
                
        except (FileNotFoundError, UnicodeDecodeError) as e:
            print(f"Ошибка загрузки хода {turn}: {e}")
        
        # Сохраняем информацию об игроках
        self.current_players = players_info
        return objects

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

    def draw_interface(self):
        """Отрисовка интерфейса управления"""
        # Отрисовка панели управления
        panel_rect = pygame.Rect(0, self.panel_y, self.screen_width, self.panel_height)
        pygame.draw.rect(self.screen, (200, 200, 200), panel_rect)
        
        # Кнопки управления
        button_width = 100
        button_height = int(self.panel_height * 0.8)
        button_y = self.panel_y + (self.panel_height - button_height) // 2
        
        # Кнопка "Предыдущий ход"
        prev_button = pygame.Rect(
            10,
            button_y,
            button_width,
            button_height
        )
        pygame.draw.rect(self.screen, (150, 150, 150), prev_button)
        prev_text = self.font.render("<-", True, (0, 0, 0))
        self.screen.blit(prev_text, (
            prev_button.centerx - prev_text.get_width() // 2,
            prev_button.centery - prev_text.get_height() // 2
        ))
        
        # Кнопка "Следующий ход"
        next_button = pygame.Rect(
            120,
            button_y,
            button_width,
            button_height
        )
        pygame.draw.rect(self.screen, (150, 150, 150), next_button)
        next_text = self.font.render("->", True, (0, 0, 0))
        self.screen.blit(next_text, (
            next_button.centerx - next_text.get_width() // 2,
            next_button.centery - next_text.get_height() // 2
        ))
        
        # Отображение текущего хода
        turn_text = self.font.render(f"Ход: {self.current_turn}", True, (0, 0, 0))
        self.screen.blit(turn_text, (250, button_y + (button_height - turn_text.get_height()) // 2))
        
        return [prev_button, next_button]

    def handle_resize(self, width, height):
        """Обработка изменения размера окна"""
        # Сохраняем новые размеры окна
        self.screen_width = width
        self.screen_height = height
        
        # Пересоздаем окно
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        
        # Вычисляем новые размеры канвы с сохранением пропорций
        available_height = height - self.panel_height
        canvas_height = available_height
        canvas_width = int(canvas_height * self.aspect_ratio)
        
        if canvas_width > width:
            canvas_width = width
            canvas_height = int(width / self.aspect_ratio)
        
        # Масштабируем канву целиком
        self.scaled_canvas = pygame.transform.scale(self.canvas, (canvas_width, canvas_height))
        
        # Обновляем позицию панели управления
        self.panel_y = canvas_height  # Панель начинается сразу после канвы
        
        # Пересчитываем размеры клеток и границы поля
        if hasattr(self, 'field_bounds'):
            scale_x = canvas_width / self.canvas_width
            scale_y = canvas_height / self.canvas_height
            
            # Обновляем границы поля с учетом масштаба
            left, top, width, height = self.field_bounds
            self.scaled_bounds = (
                int(left * scale_x),
                int(top * scale_y),
                int(width * scale_x),
                int(height * scale_y)
            )
            
            # Обновляем размеры клеток
            self.cell_width = self.scaled_bounds[2] / self.map_width
            self.cell_height = self.scaled_bounds[3] / self.map_height
            self.cell_size = min(self.cell_width, self.cell_height)
            
            # Обновляем размер шрифта и высоту панели
            self.font = pygame.font.Font(None, int(self.cell_size))
            self.panel_height = int(self.cell_size * 1.5)

    def draw_coordinates_tooltip(self, mouse_pos):
        # Получаем коэффициенты масштабирования и смещение канвы
        scale_x = self.scaled_canvas.get_width() / self.canvas_width
        canvas_x = (self.screen_width - self.scaled_canvas.get_width()) // 2
        
        # Преобразуем координаты мыши в координаты игрового поля
        field_x = (mouse_pos[0] - canvas_x) / scale_x
        field_y = mouse_pos[1] / scale_x  # Используем scale_x для сохранения пропорций
        
        # Вычисляем координаты клетки с учетом границ поля
        cell_x = int((field_x - self.field_bounds[0]) / self.base_cell_width) + 1
        cell_y = int((field_y - self.field_bounds[1]) / self.base_cell_height) + 1
        
        # Проверяем, находится ли курсор в пределах игрового поля
        if 1 <= cell_x <= self.map_width and 1 <= cell_y <= self.map_height:
            # Создаем текст координат
            coords_text = f"({cell_x}-{cell_y})"
            coords_surf = self.font.render(coords_text, True, (0, 0, 0))
            
            # Размеры всплывающего окна с учетом отступов
            padding = 2
            tooltip_width = coords_surf.get_width() + padding * 2
            tooltip_height = coords_surf.get_height() + padding * 2
            
            # Позиционирование относительно курсора
            tooltip_x = mouse_pos[0] + 10
            tooltip_y = mouse_pos[1] - tooltip_height - 10
            
            # Корректируем позицию, чтобы окно не выходило за пределы экрана
            if tooltip_x + tooltip_width > self.screen_width:
                tooltip_x = mouse_pos[0] - tooltip_width - 10
            if tooltip_x < 0:
                tooltip_x = 10
                
            if tooltip_y < 0:
                tooltip_y = mouse_pos[1] + 10
            if tooltip_y + tooltip_height > self.panel_y:  # Учитываем панель управления
                tooltip_y = self.panel_y - tooltip_height - 10
            
            # Создаем и отрисовываем фон
            background_rect = pygame.Rect(
                tooltip_x,
                tooltip_y,
                tooltip_width,
                tooltip_height
            )
            pygame.draw.rect(self.screen, (255, 255, 255), background_rect)
            pygame.draw.rect(self.screen, (0, 0, 0), background_rect, 1)
            
            # Отрисовываем текст с учетом отступов
            self.screen.blit(coords_surf, (tooltip_x + padding, tooltip_y + padding))

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
                    self.handle_resize(event.w, event.h)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if button_rects[0].collidepoint(mouse_pos):
                        self.current_turn = max(0, self.current_turn - 1)
                    elif button_rects[1].collidepoint(mouse_pos):
                        self.current_turn = min(self.max_turn, self.current_turn + 1)

            # Очистка экрана
            self.screen.fill((255, 255, 255))
            
            # Отрисовка канвы с рамкой и фоном
            self.draw_canvas()
            
            # Загрузка и отрисовка объектов текущего хода
            turn_objects = self.load_turn_data(self.current_turn)
            self.draw_game_objects(turn_objects)
            
            # Отрисовка интерфейса
            button_rects = self.draw_interface()
            
            # Отрисовка координат
            mouse_pos = pygame.mouse.get_pos()
            self.draw_coordinates_tooltip(mouse_pos)
            
            pygame.display.flip()
            
            # Отрисовка интерфейса
            button_rects = self.draw_interface()
            
            # Отрисовка координат
            mouse_pos = pygame.mouse.get_pos()
            self.draw_coordinates_tooltip(mouse_pos)
            
            pygame.display.flip()
        
        pygame.quit()

    def find_max_turn(self):
        max_turn = 0
        for file in Path('.').glob('Год*.svs'):
            try:
                turn = int(re.search(r'Год(\d+)\.svs', file.name).group(1))
                max_turn = max(max_turn, turn)
            except (AttributeError, ValueError):
                continue
        return max_turn

    def calculate_cell_size(self):
        # Учитываем границы карты при расчете размера клетки
        playable_width = self.original_background.get_width() - 2  # Вычитаем границы слева и справа
        playable_height = self.original_background.get_height() - 2  # Вычитаем границы сверху и снизу
        return min(playable_width / 120, playable_height / 60)

    def read_map_dimensions(self):
        try:
            with open('ANT.DAT', 'r') as file:
                lines = file.readlines()
                if len(lines) >= 3:
                    # Парсим вторую и третью строки для получения размеров
                    width = int(lines[1].strip())
                    height = int(lines[2].strip())
                    return width, height
        except (FileNotFoundError, ValueError, IndexError) as e:
            print(f"Ошибка чтения размеров карты: {e}")
            # Возвращаем значения по умолчанию если файл не найден
            return 130, 57

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
                print(f"x={x}, y={y}, цвет={color}, ")
                print(f"    черный={is_black_pixel} (нужно < 30 для всех компонент)")
                print(f"    белый={is_white_pixel} (нужно > 225 для всех компонент)")
                
                if is_black_pixel:
                    black_count += 1
                    if 3 <= black_count <= 10:
                        print(f"Найден черный паттерн длиной {black_count}")
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
                        print(f"Найден белый паттерн длиной {white_count}")
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
            
            # Сканируем от центра к верхнему краю (изменено направление)
            for y in range(50, 0, -1):  # Начинаем с 50 и идем к верхнему краю
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
                        border_y = y  # Граница - начало паттерна
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
                        border_y = y
                        for x_line in range(width):
                            self.debug_surface.set_at((x_line, border_y), (144, 238, 144))
                        return border_y, white_count
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

if __name__ == '__main__':
    visualizer = MapVisualizer()
    visualizer.run()
