CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL
);

INSERT OR IGNORE INTO categories (name, type) VALUES
    ('Еда', 'expense'),
    ('Транспорт/Бензин', 'expense'),
    ('Авто (запчасти/ремонт)', 'expense'),
    ('Гейминг/Хобби', 'expense'),
    ('Подписки', 'expense'),
    ('Разное', 'expense'),
    ('Зарплата/Стипендия', 'income'),
    ('Фриланс/Разработка', 'income'),
    ('Продажа вещей', 'income');
