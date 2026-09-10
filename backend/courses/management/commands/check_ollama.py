"""Tell me whether the local model is ready before I upload a book."""
from django.core.management.base import BaseCommand

from courses.explain import build_explanation, ollama_status

SAMPLE = (
    "AUTOSUM writes a SUM formula under the column you selected, but you still check the "
    "highlighted range before accepting it. An ABSOLUTE REFERENCE locked with dollar signs "
    "keeps pointing at the same cell when the formula is copied, while a RELATIVE REFERENCE "
    "moves with it. Mixing the two wrongly is the commonest cause of a spreadsheet that looks "
    "right and is not."
)


class Command(BaseCommand):
    help = "Check that Ollama is running and write one sample explanation."

    def handle(self, *args, **options):
        status = ollama_status()
        style = self.style.SUCCESS if status["running"] else self.style.WARNING
        self.stdout.write(style(status["message"]))
        if status["models"]:
            self.stdout.write(f"Models pulled: {', '.join(status['models'])}")
        self.stdout.write("\nSample explanation:\n")
        self.stdout.write(build_explanation("Absolute and relative references", SAMPLE, "module"))
        if not status["running"]:
            self.stdout.write(self.style.WARNING(
                "\nThat sample came from the built in writer. Start Ollama to use the model."
            ))
