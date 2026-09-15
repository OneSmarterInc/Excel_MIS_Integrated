"""Turn extracted book text into an easy explanation a student can actually read.

The rewrite runs on a local Ollama model, so no API key and no internet connection
are involved. If Ollama is not running, or the model is not pulled yet, the built in
writer takes over: it picks the sentences that carry the most meaning, simplifies the
wording, lists the Excel terms it found and closes with a practice step. Either way a
student always gets an explanation.
"""
from __future__ import annotations

import json
import re
import urllib.request

from django.conf import settings

from .extraction import excel_terms_in

SIMPLER = {
    "utilize": "use", "utilise": "use", "utilizing": "using",
    "commence": "start", "terminate": "end", "subsequent": "next",
    "prior to": "before", "in order to": "to", "demonstrate": "show",
    "facilitate": "help", "approximately": "about", "additionally": "also",
    "furthermore": "also", "however": "but", "therefore": "so",
    "consequently": "so", "numerous": "many", "obtain": "get",
    "modify": "change", "indicate": "show", "sufficient": "enough",
    "initiate": "start", "assist": "help", "require": "need",
    "component": "part", "methodology": "method", "endeavor": "try",
}
TERM_HELP = {
    "SUM": "adds a range of numbers",
    "AVERAGE": "finds the mean of a range",
    "COUNT": "counts how many cells hold numbers",
    "COUNTA": "counts cells that are not empty",
    "COUNTIF": "counts cells that meet one condition",
    "SUMIF": "adds only the cells that meet one condition",
    "MIN": "returns the smallest value",
    "MAX": "returns the largest value",
    "IF": "returns one answer when a test is true and another when it is false",
    "VLOOKUP": "looks a value up in the first column of a table and returns a value beside it",
    "XLOOKUP": "looks a value up in one range and returns the match from another range",
    "INDEX": "returns the value at a given row and column of a range",
    "MATCH": "returns the position of a value inside a range",
    "ROUND": "rounds a number to a set number of decimal places",
    "PMT": "calculates a loan payment",
    "NPV": "discounts future cash flows back to today",
    "IRR": "finds the rate that makes a project break even",
    "AUTOSUM": "inserts a SUM formula under the column you selected",
    "AUTOFILL": "extends a pattern by dragging the fill handle",
    "PIVOT TABLE": "summarises a long list by category without writing formulas",
    "ABSOLUTE REFERENCE": "locks a cell with dollar signs so copying does not move it",
    "RELATIVE REFERENCE": "shifts with the formula when you copy it",
    "CONDITIONAL FORMATTING": "colours cells automatically when a rule is met",
    "FREEZE PANES": "keeps headings on screen while you scroll",
    "CHART": "shows the shape of the numbers instead of the numbers themselves",
    "FILTER": "hides rows that do not match what you asked for",
    "SORT": "puts rows in order by a column you choose",
    "TEXT": "formats a number as text in a pattern you choose",
    "CONCAT": "joins pieces of text into one cell",
    "TODAY": "returns the current date",
}
TERM_EXAMPLE = {
    "SUM": ("Put 120, 340, 90 and 260 in B2 down to B5, then =SUM(B2:B5) in B6. "
            "It returns 810, and changing B3 to 400 moves B6 to 870 on its own."),
    "AVERAGE": ("With 80, 90, 70 and 0 in B2:B5, =AVERAGE(B2:B5) returns 60, not 80. "
                "The zero counts; an empty cell would not."),
    "COUNT": ("If B2:B7 holds four numbers, the word pending and a blank, =COUNT(B2:B7) "
              "returns 4 while =COUNTA(B2:B7) returns 5. The gap is the row to chase."),
    "COUNTA": ("=COUNTA(B2:B7) counts everything that is not empty, text included, so it "
               "is the one to use when you are asking how many rows were filled in."),
    "COUNTIF": ('=COUNTIF(A2:A20,"West") counts the West rows without deleting the others, '
                "which is what you want when the same file goes to four other people."),
    "SUMIF": ('=SUMIF(A2:A20,"West",C2:C20) adds only the West amounts. Sorting first and '
              "selecting by eye gets the same answer and breaks the next time a row moves."),
    "MIN": ("=MIN(B2:B10) returns the smallest number. Pair it with INDEX and MATCH when the "
            "question is which branch rather than how much."),
    "MAX": ("=MAX(B2:B10) returns the largest number, and =INDEX(A2:A10,MATCH(MAX(B2:B10),"
            "B2:B10,0)) turns that into the name beside it."),
    "IF": ('=IF(B2>=500,"Bonus","No bonus") puts a word in front of a manager instead of a '
           "number they have to interpret. Text results need the quotation marks."),
    "VLOOKUP": ('=VLOOKUP(A2,$F$2:$H$40,3,FALSE) finds the code in the first column of the '
                "table and returns the third column beside it. FALSE forces an exact match, "
                "and leaving it out is what produces answers that are almost right."),
    "XLOOKUP": ('=XLOOKUP(A2,$F$2:$F$40,$H$2:$H$40,0) does the same job in one function and '
                "takes the not-found answer directly."),
    "INDEX": ("=INDEX(C2:C20,MATCH(A2,B2:B20,0)) looks to the left as easily as to the right, "
              "which VLOOKUP cannot do."),
    "MATCH": ('=MATCH("West",A2:A20,0) returns the position of West in the list, which is what '
              "INDEX needs to fetch the value beside it."),
    "ROUND": ("=ROUND(1240.567,2) stores 1240.57. Formatting the cell to two decimals would "
              "leave 1240.567 underneath and the total would not agree with the column."),
    "AUTOSUM": ("Select the cell under the column and press AutoSum. Check the range Excel "
                "highlighted before you accept it; it guesses, and it guesses wrong on a "
                "column with a gap in it."),
    "AUTOFILL": ("Type Day 1 in A2 and Day 2 in A3, select both, then drag the fill handle. "
                 "Selecting one cell copies it instead of continuing the pattern."),
    "PIVOT TABLE": ("Branch in rows, Sum of Revenue in values, Quarter in columns, and the long "
                    "list summarises itself without a single formula. Refresh it before you "
                    "read the numbers to anybody."),
    "ABSOLUTE REFERENCE": ("Put the tax rate in E1 and write =B2*$E$1 in C2, then copy it down. "
                           "B2 moves to B3 while $E$1 stays locked. Written as =B2*E1 it would "
                           "multiply row three by the empty cell E2 and quietly return zero."),
    "RELATIVE REFERENCE": ("=B2*C2 copied from D2 to D4 becomes =B4*C4, which is what you want "
                           "on a line total and not what you want on a shared rate."),
    "CONDITIONAL FORMATTING": ("A rule of less than the target on C2:C20 colours a cell as the "
                               "figure is typed, so nobody has to scan the column afterwards."),
    "FREEZE PANES": ("Freeze the top row and the headings stay on screen through two hundred "
                     "rows, which is the difference between a readable report and a guess."),
    "CHART": ("A column chart compares branches, a line chart shows change over time. Pick the "
              "type from the question, and title it with the finding rather than the axis."),
    "FILTER": ("Filter hides the rows that do not match and changes nothing underneath, so it "
               "is the safe choice when somebody else owns the file."),
    "SORT": ("Sort the whole table rather than one column, or the rows come apart and the "
             "worksheet quietly becomes fiction."),
    "PMT": ("=PMT(0.06/12,60,25000) returns about -483.32 a month. The rate is divided by "
            "twelve because the payments are monthly, and the answer is negative because the "
            "money is leaving."),
    "NPV": ("=C1+NPV(0.09,C2:C8) discounts the future flows and adds today's outlay outside "
            "the function, because Excel assumes the first value is already a period away."),
    "IRR": ("=IRR(C1:C8) returns the rate at which the project just breaks even, which is the "
            "number a board tends to ask for after the net present value."),
}

TERM_PITFALL = {
    "AVERAGE": "a zero drags the mean down while a blank is skipped entirely",
    "COUNT": "text in a numeric column is silently ignored",
    "SUMIF": "the condition needs quotation marks when it contains an operator",
    "SUMIFS": "the range being added comes first here and last in SUMIF",
    "VLOOKUP": "leaving out FALSE allows an approximate match on unsorted data",
    "ROUND": "rounding changes the stored value, formatting does not",
    "ABSOLUTE REFERENCE": "forgetting the dollar signs looks right in row one and drifts after it",
    "AUTOFILL": "selecting one cell copies rather than continues",
    "AUTOSUM": "the highlighted range stops at the first blank cell",
    "IF": "the strictest test has to come first when they are nested",
    "PIVOT TABLE": "it does not refresh itself when the source data changes",
    "MAX": "it returns the value, never the name beside it",
}

# Only these read naturally in a sentence like "use X on a column of numbers".
FUNCTION_TERMS = {
    "SUM", "AVERAGE", "COUNT", "COUNTA", "COUNTIF", "SUMIF", "MIN", "MAX", "IF", "ROUND",
    "VLOOKUP", "XLOOKUP", "INDEX", "MATCH", "PMT", "NPV", "IRR", "AUTOSUM",
}

STOPWORDS = set(
    "the a an and or of to in for with on at by is are was were be been this that "
    "these those it its as from you your we our they their he she will can may".split()
)


def _sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", (text or "").replace("\n", " "))
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in parts if len(p.strip()) > 25]


def _simplify(sentence: str) -> str:
    sentence = re.sub(r"\([^)]{0,80}\)", "", sentence)
    for hard, easy in SIMPLER.items():
        sentence = re.sub(rf"\b{hard}\b", easy, sentence, flags=re.IGNORECASE)
    sentence = re.sub(r"\s{2,}", " ", sentence).strip()
    if len(sentence) > 260:
        cut = sentence[:260].rsplit(" ", 1)[0]
        sentence = cut + "."
    if sentence and sentence[-1] not in ".!?":
        sentence += "."
    return sentence[0].upper() + sentence[1:] if sentence else sentence


def _key_sentences(text: str, limit: int = 6, title: str = "") -> list[str]:
    sentences = _sentences(text)
    if title:
        head = title.lower().strip()
        sentences = [s for s in sentences if head not in s.lower()[: len(head) + 12]]
    if not sentences:
        return []
    frequency: dict[str, int] = {}
    for sentence in sentences:
        for word in re.findall(r"[a-zA-Z]{4,}", sentence.lower()):
            if word not in STOPWORDS:
                frequency[word] = frequency.get(word, 0) + 1
    scored = []
    for position, sentence in enumerate(sentences):
        words = [w for w in re.findall(r"[a-zA-Z]{4,}", sentence.lower()) if w not in STOPWORDS]
        if not words:
            continue
        score = sum(frequency.get(w, 0) for w in words) / len(words)
        if position < 3:
            score *= 1.3
        if excel_terms_in(sentence):
            score *= 1.25
        scored.append((score, position, sentence))
    scored.sort(key=lambda item: item[0], reverse=True)
    chosen = sorted(scored[:limit], key=lambda item: item[1])
    return [_simplify(sentence) for _, _, sentence in chosen]


def _plain_gloss(sentence: str) -> str:
    """A second, simpler line for a sentence, built from the Excel term it mentions.

    Students meet a definition once and lose it. Saying the same thing twice, the second
    time in everyday words, is the cheapest way to make it stick.
    """
    for term in excel_terms_in(sentence):
        meaning = TERM_HELP.get(term.upper())
        if meaning:
            return f"{term} {meaning}."
    if len(sentence) > 150:
        return "the long version of this is just: " + sentence.split(",")[0].strip(" .") + "."
    return ""


def local_explanation(title: str, text: str, kind: str = "chapter") -> str:
    """Write the explanation without a model, at the length a student can actually learn from."""
    subject = title.lower().strip(" .:")
    key = _key_sentences(text, limit=9, title=title)
    terms = excel_terms_in(text)
    # A sentence about doing something reads better with a function than with a concept.
    doable = next((t for t in terms if t.upper() in FUNCTION_TERMS), None)
    words = len((text or "").split())
    lines = [f"Easy explanation of {title}", ""]

    lines.append("What this is about")
    lines.append(
        f"This {kind} covers {subject}. Read this page first, then open Excel and try it. "
        "Nothing here needs anything you have not already met, and every idea below is "
        "written the way you would say it out loud."
    )
    lines.append("")

    lines.append("In plain words")
    if key:
        lines.append(" ".join(key[:3]))
        if len(key) > 3:
            lines.append(" ".join(key[3:6]))
        if len(key) > 6:
            lines.append(" ".join(key[6:9]))
    else:
        lines.append(
            f"This {kind} covers {subject}. The text extracted for it is short, so read the "
            "original pages as well, and use the practice below to make the idea concrete."
        )
    lines.append("")

    lines.append("The main ideas, one at a time")
    if key:
        for position, sentence in enumerate(key[:7], start=1):
            lines.append(f"{position}. {sentence}")
            gloss = _plain_gloss(sentence)
            if gloss:
                lines.append(f"   In other words: {gloss}")
    else:
        lines.append(f"1. Be able to say what {subject} means in one sentence of your own.")
        lines.append(f"2. Know where {subject} shows up in a real worksheet.")
        lines.append("3. Know what goes wrong when it is done carelessly.")
    lines.append("")

    if terms:
        lines.append("Excel terms used here")
        for term in terms:
            meaning = TERM_HELP.get(term.upper())
            lines.append(f"- {term}: {meaning}" if meaning else f"- {term}")
        lines.append("")

        example_term = next((t for t in terms if t.upper() in TERM_EXAMPLE), None)
        if example_term:
            lines.append("A worked example")
            lines.append(TERM_EXAMPLE[example_term.upper()])
            second = next(
                (t for t in terms if t.upper() in TERM_EXAMPLE and t != example_term), None
            )
            if second:
                lines.append(TERM_EXAMPLE[second.upper()])
            lines.append("")

        pitfalls = [
            f"{term}: {TERM_PITFALL[term.upper()]}"
            for term in terms if term.upper() in TERM_PITFALL
        ]
        if pitfalls:
            lines.append("Where people go wrong")
            for pitfall in pitfalls[:4]:
                lines.append(f"- {pitfall}")
            lines.append("")

    lines.append("Why a manager cares")
    lines.append(
        f"A worksheet is finished when somebody else can act on it. This part matters because "
        + (
            f"a decision gets made on the back of what {doable} returns, and a wrong range or "
            "a wrong format changes that decision without anybody noticing."
            if doable
            else "the numbers are read by people who will not rebuild them, so getting this "
                 "part right is what keeps the rest of the worksheet honest."
        )
    )
    lines.append("")

    lines.append("How to read this in a worksheet")
    lines.append(
        "Open the file, click on one cell and look at the formula bar. The bar shows what is "
        "really in the cell; the grid shows what it looks like after formatting. When those "
        "two disagree, believe the formula bar. Do that on three or four cells and you will "
        "have a picture of how the sheet was put together."
    )
    lines.append("")

    lines.append("Try it yourself")
    if doable:
        lines.append(
            f"Open a blank worksheet, type a short column of numbers, and use {doable.upper()} "
            "on it. "
            "Then change one input and watch which results move and which do not. Do it a "
            "second time with a deliberate mistake in it, so you know what the error looks "
            "like before you meet it under time pressure."
        )
    else:
        lines.append(
            f"Open a blank worksheet and rebuild the smallest example of {subject} by hand. "
            "Change one input, watch what moves downstream, then break it on purpose and fix it."
        )
    lines.append("")

    lines.append("Check yourself")
    lines.append(
        f"1. Can you say what {subject} means in one sentence, without looking?"
    )
    lines.append("2. Can you show it working in a worksheet you built yourself?")
    lines.append("3. Can you name one mistake somebody could make with it, and spot it?")
    lines.append(
        "4. Can you say what a manager would do differently because of the result?"
    )
    lines.append(
        "If any of those four is shaky, go back to the worked example above and rebuild it "
        "with your own numbers before you take the quiz."
    )
    if words:
        lines.append(f"This section runs to about {words} words in the original text.")
    return "\n".join(lines).strip()


def ollama_status() -> dict:
    """Report whether Ollama is reachable and which models are pulled."""
    host = getattr(settings, "OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    wanted = getattr(settings, "OLLAMA_MODEL", "llama3.1:8b")
    if not getattr(settings, "USE_OLLAMA", True):
        return {"running": False, "models": [], "model": wanted,
                "message": "Ollama is switched off, so the built in writer is being used."}
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as response:
            payload = json.loads(response.read().decode())
        models = [entry.get("name", "") for entry in payload.get("models", [])]
    except Exception as exc:
        return {"running": False, "models": [], "model": wanted,
                "message": f"Ollama is not answering on {host} ({exc}). "
                           "Run: ollama serve"}
    if not any(name == wanted or name.startswith(wanted.split(":")[0]) for name in models):
        return {"running": True, "models": models, "model": wanted,
                "message": f"Ollama is running but {wanted} is not pulled. "
                           f"Run: ollama pull {wanted}"}
    return {"running": True, "models": models, "model": wanted,
            "message": f"Ollama is running with {wanted}."}


def ollama_explanation(title: str, text: str, kind: str) -> str | None:
    """Ask the local model for the rewrite. Returns None if Ollama cannot answer."""
    if not getattr(settings, "USE_OLLAMA", True):
        return None
    host = getattr(settings, "OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = getattr(settings, "OLLAMA_MODEL", "llama3.1:8b")
    timeout = getattr(settings, "OLLAMA_TIMEOUT", 180)

    system = (
        "You write short, plain English study notes for undergraduate business students "
        "learning Microsoft Excel. You never use markdown symbols, asterisks, or bullet "
        "characters. You keep sentences short and concrete."
    )
    prompt = (
        f"Rewrite the {kind} below as an easy explanation of about 300 words.\n"
        f"The {kind} is titled: {title}\n\n"
        "Use exactly these five headings, each on its own line, with plain paragraphs or "
        "numbered lines underneath:\n"
        "In plain words\n"
        "The main ideas\n"
        "Excel terms used here\n"
        "Try it yourself\n"
        "Check yourself\n\n"
        "Stay with what the source text actually says. Do not invent facts. "
        "Where an Excel function appears, say in one short line what it does.\n\n"
        "Source text:\n" + (text or "")[:9000]
    )
    body = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 2200},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }).encode()
    request = urllib.request.Request(
        f"{host}/api/chat", data=body, headers={"content-type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode())
    except Exception:
        return None

    answer = (payload.get("message") or {}).get("content", "").strip()
    if len(answer) < 120:
        return None
    # Small models sometimes slip a markdown symbol in, and the house style has none.
    answer = re.sub(r"^#{1,6}\s*", "", answer, flags=re.MULTILINE)
    answer = answer.replace("**", "").replace("*", "").replace("`", "")
    answer = re.sub(r"^\s*[-\u2022]\s*", "- ", answer, flags=re.MULTILINE)
    return f"Easy explanation of {title}\n\n{answer}".strip()


def build_explanation(title: str, text: str, kind: str = "chapter") -> str:
<<<<<<< HEAD
    """The model writes it. The built in writer is only there for when it cannot.

    A local model occasionally returns a stub on the first pass, so it gets a second ask
    before the fallback takes over, and a short answer is treated as no answer.
    """
    for _ in range(2):
        written = ollama_explanation(title, text, kind)
        if written and len(written.split()) >= 120:
            return written
    return local_explanation(title, text, kind)


# --------------------------------------------------------------------- figure captions

def _ollama_chat(model: str, system: str, prompt: str, images: list[str] | None = None,
                 tokens: int = 220, temperature: float = 0.2) -> str | None:
    """One short exchange with Ollama. Returns None whenever it cannot answer."""
    if not getattr(settings, "USE_OLLAMA", True):
        return None
    host = getattr(settings, "OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    message = {"role": "user", "content": prompt}
    if images:
        message["images"] = images
    body = json.dumps({
        "model": model,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": tokens},
        "messages": [{"role": "system", "content": system}, message],
    }).encode()
    request = urllib.request.Request(
        f"{host}/api/chat", data=body, headers={"content-type": "application/json"}
    )
    try:
        with urllib.request.urlopen(
            request, timeout=getattr(settings, "OLLAMA_CAPTION_TIMEOUT", 90)
        ) as response:
            payload = json.loads(response.read().decode())
    except Exception:
        return None
    answer = (payload.get("message") or {}).get("content", "").strip()
    return answer or None


def _tidy_caption(answer: str) -> str:
    answer = re.sub(r"^#{1,6}\s*", "", answer, flags=re.MULTILINE)
    answer = answer.replace("**", "").replace("*", "").replace("`", "").strip()
    answer = re.sub(r"^(caption|figure)\s*[:\-]\s*", "", answer, flags=re.IGNORECASE)
    answer = re.sub(r"\s+", " ", answer).strip().strip('"')
    if len(answer) > 320:
        answer = answer[:320].rsplit(" ", 1)[0] + "."
    if answer and answer[-1] not in ".!?":
        answer += "."
    return answer


def figure_caption(section_title: str, explanation: str, context: str,
                   image_base64: str = "") -> str | None:
    """Ask the local model to say, in one or two lines, what this picture shows.

    A vision model is used when one is configured, because it can describe the picture
    itself. Without one the ordinary model is given the words that surrounded the picture
    in the book along with the explanation the student is reading, which is enough to say
    what the figure is there to show. Either way this returns None if Ollama is not
    answering, and the caller keeps the plain caption it already had.
    """
    vision = getattr(settings, "OLLAMA_VISION_MODEL", "")
    system = (
        "You caption figures in a Microsoft Excel textbook for undergraduate business "
        "students. You answer with one or two short sentences of plain English, no "
        "markdown, no bullet characters, and no preamble."
    )
    if vision and image_base64:
        prompt = (
            f"This picture appears in a section called '{section_title}'.\n"
            "Say what the picture shows and what a student should notice in it. "
            "If it is a screenshot of a worksheet, say what is on the sheet.\n"
            "Two short sentences at most."
        )
        answer = _ollama_chat(vision, system, prompt, images=[image_base64])
        if answer:
            return _tidy_caption(answer)

    if not (context or "").strip():
        return None
    model = getattr(settings, "OLLAMA_MODEL", "llama3.1:8b")
    prompt = (
        f"A figure appears in a textbook section called '{section_title}'.\n\n"
        "These are the words printed around it on the page:\n"
        + context[:1200]
        + "\n\nThis is the explanation the student is reading:\n"
        + (explanation or "")[:1200]
        + "\n\nWrite one or two short sentences telling the student what this figure is "
        "showing and why it is worth looking at. Stay with what the words above say. "
        "Do not invent numbers that are not there. Do not begin with the word Figure."
    )
    answer = _ollama_chat(model, system, prompt)
    return _tidy_caption(answer) if answer else None
=======
    return ollama_explanation(title, text, kind) or local_explanation(title, text, kind)
>>>>>>> origin/main
