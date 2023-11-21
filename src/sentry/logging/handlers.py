import logging
import re

from django.utils.timezone import now
from structlog import get_logger
from structlog.processors import _json_fallback_handler

from sentry.utils import json, metrics

# These are values that come default from logging.LogRecord.
# They are defined here:
# https://github.com/python/cpython/blob/2.7/Lib/logging/__init__.py#L237-L310
throwaways = frozenset(
    (
        "threadName",
        "thread",
        "created",
        "process",
        "processName",
        "args",
        "module",
        "filename",
        "levelno",
        "exc_text",
        "msg",
        "pathname",
        "lineno",
        "funcName",
        "relativeCreated",
        "levelname",
        "msecs",
    )
)


def get_JSONEncoder(skipkeys=False):
    return json.JSONEncoder(
        separators=(",", ":"),
        ignore_nan=True,
        skipkeys=skipkeys,
        ensure_ascii=True,
        check_circular=True,
        allow_nan=True,
        indent=None,
        encoding="utf-8",
        default=_json_fallback_handler,
    )


JSONEncoder_skipkeys = get_JSONEncoder(skipkeys=True)
JSONEncoder_no_skipkeys = get_JSONEncoder(skipkeys=False)


class JSONRenderer:
    def __call__(self, logger, name, event_dict):
        # importing inside of the function to avoid circular imports
        from django.conf import settings  # NOQA isort:skip # pylint:disable=import-outside-toplevel

        try:
            return JSONEncoder_no_skipkeys.encode(event_dict)
        except Exception:
            logging.warning("Failed to serialize event", exc_info=True)
            # in Production, we want to skip non-serializable keys, rather than raise an exception
            if settings.IS_PROD:
                return JSONEncoder_skipkeys.encode(event_dict)
            else:
                raise


class HumanRenderer:
    def __call__(self, logger, name, event_dict):
        level = event_dict.pop("level")
        real_level = level.upper() if isinstance(level, str) else logging.getLevelName(level)
        base = "{} [{}] {}: {}".format(
            now().strftime("%H:%M:%S"),
            real_level,
            event_dict.pop("name", "root"),
            event_dict.pop("event", ""),
        )
        join = " ".join(k + "=" + repr(v) for k, v in event_dict.items())
        return "{}{}".format(base, (" (%s)" % join if join else ""))


class StructLogHandler(logging.StreamHandler):
    def get_log_kwargs(self, record, logger):
        kwargs = {k: v for k, v in vars(record).items() if k not in throwaways and v is not None}
        kwargs.update({"level": record.levelno, "event": record.msg})

        if record.args:
            # record.args inside of LogRecord.__init__ gets unrolled
            # if it's the shape `({},)`, a single item dictionary.
            # so we need to check for this, and re-wrap it because
            # down the line of structlog, it's expected to be this
            # original shape.
            if isinstance(record.args, (tuple, list)):
                kwargs["positional_args"] = record.args
            else:
                kwargs["positional_args"] = (record.args,)

        return kwargs

    def emit(self, record, logger=None):
        # If anyone wants to use the 'extra' kwarg to provide context within
        # structlog, we have to strip all of the default attributes from
        # a record because the RootLogger will take the 'extra' dictionary
        # and just turn them into attributes.
        try:
            if logger is None:
                logger = get_logger()
            logger.log(**self.get_log_kwargs(record=record, logger=logger))
        except Exception:
            if logging.raiseExceptions:
                raise


class MessageContainsFilter(logging.Filter):
    """
    A logging filter that allows log records where the message
    contains given substring(s).

    contains -- a string or list of strings to match
    """

    def __init__(self, contains):
        if not isinstance(contains, list):
            contains = [contains]
        if not all(isinstance(c, str) for c in contains):
            raise TypeError("'contains' must be a string or list of strings")
        self.contains = contains

    def filter(self, record):
        message = record.getMessage()
        return any(c in message for c in self.contains)


whitespace_re = re.compile(r"\s+")
metrics_badchars_re = re.compile("[^a-z0-9_.]")


class MetricsLogHandler(logging.Handler):
    def emit(self, record, logger=None):
        """
        Turn something like:
            > django.request.Forbidden (CSRF cookie not set.): /account
        into:
            > django.request.forbidden_csrf_cookie_not_set
        and track it as an incremented counter.
        """
        key = record.name + "." + record.getMessage()
        key = key.lower()
        key = whitespace_re.sub("_", key)
        key = metrics_badchars_re.sub("", key)
        key = ".".join(key.split(".")[:3])
        metrics.incr(key, skip_internal=False)
