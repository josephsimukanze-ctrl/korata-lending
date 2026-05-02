# notifications/push_utils.py
def send_push_notification(user, title, body, url):
    """Send push notification - integrate with your push service"""
    # Example using Firebase Cloud Messaging
    print(f"Push notification to {user.username}: {title} - {body}")
    return True