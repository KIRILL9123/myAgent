# Action Center

## Назначение

Action Center — единый read-only слой над существующими модулями проекта. Он не заменяет commitments, subscriptions, countdowns или approvals, а приводит их к одному контракту для интерфейса Notification Center, чата и Telegram.

Веб-интерфейс доступен по маршрутам `/notifications` и `/notifications/preferences`. Центр показывает режимы «Требуют внимания» и «Все сигналы», фильтры по типу, сводные счётчики и переходы в исходные разделы. Страница настроек управляет Telegram-доставкой, часовым поясом, тихими часами, минимальным приоритетом, бюджетом и coalescing. Доменные действия по-прежнему выполняются только в своих модулях; Notification Center не создаёт вторую копию состояния.

## Текущий контракт

`GET /api/actions`

Параметры:

- `mode=attention` — только просроченные, ближайшие, требующие подтверждения и активные напоминания;
- `mode=all` — также плановые активные элементы;
- `limit` — максимум 100 элементов;
- `include_external=true` — добавить агрегированные непрочитанные письма;
- `reference_time` — ISO-8601 время для детерминированного тестирования. День и локальные границы вычисляются в timezone из настроек Notification Center; timestamps сравниваются в UTC.

Каждый action содержит `kind`, `source_id`, `title`, `summary`, `status`, `priority`, `due_at`, `reminder_at`, `reminder_due`, `source`, `target`, `requires_approval` и `metadata`.

## v1.1 — действия пользователя

Action Center остаётся projection, но теперь хранит отдельное UI-состояние для
сигнала. Это не меняет статус исходной сущности:

- `POST /api/actions/{action_id}/read` — убрать сигнал из режима «Требуют внимания»;
- `POST /api/actions/{action_id}/unread` — вернуть сигнал в внимание;
- `POST /api/actions/{action_id}/snooze` с `snoozed_until` — временно скрыть сигнал;
- `POST /api/actions/{action_id}/dismiss` — скрыть обработанный сигнал;
- Commitment-действия «Готово» и «Перенести» вызывают существующий Commitment API;
- все изменения автоматически обновляют Today и Notification Center через общий cache invalidation.

Состояния проекции хранятся в `action_states`. Это локальная пользовательская
метаинформация, а не копия task, event, subscription или notification.

## Источники

- `commitments` — активные и просроченные обязательства;
- `subscriptions` — ближайшие списания и окончания trial;
- `finance` — ближайшая активная операция из Finance recurring templates;
- `countdowns` — дедлайны;
- `approvals` — предложения из фактов, обязательств, подписок и pending actions;
- `error reports` — открытые технические ошибки из `/api/errors`, пока они не достигли статуса `closed`;
- почта — только агрегированный unread-сигнал при явном `include_external=true`.

## Правила

- `critical`: просрочено;
- `high`: сегодня, ближайший срок или активное напоминание;
- `medium`: требуется подтверждение;
- `low`: плановый элемент в режиме `all`.

Единый контракт времени реализован в `backend/app/temporal/time_context.py` и используется
также Personal State, countdowns, утренней Telegram-сводкой и Telegram-доставкой. Это
гарантирует, что граница «сегодня» не зависит от системного timezone машины.

Источники остаются владельцами своих данных и переходов статусов. Action Center не выполняет мутации. Delivery-layer v1 уже добавляет общий Telegram-контур: тихие часы, rolling budget, coalescing нескольких действий в одно сообщение и дедупликацию повторных уведомлений.

Finance recurring templates проецируются только ближайшим occurrence каждого
шаблона. Шаблоны, уже связанные с активной подпиской через
`subscription_finance_links`, не дублируются: для них остаётся subscription
signal. Переход из карточки ведёт в `/finance`, а сама операция не изменяется
через Notification Center. В день операции сигнал помечается как готовый к
напоминанию и проходит через существующий Telegram delivery policy; отдельная
настройка напоминания для Finance-шаблона пока не вводится.

Настройки доступны через:

- `GET /api/notifications/preferences`;
- `PUT /api/notifications/preferences`.

По умолчанию используются часовой пояс `Europe/Berlin`, тихие часы `22:00–08:00`, не более трёх сообщений в час и минимальный приоритет `medium`. Критические просроченные действия обходят тихие часы и лимит.
