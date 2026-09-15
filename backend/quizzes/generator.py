"""Generate Excel quiz questions, each with its own small workbook.

Every question carries the worksheet a student needs to look at, so the app can show
a different spreadsheet on the right of every question. The data inside each workbook
is randomised on every call, and the seven templates used in an attempt are drawn
without replacement, so no two questions in a quiz repeat and a second attempt on the
same chapter produces a fresh paper.
"""
from __future__ import annotations

import random

COMPANIES = [
    "Lakeview Office Supply", "Corner Market", "Riverbend Tools", "Dayton Print Works",
    "Northgate Foods", "Springboro Textiles", "Harbor Point Cafe", "Maple Ridge Hardware",
    "Clearwater Logistics", "Beacon Auto Parts", "Sundial Bakery", "Ironwood Furniture",
]
REGIONS = ["North", "South", "East", "West", "Central", "Downtown", "Airport", "Riverside"]
PRODUCTS = ["Ledger Pad", "Ink Cartridge", "Desk Lamp", "Filing Box", "Stapler",
            "Chair Mat", "Toner Kit", "Whiteboard", "Label Roll", "Paper Ream"]
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def column_letter(index: int) -> str:
    return chr(ord("A") + index)


def sheet(file_name: str, sheet_name: str, headers: list[str], rows: list[list],
          highlight: list[str] | None = None, note: str = "") -> dict:
    """Row 1 holds the headers, so data starts at row 2 exactly like a real worksheet."""
    return {
        "file": file_name,
        "sheet": sheet_name,
        "columns": [column_letter(i) for i in range(len(headers))],
        "rows": [[str(h) for h in headers]] + [[str(c) for c in row] for row in rows],
        "highlight": highlight or [],
        "note": note,
    }


def money(value: float) -> str:
    return f"${value:,.2f}"


def choices(correct, wrong: list, rng: random.Random) -> tuple[list[str], int]:
    seen = {str(correct)}
    options = [str(correct)]
    for candidate in wrong:
        text = str(candidate)
        if text not in seen:
            seen.add(text)
            options.append(text)
        if len(options) == 4:
            break
    filler = 0
    while len(options) < 4:
        filler += 1
        options.append(f"None of these ({filler})")
    rng.shuffle(options)
    return options, options.index(str(correct))


# --------------------------------------------------------------------------- templates

def q_sum_formula(rng):
    company = rng.choice(COMPANIES)
    regions = rng.sample(REGIONS, 5)
    units = [rng.randrange(40, 400) for _ in regions]
    rows = [[r, u, money(u * rng.choice([12.5, 18.0, 24.75]))] for r, u in zip(regions, units)]
    correct = "=SUM(B2:B6)"
    options, index = choices(correct, ["=TOTAL(B2:B6)", "=SUM(B2,B6)", "=ADD(B2:B6)",
                                       "=SUM(B1:B6)"], rng)
    return {
        "prompt": f"{company} needs total units in cell B7. Which formula belongs in B7?",
        "options": options, "correct_index": index, "skill": "SUM and AutoSum",
        "explanation": ("SUM adds every cell in a range, and the colon makes B2:B6 a range. "
                        "=SUM(B2,B6) adds only the first and last row, and B1 would pull the "
                        "heading into the calculation."),
        "workbook": sheet(f"{company.split()[0]}_Units.xlsx", "Weekly Units",
                          ["Region", "Units", "Revenue"], rows + [["Total", "", ""]],
                          ["B2:B6"], "Row 7 is empty and waiting for the total."),
    }


def q_sum_value(rng):
    company = rng.choice(COMPANIES)
    months = MONTHS[: 5]
    values = [rng.randrange(1200, 9000) for _ in months]
    total = sum(values)
    rows = [[m, v] for m, v in zip(months, values)]
    wrong = [total - values[-1], total + values[0], values[0] + values[-1]]
    options, index = choices(total, wrong, rng)
    return {
        "prompt": (f"The worksheet for {company} holds =SUM(B2:B6) in cell B7. "
                   "What number appears in B7?"),
        "options": options, "correct_index": index, "skill": "Reading a SUM result",
        "explanation": (f"SUM adds the five monthly figures: "
                        f"{' + '.join(str(v) for v in values)} = {total}."),
        "workbook": sheet("Monthly_Sales.xlsx", "Sales", ["Month", "Sales"],
                          rows + [["Total", "=SUM(B2:B6)"]], ["B2:B6"]),
    }


def q_average(rng):
    products = rng.sample(PRODUCTS, 4)
    scores = [rng.randrange(60, 100) for _ in products]
    average = round(sum(scores) / len(scores), 2)
    rows = [[p, s] for p, s in zip(products, scores)]
    wrong = [max(scores), min(scores), sum(scores)]
    options, index = choices(average, wrong, rng)
    return {
        "prompt": "Cell B6 holds =AVERAGE(B2:B5). What value does it return?",
        "options": options, "correct_index": index, "skill": "AVERAGE",
        "explanation": (f"AVERAGE adds the four scores to {sum(scores)} and divides by 4, "
                        f"which gives {average}."),
        "workbook": sheet("Quality_Scores.xlsx", "Inspection", ["Product", "Score"],
                          rows + [["Average", "=AVERAGE(B2:B5)"]], ["B2:B5"]),
    }


def q_max_min(rng):
    regions = rng.sample(REGIONS, 5)
    revenue = rng.sample(range(3000, 20000, 137), 5)
    rows = [[r, money(v)] for r, v in zip(regions, revenue)]
    best = regions[revenue.index(max(revenue))]
    ask_max = rng.random() < 0.5
    if ask_max:
        correct, wrong = "=MAX(B2:B6)", ["=MIN(B2:B6)", "=LARGE(B2:B6)", "=TOP(B2:B6)"]
        prompt = "Which formula returns the highest revenue in the range B2:B6?"
        why = "MAX returns the largest number in a range. MIN returns the smallest."
    else:
        correct, wrong = "=MIN(B2:B6)", ["=MAX(B2:B6)", "=SMALL(B2:B6)", "=LOW(B2:B6)"]
        prompt = "Which formula returns the lowest revenue in the range B2:B6?"
        why = "MIN returns the smallest number in a range. MAX returns the largest."
    options, index = choices(correct, wrong, rng)
    return {
        "prompt": prompt, "options": options, "correct_index": index, "skill": "MAX and MIN",
        "explanation": f"{why} On this sheet the strongest branch is {best}.",
        "workbook": sheet("Branch_Revenue.xlsx", "Branches", ["Branch", "Revenue"], rows,
                          ["B2:B6"]),
    }


def q_count_vs_counta(rng):
    products = rng.sample(PRODUCTS, 6)
    values, numeric = [], 0
    for _ in products:
        if rng.random() < 0.65:
            values.append(rng.randrange(10, 300))
            numeric += 1
        else:
            values.append(rng.choice(["", "pending", "n/a"]))
    filled = sum(1 for v in values if v != "")
    rows = [[p, v] for p, v in zip(products, values)]
    options, index = choices(numeric, [filled, len(products), numeric + 1], rng)
    return {
        "prompt": "Cell B8 holds =COUNT(B2:B7). What number does it return?",
        "options": options, "correct_index": index, "skill": "COUNT and COUNTA",
        "explanation": (f"COUNT only counts cells holding numbers, so it returns {numeric}. "
                        f"COUNTA counts every non empty cell and would return {filled}."),
        "workbook": sheet("Stock_Check.xlsx", "Inventory", ["Product", "Units on hand"],
                          rows + [["Count", "=COUNT(B2:B7)"]], ["B2:B7"],
                          "Some cells hold text or are empty."),
    }


def q_countif(rng):
    target = rng.choice(REGIONS)
    others = [r for r in REGIONS if r != target]
    labels = [target] * rng.randrange(2, 4) + rng.sample(others, 3)
    rng.shuffle(labels)
    hits = labels.count(target)
    rows = [[label, rng.randrange(100, 900)] for label in labels]
    options, index = choices(hits, [len(labels), hits + 1, max(hits - 1, 0)], rng)
    return {
        "prompt": (f'Cell E2 holds =COUNTIF(A2:A{len(labels) + 1},"{target}"). '
                   "What number does it return?"),
        "options": options, "correct_index": index, "skill": "COUNTIF",
        "explanation": (f"COUNTIF counts the rows whose region matches {target}. "
                        f"That region appears {hits} times in column A."),
        "workbook": sheet("Order_Log.xlsx", "Orders", ["Region", "Order value"], rows,
                          [f"A2:A{len(labels) + 1}"]),
    }


def q_sumif(rng):
    target = rng.choice(REGIONS)
    others = [r for r in REGIONS if r != target]
    labels = [target, target] + rng.sample(others, 3)
    rng.shuffle(labels)
    amounts = [rng.randrange(200, 2000) for _ in labels]
    matched = sum(a for label, a in zip(labels, amounts) if label == target)
    rows = [[label, amount] for label, amount in zip(labels, amounts)]
    options, index = choices(matched, [sum(amounts), matched + amounts[0],
                                       sum(amounts) - matched], rng)
    return {
        "prompt": f'Cell E2 holds =SUMIF(A2:A6,"{target}",B2:B6). What value does it return?',
        "options": options, "correct_index": index, "skill": "SUMIF",
        "explanation": (f"SUMIF checks column A for {target} and adds only the matching "
                        f"amounts from column B, which comes to {matched}."),
        "workbook": sheet("Regional_Sales.xlsx", "Sales", ["Region", "Amount"], rows,
                          ["A2:B6"]),
    }


def q_if_function(rng):
    target = rng.randrange(500, 900, 50)
    reps = rng.sample(["Patel", "Novak", "Ruiz", "Okafor", "Klein", "Barnes"], 4)
    sales = [rng.randrange(300, 1200) for _ in reps]
    row_number = rng.randrange(2, 6)
    value = sales[row_number - 2]
    answer = "Bonus" if value >= target else "No bonus"
    rows = [[rep, s] for rep, s in zip(reps, sales)]
    options, index = choices(answer, ["No bonus" if answer == "Bonus" else "Bonus",
                                      "TRUE", "#VALUE!"], rng)
    return {
        "prompt": (f'Cell C{row_number} holds =IF(B{row_number}>={target},"Bonus","No bonus"). '
                   f"What does it display?"),
        "options": options, "correct_index": index, "skill": "IF",
        "explanation": (f"The test asks whether B{row_number}, which holds {value}, is at least "
                        f"{target}. That test is "
                        f"{'true' if value >= target else 'false'}, so IF returns "
                        f"the {'first' if value >= target else 'second'} result, {answer}."),
        "workbook": sheet("Bonus_Review.xlsx", "Team", ["Rep", "Sales", "Status"], rows,
                          [f"B{row_number}"], f"The bonus threshold is {target}."),
    }


def q_vlookup(rng):
    codes = [f"P-{100 + i}" for i in rng.sample(range(0, 9), 5)]
    names = rng.sample(PRODUCTS, 5)
    prices = [round(rng.uniform(5, 90), 2) for _ in codes]
    pick = rng.randrange(0, 5)
    answer = money(prices[pick])
    rows = [[c, n, money(p)] for c, n, p in zip(codes, names, prices)]
    wrong = [money(prices[(pick + 1) % 5]), names[pick], "#N/A"]
    options, index = choices(answer, wrong, rng)
    return {
        "prompt": (f'Cell F2 holds =VLOOKUP("{codes[pick]}",A2:C6,3,FALSE). '
                   "What does it return?"),
        "options": options, "correct_index": index, "skill": "VLOOKUP",
        "explanation": (f"VLOOKUP finds {codes[pick]} in the first column of A2:C6 and returns "
                        f"the value in the third column of that same row, which is {answer}. "
                        "FALSE forces an exact match."),
        "workbook": sheet("Price_List.xlsx", "Catalog", ["Code", "Product", "Price"], rows,
                          ["A2:C6"]),
    }


def q_absolute_reference(rng):
    rate = round(rng.uniform(0.04, 0.09), 3)
    products = rng.sample(PRODUCTS, 4)
    prices = [round(rng.uniform(10, 60), 2) for _ in products]
    rows = [[p, money(v), ""] for p, v in zip(products, prices)]
    correct = "=B3*$E$1"
    options, index = choices(correct, ["=B3*E2", "=B2*$E$1", "=$B$3*E1"], rng)
    return {
        "prompt": ("Cell C2 holds =B2*$E$1 and is copied down to C3. "
                   "What does C3 contain after the copy?"),
        "options": options, "correct_index": index,
        "skill": "Absolute and relative references",
        "explanation": ("B2 is relative, so it moves down to B3. $E$1 is absolute because of "
                        "the dollar signs, so it stays locked on the tax rate cell."),
        "workbook": sheet("Tax_Calc.xlsx", "Pricing", ["Product", "Price", "Tax"], rows,
                          ["C2", "E1"], f"Cell E1 holds the tax rate {rate}."),
    }


def q_relative_copy(rng):
    products = rng.sample(PRODUCTS, 4)
    units = [rng.randrange(5, 60) for _ in products]
    prices = [round(rng.uniform(4, 40), 2) for _ in products]
    rows = [[p, u, money(v), ""] for p, u, v in zip(products, units, prices)]
    correct = "=B4*C4"
    options, index = choices(correct, ["=B2*C2", "=B4*C2", "=$B$2*$C$2"], rng)
    return {
        "prompt": "Cell D2 holds =B2*C2 and is copied to D4. What formula sits in D4?",
        "options": options, "correct_index": index, "skill": "Relative references",
        "explanation": ("Both references are relative, so copying two rows down shifts both "
                        "of them two rows down as well."),
        "workbook": sheet("Line_Totals.xlsx", "Invoice",
                          ["Item", "Units", "Unit price", "Line total"], rows, ["D2", "D4"]),
    }


def q_margin(rng):
    company = rng.choice(COMPANIES)
    revenue = rng.randrange(8000, 40000, 100)
    cost = rng.randrange(3000, revenue - 500, 100)
    margin = round((revenue - cost) / revenue * 100, 1)
    rows = [["Revenue", money(revenue)], ["Operating cost", money(cost)], ["Margin", ""]]
    wrong = [round(cost / revenue * 100, 1), round((revenue - cost) / cost * 100, 1),
             round(revenue / cost, 1)]
    options, index = choices(f"{margin}%", [f"{w}%" for w in wrong], rng)
    return {
        "prompt": (f"{company} defines margin as (revenue minus cost) divided by revenue. "
                   "With B4 holding =(B2-B3)/B2 formatted as a percentage, what does B4 show?"),
        "options": options, "correct_index": index, "skill": "Percentage formulas",
        "explanation": (f"Revenue minus cost is {revenue - cost}. Dividing by revenue "
                        f"{revenue} gives {margin} percent. Dividing by cost instead is the "
                        "commonest mistake here."),
        "workbook": sheet("Margin_Review.xlsx", "Summary", ["Item", "Amount"], rows,
                          ["B2:B4"]),
    }


def q_order_of_operations(rng):
    a, b, c = rng.randrange(2, 20), rng.randrange(2, 12), rng.randrange(2, 9)
    correct = a + b * c
    wrong = [(a + b) * c, a * b + c, a + b + c]
    options, index = choices(correct, wrong, rng)
    return {
        "prompt": "Cell B4 holds =B1+B2*B3. What value does Excel display?",
        "options": options, "correct_index": index, "skill": "Order of operations",
        "explanation": (f"Excel multiplies before it adds, so it works out {b} times {c} "
                        f"first, which is {b * c}, then adds {a} to get {correct}. "
                        f"Brackets would be needed to add first."),
        "workbook": sheet("Calc_Practice.xlsx", "Sheet1", ["Label", "Value"],
                          [["First", a], ["Second", b], ["Third", c], ["Result", "=B1+B2*B3"]],
                          ["B1:B3"]),
    }


def q_round(rng):
    raw = round(rng.uniform(100, 999) + rng.random(), 4)
    places = rng.choice([0, 1, 2])
    correct = f"{round(raw, places):.{places}f}" if places else str(int(round(raw, 0)))
    wrong = [str(raw), f"{int(raw)}", f"{round(raw, 3):.3f}"]
    options, index = choices(correct, wrong, rng)
    return {
        "prompt": f"Cell B3 holds =ROUND(B2,{places}). What does it display?",
        "options": options, "correct_index": index, "skill": "ROUND",
        "explanation": (f"ROUND changes the stored value, not just the look of it. "
                        f"Rounding {raw} to {places} decimal places gives {correct}. "
                        "Formatting a cell would leave the underlying number untouched."),
        "workbook": sheet("Rounding.xlsx", "Sheet1", ["Label", "Value"],
                          [["Raw amount", raw], ["Rounded", f"=ROUND(B2,{places})"]], ["B2"]),
    }


def q_number_format(rng):
    rate = round(rng.uniform(0.05, 0.35), 3)
    rows = [["Growth rate", rate], ["Revenue", rng.randrange(5000, 50000)],
            ["Order date", "2026-03-14"], ["Orders", rng.randrange(20, 300)]]
    correct = "Percentage"
    options, index = choices(correct, ["Currency", "Accounting", "General"], rng)
    return {
        "prompt": (f"Cell B2 stores {rate} and the report needs it to read as a rate. "
                   "Which number format belongs on B2?"),
        "options": options, "correct_index": index, "skill": "Number formats",
        "explanation": (f"The percentage format multiplies the display by 100 and adds the "
                        f"percent sign, so {rate} reads as {rate * 100:.1f} percent. The "
                        "stored value does not change."),
        "workbook": sheet("Format_Check.xlsx", "Report", ["Item", "Value"], rows, ["B2"]),
    }


def q_autofill(rng):
    start = rng.randrange(1, 6)
    step = rng.choice([1, 2, 5])
    series = [start, start + step]
    fifth = start + step * 4
    rows = [[f"Day {series[0]}", rng.randrange(100, 900)],
            [f"Day {series[1]}", rng.randrange(100, 900)],
            ["", ""], ["", ""], ["", ""]]
    options, index = choices(f"Day {fifth}",
                             [f"Day {start + step * 3}", f"Day {series[1]}",
                              f"Day {start + 4}"], rng)
    return {
        "prompt": (f"Cells A2 and A3 hold Day {series[0]} and Day {series[1]}. "
                   "Both are selected and the fill handle is dragged down to A6. "
                   "What appears in A6?"),
        "options": options, "correct_index": index, "skill": "AutoFill",
        "explanation": (f"AutoFill reads the step between the two selected cells, which is "
                        f"{step}, and continues the pattern. A6 is four steps past the start, "
                        f"so it reads Day {fifth}. Selecting only one cell would copy it instead."),
        "workbook": sheet("Daily_Log.xlsx", "Week", ["Day", "Visits"], rows, ["A2:A3"]),
    }


def q_cell_address(rng):
    regions = rng.sample(REGIONS, 4)
    units = [rng.randrange(50, 500) for _ in regions]
    pick = rng.randrange(0, 4)
    correct = f"C{pick + 2}"
    wrong = [f"B{pick + 2}", f"C{pick + 1}", f"{pick + 2}C"]
    rows = [[i + 1, r, u] for i, (r, u) in enumerate(zip(regions, units))]
    options, index = choices(correct, wrong, rng)
    return {
        "prompt": (f"Which cell holds the unit figure {units[pick]} for the "
                   f"{regions[pick]} branch?"),
        "options": options, "correct_index": index, "skill": "Cell addresses",
        "explanation": ("A cell address is the column letter followed by the row number. "
                        f"Units sit in column C, and the {regions[pick]} branch is on "
                        f"row {pick + 2} because row 1 holds the headings."),
        "workbook": sheet("Branch_Units.xlsx", "Units", ["No.", "Branch", "Units"], rows,
                          [correct]),
    }


def q_tool_choice(rng):
    scenario, correct, wrong = rng.choice([
        ("The manager wants to see only the orders above 500 without deleting anything.",
         "Filter", ["Sort", "Freeze Panes", "Wrap Text"]),
        ("The manager wants the branch list arranged from highest revenue to lowest.",
         "Sort", ["Filter", "AutoSum", "Merge Cells"]),
        ("The headings scroll off the screen on a long list and need to stay visible.",
         "Freeze Panes", ["Wrap Text", "Filter", "Merge Cells"]),
        ("Every cell below target should turn red automatically as figures are typed.",
         "Conditional formatting", ["Cell Styles", "Sort", "AutoFill"]),
        ("A long heading makes one column far too wide to print.",
         "Wrap Text", ["Merge Cells", "Freeze Panes", "AutoSum"]),
    ])
    rows = [[rng.choice(REGIONS), rng.randrange(100, 900), money(rng.randrange(500, 9000))]
            for _ in range(5)]
    options, index = choices(correct, wrong, rng)
    return {
        "prompt": f"{scenario} Which Excel tool does the job?",
        "options": options, "correct_index": index, "skill": "Worksheet tools",
        "explanation": (f"{correct} is built for exactly this. The other three change something "
                        "else about the sheet and would leave the manager's question unanswered."),
        "workbook": sheet("Branch_Report.xlsx", "Report", ["Branch", "Orders", "Revenue"], rows),
    }


def q_error_value(rng):
    error, meaning, wrong = rng.choice([
        ("#DIV/0!", "a formula divided by an empty cell or by zero",
         ["The column is too narrow", "The formula name is misspelled", "A cell holds text"]),
        ("#NAME?", "Excel does not recognise the function name, usually a spelling slip",
         ["A number was divided by zero", "The column is too narrow", "A range is missing"]),
        ("#####", "the column is too narrow to display the value",
         ["The formula divided by zero", "The function name is wrong", "The cell holds text"]),
        ("#VALUE!", "the formula points at text where it expects a number",
         ["The column is too narrow", "A range was deleted", "The workbook is read only"]),
    ])
    rows = [[rng.choice(PRODUCTS), rng.randrange(10, 80), error] for _ in range(4)]
    options, index = choices(meaning[0].upper() + meaning[1:], wrong, rng)
    return {
        "prompt": f"Column C shows {error}. What has gone wrong?",
        "options": options, "correct_index": index, "skill": "Reading Excel errors",
        "explanation": f"{error} means {meaning}. Fix the cause rather than deleting the formula.",
        "workbook": sheet("Error_Check.xlsx", "Sheet1", ["Item", "Units", "Result"], rows,
                          ["C2:C5"]),
    }


# What each question is about, so a quiz can be drawn from the section the student just
# read rather than from Excel in general. The words are matched against the module text.
TOPIC_KEYWORDS = {
    "q_sum_formula": ["sum", "autosum", "total", "add"],
    "q_sum_value": ["sum", "total", "add", "column"],
    "q_average": ["average", "mean"],
    "q_max_min": ["max", "min", "largest", "smallest", "highest", "lowest"],
    "q_count_vs_counta": ["count", "counta", "blank", "empty", "missing"],
    "q_countif": ["countif", "condition", "criteria", "how many"],
    "q_sumif": ["sumif", "condition", "criteria", "region", "category"],
    "q_if_function": ["if", "logical", "true", "false", "test", "condition"],
    "q_vlookup": ["vlookup", "lookup", "xlookup", "index", "match", "table"],
    "q_absolute_reference": ["absolute", "dollar", "$", "lock", "copy", "reference"],
    "q_relative_copy": ["relative", "copy", "fill", "reference"],
    "q_margin": ["percentage", "percent", "margin", "rate", "ratio"],
    "q_order_of_operations": ["order of operations", "bracket", "parenthes", "operator",
                              "multipl", "precedence"],
    "q_round": ["round", "decimal", "rounding"],
    "q_number_format": ["format", "currency", "percentage", "decimal", "date"],
    "q_autofill": ["autofill", "fill handle", "pattern", "series", "drag"],
    "q_cell_address": ["cell", "address", "row", "column", "range", "workbook", "worksheet"],
    "q_tool_choice": ["sort", "filter", "freeze", "conditional formatting", "wrap", "table"],
    "q_error_value": ["error", "#div", "#name", "#value", "#ref", "n/a"],
}


def score_template(template, text: str) -> int:
    """How many of a template's topic words appear in the section the quiz is for."""
    lowered = (text or "").lower()
    if not lowered:
        return 0
    from . import business  # imported here because business imports this module

    words = TOPIC_KEYWORDS.get(template.__name__) or business.BUSINESS_TOPICS.get(
        template.__name__, []
    )
    return sum(1 for word in words if word in lowered)


def choose_templates(pool: list, count: int, rng: random.Random, text: str = "") -> list:
    """Take the templates this section is actually about, then fill up at random.

    With no text to go on, or a section that matches nothing in the bank, this is the same
    random draw as before, so a quiz always has its full set of questions.
    """
    scored = [(score_template(template, text), rng.random(), template) for template in pool]
    matching = [item for item in scored if item[0] > 0]
    matching.sort(key=lambda item: (-item[0], item[1]))
    picked = [item[2] for item in matching[:count]]
    if len(picked) < count:
        rest = [template for template in pool if template not in picked]
        rng.shuffle(rest)
        picked += rest[: count - len(picked)]
    rng.shuffle(picked)
    return picked[:count]


TEMPLATES = [
    q_sum_formula, q_sum_value, q_average, q_max_min, q_count_vs_counta, q_countif,
    q_sumif, q_if_function, q_vlookup, q_absolute_reference, q_relative_copy, q_margin,
    q_order_of_operations, q_round, q_number_format, q_autofill, q_cell_address,
    q_tool_choice, q_error_value,
]

QUESTIONS_PER_QUIZ = 7          # multiple choice questions
BUSINESS_PER_QUIZ = 3           # long typed answer questions after them
TOTAL_PER_QUIZ = QUESTIONS_PER_QUIZ + BUSINESS_PER_QUIZ


def generate_questions(count: int = QUESTIONS_PER_QUIZ, seed: int | None = None,
                       context: str = "", source_text: str = "") -> list[dict]:
    """Return `count` questions on the topic of this section, with fresh data each time."""
    rng = random.Random(seed)
    picked = choose_templates(TEMPLATES, count, rng, f"{context} {source_text}")
    while len(picked) < count:
        picked.append(rng.choice(TEMPLATES))
    questions = []
    for position, template in enumerate(picked, start=1):
        question = template(rng)
        question["order"] = position
        question["kind"] = "MCQ"
        question["context"] = context
        questions.append(question)
    return questions
