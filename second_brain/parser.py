import re
from datetime import date, timedelta
 
WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
 
MONTH_LOOKUP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
 
# Vosk transcribes numbers as spoken words ("twenty four", "three pm"),
# not digits — the regex patterns below only recognize digits, so this
# runs first and converts words like that into "24"/"3" before anything
# else touches the text. Calendar dates are also often spoken as
# ordinals ("december first", "the twenty fourth"), so those are
# handled too, not just cardinal numbers.
_CARDINAL_ONES = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9,
}
_ORDINAL_ONES = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
    "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9,
}
_SMALL = {
    "zero": 0, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
}
_SMALL_ORDINAL = {
    "zeroth": 0, "tenth": 10, "eleventh": 11, "twelfth": 12, "thirteenth": 13,
    "fourteenth": 14, "fifteenth": 15, "sixteenth": 16, "seventeenth": 17,
    "eighteenth": 18, "nineteenth": 19,
}
_TENS = {"twenty": 20, "thirty": 30}
_TENS_ORDINAL = {"twentieth": 20, "thirtieth": 30}
 
# What may follow a tens word ("twenty"/"thirty") to form a compound —
# either cardinal ("twenty four") or ordinal ("twenty fourth").
_ONES_ANY = {**_CARDINAL_ONES, **_ORDINAL_ONES}
# Every standalone word that converts to a single digit string on its own.
_STANDALONE = {**_CARDINAL_ONES, **_ORDINAL_ONES, **_SMALL, **_SMALL_ORDINAL, **_TENS, **_TENS_ORDINAL}
 
 
def _normalize_number_words(text):
    """Converts spoken numbers (cardinal or ordinal) to digits, e.g.
    'twenty four' -> '24', 'thirty first' -> '31', 'third' -> '3'.
    Also merges a split 'a m'/'p m' into 'am'/'pm', since some models
    emit those as two separate tokens."""
    tokens = text.split()
    result = []
    i = 0
    while i < len(tokens):
        word = tokens[i].lower()
 
        # "a m" / "p m" -> "am" / "pm"
        if word in ("a", "p") and i + 1 < len(tokens) and tokens[i + 1].lower() == "m":
            result.append(word + "m")
            i += 2
            continue
 
        # "twenty four" / "thirty first" -> "24" / "31"
        if word in _TENS and i + 1 < len(tokens) and tokens[i + 1].lower() in _ONES_ANY:
            value = _TENS[word] + _ONES_ANY[tokens[i + 1].lower()]
            result.append(str(value))
            i += 2
            continue
 
        # bare number word -> digit ("three" -> "3", "twelfth" -> "12")
        if word in _STANDALONE:
            result.append(str(_STANDALONE[word]))
            i += 1
            continue
 
        result.append(tokens[i])
        i += 1
 
    return " ".join(result)
 
_MONTH_ALT = "|".join(MONTH_LOOKUP.keys())
_ORDINAL = r"(?:st|nd|rd|th)?"
 
_TIME_PATTERNS = [
    # Colon form: "at 3:30 pm", "3:30pm"
    re.compile(r"\bat\s+(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<ap>am|pm)?\b", re.IGNORECASE),
    # Spoken triple form (no colon, since Vosk never produces one):
    # "at 3 30 pm" — minute is a mandatory separate token here so this
    # can't misfire on "at 3 pm" (no middle number to match).
    re.compile(r"\bat\s+(?P<h>\d{1,2})\s+(?P<m>\d{1,2})\s*(?P<ap>am|pm)?\b", re.IGNORECASE),
    re.compile(r"\bat\s+(?P<h>\d{1,2})\s*(?P<ap>am|pm)\b", re.IGNORECASE),
    # Bare "at 3" — least specific, tried last among "at ..." forms so
    # it doesn't grab just the hour when a minute/am-pm follows.
    re.compile(r"\bat\s+(?P<h>\d{1,2})\b", re.IGNORECASE),
    re.compile(r"\b(?P<h>\d{1,2}):(?P<m>\d{2})\s*(?P<ap>am|pm)?\b", re.IGNORECASE),
    # Spoken triple with no "at" — am/pm required here, since without
    # "at" AND without am/pm, three bare numbers in a row is too
    # ambiguous to safely assume it's a time.
    re.compile(r"\b(?P<h>\d{1,2})\s+(?P<m>\d{1,2})\s*(?P<ap>am|pm)\b", re.IGNORECASE),
    re.compile(r"\b(?P<h>\d{1,2})\s*(?P<ap>am|pm)\b", re.IGNORECASE),
]
 
_RELATIVE_PATTERN = re.compile(r"\b(day after tomorrow|tomorrow|today)\b", re.IGNORECASE)
_WEEKDAY_PATTERN = re.compile(
    r"\b(next|this)?\s*(" + "|".join(WEEKDAY_NAMES) + r")\b", re.IGNORECASE
)
_MONTH_FIRST = re.compile(
    r"\b(?:on\s+)?(?:the\s+)?(?P<month>" + _MONTH_ALT + r")\.?\s+"
    r"(?P<day>\d{1,2})" + _ORDINAL + r"(?:\s*,?\s*(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
_DAY_FIRST = re.compile(
    r"\b(?:on\s+)?(?:the\s+)?(?P<day>\d{1,2})" + _ORDINAL + r"\s+(?:of\s+)?"
    r"(?P<month>" + _MONTH_ALT + r")\.?(?:\s*,?\s*(?P<year>\d{4}))?\b",
    re.IGNORECASE,
)
 
_BOUNDARY_WORD = re.compile(r"^(on|for|at|the|of)\b[,]?\s*|\s*[,]?\b(on|for|at|the|of)$", re.IGNORECASE)
 
 
def parse_event_command(raw_text, today=None):
    """
    raw_text: everything AFTER the "add event "/"event " prefix has
              already been stripped by the caller. Original casing is
              kept so the title reads naturally.
    today:    injectable for testing; defaults to date.today().
 
    Returns {"title": str, "date": date|None, "time": "HH:MM"|None}
    """
    if today is None:
        today = date.today()
 
    working = _normalize_number_words(raw_text.strip())
 
    time_str, working = _extract_time(working)
    event_date, working = _extract_date(working, today)
 
    title = _clean_title(working)
    if not title:
        title = "Untitled event"
 
    return {"title": title, "date": event_date, "time": time_str}
 
 
def _extract_time(text):
    """Finds the first time expression anywhere in text. Returns
    (time_str_or_None, text_with_it_removed)."""
    for pattern in _TIME_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
 
        groups = match.groupdict()
        hour = int(groups["h"])
        minute = int(groups["m"]) if groups.get("m") else 0
        ampm = groups.get("ap")
        if ampm:
            ampm = ampm.lower()
 
        if ampm:
            if not (1 <= hour <= 12):
                continue  # e.g. "13 pm" makes no sense — try a looser pattern
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
        else:
            if not (0 <= hour <= 23):
                continue
 
        if not (0 <= minute <= 59):
            continue
 
        start, end = match.span()
        remaining = text[:start] + " " + text[end:]
        return f"{hour:02d}:{minute:02d}", remaining
 
    return None, text
 
 
def _extract_date(text, today):
    """Finds the first date expression anywhere in text. Returns
    (date_or_None, text_with_it_removed)."""
    match = _RELATIVE_PATTERN.search(text)
    if match:
        word = match.group(1).lower()
        result = {
            "today": today,
            "tomorrow": today + timedelta(days=1),
            "day after tomorrow": today + timedelta(days=2),
        }[word]
        start, end = match.span()
        return result, text[:start] + " " + text[end:]
 
    match = _WEEKDAY_PATTERN.search(text)
    if match:
        modifier = (match.group(1) or "").lower()
        weekday_name = match.group(2).lower()
        target_idx = WEEKDAY_NAMES.index(weekday_name)
        days_ahead = (target_idx - today.weekday()) % 7
        if modifier == "next":
            # "next monday" = the monday after the nearest upcoming one,
            # not this week's occurrence.
            days_ahead = days_ahead + 7 if days_ahead != 0 else 7
        # "this <weekday>" or a bare weekday name both mean the nearest
        # upcoming occurrence, today included if it matches.
        start, end = match.span()
        return today + timedelta(days=days_ahead), text[:start] + " " + text[end:]
 
    match = _MONTH_FIRST.search(text) or _DAY_FIRST.search(text)
    if match:
        groups = match.groupdict()
        month = MONTH_LOOKUP[groups["month"].lower()]
        day = int(groups["day"])
        year = int(groups["year"]) if groups.get("year") else today.year
        try:
            result = date(year, month, day)
        except ValueError:
            return None, text  # e.g. "february 30th" isn't a real date
 
        if not groups.get("year") and result < today:
            # No year was said and the date's already passed this year —
            # assume next year's occurrence instead.
            try:
                result = date(year + 1, month, day)
            except ValueError:
                return None, text
 
        start, end = match.span()
        return result, text[:start] + " " + text[end:]
 
    return None, text
 
 
def _clean_title(text):
    """Strips leftover connector words ('on', 'for', 'at'...) from the
    edges of whatever's left after date/time extraction, and collapses
    whitespace."""
    text = text.strip()
    previous = None
    while text != previous:
        previous = text
        text = _BOUNDARY_WORD.sub("", text).strip()
    return re.sub(r"\s+", " ", text).strip()