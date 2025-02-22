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
        self.svstem_encoding = locale.getpreferredencoding()
        if sys.platform == 'win32':
            self.svstem_encoding = 'cp1251'

        # Загружаем фоновое изображение
        self.original_background = pygame.image.load('MAP.bmp')
        self.background = self.original_background
        
        # Начальные размеры окна
        self.screen_width = self.background.get_width()
        self.screen_height = self.background.get_height()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height + 40), pygame.RESIZABLE)
        
        # Сохраняем исходное соотношение сторон
        self.aspect_ratio = self.screen_width / self.screen_height

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

    def load_turn_data(self, turn):
        filename = f'Год{turn}.svs'
        objects = []
        try:
            with open(filename, 'rb') as file:
                content = file.read()
                # Сначала декодируем из CP1251
                text = content.decode('cp1251')
                print(f"\nЗагружено из файла {filename} (cp1251):")
                print(text[:200] + "...") # Выводим начало файла для проверки
                
                lines = text.split('\n')
                print(f"Всего строк: {len(lines)}")
                
                for line in lines:
                    # Удаляем запятую в конце строки и лишние пробелы
                    line = line.strip().rstrip(',').strip()
                    if not line or line.startswith(('Player', 'END')):
                        continue
                    
                    # Разбиваем строку на части и очищаем от пустых элементов
                    parts = [part.strip() for part in line.split() if part.strip()]
                    
                    if len(parts) >= 3:
                        obj_type = parts[0]
                        if obj_type in self.game_objects:
                            try:
                                x = int(parts[1])
                                y = int(parts[2])
                                # Обработка состояния (может быть с запятой)
                                state = int(parts[3].rstrip(',')) if len(parts) > 3 else 0
                                objects.append((obj_type, x, y, state))
                                print(f"Загружен объект: тип={obj_type}, x={x}, y={y}, состояние={state}")
                            except (ValueError, IndexError) as e:
                                print(f"Ошибка парсинга строки '{line}': {e}")
                                continue
                        else:
                            print(f"Неизвестный тип объекта: {obj_type} в строке: {line}")
                    else:
                        print(f"Некорректный формат строки: {line}")
                        
        except (FileNotFoundError, UnicodeDecodeError) as e:
            print(f"Ошибка загрузки хода {turn}: {e}")
            
        print(f"Всего загружено объектов: {len(objects)}")
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
        # Получаем размеры и позицию фона один раз
        bg_x = (self.screen_width - self.background.get_width()) // 2
        bg_y = (self.screen_height - self.background.get_height()) // 2
        
        for obj_type, x, y, state in objects:
            try:
                # Пересчитываем координаты с учетом масштаба
                cell_size = self.calculate_cell_size()
                center_x = bg_x + (x * cell_size)
                center_y = bg_y + (y * cell_size)
                radius = int(cell_size / 3)  # Радиус тоже зависит от размера клетки
                
                # Вычисляем центр объекта один раз
                center_pos = (center_x + cell_size/2, center_y + cell_size/2)
                
                color = self.game_objects[obj_type][1]
                
                if obj_type in 'КГЗПБ':  # Строения
                    # Масштабируем иконки пропорционально размеру клетки
                    icon = self.army_icons[self.icon_indices[obj_type]]
                    icon_size = int(cell_size * 0.8)  # Размер иконки как процент от клетки
                    scaled_icon = pygame.transform.scale(icon, (icon_size, icon_size))
                    
                    # Создаем поверхность для закрашенной иконки
                    colored_icon = pygame.Surface(scaled_icon.get_size(), pygame.SRCALPHA)
                    colored_icon.fill((*color, 128))
                    
                    # Накладываем иконку как маску
                    colored_icon.blit(scaled_icon, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    
                    # Отрисовываем на экране
                    icon_rect = colored_icon.get_rect(center=center_pos)
                    self.screen.blit(colored_icon, icon_rect)
                    
                elif obj_type in 'CSGM':  # Рудники
                    icon = self.mine_icons[self.icon_indices[obj_type]]
                    icon_size = int(cell_size * 0.8)
                    scaled_icon = pygame.transform.scale(icon, (icon_size, icon_size))
                    icon_rect = scaled_icon.get_rect(center=center_pos)
                    self.screen.blit(scaled_icon, icon_rect)
                    
                else:  # Армии
                    # Рисуем круг с цветом игрока
                    pygame.draw.circle(self.screen, color, center_pos, radius)
                    pygame.draw.circle(self.screen, (0, 0, 0), center_pos, radius, 1)
                    
                    # Добавляем иконку
                    if obj_type in self.icon_indices:
                        icon = self.army_icons[self.icon_indices[obj_type]]
                        icon_size = int(cell_size * 0.6)  # Иконка армии немного меньше
                        scaled_icon = pygame.transform.scale(icon, (icon_size, icon_size))
                        icon_rect = scaled_icon.get_rect(center=center_pos)
                        self.screen.blit(scaled_icon, icon_rect)
                
                # Добавляем обводку для различных состояний
                if state & 128:  # Столица/ЛВ
                    pygame.draw.circle(self.screen, (255, 215, 0), center_pos, radius + 2, 2)
                elif state & 32:  # Без АД
                    pygame.draw.circle(self.screen, (128, 128, 128), center_pos, radius + 2, 2)
                
                if state & 64:  # На воде
                    pygame.draw.circle(self.screen, (0, 0, 255), center_pos, radius + 4, 2)
                    
            except (KeyError, IndexError) as e:
                print(f"Ошибка отрисовки объекта {obj_type}: {e}")

    def draw_interface(self):
        # Фон для интерфейса
        pygame.draw.rect(self.screen, (200, 200, 200), (0, self.screen_height, self.screen_width, 40))
        
        # Кнопки и текст хода
        prev_text = "Предыдущий ход"
        next_text = "Следующий ход"
        turn_text = f"Ход: {self.current_turn}"
        
        # Отрисовка элементов управления
        prev_surf = self.font.render(prev_text, True, (0, 0, 0))
        next_surf = self.font.render(next_text, True, (0, 0, 0))
        turn_surf = self.font.render(turn_text, True, (0, 0, 0))
        
        prev_rect = prev_surf.get_rect(center=(80, self.screen_height + 20))
        next_rect = next_surf.get_rect(center=(self.screen_width - 80, self.screen_height + 20))
        turn_rect = turn_surf.get_rect(center=(self.screen_width // 2, self.screen_height + 20))
        
        self.screen.blit(prev_surf, prev_rect)
        self.screen.blit(next_surf, next_rect)
        self.screen.blit(turn_surf, turn_rect)
        
        return [prev_rect, next_rect]

    def handle_resize(self, width, height):
        # Обновляем размеры окна
        self.screen_width = width
        self.screen_height = height - 40  # Учитываем панель управления

        # Масштабируем изображение с сохранением пропорций
        new_width = self.screen_width
        new_height = int(new_width / self.aspect_ratio)

        if new_height > self.screen_height:
            new_height = self.screen_height
            new_width = int(new_height * self.aspect_ratio)

        self.background = pygame.transform.smoothscale(self.original_background, (new_width, new_height))
        
        # Обновляем размер клетки
        self.cell_size = self.calculate_cell_size()

    def run(self):
        running = True
        while running:
            self.screen.fill((255, 255, 255))
            
            # Центрируем фоновое изображение
            bg_x = (self.screen_width - self.background.get_width()) // 2
            bg_y = (self.screen_height - self.background.get_height()) // 2
            self.screen.blit(self.background, (bg_x, bg_y))
            
            # Загрузка и отрисовка объектов текущего хода
            turn_objects = self.load_turn_data(self.current_turn)
            self.draw_game_objects(turn_objects)
            
            # Отрисовка интерфейса
            button_rects = self.draw_interface()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    self.handle_resize(event.w, event.h)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if button_rects[0].collidepoint(mouse_pos):  # Предыдущий ход
                        self.current_turn = max(0, self.current_turn - 1)
                    elif button_rects[1].collidepoint(mouse_pos):  # Следующий ход
                        self.current_turn = min(self.max_turn, self.current_turn + 1)
            
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
        # Определяем размер клетки на основе фиксированной сетки 120x60
        return min(self.background.get_width() / 120, self.background.get_height() / 60)

if __name__ == '__main__':
    visualizer = MapVisualizer()
    visualizer.run()
