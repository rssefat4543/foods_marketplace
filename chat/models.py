from django.db import models
from django.conf import settings




class Message(models.Model):
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages",default=None)
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE, related_name="received_messages",default=None)
    is_read = models.BooleanField(default=False)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)    

    def __str__(self):
        return f"Msg by {self.sender}  to {self.receiver} at {self.timestamp}" 
    



