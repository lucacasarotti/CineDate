from django.contrib.auth.models import User
from django.db import models

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from inviti.models import Invito


class Room(models.Model):

    title = models.CharField(max_length=255)
    users=models.ManyToManyField(User,related_name='iscritti', blank=True)
    invito=models.ForeignKey(Invito,related_name='invito',on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    @property
    def group_name(self):
        """
        Returns the Channels Group name that sockets should subscribe to to get sent
        messages as they are generated.
        """
        return "room-%s" % self.id

    class Meta:
        verbose_name='Room'
        verbose_name_plural='Rooms'

class MessageModel(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipient = models.ForeignKey(Room, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    body = models.TextField('body')

    def __str__(self):
        return str(self.id)

    def characters(self):

        return len(self.body)

    def notify_ws_clients(self):
        """
        Inform client there is a new message.
        """
        notification = {
            'type': 'recieve_group_message',
            'message': '{}'.format(self.id)
        }

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)("{}".format(self.user.id), notification)
        async_to_sync(channel_layer.group_send)("{}".format(self.recipient.id), notification)

    def save(self, *args, **kwargs):

        new = self.id
        self.body = self.body.strip()
        super(MessageModel, self).save(*args, **kwargs)
        if new is None:
            self.notify_ws_clients()

    # Meta
    class Meta:

        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ('-timestamp',)
