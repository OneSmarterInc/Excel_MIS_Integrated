from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0004_rubric_tracks_progress"),
    ]

    operations = [
        migrations.CreateModel(
            name="BookImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True,
                                           serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="book_images/")),
                ("page", models.IntegerField(default=0)),
                ("order", models.IntegerField(default=0)),
                ("width", models.IntegerField(default=0)),
                ("height", models.IntegerField(default=0)),
                ("context_text", models.TextField(blank=True)),
                ("caption", models.TextField(blank=True)),
                ("described_at", models.DateTimeField(blank=True, null=True)),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                           related_name="images", to="courses.book")),
                ("chapter", models.ForeignKey(blank=True, null=True,
                                              on_delete=django.db.models.deletion.CASCADE,
                                              related_name="images", to="courses.chapter")),
                ("module", models.ForeignKey(blank=True, null=True,
                                             on_delete=django.db.models.deletion.CASCADE,
                                             related_name="images", to="courses.module")),
            ],
            options={"ordering": ["page", "order", "id"]},
        ),
    ]
