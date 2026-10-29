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

## Локальная конфигурация

Для локального тестирования использовать upstream compose.local.yml с отдельной тестовой базой.
Продуктивные секреты и личные данные не добавлять в Git.
