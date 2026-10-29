# Kaneo на Global

Форк: https://github.com/evgeny-babaev/kaneo, ветка `deploy/global`.
Образ собирается GitHub Actions из Dockerfile.kaneo этого форка.
Тег образа содержит SHA исходного коммита; upstream latest не используется.

Адрес: https://kaneo.45.38.3.79.sslip.io
MCP: https://kaneo.45.38.3.79.sslip.io/api/mcp

Checkout: /opt/apps/kaneo.
Секреты: /opt/configs/kaneo/production.env.
Данные: /opt/data/kaneo, резервные копии: /opt/backups/kaneo.
HTTPS использует существующий Traefik file provider.
Это отдельный Compose рядом с Coolify, не ресурс панели Coolify.

## Развёртывание

Получить artifact kaneo-global-image из workflow Global image.
Проверить sha256sum, загрузить образ через docker load.
Установить KANEO_IMAGE=kaneo-global:<SHA> в production.env.
Запустить validate-env.sh и docker compose --env-file /opt/configs/kaneo/production.env -f deploy/global/compose.yml up -d.

После изменения production.env пересоздать контейнеры.
Не включать открытые регистрацию и гостевой вход на публичном адресе.
База не публикует порт на хосте. Логи ограничены, заданы лимиты памяти.
POSTGRES_HOST=kaneo-global-postgres-1: имя postgres конфликтует с другими контейнерами общей сети.

## Результат 29 октября 2026

Импортирована вся EVG: 712 задач, 13 проектов, 106 комментариев, 986 связей.
1 688 записей истории статусов сохранены в описаниях. Исходные даты и авторы
комментариев сохранены в тексте; системные даты Kaneo отражают импорт.
Оценки перенесены числовым полем «Оценка Linear (points)», без пересчёта в часы.
Срок без времени трактуется как конец дня Europe/Moscow; исходная дата остаётся в описании.
Архив использует статус archived; Canceled и Duplicate — отдельные конечные колонки.
Семантика duplicateOf дополнительно сохранена в описании; нативная связь — related.
Вложения сохранены ссылками, связанный документ включён в описание.
Linear и существующие трекеры не изменялись. Постоянная синхронизация не включена.

verify_linear.py сверил содержимое PostgreSQL с приватным снимком без ошибок.
check_mcp.py проверил HTTPS, 42 инструмента, создание/изменение/чтение/удаление
синтетической задачи, 401 без токена и OAuth discovery. UI формы входа проверен браузером.
Образ собран из коммита 609da62e90ca55b0eabcfa9a791e453979dec6d6.
Позднейшие коммиты содержат только скрипты развёртывания, импорта и документацию.

## Резервные копии

backup.sh сохраняет pg_dump -Fc, конфигурацию и runtime в /opt/backups/kaneo.
Хранение 14 дней. Копия на том же VPS не защищает от потери сервера.
Восстановление: остановить приложение, восстановить конфигурацию/runtime,
создать чистую базу kaneo и выполнить pg_restore -U kaneo -d kaneo из dump,
затем запустить приложение с соответствующим тегом образа.
Пароль владельца хранится в /opt/configs/kaneo/access.json (0600) и локальном Common/Env/apps/kaneo.

## Локальная конфигурация

Для локального тестирования использовать upstream compose.local.yml с отдельной тестовой базой.
Продуктивные секреты и личные данные не добавлять в Git.
