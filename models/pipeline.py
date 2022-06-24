"""
Data Pipeline Models
"""

import os
import json
import logging
import time
import urllib

from django.db import models
from django.utils import timezone as tz
from django.core.mail import mail_admins
from django.core.files.base import ContentFile
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


"""
Log timing constants
"""
MAX_REQUEST_LENGTH = 4
MAX_REQUEST_DELTA = tz.timedelta(seconds=2)
WAIT_INTERVAL = 2
EMAIL_REQUEST_LENGTH = 8

# TODO: Associate with models, as views of data


class RequestLog(models.Model):
    """Log data about requests made"""
    url = models.URLField()
    ua_header = models.TextField()
    params = models.TextField()
    start_time = models.DateTimeField(blank=True, null=True, default=None)
    end_time = models.DateTimeField(blank=True, null=True, default=None)
    delta = models.FloatField(default=0)
    response_code = models.IntegerField(default=0)
    wait = models.FloatField(default=0)

    def __str__(self):
        return f"{self.url} [{self.response_code}] ({self.delta}s)>"


class SourceLog(models.Model):
    """Store data from every query"""
    request = models.ForeignKey(
        RequestLog,
        on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='papernet/sources/',
                            blank=True, null=True, default=None)
    file_type = models.CharField(max_length=128, default="raw")

    _data = None

    @property
    def data(self):
        if self._data is None:
            self._data = json.loads(self.file.read())

        return self._data

    def generate_filepath(self, file_type=None):
        """Generate filename to save data"""
        upload_dir = self.file.field.upload_to

        path = urllib.parse.urlsplit(self.request.url).path
        timestamp = tz.now().strftime("%Y-%m%-d-%H-%S")

        # Update file_type
        self.file_type = file_type or self.file_type

        filepath = upload_dir + path + timestamp + "." + file_type

        # filepath = os.path.join(upload_dir, self.pk, self.file_type)
        return filepath

    def store_data(self, data, file_type=None):
        """Store data in file field"""
        self.data = data

        filepath = self.generate_filepath(file_type)

        file = ContentFile(data)

        self.file.save(filepath, file, True)


class Attribution(models.Model):
    """Link models to sources"""
    source = models.ForeignKey(
        SourceLog,
        on_delete=models.CASCADE
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE,
        blank=True, null=True)
    object_id = models.PositiveIntegerField(
        blank=True, null=True)
    model = GenericForeignKey('content_type', 'object_id')

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(default=tz.now)


def log_source(response, requestlog, request=None):
    """Log source data"""
    source = SourceLog(request=requestlog)

    # TODO: get content-type

    try:
        data = json.loads(response.content)
    except json.JSONDecodeError as e:
        logger.exception(e)
        data = response.content
        file_type = "raw"
    else:
        file_type = "json"

    source.store_data(data, file_type)

    source.save()

    return source


def log_request(url, params, start_time, end_time, response, wait):
    """Create RequestLog"""
    params = json.dumps(params)
    delta = end_time - start_time
    delta_secs = delta.total_seconds()

    if delta > MAX_REQUEST_DELTA:
        logger.warning("Request to %s took too long: %.1fs (max %.1fs)",
                       url, delta_secs, MAX_REQUEST_DELTA.total_seconds())

    log = RequestLog(url=url, params=params, start_time=start_time,
                     end_time=end_time, delta=delta_secs,
                     response_code=response.status_code, wait=wait)
    log.save()

    return log


def rate_limit_warn_email(request):
    """Email admins to warn of long request wait"""
    subject = f"API request took {request.delta}"
    message = f"Request {request} to {request.url}"
    mail_admins(subject, message)


def rate_limit(url=None, params=None):
    """Check last response time and sleep if need be"""

    # TODO: Send email as task
    # TODO: Different rate limits for different routes

    last_request = RequestLog.objects.last()
    delta = last_request.delta or 0

    if delta > EMAIL_REQUEST_LENGTH:
        rate_limit_warn_email(last_request)

    if delta > MAX_REQUEST_LENGTH:

        wait = max(WAIT_INTERVAL, delta * 2)
        # wait = WAIT_INTERVAL

        elapsed = (tz.now() - last_request.end_time).total_seconds()
        remaining = wait - elapsed

        if remaining > 0:
            logger.warning("Last Request (%s) took took too long. "
                           "Waiting %.1fs (%.1fs remaining)",
                           last_request, wait, remaining)
            time.sleep(remaining)
        return wait
    return 0

