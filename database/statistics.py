from datetime import datetime, timedelta
from typing import Dict, Any

async def get_bot_statistics() -> Dict[str, Any]:
    """Получить общую статистику бота"""
    from database.operations import users_collection, payments_collection
    
    # Текущее время и время 24 часа назад
    now = datetime.now()
    day_ago = now - timedelta(days=1)
    
    # Общая статистика
    total_users = await users_collection.count_documents({})
    
    # Подсчет сообщений (через историю чатов)
    pipeline = [
        {"$project": {"message_count": {"$size": {"$ifNull": ["$chat_history", []]}}}},
        {"$group": {"_id": None, "total_messages": {"$sum": "$message_count"}}}
    ]
    messages_result = await users_collection.aggregate(pipeline).to_list(length=1)
    total_messages = messages_result[0]["total_messages"] if messages_result else 0
    
    # Статистика платежей
    total_payments = await payments_collection.count_documents({"status": "succeeded"})
    
    # Сумма платежей
    pipeline = [
        {"$match": {"status": "succeeded"}},
        {"$group": {"_id": None, "total_amount": {"$sum": "$amount"}}}
    ]
    amount_result = await payments_collection.aggregate(pipeline).to_list(length=1)
    total_amount = amount_result[0]["total_amount"] if amount_result else 0
    
    # Статистика за последние 24 часа
    new_users_24h = await users_collection.count_documents({"created_at": {"$gte": day_ago}})
    
    # Сообщения за 24 часа
    pipeline = [
        {"$unwind": "$chat_history"},
        {"$match": {"chat_history.timestamp": {"$gte": day_ago}}},
        {"$count": "messages_24h"}
    ]
    messages_24h_result = await users_collection.aggregate(pipeline).to_list(length=1)
    messages_24h = messages_24h_result[0]["messages_24h"] if messages_24h_result else 0
    
    # Платежи за 24 часа
    payments_24h = await payments_collection.count_documents({
        "status": "succeeded", 
        "completed_at": {"$gte": day_ago}
    })
    
    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "total_payments": total_payments,
        "total_amount": total_amount,
        "new_users_24h": new_users_24h,
        "messages_24h": messages_24h,
        "payments_24h": payments_24h
    } 