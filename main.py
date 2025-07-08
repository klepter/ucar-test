from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, AsyncIterator
import aiosqlite
from fastapi import Depends, FastAPI
from pydantic import BaseModel
import uvicorn


DATABASE_URL = 'reviews.db'


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    async with aiosqlite.connect(DATABASE_URL) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        ''')
        await db.commit()
    yield


async def get_db():
    async with aiosqlite.connect(DATABASE_URL) as db:
        try:
            db.row_factory = aiosqlite.Row
            yield db
            await db.commit()
        except:
            await db.rollback()
            raise
        finally:
            await db.close()


app = FastAPI(lifespan=lifespan)


class SentimentEnum(Enum):
    NEUTRAL = 'neutral'
    POSITIVE = 'positive'
    NEGATIVE = 'negative'


class ReviewDTO(BaseModel):
    id: int
    text: str
    sentiment: SentimentEnum
    created_at: datetime

    model_config = {
        'from_attributes': True
    }


class CreateReviewRequest(BaseModel):
    text: str


@dataclass
class ReviewDAO:
    db_session: aiosqlite.Connection

    async def create(self, text: str, sentiment: SentimentEnum, created_at: datetime) -> ReviewDTO:
        cursor = await self.db_session.execute('''
            INSERT INTO reviews (text, sentiment, created_at)
            VALUES (?, ?, ?)
            RETURNING id, text, sentiment, created_at
        ''',
        (text, sentiment.value, created_at.isoformat()))
        review = await cursor.fetchone()
        if review is None:
            raise Exception('Error trying to save to database')

        return ReviewDTO(**review)
    
    async def get_list_by_sentiment(self, sentiment: SentimentEnum) -> list[ReviewDTO]:
        cursor = await self.db_session.execute('''
            SELECT id, text, sentiment, created_at
            FROM reviews
            WHERE sentiment = ?
        ''', (sentiment.value, ))
        data = await cursor.fetchall()
        return [ReviewDTO(**row) for row in data]


@dataclass
class ReviewService:
    review_dao: ReviewDAO

    async def create(self, data: CreateReviewRequest) -> ReviewDTO:
        text = data.text.lower()

        positive_keywords = ['хорош', 'люблю']
        negative_keywords = ['плохо', 'ненавиж']

        sentiment = SentimentEnum.NEUTRAL
        if any(word in text for word in positive_keywords):
            sentiment = SentimentEnum.POSITIVE
        elif any(word in text for word in negative_keywords):
            sentiment = SentimentEnum.NEGATIVE

        return await self.review_dao.create(
            text=data.text,
            sentiment=sentiment,
            created_at=datetime.now(timezone.utc)
        )
    
    async def get_list_by_sentiment(self, data: SentimentEnum) -> list[ReviewDTO]:
        return await self.review_dao.get_list_by_sentiment(sentiment=data)


@app.post('/reviews', tags=['reviews'])
async def create_review(
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    review_data: CreateReviewRequest
) -> ReviewDTO:
    return await ReviewService(
        review_dao=ReviewDAO(db_session=db)
    ).create(data=review_data)


@app.get('/reviews', tags=['reviews'])
async def get_reviews_by_sentiment(
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
    sentiment: SentimentEnum = SentimentEnum.NEGATIVE
) -> list[ReviewDTO]:
    return await ReviewService(
        review_dao=ReviewDAO(db_session=db)
    ).get_list_by_sentiment(data=sentiment)


if __name__ == '__main__':
    uvicorn.run('main:app', reload=True)
