import os
import codecs
from pathlib import Path

class FileHandler:
    def parse_coordinates(self, coord_str):
        """Преобразование строки координат в числа"""
        try:
            if ',' in coord_str:
                x, y = coord_str.split(',')
                return int(x), int(y)
            return int(coord_str), None  # Для одиночных значений (например, количество войск)
        except ValueError:
            print(f"Пропуск некорректных координат: '{coord_str}'")
            return None, None

    def parse_game_object(self, line):
        """Парсинг строки с игровым объектом"""
        try:
            parts = line.strip().split()
            if not parts:
                return None

            obj_type = parts[0]
            if len(parts) < 2:
                return None

            # Первые два значения - тип объекта и количество
            result = {
                'type': obj_type,
                'count': int(parts[1]),
                'coordinates': []
            }

            # Парсим все координаты и параметры после типа и количества
            i = 2
            while i < len(parts):
                if ',' in parts[i]:  # Это пара координат
                    x, y = self.parse_coordinates(parts[i])
                    if x is not None and y is not None:
                        result['coordinates'].append((x, y))
                else:  # Это дополнительный параметр (например, состояние)
                    try:
                        value = int(parts[i])
                        result['coordinates'].append(value)
                    except ValueError:
                        print(f"Пропуск некорректного параметра: '{parts[i]}'")
                i += 1

            return result if result['coordinates'] else None

        except Exception as e:
            print(f"Пропуск некорректной строки: '{line}'")
            return None

    def load_turn_file(self, turn_file):
        """Загрузка данных из файла хода"""
        try:
            with open(turn_file, 'rb') as f:
                content = f.read()
                
                # Пробуем декодировать файл один раз
                for encoding in ['cp1251', 'cp866', 'utf-8']:
                    try:
                        text = content.decode(encoding)
                        print(f"Файл {turn_file} успешно декодирован с кодировкой {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    print(f"Не удалось декодировать файл {turn_file}")
                    return []

                lines = text.split('\n')
                objects = []
                current_player = None
                
                for line in lines:
                    line = line.strip()
                    if not line or line == 'END':
                        continue
                        
                    if line.startswith('Player'):
                        if current_player:
                            objects.append(current_player)
                        current_player = {'type': 'player', 'objects': []}
                        continue
                        
                    if current_player is not None:
                        if not line[0].isdigit():
                            current_player['name'] = line
                        else:
                            parts = line.split()
                            if len(parts) >= 3:
                                try:
                                    current_player['treasury'] = int(parts[1])
                                    current_player['color'] = int(parts[2])
                                except ValueError:
                                    print(f"Пропуск некорректных данных игрока: '{line}'")
                    else:
                        game_object = self.parse_game_object(line)
                        if game_object:
                            objects.append(game_object)
                
                # Добавляем последнего игрока
                if current_player:
                    objects.append(current_player)
                    
                return objects
                
        except Exception as e:
            print(f"Ошибка загрузки файла {turn_file}: {e}")
            return [] 