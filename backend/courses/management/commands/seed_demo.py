"""Create a faculty account, a student account and a sample MIS 3000 course."""
import os
import tempfile

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from courses.extraction import extract
from courses.models import (
    Approval, Book, Chapter, Course, Enrollment, Invitation, Module,
)

SAMPLE_BOOK = """Excel for Business Decisions

Chapter 1: Preparing Business Data in Excel
A spreadsheet is not finished merely because it contains the correct numbers. A useful
business worksheet lets another person work out what the data represents, how the values
are measured and where to find the important result.

Module 1: Workbooks, worksheets and cells
A workbook is the file. A worksheet is one tab inside that file. A cell is the box where a
column and a row meet, and its address is the column letter followed by the row number.
Name every worksheet after its content rather than leaving it as Sheet1, because a colleague
opening the file six months later has only those names to go on.

Module 2: Entering and extending data
Press Enter to move down a column and Tab to move across a row. AUTOFILL extends a pattern
when you select the first two values and drag the fill handle, so day 1 and day 2 become a
full week. Always inspect the result, because AutoFill copies a value when it cannot see a
pattern.

Module 3: Formats that carry meaning
Currency belongs on money, percentage belongs on rates and whole numbers belong on counts.
Formatting changes how a value appears, not the value stored underneath. Use the same number
of decimal places inside one column so the figures line up when a manager scans them.

Chapter 2: Formulas, Functions and Cell References
Every formula starts with an equals sign. Excel multiplies and divides before it adds and
subtracts, so brackets decide the answer more often than students expect.

Module 1: Building formulas
A formula points at cells rather than repeating numbers, which is what lets one change flow
through the whole worksheet. AUTOSUM writes a SUM formula under the column you selected, but
you still check the highlighted range before accepting it.

Module 2: Relative and absolute references
A RELATIVE REFERENCE shifts when the formula is copied. An ABSOLUTE REFERENCE is locked with
dollar signs, so $E$1 keeps pointing at the tax rate no matter where the formula lands. Mixing
the two wrongly is the single commonest cause of a spreadsheet that looks right and is not.

Module 3: The core functions
SUM adds a range. AVERAGE finds the mean. MIN and MAX return the smallest and largest values.
COUNT counts numbers while COUNTA counts anything that is not empty, and the gap between those
two answers usually means missing data.

Chapter 3: Analysis and Management Reporting
Numbers earn their keep only when someone can act on them, so the last step of any analysis is
a sentence a manager can use.

Module 1: Conditional logic
IF returns one answer when a test is true and another when it is false. COUNTIF counts the rows
that meet a condition and SUMIF adds only the matching amounts, which is how a branch report
answers a question about one region without deleting the other rows.

Module 2: Lookups
VLOOKUP finds a value in the first column of a table and returns something beside it. The final
argument FALSE forces an exact match, and leaving it out is what produces answers that are almost
right.

Module 3: Presenting the result
SORT arranges rows, FILTER hides the ones that do not matter and CONDITIONAL FORMATTING colours
cells against a rule. A CHART shows the shape of the numbers. Finish with one sentence naming the
branch that needs management attention and the evidence behind it.
"""


class Command(BaseCommand):
    help = "Seed a demo faculty, student, course and book."

    def handle(self, *args, **options):
        faculty, created = User.objects.get_or_create(
            email="faculty@mis3000.edu",
            defaults={"name": "Dr Vikram", "role": User.Role.FACULTY},
        )
        if created:
            faculty.set_password("faculty123")
            faculty.save()
        student, created = User.objects.get_or_create(
            email="student@mis3000.edu",
            defaults={"name": "Asha Patel", "role": User.Role.STUDENT},
        )
        if created:
            student.set_password("student123")
            student.save()

        admin, created = User.objects.get_or_create(
            email="admin@mis3000.edu",
            defaults={"name": "Platform Admin", "role": User.Role.ADMIN,
                      "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin123")
            admin.save()

        course, _ = Course.objects.get_or_create(
            code="MIS3000",
            defaults={
                "name": "Excel Fundamentals for Business",
                "description": "Excel mechanics taught through realistic business situations.",
                "faculty": faculty,
            },
        )
        Invitation.objects.get_or_create(
            course=course, email=student.email,
            defaults={"invited_by": faculty, "status": Invitation.Status.ACCEPTED},
        )
        Enrollment.objects.get_or_create(course=course, student=student)

        if not course.books.exists():
            # A temporary file the operating system chooses, so this runs on Windows and
            # macOS as happily as on Linux. /tmp does not exist on Windows.
            with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", encoding="utf-8", delete=False
            ) as handle:
                handle.write(SAMPLE_BOOK)
                path = handle.name
            try:
                result = extract(path, "sample_excel_book.txt", use_model=False)
            finally:
                os.unlink(path)
            book = Book.objects.create(
                course=course, title="Excel for Business Decisions",
                file=ContentFile(SAMPLE_BOOK.encode(), name="sample_excel_book.txt"),
                kind="txt", extraction_note=result["note"],
                character_count=result["character_count"],
            )
            for chapter_data in result["chapters"]:
                chapter = Chapter.objects.create(
                    book=book, number=chapter_data["number"],
                    title=chapter_data["title"], raw_text=chapter_data["raw_text"],
                )
                for module_data in chapter_data["modules"]:
                    Module.objects.create(
                        chapter=chapter, number=module_data["number"],
                        title=module_data["title"], raw_text=module_data["raw_text"],
                    )
            # The demo book arrives already approved and published, so the sample course
            # is readable straight away. Anything uploaded later starts as a draft.
            now = timezone.now()
            book.chapters.update(status=Approval.PUBLISHED, published_at=now)
            Module.objects.filter(chapter__book=book).update(status=Approval.PUBLISHED)
            self.stdout.write(self.style.SUCCESS(
                f"Book stored with {book.chapters.count()} published chapters."
            ))

        self.stdout.write(self.style.SUCCESS(
            "Demo ready. admin@mis3000.edu / admin123, faculty@mis3000.edu / faculty123 "
            "and student@mis3000.edu / student123"
        ))
