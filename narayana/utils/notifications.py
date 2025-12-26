from models import db, Notification

def create_notification(user_id, message):
    """Create a notification for a user"""
    notification = Notification(user_id=user_id, message=message)
    db.session.add(notification)
    db.session.commit()

def get_unread_count(user_id):
    """Get count of unread notifications for a user"""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()

def mark_as_read(notification_id):
    """Mark a notification as read"""
    notification = Notification.query.get(notification_id)
    if notification:
        notification.is_read = True
        db.session.commit()
