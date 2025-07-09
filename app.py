from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import sqlite3
from flask import Flask, request, jsonify


DATABASE_URL = 'reviews.db'


app = Flask(__name__)


def init_db():
    with sqlite3.connect(DATABASE_URL) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        conn.commit()


init_db()


class SentimentEnum(str, Enum):
    NEUTRAL = 'neutral'
    POSITIVE = 'positive'
    NEGATIVE = 'negative'


@dataclass
class ReviewDTO:
    id: int
    text: str
    sentiment: SentimentEnum
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "sentiment": self.sentiment.value,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ReviewDAO:
    conn: sqlite3.Connection

    def create(self, text: str, sentiment: SentimentEnum, created_at: datetime) -> ReviewDTO:
        cursor = self.conn.execute('''
            INSERT INTO reviews (text, sentiment, created_at)
            VALUES (?, ?, ?)
        ''', (text, sentiment.value, created_at.isoformat()))
        review_id = cursor.lastrowid
        if review_id is None:
            raise Exception('Error while trying save to database')

        self.conn.commit()

        return ReviewDTO(
            id=review_id,
            text=text,
            sentiment=sentiment,
            created_at=created_at
        )

    def get_list_by_sentiment(self, sentiment: SentimentEnum) -> list[ReviewDTO]:
        cursor = self.conn.execute('''
            SELECT id, text, sentiment, created_at
            FROM reviews
            WHERE sentiment = ?
        ''', (sentiment.value,))
        rows = cursor.fetchall()
        result: list[ReviewDTO] = []
        for row in rows:
            result.append(
                ReviewDTO(
                    id=row[0],
                    text=row[1],
                    sentiment=SentimentEnum(row[2]),
                    created_at=datetime.fromisoformat(row[3])
                )
            )
        return result


@dataclass
class ReviewService:
    review_dao: ReviewDAO

    def create(self, text: str) -> ReviewDTO:
        lower_text = text.lower()

        positive_keywords = ['хорош', 'люблю']
        negative_keywords = ['плохо', 'ненавиж']

        sentiment = SentimentEnum.NEUTRAL
        if any(word in lower_text for word in positive_keywords):
            sentiment = SentimentEnum.POSITIVE
        elif any(word in lower_text for word in negative_keywords):
            sentiment = SentimentEnum.NEGATIVE

        return self.review_dao.create(
            text=text,
            sentiment=sentiment,
            created_at=datetime.now(timezone.utc)
        )

    def get_list_by_sentiment(self, sentiment: SentimentEnum) -> list[ReviewDTO]:
        return self.review_dao.get_list_by_sentiment(sentiment)


@app.route('/reviews', methods=['POST'])
def create_review():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Field "text" is required'}), 400

    with sqlite3.connect(DATABASE_URL) as conn:
        service = ReviewService(review_dao=ReviewDAO(conn))
        review = service.create(data['text'])
        return jsonify(review.to_dict()), 201


@app.route('/reviews', methods=['GET'])
def get_reviews_by_sentiment():
    sentiment_str = request.args.get('sentiment', SentimentEnum.NEGATIVE.value)
    try:
        sentiment = SentimentEnum(sentiment_str)
    except ValueError:
        return jsonify({
            'error': f"Invalid sentiment: {sentiment_str}, should be 'negative', 'positive' or 'neutral'"
        }), 400

    with sqlite3.connect(DATABASE_URL) as conn:
        service = ReviewService(review_dao=ReviewDAO(conn))
        reviews = service.get_list_by_sentiment(sentiment)
        return jsonify([r.to_dict() for r in reviews]), 200


if __name__ == '__main__':
    app.run(debug=True)
