## Установка зависимостей и запуск

```bash 
pip install fastapi uvicorn aiosqlite
uvicorn main:app --reload
```

## Эндпоинты


### POST */reviews*
```
curl -X 'POST' \
  'http://127.0.0.1:8000/reviews' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
        "text": "Плохой сервис, но хотелось бы посмотреть на его дальнейшее развитие"
    }'
```

Ответ:
```json
{
  "id": 1,
  "text": "Плохой сервис, но хотелось бы посмотреть на его дальнейшее развитие",
  "sentiment": "negative",
  "created_at": "2025-07-08T19:54:03.853878"
}
```


### GET */reviews?sentiment=negative*

```
curl -X 'GET' \
  'http://127.0.0.1:8000/reviews?sentiment=negative' \
  -H 'accept: application/json'
```

Ответ:
```json
[
  {
    "id": 1,
    "text": "Плохой сервис, но хотелось бы посмотреть на его дальнейшее развитие",
    "sentiment": "negative",
    "created_at": "2025-07-08T19:54:03.853878"
  },
  {
    "id": 2,
    "text": "Ненавижу этот сервис!!!",
    "sentiment": "negative",
    "created_at": "2025-07-08T19:55:39.594959"
  }
]
```