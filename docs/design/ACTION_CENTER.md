# Action Center

## Назначение

Action Center — единый read-only слой над существующими модулями проекта. Он не заменяет commitments, subscriptions, countdowns или approvals, а приводит их к одному контракту для будущего интерфейса, чата и Telegram.

## Текущий контракт

`GET /api/actions`

Параметры:

- `mode=attention` — только просроченные, ближайшие, требующие подтверждения и активные напоминания;
- `mode=all` — также плановые активные элементы;
- `limit` — максимум 100 элементов;
- `include_external=true` — добавить агрегированные непрочитанные письма;
- `reference_time` — ISO-8601 время для детерминированного тестирования.

Каждый action содержит `kind`, `source_id`, `title`, `summary`, `status`, `priority`, `due_at`, `reminder_at`, `reminder_due`, `source`, `target`, `requires_approval` и `metadata`.

## Источники

- `commitments` — активные и просроченные обязательства;
- `subscriptions` — ближайшие списания и окончания trial;
- `countdowns` — дедлайны;
- `approvals` — предложения из фактов, обязательств, подписок и pending actions;
- почта — только агрегированный unread-сигнал при явном `include_external=true`.

## Правила

- `critical`: просрочено;
- `high`: сегодня, ближайший срок или активное напоминание;
- `medium`: требуется подтверждение;
- `low`: плановый элемент в режиме `all`.

Источники остаются владельцами своих данных и переходов статусов. Action Center не выполняет мутации. Delivery-layer v1 уже добавляет общий Telegram-контур: тихие часы, rolling budget, coalescing нескольких действий в одно сообщение и дедупликацию повторных уведомлений.

Настройки доступны через:

- `GET /api/notifications/preferences`;
- `PUT /api/notifications/preferences`.

По умолчанию используются часовой пояс `Europe/Berlin`, тихие часы `22:00–08:00`, не более трёх сообщений в час и минимальный приоритет `medium`. Критические просроченные действия обходят тихие часы и лимит.
