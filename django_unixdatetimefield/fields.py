import datetime
import warnings
import time

from django.conf import settings
from django.core import exceptions
from django.utils import timezone
import django.db.models as models
from django.utils.dateparse import parse_datetime


class UnixDateTimeField(models.DateTimeField):
    # TODO(niklas9):
    # * metaclass below just for Django < 1.9, fix a if stmt for it?
    #__metaclass__ = models.SubfieldBase
    description = "Unix timestamp integer to datetime object"

    def get_internal_type(self):
        return 'PositiveIntegerField'

    def to_python(self, val):
        if val is None or isinstance(val, datetime.datetime):
            return val
        if isinstance(val, datetime.date):
            value = datetime.datetime(val.year, val.month, val.day)
            if settings.USE_TZ:
                # For backwards compatibility, interpret naive datetimes in
                # local time. This won't work during DST change, but we can't
                # do much about it, so we let the exceptions percolate up the
                # call stack.
                warnings.warn("DateTimeField %s.%s received a naive datetime "
                              "(%s) while time zone support is active." %
                              (self.model.__name__, self.name, value),
                              RuntimeWarning)
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_aware(value, default_timezone)
            return value

        if self._is_string(val):
            try:
                parsed = parse_datetime(val)
                if parsed is not None:
                    return parsed
            except ValueError:
                raise exceptions.ValidationError(
                    self.error_messages['invalid_datetime'],
                    code='invalid_datetime',
                    params={'value': value},
                )
        else:
            value = datetime.datetime.fromtimestamp(val)
            if settings.USE_TZ:
                default_timezone = timezone.get_default_timezone()
                value = timezone.make_aware(value, default_timezone)
            return value

    def _is_string(value, val):
        try:
            return isinstance(val, unicode)
        except NameError:
            return isinstance(val, str)

    def get_db_prep_value(self, val, *args, **kwargs):
        if val is None:
            if self.default == models.fields.NOT_PROVIDED:  return None
            return self.default
        return int(time.mktime(val.timetuple()))

    def value_to_string(self, obj):
        val = self.value_from_object(obj)
        return '' if val is None else val.isoformat()

    def from_db_value(self, val, expression, connection, context):
        return self.to_python(val)
