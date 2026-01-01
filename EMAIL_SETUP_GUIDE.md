# Настройка Email для HandshakeMe Admin Panel

## Проблема
Если при отправке email показывается "success", но письма не приходят, скорее всего проблема в настройках SMTP аутентификации.

## Решение для Gmail

### 1. Включите двухфакторную аутентификацию
1. Перейдите в [Google Account Settings](https://myaccount.google.com/)
2. Выберите "Безопасность" → "Двухэтапная аутентификация"
3. Включите двухэтапную аутентификацию

### 2. Создайте App Password
1. В настройках безопасности Google найдите "Пароли приложений"
2. Выберите "Почта" и "Другое устройство"
3. Введите название "HandshakeMe Admin"
4. Скопируйте сгенерированный 16-символьный пароль

### 3. Обновите настройки в .env файле
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_16_char_app_password
```

### 4. Перезапустите Django сервер
После изменения .env файла обязательно перезапустите сервер Django.

## Альтернативные SMTP провайдеры

### Yandex Mail
```env
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@yandex.ru
EMAIL_HOST_PASSWORD=your_password
```

### Mail.ru
```env
EMAIL_HOST=smtp.mail.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@mail.ru
EMAIL_HOST_PASSWORD=your_password
```

## Тестирование

### Через Django Management команду
```bash
python manage.py test_email --email your_test@email.com
```

### Через диагностику
```bash
python manage.py diagnose_email
```

## Отладка

### Проверьте логи Django
Логи покажут детальную информацию об ошибках отправки.

### Проверьте папку спам
Gmail может помещать письма от новых отправителей в спам.

### Проверьте настройки безопасности
Убедитесь, что "Менее безопасные приложения" отключены и используется App Password.