# MIS 3000 Excel Learning Platform

A faculty and student learning platform for an Excel course. Faculty create courses, upload
the textbook in PDF, Word, PowerPoint or plain text, and the platform pulls the real text out
of it, finds the chapters, splits each chapter into modules and writes a plain English
explanation of anything a person taps. Students join a course with its course code, read those
explanations, and take seven question Excel quizzes where each question comes with its own
worksheet shown beside it.

React Native (Expo) on the front, Django REST Framework on the back, SQLite for storage, and a
local Ollama model for the explanations. Nothing calls a paid API and no API key is needed.

---

## 1. What you need installed

Python 3.10 or newer, Node 18 or newer, and Ollama from https://ollama.com/download.
Expo Go on your phone if you want to run the app on a real device.

## 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 0.0.0.0:8000
```

`seed_demo` creates two accounts and one course with a book already split into chapters and
modules, so you can see the whole flow before uploading anything of your own.

| Role | Email | Password |
| --- | --- | --- |
| Admin | admin@mis3000.edu | admin123 |
| Faculty | faculty@mis3000.edu | faculty123 |
| Student | student@mis3000.edu | student123 |

Everything is written to `backend/db.sqlite3`, so accounts, uploads, quiz papers and marks
survive a restart. Uploaded books are kept under `backend/media/books/`.

An optional Django admin account: `python manage.py createsuperuser`, then http://127.0.0.1:8000/admin/

## 3. Ollama, in a second terminal

```bash
ollama serve
ollama pull llama3.1:8b
```

Then confirm the platform can see it:

```bash
cd backend
python manage.py check_ollama
```

That prints whether the model answered and shows one sample explanation. A smaller machine can
use `ollama pull llama3.2:3b` instead and point the platform at it:

```bash
export OLLAMA_MODEL=llama3.2:3b       # Windows: set OLLAMA_MODEL=llama3.2:3b
```

Other settings you can override the same way: `OLLAMA_HOST` (default `http://127.0.0.1:11434`),
`OLLAMA_TIMEOUT` (seconds), and `USE_OLLAMA=0` to switch the model off entirely.

If Ollama is not running, explanations still appear. The platform falls back to a built in
writer that scores the sentences in the extracted text, simplifies the wording, lists the Excel
functions it found and closes with a practice step. The Profile screen in the app says which of
the two wrote what you are reading.

## 4. Mobile app

```bash
cd mobile
npm install
npx expo start
```

Press `w` for a browser, `a` for an Android emulator, or scan the QR code with Expo Go.

Set the server address once in `mobile/src/api/client.js`. The web build and Android emulator
are already handled (`127.0.0.1` and `10.0.2.2`). For a real phone, put your laptop's LAN
address in `LAN_ADDRESS`, for example `http://192.168.1.24:8000`, and keep both devices on the
same network.

---

## 5. Two ways to build a course

When a faculty member creates a course the platform asks one question first: do you already
have the content? Both paths ask for the course code and name.

Answer yes and the course opens on the upload panel, which is the original route. Upload the
book as PDF, Word, PowerPoint or text, and the chapters and modules are pulled out of it.

Answer no and the course opens on the build panel instead. Add whatever you do have, lecture
slides, a montage, screenshots, a handout, or nothing but a list of topic names typed into the
box. Headings are read out of the material, the biggest line on each slide being treated as its
heading, and they become the chapter and module structure. Each module's prose is then written
by the local Ollama model against the surrounding lecture text, or by the built in writer when
Ollama is not running. The finished book is stored exactly like an uploaded one, so chapters,
modules, explanations and quizzes all behave the same afterwards. An image carries no readable
text, so name image files after the topic they cover, or type the topics in.

Building a book runs one model call per module, so a six chapter course takes a few minutes.
The book card afterwards says which writer produced it and which files it came from.

## 6. Who can take a course

Faculty have an Access provision section in the sidebar. Pick a course, paste in the student
email addresses, one per line or separated by commas, and each one appears with its status:
waiting, accepted or declined. An address can be added before that student has an account.
Removing an address takes the course away again.

Students have a Courses provided section. Every course opened to their email address shows up
there with the instructor's name, and accepting it enrols them. The course code dropdown still
works, but it now lists only courses that have been opened to them, and joining by code without
an invitation is refused.

## 7. What each login can do

Faculty sidebar holds Dashboard, Course, Access provision and Profile.

Dashboard shows every course they teach with the number of students enrolled, the course wise
average mark, which is the marks earned over the marks available rather than an average of
percentages, how many quizzes have been taken, and the chapter and module counts. Course lets
them create a course with a code and a name, upload a book, expand the chapter and module tree,
open any section to read the explanation, preview a generated quiz with the answers marked, see
the roster and see each student's marks. Profile handles the name, the model status and signing
out.

Student sidebar holds Dashboard, Courses provided, Course, Feedback and Profile.

Dashboard shows the marks course by course with the average, the best attempt and the recent
quizzes. Course starts with a dropdown of the course codes faculty have created; the student
picks one, joins, and the chapters and modules open up, each tappable for its explanation and
each with its own quiz. Feedback is course wise: the overall percentage, a skill by skill
breakdown built from every question answered, a list of quizzes taken, and a box for sending a
comment to the instructor.

## 8. How the book is taken apart

`backend/courses/extraction.py` holds the whole engine. Each format has its own reader, pypdf
for PDF, python-docx for Word including tables, python-pptx for slides, plus plain text, and
all of them return the same list of blocks, so the splitters never care where the text came
from. Chapters are found from headings such as `Chapter 3`, `Unit II`, `Part Four` and from
Word Heading 1 styles. Table of contents lines are thrown out, and when a chapter number
appears twice the occurrence with real text after it wins over the contents page echo. Modules
come from `Module 1.2`, `Section`, `Lesson`, `Topic`, numbered headings like `2.3 Title`, and
Heading 2 styles. A book with no headings at all is divided into evenly sized chapters with
titles taken from the first real sentence, and the app says so on the book card. The text of
every chapter and module is stored exactly as extracted and can be read in the app behind
"show the text from the book".

<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
## 8a. Pictures inside the book

A textbook explains as much with its screenshots as with its sentences, so the pictures are
taken out of the file along with the text. `backend/courses/figures.py` reads the uploaded
file a second time: pypdf for PDF pages, python-docx for Word, python-pptx for slides. Each
picture keeps the words that were printed around it, and that text is what decides where it
belongs, matched against the text of every module and then every chapter. A picture lands on
the smallest section it fits, which is usually a module.

Logos, rules and bullets are left out. A picture that appears on more than three pages is a
running header, an identical picture is only kept once, and anything under about 110 pixels on
a side is furniture rather than a figure. With Pillow installed the size on screen decides it;
without Pillow the weight of the file is used instead.

Captions are written by the local model, but not at upload time, because forty figures would
mean forty captions before the upload finished. Instead the first person to open a section has
a handful of its figures captioned, with the explanation they are reading given to the model
as context, and the rest are picked up on the next visit. Until a caption is written the page
shows the sentence that was printed beside the picture in the book. Pull a vision model and
name it in `OLLAMA_VISION_MODEL` and the picture itself is described instead of the words
around it:

```bash
ollama pull llava:7b
export OLLAMA_VISION_MODEL=llava:7b
```

Set `EXTRACT_BOOK_IMAGES=0` to go back to text only uploads. Nothing here can stop an upload:
every reader is wrapped, and a file whose pictures cannot be read produces exactly the
chapters and modules it did before.

The pictures come back on the chapter and module endpoints under `images`, and the reading
screen draws them under the explanation. Opening a chapter shows every figure printed in it,
including the ones inside its modules. Opening a single module shows only its own.

## 9. How the quizzes work

Every quiz is ten questions: seven multiple choice, then three long business questions. The
multiple choice ones are written by the local model from the explanation the student has just
read for that section, with the book's own words behind it as supporting detail, so the quiz
asks about the page they actually read rather than about Excel in general. If a section has
never been opened its explanation is written first, so the quiz has something to be about.
Anything the model returns that does not share its subject with that passage is dropped, and
the template bank fills the gap, so a paper is always ten questions whether or not Ollama is
running.
<<<<<<< HEAD
=======
=======
## 9. How the quizzes work

Every quiz is ten questions: seven multiple choice, then three long business questions.
>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a


`backend/quizzes/generator.py` holds nineteen question templates covering SUM and AutoSum,
AVERAGE, MIN and MAX, COUNT against COUNTA, COUNTIF, SUMIF, IF, VLOOKUP, absolute and relative
references, margin percentages, order of operations, ROUND, number formats, AutoFill, cell
addresses, choosing the right tool, and reading Excel errors.

Each section has five fixed sets rather than a new paper every time. All five ask the same
skills in the same order, so they are level with each other, and only the company names,
figures and scenarios differ. Students are handed them in turn: the first student on a
section gets set one, the sixth gets set one again. A retake moves that student on to the
next set, so a second attempt is a different paper of the same difficulty and a sixth
attempt comes back to the one they started on. That is what makes the questions reviewable:
an instructor has fifty questions to read on a section, not an endless stream. Question sets
for this section, on the reading screen, opens all five with every question editable in
place, and the next student to sit that set sees the new wording. Rebuilding the five sets
is a deliberate button, and it discards anything you had rewritten. Each question carries its own
small workbook as data, which the app renders as a real grid with column letters, row numbers,
monospace cells, formulas in green and the relevant range shaded. On a wide screen the
worksheet sits to the right of the question; on a phone it sits above it. The answer key stays
on the server until the paper is submitted.

Questions eight, nine and ten are the business questions, and they work differently. Each one
is a paragraph or two of a real situation, a purchase order with no line totals, an order log
with every region mixed together, a branch list where the question is growth rather than size.
There are no options. The student works in the sheet beside the question and types the answer
into a field.

That sheet is a working Excel window rather than a table. It has the title bar, the ribbon tabs
across the top, ribbon buttons grouped as Editing, Sort and Filter and Select, the Name Box and
the fx formula bar, lettered column headings and numbered rows, the sheet tab along the bottom
and the status bar under it.

Tapping a cell selects it and puts its contents in the formula bar; tapping a column letter
selects the whole column and highlights the heading. The status bar shows Average, Count, Min,
Max and Sum for whatever is selected, exactly where Excel puts them, and tapping any of those
figures sends it straight up into the answer box on the question. AutoSum writes a SUM formula
under the selected column. Sort A to Z and Sort Z to A reorder the rows by the selected column
and keep the heading row in place. Typing into the formula bar and pressing Enter writes a value
or a formula into the selected cell, and Fill down copies it through a selected range with the
relative references shifted, so =B2*C2 becomes =B3*C3 the way it would in Excel. Reset puts
everything back to how the sheet arrived.

Under the answer box is a Check button. It sends the typed answer to the server, which stores it
and replies with nothing more than whether it holds up, so the student sees a green tick or a red
cross against that question without the expected value ever being sent to the app. A wrong answer
can be reworked in the sheet and checked again. Marking at submission is unchanged, so the score
is still worked out on the server against every question.

`mobile/src/lib/formula.js` is the engine behind that. It understands cell addresses, ranges,
the arithmetic and comparison operators, text joining with the ampersand, and SUM, AVERAGE,
COUNT, COUNTA, COUNTBLANK, MIN, MAX, MEDIAN, LARGE, SMALL, ROUND, ROUNDUP, ROUNDDOWN, ABS, INT,
SQRT, POWER, IF, COUNTIF, SUMIF, AVERAGEIF, SUMPRODUCT and PRODUCT, and it returns the same
error codes Excel does, so #DIV/0! and #NAME? show up where they should.

Marking a typed answer compares meaning rather than characters. $12,480.00, 12,480 and 12480
all pass, a percentage is accepted whether it is typed as 18.5 or as 0.185 because both are
what Excel shows depending on the format, and each question carries its own tolerance so a
rounding difference in the last place does not cost a mark. A named answer, such as which
branch earns most per order, is matched without regard to case.

After submitting, a student sees how many were right and wrong, the split between the multiple
choice and the business questions, then every question again with their answer, the correct
answer, the worksheet and the explanation of why. The business questions also show the steps
that would have produced the answer.

## 10. API

Auth: `POST /api/auth/register/`, `POST /api/auth/login/`, `GET|PATCH /api/auth/profile/`,
`POST /api/auth/refresh/`

Courses: `GET|POST /api/courses/`, `GET|PATCH|DELETE /api/courses/<id>/`,
`POST /api/courses/<id>/books/` (multipart upload), `POST /api/courses/<id>/generate-book/`
(multipart slides, images or a `topics` field), `DELETE /api/books/<id>/`,
`GET /api/courses/<id>/students/`, `GET /api/courses/<id>/performance/`

Access: `GET|POST /api/courses/<id>/invitations/`, `DELETE /api/invitations/<id>/`,
`GET /api/my-invitations/`, `POST /api/invitations/<id>/respond/`

Content: `GET /api/chapters/<id>/`, `GET /api/modules/<id>/`, both accepting `?refresh=1` to
rewrite the explanation

Joining: `GET /api/course-codes/`, `POST /api/join-course/`

Dashboards: `GET /api/faculty/dashboard/`, `GET /api/student/dashboard/`,
`GET /api/ai-status/`

Quizzes: `POST /api/quizzes/start/`, `POST /api/quizzes/<id>/submit/`,
`POST /api/quizzes/<id>/check/` (checks one business answer while the paper is open),
`GET /api/quizzes/<id>/`, `GET /api/quizzes/attempts/`, `POST /api/quizzes/preview/` (faculty)

Feedback: `GET|POST /api/feedback/`, `GET /api/feedback/course/<id>/`,
`POST /api/feedback/<id>/reply/` (faculty)

## 11. Checking it all works

```bash
cd backend
python manage.py shell < smoke_test.py
python manage.py shell < tests_averages.py
SAMPLE_DIR=/path/to/your/slides python manage.py shell < tests_access_and_generation.py
```

`tests_averages.py` builds a course with a ten mark paper at sixty percent and a four mark paper
at zero, then checks that the course average, the class average and the student's own average
all read 42.9, which is six marks out of fourteen, rather than the 30 an average of percentages
would give. `tests_access_and_generation.py` builds a course from slides and a montage, gives
two students access, accepts as one of them, and confirms an uninvited student is refused.

Three more checks cover the newer parts:

```bash
python manage.py shell < checks_averages.py       # marks in, percentages out
python manage.py shell < checks_invitations.py    # granting, accepting, declining
python manage.py shell < checks_generation.py     # writing a book from slides or topics
python manage.py shell < checks_workflow.py       # editing, approval, rubrics, admin
python manage.py shell < checks_student_journey.py  # accept access, read, quiz, results
python manage.py shell < checks_download.py       # the whole book download
python manage.py shell < checks_uploaded_book.py  # what the student sees of an upload
python manage.py shell < checks_question_sets.py  # five sets, handed out in turn
python manage.py shell < checks_rubrics.py        # rubric terms and rubric-scored progress
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
python checks_book_images.py                      # pictures out of a book and onto a section
```

`checks_book_images.py` runs on its own rather than through the shell. It builds a Word file, a
PowerPoint file and a PDF with figures in known places, pushes each through the same path an
upload takes, prints which chapter or module every picture landed on, then uploads one of them
through the API and checks the chapter comes back with an address the app can load. Ollama is
not needed for it.

<<<<<<< HEAD
=======
=======
```

>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
Run those on a fresh database, straight after `seed_demo`.

The main smoke test signs in as both roles, joins a course by code, reads a chapter and a module, starts a
quiz, checks the paper is ten questions split seven and three, checks the business questions
carry no options and the multiple choice ones do, checks each question carries its own
worksheet, checks the answer key is not being sent to the student app, submits, reads the
results, starts a second quiz to confirm the questions regenerate, runs ten cases through the
typed answer marker, and reads both dashboards and the course feedback.

## 12. Layout

```
backend/
  config/            settings, urls, wsgi
  accounts/          user model with FACULTY and STUDENT roles, JWT auth, permissions
  courses/           courses, enrolments, books, chapters, modules
    extraction.py    readers for pdf, docx, pptx, txt and the chapter/module splitters
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
    figures.py       pulling the pictures out of a book and matching them to a section
    figure_store.py  saving those pictures and having the model caption them
    generate.py      building a book from slides, images or topic names
    explain.py       Ollama client, figure captions, and the built in fallback writer
<<<<<<< HEAD
=======
=======
    generate.py      building a book from slides, images or topic names
    explain.py       Ollama client and the built in fallback writer
>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
    management/commands/seed_demo.py, check_ollama.py
  quizzes/           attempts, per question storage
    generator.py     nineteen multiple choice templates
    business.py      nine long business question templates and the typed answer marking
  feedback/          course wise feedback and student comments
  smoke_test.py

mobile/
  App.js
  src/api/client.js          axios instance, server address, error messages
  src/store/auth.js          login state kept in AsyncStorage
  src/navigation/index.js    role based sidebar
  src/theme.js               colours, type scale, monospace face
  src/lib/formula.js         the spreadsheet engine behind the live sheet
  src/lib/sheet.js           resolving, filling down, sorting and number formats
  src/components/            shared controls, the read only Workbook and InteractiveWorkbook
  src/screens/faculty/       dashboard, courses, course detail, quiz preview
  src/screens/student/       dashboard, courses, course detail, quiz, results, feedback
  src/screens/shared/        login, register, profile, chapter and module reading
```

## 13. If something goes wrong

The app says "Cannot reach the server" when the address in `src/api/client.js` does not match
where Django is listening. Start Django with `0.0.0.0:8000` rather than the default so a phone
can reach it.

An upload that returns "No readable text was found" is almost certainly a scanned PDF, which is
a picture of a page rather than text. Run it through OCR first, or upload the Word original.

If explanations look thin, check `python manage.py check_ollama`. A thin explanation with
Ollama down is the fallback writer doing its best with the extracted text.
<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a

## 5c. Where the local model is used

Three jobs, and each one keeps working when Ollama is not running.

Structure. The model does the reading of an uploaded book. Running heads come off first,
because a short line appearing on three or more pages is a header or a footer rather than
text. The lines are then numbered and handed to the model, which says which of them start a
chapter or a module, and is told to leave out the table of contents, running headers and
footers, page numbers, an index, repeated headings and lines that only look like headings.
It answers with line numbers, never prose, and the book is sliced at them. Two safety nets
sit behind that: if its outline does not hold up against the lines that were sent, the
pattern matcher's candidates go back to it with the text following each one for a simpler
keep or drop decision with a reason, and if that fails too the pattern matcher's own reading
stands. The book card says which route ran, so you always know what read your file.

Explanations. Each chapter and module is explained by the model from that section's own
text, about 800 words in very plain English with a worked example, the common mistakes and
a self check. It gets a second ask if the first comes back as a stub, and a short answer
counts as no answer. Only when it cannot answer at all does the built in writer step in,
producing the same shape at about 500 words from the same text.

Quizzes. The seven multiple choice questions in each set are written by the model from the
passage the student is reading, with plausible wrong answers and, where it helps, a small
worksheet beside the question. Each of the five sets is written separately so they differ.
Every question is checked before it is stored: a prompt, four distinct options, an answer
pointing at one of them, an explanation, and subject words that actually appear in the
section, so a question about something the module never covered is dropped and the template
bank fills the gap. The three business questions always come from the template bank, because
those are marked against a number the platform worked out itself and a model's arithmetic is
not something to stake a mark on.

<<<<<<< HEAD
=======
=======
>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
