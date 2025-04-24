from datetime import datetime
from typing import Dict, List, Optional, Union

# Модель пользователя
class User:
    def __init__(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        tokens: int = 0,
        is_subscribed: bool = False,
        is_unlimited: bool = False,
        created_at: datetime = None,
        last_activity: datetime = None,
        chat_history: Optional[List[Dict]] = None,
        referral_code: Optional[str] = None,
        referred_by: Optional[int] = None,
        referral_count: int = 0
    ):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.tokens = tokens
        self.is_subscribed = is_subscribed
        self.is_unlimited = is_unlimited
        self.created_at = created_at or datetime.now()
        self.last_activity = last_activity or datetime.now()
        self.chat_history = chat_history or []
        self.referral_code = referral_code
        self.referred_by = referred_by
        self.referral_count = referral_count
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        return cls(
            user_id=data.get('user_id'),
            username=data.get('username'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            tokens=data.get('tokens', 0),
            is_subscribed=data.get('is_subscribed', False),
            is_unlimited=data.get('is_unlimited', False),
            created_at=data.get('created_at'),
            last_activity=data.get('last_activity'),
            chat_history=data.get('chat_history', []),
            referral_code=data.get('referral_code'),
            referred_by=data.get('referred_by'),
            referral_count=data.get('referral_count', 0)
        )
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'tokens': self.tokens,
            'is_subscribed': self.is_subscribed,
            'is_unlimited': self.is_unlimited,
            'created_at': self.created_at,
            'last_activity': self.last_activity,
            'chat_history': self.chat_history,
            'referral_code': self.referral_code,
            'referred_by': self.referred_by,
            'referral_count': self.referral_count
        }

# Модель платежа
class Payment:
    def __init__(
        self,
        payment_id: str,
        user_id: int,
        tariff: str,
        amount: float,
        tokens: int,
        status: str = 'pending',
        created_at: datetime = None,
        completed_at: Optional[datetime] = None
    ):
        self.payment_id = payment_id
        self.user_id = user_id
        self.tariff = tariff
        self.amount = amount
        self.tokens = tokens
        self.status = status
        self.created_at = created_at or datetime.now()
        self.completed_at = completed_at
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Payment':
        return cls(
            payment_id=data.get('payment_id'),
            user_id=data.get('user_id'),
            tariff=data.get('tariff'),
            amount=data.get('amount'),
            tokens=data.get('tokens'),
            status=data.get('status', 'pending'),
            created_at=data.get('created_at'),
            completed_at=data.get('completed_at')
        )
    
    def to_dict(self) -> Dict:
        return {
            'payment_id': self.payment_id,
            'user_id': self.user_id,
            'tariff': self.tariff,
            'amount': self.amount,
            'tokens': self.tokens,
            'status': self.status,
            'created_at': self.created_at,
            'completed_at': self.completed_at
        }

# Модель отзыва
class Review:
    def __init__(
        self,
        review_id: str,
        user_id: int,
        text: str,
        rating: Optional[int] = None,
        created_at: datetime = None
    ):
        self.review_id = review_id
        self.user_id = user_id
        self.text = text
        self.rating = rating
        self.created_at = created_at or datetime.now()
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Review':
        return cls(
            review_id=data.get('review_id'),
            user_id=data.get('user_id'),
            text=data.get('text'),
            rating=data.get('rating'),
            created_at=data.get('created_at')
        )
    
    def to_dict(self) -> Dict:
        return {
            'review_id': self.review_id,
            'user_id': self.user_id,
            'text': self.text,
            'rating': self.rating,
            'created_at': self.created_at
        } 