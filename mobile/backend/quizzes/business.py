"""Long business questions where the student works in the sheet and types the answer.

These sit after the seven multiple choice questions and carry no options. The student
selects cells, sorts a column, applies SUM, AVERAGE, MIN, MAX or a formula of their own
in the worksheet beside the question, then types what they found. Marking compares the
typed value against the expected one within a tolerance, so $12,480.00 and 12480 both
count as right.
"""
from __future__ import annotations

import random

from .generator import COMPANIES, PRODUCTS, REGIONS, choose_templates, money, sheet

BUSINESS_PER_QUIZ = 3


def _rows(pairs):
    return [list(map(str, row)) for row in pairs]


# --------------------------------------------------------------------------- templates

def b_top_three_revenue(rng):
    company = rng.choice(COMPANIES)
    branches = rng.sample(REGIONS, 8)
    revenue = rng.sample(range(18000, 96000, 373), 8)
    orders = [rng.randrange(120, 900) for _ in branches]
    ranked = sorted(revenue, reverse=True)
    answer = sum(ranked[:3])
    rows = _rows([[b, r, o] for b, r, o in zip(branches, revenue, orders)])
    return {
        "skill": "Sorting and SUM",
        "prompt": (
            f"{company} is preparing the quarterly review pack. The board wants to know how much "
            "of the quarter's revenue came from the three strongest branches, because the "
            "marketing budget for next quarter is being split between those three and everyone "
            "else.\n\n"
            "Work in the sheet beside this question. Select the Revenue column, sort it from "
            "largest to smallest so the strongest branches move to the top, then select the top "
            "three revenue figures and read the Sum from the status bar under the sheet.\n\n"
            "What is the combined revenue of the three strongest branches?"
        ),
        "expected": answer,
        "format": "currency",
        "tolerance": 1,
        "steps": "Sort Revenue descending, select the top three revenue cells, read Sum.",
        "explanation": (
            f"Sorted from largest to smallest the top three revenue figures are "
            f"{ranked[0]:,}, {ranked[1]:,} and {ranked[2]:,}. Their sum is {answer:,}. "
            "Sorting first matters because the sheet arrives in branch order, not in size order, "
            "so the three largest are not the three at the top when you open it."
        ),
        "workbook": sheet(
            f"{company.split()[0]}_Quarterly.xlsx", "Branches",
            ["Branch", "Revenue", "Orders"], rows, [], "Sort this list before you total anything.",
        ),
    }


def b_average_without_worst(rng):
    company = rng.choice(COMPANIES)
    months = ["January", "February", "March", "April", "May", "June",
              "July", "August", "September"]
    sales = [rng.randrange(9000, 42000, 137) for _ in months]
    worst = min(sales)
    kept = [value for value in sales if value != worst]
    answer = round(sum(kept) / len(kept), 2)
    rows = _rows([[m, s] for m, s in zip(months, sales)])
    return {
        "skill": "AVERAGE, MIN and exclusions",
        "prompt": (
            f"The owner of {company} thinks one very bad month is dragging the year's average "
            "down and making the shop look weaker than it is. Before the bank meeting she wants "
            "the average monthly sales figure with that single worst month left out, so she can "
            "show both numbers and explain the gap.\n\n"
            "In the sheet, select the Sales column and read the Min from the status bar to find "
            "the worst month. Then work out the average of the remaining eight months, either by "
            "selecting those eight cells and reading Average, or by writing a formula such as "
            "=(SUM(B2:B10)-MIN(B2:B10))/8 in an empty cell.\n\n"
            "What is the average monthly sales figure once the worst month is excluded? Give it "
            "to two decimal places."
        ),
        "expected": answer,
        "format": "currency",
        "tolerance": 1,
        "steps": "Find MIN, subtract it from the total, divide by eight.",
        "explanation": (
            f"The worst month is {worst:,}. Taking it out of the total of {sum(sales):,} leaves "
            f"{sum(kept):,} across eight months, which averages {answer:,.2f}. AVERAGE over all "
            f"nine months gives {sum(sales) / 9:,.2f}, and the gap between the two is the number "
            "the owner actually wants to talk about."
        ),
        "workbook": sheet(
            "Monthly_Sales.xlsx", "This Year", ["Month", "Sales"], rows, [],
            "Nine months of trading. One of them is the problem.",
        ),
    }


def b_lowest_margin(rng):
    company = rng.choice(COMPANIES)
    branches = rng.sample(REGIONS, 6)
    revenue = [rng.randrange(20000, 70000, 211) for _ in branches]
    cost = [int(r * rng.uniform(0.58, 0.93)) for r in revenue]
    margins = [round((r - c) / r * 100, 1) for r, c in zip(revenue, cost)]
    answer = min(margins)
    weakest = branches[margins.index(answer)]
    rows = _rows([[b, r, c, ""] for b, r, c in zip(branches, revenue, cost)])
    return {
        "skill": "Percentage formulas and MIN",
        "prompt": (
            f"{company} measures branch health with margin, defined as revenue minus operating "
            "cost, divided by revenue. Two branches turn over a lot of money and keep very little "
            "of it, and the operations manager wants the weakest one named before the Monday "
            "meeting rather than a table she has to read herself.\n\n"
            "In the sheet, fill the Margin column. Put =(B2-C2)/B2 in D2 and copy it down to D7, "
            "then select D2:D7 and read the Min from the status bar.\n\n"
            "What is the lowest branch margin, written as a percentage to one decimal place?"
        ),
        "expected": answer,
        "format": "percent",
        "tolerance": 0.2,
        "steps": "Build the margin column with =(B2-C2)/B2, copy it down, take the minimum.",
        "explanation": (
            f"The weakest branch is {weakest} at {answer} percent. Dividing by cost instead of "
            "revenue is the usual slip and gives a larger, flattering number that means something "
            "else entirely."
        ),
        "workbook": sheet(
            "Margin_Review.xlsx", "Branches",
            ["Branch", "Revenue", "Operating cost", "Margin"], rows, ["D2"],
            "Column D is empty and waiting for your formula.",
        ),
    }


def b_region_total(rng):
    company = rng.choice(COMPANIES)
    target = rng.choice(REGIONS)
    others = [r for r in REGIONS if r != target]
    labels = [target] * rng.randrange(3, 5) + rng.sample(others, 5)
    rng.shuffle(labels)
    amounts = [rng.randrange(400, 6400, 37) for _ in labels]
    answer = sum(a for label, a in zip(labels, amounts) if label == target)
    rows = _rows([[f"ORD-{2400 + i}", label, amount] for i, (label, amount) in
                  enumerate(zip(labels, amounts))])
    return {
        "skill": "SUMIF and filtering",
        "prompt": (
            f"An order log has come across from the {company} sales desk with every region mixed "
            f"together. Finance only needs the {target} figure, and deleting the other rows is not "
            "an option because the same file goes to three other people afterwards.\n\n"
            "Work in the sheet without removing anything. Either write "
            f'=SUMIF(B2:B10,"{target}",C2:C10) in an empty cell, or sort by Region so the '
            f"{target} rows sit together and select just those order values to read the Sum.\n\n"
            f"What is the total order value for the {target} region?"
        ),
        "expected": answer,
        "format": "currency",
        "tolerance": 1,
        "steps": f'Use =SUMIF(B2:B10,"{target}",C2:C10), or sort and select.',
        "explanation": (
            f"There are {labels.count(target)} {target} orders in the log and they add up to "
            f"{answer:,}. SUMIF is the safer route here because it leaves the file exactly as the "
            "next person expects to find it."
        ),
        "workbook": sheet(
            "Order_Log.xlsx", "Orders", ["Order", "Region", "Order value"], rows, [],
            "Every region is in this list. Only one of them is being asked about.",
        ),
    }


def b_reorder_count(rng):
    company = rng.choice(COMPANIES)
    products = rng.sample(PRODUCTS, 9)
    on_hand = [rng.randrange(0, 260, 7) for _ in products]
    reorder = [rng.randrange(40, 200, 5) for _ in products]
    answer = sum(1 for h, r in zip(on_hand, reorder) if h < r)
    rows = _rows([[p, h, r] for p, h, r in zip(products, on_hand, reorder)])
    return {
        "skill": "IF, COUNTIF and comparisons",
        "prompt": (
            f"The stockroom at {company} runs a Monday check against the reorder points agreed "
            "with the buyer. Anything sitting below its reorder point has to go on the purchase "
            "order that afternoon, and the buyer wants a count first so she knows whether this is "
            "a five minute job or a real order.\n\n"
            "In the sheet, compare each product's units on hand against its reorder point. You "
            'can put =IF(B2<C2,1,0) in D2 and copy it down, then sum column D, or write '
            "=SUMPRODUCT((B2:B10<C2:C10)*1) in one cell.\n\n"
            "How many products need to be reordered this week?"
        ),
        "expected": answer,
        "format": "number",
        "tolerance": 0,
        "steps": "Compare column B against column C row by row and count the rows where B is lower.",
        "explanation": (
            f"{answer} of the nine products sit below their reorder point. A plain COUNTIF will "
            "not do this on its own, because the threshold is different on every row rather than "
            "one fixed number, which is exactly when a helper column earns its place."
        ),
        "workbook": sheet(
            "Stock_Check.xlsx", "Inventory",
            ["Product", "Units on hand", "Reorder point"], rows, [],
            "Each product has its own reorder point.",
        ),
    }


def b_order_value(rng):
    company = rng.choice(COMPANIES)
    products = rng.sample(PRODUCTS, 6)
    prices = [round(rng.uniform(6, 74), 2) for _ in products]
    units = [rng.randrange(3, 90) for _ in products]
    answer = round(sum(u * p for u, p in zip(units, prices)), 2)
    rows = _rows([[p, u, f"{price:.2f}", ""] for p, u, price in zip(products, units, prices)])
    return {
        "skill": "Multiplication down a column and SUM",
        "prompt": (
            f"A purchase order for {company} has arrived with quantities and unit prices but no "
            "line totals and no order total, and accounts payable will not process it in that "
            "state. You have been asked to finish it before it goes back.\n\n"
            "In the sheet, put =B2*C2 in D2 and copy it down to D7 so every line has its own "
            "total. Then select D2:D7 and read the Sum from the status bar, or write "
            "=SUM(D2:D7) underneath.\n\n"
            "What is the total value of this purchase order? Give it to two decimal places."
        ),
        "expected": answer,
        "format": "currency",
        "tolerance": 0.5,
        "steps": "Build line totals with =B2*C2, copy down, then sum the column.",
        "explanation": (
            f"The six line totals add up to {answer:,.2f}. Multiplying the total units by the "
            "average price is the shortcut people reach for here, and it gives a different answer "
            "whenever the prices are not all the same."
        ),
        "workbook": sheet(
            "Purchase_Order.xlsx", "PO", ["Item", "Units", "Unit price", "Line total"], rows,
            ["D2:D7"], "Column D is empty. Nothing has been totalled yet.",
        ),
    }


def b_growth_percent(rng):
    company = rng.choice(COMPANIES)
    branches = rng.sample(REGIONS, 6)
    last_year = [rng.randrange(14000, 62000, 173) for _ in branches]
    this_year = [int(v * rng.uniform(0.78, 1.34)) for v in last_year]
    growth = [round((t - l) / l * 100, 1) for l, t in zip(last_year, this_year)]
    answer = max(growth)
    best = branches[growth.index(answer)]
    rows = _rows([[b, l, t, ""] for b, l, t in zip(branches, last_year, this_year)])
    return {
        "skill": "Percentage change and MAX",
        "prompt": (
            f"{company} is deciding where to put a second delivery van next year. Raw revenue "
            "favours the big branches automatically, so the decision is being made on growth "
            "instead: which branch improved the most against its own last year.\n\n"
            "In the sheet, put =(C2-B2)/B2 in D2 and copy it down to D7, then select D2:D7 and "
            "read the Max from the status bar.\n\n"
            "What is the highest growth rate, written as a percentage to one decimal place?"
        ),
        "expected": answer,
        "format": "percent",
        "tolerance": 0.2,
        "steps": "Percentage change is (this year minus last year) divided by last year.",
        "explanation": (
            f"{best} grew {answer} percent, which is the largest change in the list. Dividing by "
            "this year rather than last year is the common error and understates every positive "
            "change in the column."
        ),
        "workbook": sheet(
            "Growth_Review.xlsx", "Branches",
            ["Branch", "Last year", "This year", "Growth"], rows, ["D2"],
            "Growth is measured against each branch's own last year.",
        ),
    }


def b_range_spread(rng):
    company = rng.choice(COMPANIES)
    reps = rng.sample(["Patel", "Novak", "Ruiz", "Okafor", "Klein", "Barnes", "Adeyemi", "Sato"], 7)
    sales = rng.sample(range(2400, 19000, 149), 7)
    answer = max(sales) - min(sales)
    rows = _rows([[r, s] for r, s in zip(reps, sales)])
    return {
        "skill": "MAX, MIN and the spread",
        "prompt": (
            f"The sales manager at {company} is arguing for a change to the commission scheme. "
            "Her case rests on how far apart the best and worst performing representatives are, "
            "because a wide gap suggests territory rather than effort is doing the work.\n\n"
            "In the sheet, select the Sales column and read Max and Min from the status bar, or "
            "write =MAX(B2:B8)-MIN(B2:B8) in an empty cell.\n\n"
            "What is the gap between the highest and the lowest sales figure?"
        ),
        "expected": answer,
        "format": "currency",
        "tolerance": 1,
        "steps": "Subtract the smallest value in the column from the largest.",
        "explanation": (
            f"The highest figure is {max(sales):,} and the lowest is {min(sales):,}, so the "
            f"spread is {answer:,}. The average tells you nothing about this gap, which is why "
            "the manager asked for the spread rather than the mean."
        ),
        "workbook": sheet(
            "Team_Sales.xlsx", "Team", ["Representative", "Sales"], rows, [],
            "Seven representatives, one quarter.",
        ),
    }


def b_best_per_order(rng):
    company = rng.choice(COMPANIES)
    branches = rng.sample(REGIONS, 6)
    orders = [rng.randrange(90, 700) for _ in branches]
    revenue = [o * rng.randrange(28, 140) for o in orders]
    per_order = [r / o for r, o in zip(revenue, orders)]
    answer = branches[per_order.index(max(per_order))]
    rows = _rows([[b, o, r, ""] for b, o, r in zip(branches, orders, revenue)])
    return {
        "skill": "Derived measures and ranking",
        "prompt": (
            f"{company} wants to know which branch gets the most out of each order it takes, not "
            "which one takes the most orders. A branch with a small number of large orders can "
            "beat a busy branch that sells cheap items all day, and the two look identical in a "
            "revenue table.\n\n"
            "In the sheet, put =C2/B2 in D2 and copy it down to D7 to get revenue per order. Then "
            "sort the sheet by column D from largest to smallest and look at which branch is now "
            "on top.\n\n"
            "Which branch has the highest revenue per order? Type the branch name."
        ),
        "expected": answer,
        "format": "text",
        "tolerance": 0,
        "steps": "Divide revenue by orders, then sort that column descending.",
        "explanation": (
            f"{answer} earns the most per order at "
            f"{max(per_order):,.2f} against an order count that is not the largest in the list. "
            "This is the question MAX on its own cannot answer, because MAX returns the value and "
            "the manager asked for the name."
        ),
        "workbook": sheet(
            "Per_Order.xlsx", "Branches",
            ["Branch", "Orders", "Revenue", "Revenue per order"], rows, ["D2"],
            "Column D is empty. Build it before you sort.",
        ),
    }


# The same topic matching as the multiple choice bank, so the long questions come from
# the section the student just read.
BUSINESS_TOPICS = {
    "b_top_three_revenue": ["sort", "sum", "total", "rank", "largest", "order"],
    "b_average_without_worst": ["average", "mean", "min", "exclude", "smallest"],
    "b_lowest_margin": ["percentage", "percent", "margin", "min", "ratio", "rate"],
    "b_region_total": ["sumif", "condition", "criteria", "filter", "category", "region"],
    "b_reorder_count": ["if", "count", "countif", "condition", "compare", "logical"],
    "b_order_value": ["multipl", "line total", "sum", "formula", "copy", "fill"],
    "b_growth_percent": ["percentage", "percent", "growth", "change", "max"],
    "b_range_spread": ["max", "min", "range", "spread", "largest", "smallest"],
    "b_best_per_order": ["divide", "ratio", "per", "sort", "index", "match", "rank"],
}

BUSINESS_TEMPLATES = [
    b_top_three_revenue, b_average_without_worst, b_lowest_margin, b_region_total,
    b_reorder_count, b_order_value, b_growth_percent, b_range_spread, b_best_per_order,
]


def add_answer_cell(question: dict) -> dict:
    """Give every business sheet a labelled answer cell at the bottom.

    Whatever the student puts in that cell, a typed number or a formula such as
    =SUM(B2:B9), is read straight back into the question as their answer.
    """
    book = question["workbook"]
    width = max(len(row) for row in book["rows"])
    book["rows"] = [list(row) + [""] * (width - len(row)) for row in book["rows"]]
    book["rows"].append([""] * width)
    label_row = [""] * width
    label_row[0] = "YOUR ANSWER"
    book["rows"].append(label_row)

    answer_row = len(book["rows"])          # one based, the row just appended
    answer_cell = f"B{answer_row}"
    book["answer_cell"] = answer_cell
    book["note"] = (
        (book.get("note", "") + " ").strip() +
        f" Put your result in {answer_cell}. It is read back into the question as you type."
    ).strip()
    question["answer_cell"] = answer_cell
    question["prompt"] = (
        question["prompt"]
        + f"\n\nPut your result in cell {answer_cell} of the sheet, either as a number you have "
          "read off the status bar or as a formula. It is picked up as your answer "
          "automatically, and you can check it before you move on."
    )
    return question


def generate_business_questions(count: int = BUSINESS_PER_QUIZ, seed: int | None = None,
                                start_order: int = 8, context: str = "",
                                source_text: str = "") -> list[dict]:
    """Three long questions on this section's topic, each with fresh figures."""
    rng = random.Random(seed)
    picked = choose_templates(BUSINESS_TEMPLATES, count, rng, f"{context} {source_text}")
    questions = []
    for offset, template in enumerate(picked):
        question = add_answer_cell(template(rng))
        question["order"] = start_order + offset
        question["kind"] = "BUSINESS"
        question["context"] = context
        questions.append(question)
    return questions


# --------------------------------------------------------------------------- marking

def _as_number(text: str):
    cleaned = str(text).strip().replace(",", "").replace("$", "").replace("%", "")
    cleaned = cleaned.replace("(", "-").replace(")", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def grade_typed_answer(typed: str, expected: str, answer_format: str, tolerance: float) -> bool:
    """A typed answer is right if it means the same thing, not if it looks the same.

    $12,480.00, 12480 and 12480.00 all pass. A percentage passes whether the student
    types 18.5 or 0.185, because both are what Excel shows depending on the format.
    """
    typed = (typed or "").strip()
    if not typed:
        return False
    if answer_format == "text":
        return typed.casefold() == str(expected).strip().casefold()

    given = _as_number(typed)
    want = _as_number(expected)
    if given is None or want is None:
        return False
    if abs(given - want) <= max(tolerance, 0.0001):
        return True
    # A percentage typed as a decimal, or the other way round.
    if answer_format == "percent":
        for scaled in (given * 100, given / 100):
            if abs(scaled - want) <= max(tolerance, 0.0001):
                return True
    return False
