import { useFocusEffect } from '@react-navigation/native';
import * as DocumentPicker from 'expo-document-picker';
import React, { useCallback, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';

import api, { API_HOST, readError } from '../../api/client';
import { Button, ConfirmDialog, Empty, Field, Loading, Notice, Surface }
  from '../../components/ui';
import { colors, mono, radius, spacing, type } from '../../theme';

const STATUS_LABEL = {
  DRAFT: 'Draft',
  UNDER_REVIEW: 'Under review',
  CHANGES: 'Changes requested',
  APPROVED: 'Approved, ready to publish',
  PUBLISHED: 'Published',
};

function StatusChip({ status }) {
  const tint = {
    DRAFT: { bg: colors.canvas, fg: colors.muted },
    UNDER_REVIEW: { bg: colors.amberSoft, fg: colors.amber },
    CHANGES: { bg: colors.redSoft, fg: colors.red },
    APPROVED: { bg: colors.accentSoft, fg: colors.accent },
    PUBLISHED: { bg: colors.accent, fg: colors.paper },
  }[status] || { bg: colors.canvas, fg: colors.muted };
  return (
    <Text style={[styles.chip, { backgroundColor: tint.bg, color: tint.fg }]}>
      {STATUS_LABEL[status] || status}
    </Text>
  );
}

/**
 * Everything an instructor does to one chapter after it comes out of a book: rewrite it,
 * split or merge it, hang a screenshot and a walkthrough off a module, send it for
 * approval and publish it once an admin agrees.
 */
export function ChapterWorkshop({ route, navigation }) {
  const { id, bookId } = route.params;
  const [chapter, setChapter] = useState(null);
  const [title, setTitle] = useState('');
  const [text, setText] = useState('');
  const [resources, setResources] = useState([]);
  const [demos, setDemos] = useState([]);
  const [target, setTarget] = useState(null);
  const [splitAt, setSplitAt] = useState('');
  const [demoTitle, setDemoTitle] = useState('');
  const [demoSteps, setDemoSteps] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [pending, setPending] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/chapters/${id}/`);
      setChapter(data);
      setTitle(data.title);
      setText(data.raw_text);
      const first = data.modules[0]?.id ?? null;
      setTarget((current) => current ?? first);
      const [res, demo] = await Promise.all([
        api.get(`/resources/?chapter=${id}`).catch(() => ({ data: [] })),
        api.get(`/demonstrations/?chapter=${id}`).catch(() => ({ data: [] })),
      ]);
      setResources(Array.isArray(res.data) ? res.data : []);
      setDemos(Array.isArray(demo.data) ? demo.data : []);
      setError('');
    } catch (err) {
      setError(readError(err));
    }
  }, [id]);

  useFocusEffect(useCallback(() => {
    navigation.setOptions({ title: 'Chapter workshop' });
    load();
  }, [load, navigation]));

  const run = async (work, note) => {
    setBusy(true);
    setMessage('');
    setError('');
    try {
      await work();
      setMessage(note);
      load();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  const loadModuleExtras = async (moduleId) => {
    setTarget(moduleId);
    try {
      const [res, demo] = await Promise.all([
        api.get(`/resources/?module=${moduleId}`).catch(() => ({ data: [] })),
        api.get(`/demonstrations/?module=${moduleId}`).catch(() => ({ data: [] })),
      ]);
      setResources(Array.isArray(res.data) ? res.data : []);
      setDemos(Array.isArray(demo.data) ? demo.data : []);
    } catch (err) {
      setError(readError(err));
    }
  };

  const addResource = async () => {
    const picked = await DocumentPicker.getDocumentAsync({ copyToCacheDirectory: true });
    if (picked.canceled || !picked.assets?.length) return;
    const file = picked.assets[0];
    const body = new FormData();
    body.append(target ? 'module' : 'chapter', String(target || id));
    body.append('title', file.name.replace(/\.[^.]+$/, ''));
    body.append('kind', /\.(png|jpe?g|gif|webp)$/i.test(file.name) ? 'IMAGE' : 'FILE');
    if (Platform.OS === 'web') body.append('file', file.file, file.name);
    else body.append('file', { uri: file.uri, name: file.name, type: file.mimeType || 'application/octet-stream' });
    await run(
      () => api.post('/resources/', body, { headers: { 'Content-Type': 'multipart/form-data' } }),
      'Students will see that beside the reading.'
    );
  };

  const addDemonstration = async () => {
    const steps = demoSteps
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const [head, ...rest] = line.split(':');
        return rest.length
          ? { title: head.trim(), instruction: rest.join(':').trim() }
          : { instruction: line };
      });
    if (!demoTitle.trim() || steps.length === 0) {
      setError('Give the walkthrough a title and at least one step.');
      return;
    }
    await run(
      () => api.post('/demonstrations/', {
        [target ? 'module' : 'chapter']: target || id,
        title: demoTitle.trim(),
        steps,
      }),
      'Walkthrough saved.'
    );
    setDemoTitle('');
    setDemoSteps('');
  };

  if (!chapter) return <Loading label="Loading the chapter" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <View style={styles.head}>
        <Text style={type.title}>Chapter {chapter.number}</Text>
        <StatusChip status={chapter.status} />
      </View>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Edit it, add references, then send it for approval. Editing approved work sends it
        back to draft, so students never read something that changed after review.
      </Text>

      <ConfirmDialog
        visible={!!pending}
        title={pending ? `Remove ${pending.what}?` : ''}
        message={pending ? pending.note : ''}
        confirmLabel="Yes, remove it"
        cancelLabel="No, keep it"
        onCancel={() => setPending(null)}
        onConfirm={() => {
          const job = pending;
          setPending(null);
          run(job.work, job.done);
        }}
      />

      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />
      {chapter.review_comment ? (
        <Notice text={`Admin comment: ${chapter.review_comment}`} tone="warn" />
      ) : null}

      <Surface>
        <Field label="Chapter title" value={title} onChangeText={setTitle} />
        <Text style={styles.label}>Chapter text</Text>
        <TextInput
          value={text}
          onChangeText={setText}
          multiline
          style={styles.editor}
          placeholder="The text students read"
          placeholderTextColor={colors.muted}
        />
        <Button
          label={busy ? 'Saving' : 'Save changes'}
          disabled={busy}
          onPress={() => run(
            () => api.patch(`/chapters/${id}/edit/`, { title, raw_text: text }),
            'Chapter saved.'
          )}
        />
      </Surface>

      <Surface>
        <Text style={type.heading}>Modules</Text>
        <Text style={[type.small, { marginBottom: 8 }]}>
          Tap one to attach a screenshot or a walkthrough to it.
        </Text>
        {chapter.modules.map((module) => (
          <Pressable
            key={module.id}
            onPress={() => loadModuleExtras(module.id)}
            style={[styles.moduleRow, target === module.id && styles.moduleRowActive]}
          >
            <Text style={styles.moduleNumber}>{chapter.number}.{module.number}</Text>
            <Text style={styles.moduleTitle} numberOfLines={2}>{module.title}</Text>
            <Pressable
              onPress={() => setPending({
                what: `the module ${module.title}`,
                note: 'Its text goes with it, and the chapter drops back to draft.',
                work: () => api.delete(`/modules/${module.id}/edit/`),
                done: 'Module removed.',
              })}
            >
              <Text style={styles.remove}>Remove</Text>
            </Pressable>
          </Pressable>
        ))}

        <View style={styles.splitRow}>
          <TextInput
            value={splitAt}
            onChangeText={setSplitAt}
            placeholder="Split before module number"
            placeholderTextColor={colors.muted}
            keyboardType="number-pad"
            style={styles.smallInput}
          />
          <Button
            tone="quiet"
            label="Split chapter"
            disabled={busy || !splitAt}
            onPress={() => run(
              () => api.post(`/chapters/${id}/split/`, { at_module_number: Number(splitAt) }),
              'Chapter split in two.'
            )}
            style={{ flex: 1 }}
          />
        </View>
      </Surface>

      <Surface>
        <Text style={type.heading}>References for students</Text>
        <Text style={[type.small, { marginBottom: 8 }]}>
          A screenshot here shows up in the reading itself, right under the explanation.
        </Text>
        {resources.length === 0 ? (
          <Text style={type.small}>Nothing attached yet.</Text>
        ) : resources.map((resource) => (
          <View key={resource.id} style={styles.listRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.listTitle}>{resource.title}</Text>
              <Text style={type.small}>{resource.kind} · {resource.added_by_name}</Text>
            </View>
            <Pressable onPress={() => setPending({
              what: resource.title,
              note: 'Students will stop seeing it beside the reading.',
              work: () => api.delete(`/resources/${resource.id}/`),
              done: 'Resource removed.',
            })}>
              <Text style={styles.remove}>Remove</Text>
            </Pressable>
          </View>
        ))}
        <Button tone="quiet" label="Upload a screenshot or handout" onPress={addResource}
                style={{ marginTop: 10 }} />
      </Surface>

      <Surface>
        <Text style={type.heading}>Step by step demonstration</Text>
        <Text style={[type.small, { marginBottom: 8 }]}>
          One step per line. Put a colon after a short step title if you want one.
        </Text>
        {demos.map((demo) => (
          <View key={demo.id} style={styles.listRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.listTitle}>{demo.title}</Text>
              <Text style={type.small}>{demo.step_count} steps</Text>
            </View>
            <Pressable onPress={() => setPending({
              what: demo.title,
              note: `All ${demo.step_count} steps go with it.`,
              work: () => api.delete(`/demonstrations/${demo.id}/`),
              done: 'Walkthrough removed.',
            })}>
              <Text style={styles.remove}>Remove</Text>
            </Pressable>
          </View>
        ))}
        <Field label="Walkthrough title" value={demoTitle} onChangeText={setDemoTitle}
               placeholder="Totalling a column the way I do it in class" />
        <TextInput
          value={demoSteps}
          onChangeText={setDemoSteps}
          multiline
          style={styles.editor}
          placeholder={'Select the column: click B2 and drag to B6\nPress AutoSum: Home tab, Editing group'}
          placeholderTextColor={colors.muted}
        />
        <Button label="Save walkthrough" onPress={addDemonstration} disabled={busy} />
      </Surface>

      <Surface>
        <Text style={type.heading}>Approval</Text>
        <Text style={[type.small, { marginBottom: 10 }]}>
          {chapter.status === 'APPROVED'
            ? 'An admin has approved this. Publishing it puts it in front of students.'
            : chapter.status === 'PUBLISHED'
            ? 'Students can read this chapter now.'
            : 'Send it to an admin when you are happy with it.'}
        </Text>
        <Button
          label="Send for approval"
          disabled={busy || chapter.status === 'UNDER_REVIEW'}
          onPress={() => run(() => api.post(`/chapters/${id}/submit/`, {}), 'Sent to an admin.')}
          style={{ marginBottom: 8 }}
        />
        <Button
          tone="accent"
          label="Publish"
          disabled={busy || chapter.status !== 'APPROVED'}
          onPress={() => run(() => api.post(`/chapters/${id}/publish/`, {}), 'Published.')}
          style={{ marginBottom: 8 }}
        />
        <Button
          tone="quiet"
          label="Download this chapter"
          onPress={() => run(async () => {
            const { data } = await api.get(`/chapters/${id}/download/`);
            setMessage(`Downloaded ${String(data).length} characters.`);
          }, 'Chapter downloaded.')}
        />
        <Text style={styles.hint}>
          On the web the file also opens at {API_HOST}/api/chapters/{id}/download/
        </Text>
      </Surface>
    </ScrollView>
  );
}

/**
 * The marking scheme for a course.
 *
 * The terms are already written. An instructor says how much each one counts, drops the
 * ones that do not apply, and adds any of their own. Whatever they set here is what the
 * progress screen scores students against.
 */
export function RubricsScreen() {
  const [courses, setCourses] = useState([]);
  const [catalogue, setCatalogue] = useState([]);
  const [rubrics, setRubrics] = useState(null);
  const [course, setCourse] = useState(null);
  const [title, setTitle] = useState('Marking scheme');
  const [weights, setWeights] = useState({});
  const [own, setOwn] = useState([]);
  const [newTerm, setNewTerm] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [courseList, terms, rubricList] = await Promise.all([
        api.get('/courses/'), api.get('/rubrics/catalogue/'), api.get('/rubrics/'),
      ]);
      setCourses(courseList.data);
      setCatalogue(terms.data.terms);
      setRubrics(rubricList.data);
      const chosen = course ?? courseList.data[0]?.id ?? null;
      setCourse(chosen);

      // Start from whatever this course is already tracked against, or from the defaults.
      const existing = rubricList.data.find(
        (item) => item.course === chosen && item.tracks_progress
      );
      if (existing) {
        setTitle(existing.title);
        setWeights(Object.fromEntries(
          existing.criteria.filter((item) => item.key).map((item) => [item.key, item.points])
        ));
        setOwn(existing.criteria.filter((item) => !item.key)
          .map((item) => ({ name: item.name, points: item.points })));
      } else {
        setWeights(Object.fromEntries(terms.data.terms.map((t) => [t.key, t.points])));
        setOwn([]);
      }
      setError('');
    } catch (err) {
      setError(readError(err));
      setRubrics([]);
    }
  }, [course]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const step = (key, by) => setWeights((current) => ({
    ...current,
    [key]: Math.max(0, Math.min(30, (current[key] ?? 0) + by)),
  }));

  const total = Object.values(weights).reduce((sum, value) => sum + (value || 0), 0)
    + own.reduce((sum, item) => sum + (item.points || 0), 0);

  const save = async () => {
    const criteria = [
      ...catalogue
        .filter((term) => (weights[term.key] ?? 0) > 0)
        .map((term) => ({ key: term.key, points: weights[term.key] })),
      ...own.filter((item) => item.name.trim() && item.points > 0),
    ];
    if (!criteria.length || !course) {
      setError('Give at least one term an importance above zero.');
      return;
    }
    setBusy(true);
    setMessage('');
    setError('');
    try {
      const mine = (rubrics || []).find(
        (item) => item.course === course && item.tracks_progress
      );
      if (mine) {
        await api.patch(`/rubrics/${mine.id}/`, { title: title.trim(), criteria });
      } else {
        await api.post('/rubrics/', { course, title: title.trim(), criteria });
      }
      setMessage('Saved. Progress on this course is now scored against these terms.');
      load();
    } catch (err) {
      setError(readError(err));
    } finally {
      setBusy(false);
    }
  };

  if (!rubrics) return <Loading label="Loading the marking terms" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Rubrics</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        The terms are written for you. Set how much each one counts on your course, drop the
        ones that do not apply by taking them to zero, and add your own at the bottom.
        Measured terms are scored from what students have actually done here; judged terms
        wait for you to mark them from a student's progress page.
      </Text>
      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      <View style={styles.filterRow}>
        {courses.map((item) => (
          <Pressable
            key={item.id}
            onPress={() => setCourse(item.id)}
            style={[styles.filter, course === item.id && styles.filterActive]}
          >
            <Text
              style={[styles.filterText, course === item.id && { color: colors.tabActiveText }]}
            >
              {item.code}
            </Text>
          </Pressable>
        ))}
      </View>

      <Surface>
        <Field label="What you call this scheme" value={title} onChangeText={setTitle} />
        <Text style={styles.label}>Importance of each term</Text>
        {catalogue.map((term) => {
          const points = weights[term.key] ?? 0;
          return (
            <View key={term.key} style={[styles.termRow, points === 0 && { opacity: 0.5 }]}>
              <View style={{ flex: 1, paddingRight: 10 }}>
                <Text style={styles.termName}>
                  {term.name}
                  <Text style={styles.termKind}>
                    {'  '}{term.source === 'measured' ? 'measured for you' : 'you mark it'}
                  </Text>
                </Text>
                <Text style={styles.termNote}>{term.descriptor}</Text>
              </View>
              <View style={styles.stepper}>
                <Pressable onPress={() => step(term.key, -1)} style={styles.stepButton}>
                  <Text style={styles.stepText}>−</Text>
                </Pressable>
                <Text style={styles.points}>{points}</Text>
                <Pressable onPress={() => step(term.key, 1)} style={styles.stepButton}>
                  <Text style={styles.stepText}>+</Text>
                </Pressable>
              </View>
            </View>
          );
        })}

        {own.map((item, index) => (
          <View key={`own${index}`} style={styles.termRow}>
            <View style={{ flex: 1, paddingRight: 10 }}>
              <TextInput
                value={item.name}
                onChangeText={(value) => setOwn((list) => list.map((row, position) =>
                  position === index ? { ...row, name: value } : row))}
                style={styles.smallInput}
              />
              <Text style={styles.termNote}>Your own term. You mark it yourself.</Text>
            </View>
            <View style={styles.stepper}>
              <Pressable
                onPress={() => setOwn((list) => list.map((row, position) => position === index
                  ? { ...row, points: Math.max(0, row.points - 1) } : row))}
                style={styles.stepButton}
              >
                <Text style={styles.stepText}>−</Text>
              </Pressable>
              <Text style={styles.points}>{item.points}</Text>
              <Pressable
                onPress={() => setOwn((list) => list.map((row, position) => position === index
                  ? { ...row, points: row.points + 1 } : row))}
                style={styles.stepButton}
              >
                <Text style={styles.stepText}>+</Text>
              </Pressable>
            </View>
          </View>
        ))}

        <View style={styles.splitRow}>
          <TextInput
            value={newTerm}
            onChangeText={setNewTerm}
            placeholder="Add a term of your own"
            placeholderTextColor={colors.muted}
            style={styles.smallInput}
          />
          <Button
            tone="quiet"
            label="Add"
            disabled={!newTerm.trim()}
            onPress={() => {
              setOwn((list) => [...list, { name: newTerm.trim(), points: 5 }]);
              setNewTerm('');
            }}
            style={{ marginLeft: 8 }}
          />
        </View>

        <Text style={styles.total}>Worth {total} points in total</Text>
        <Button label={busy ? 'Saving' : 'Save the marking scheme'} onPress={save} disabled={busy} />
      </Surface>

      {rubrics.filter((item) => item.course === course).map((rubric) => (
        <Surface key={rubric.id}>
          <View style={styles.head}>
            <Text style={styles.listTitle}>{rubric.title}</Text>
            <Text style={styles.points}>{rubric.total_points} points</Text>
          </View>
          <Text style={type.small}>
            {rubric.tracks_progress
              ? 'Progress on this course is scored against this scheme.'
              : 'Kept for reference.'}
          </Text>
          {rubric.criteria.map((item) => (
            <View key={item.name} style={styles.criterion}>
              <Text style={styles.criterionName}>
                {item.name}
                <Text style={styles.termKind}>
                  {'  '}{item.source === 'measured' ? 'measured' : 'judged'}
                </Text>
              </Text>
              <Text style={styles.rowValue}>{item.points}</Text>
            </View>
          ))}
        </Surface>
      ))}
    </ScrollView>
  );
}

/** The class list, one student's detail, their quiz answers and written feedback. */
export function ProgressScreen() {
  const [courses, setCourses] = useState([]);
  const [course, setCourse] = useState(null);
  const [rows, setRows] = useState(null);
  const [student, setStudent] = useState(null);
  const [rubrics, setRubrics] = useState([]);
  const [comment, setComment] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/courses/');
      setCourses(data);
      const chosen = course ?? data[0]?.id ?? null;
      setCourse(chosen);
      if (chosen) {
        const [progress, rubricList] = await Promise.all([
          api.get(`/courses/${chosen}/progress/`),
          api.get(`/rubrics/?course_id=${chosen}`),
        ]);
        setRows(progress.data.students);
        setRubrics(rubricList.data);
      } else {
        setRows([]);
      }
      setError('');
    } catch (err) {
      setError(readError(err));
      setRows([]);
    }
  }, [course]);

  useFocusEffect(useCallback(() => { load(); }, [load]));

  const openStudent = async (row) => {
    setStudent(null);
    setMessage('');
    try {
      const { data } = await api.get(`/courses/${course}/progress/${row.student_id}/`);
      setStudent(data);
    } catch (err) {
      setError(readError(err));
    }
  };

  const sendFeedback = async (rubricId) => {
    if (!comment.trim() && !rubricId) {
      setError('Write something, or pick a rubric to mark against.');
      return;
    }
    try {
      await api.post('/evaluations/', {
        course,
        student: student.student.id,
        rubric: rubricId || null,
        comment: comment.trim(),
      });
      setComment('');
      setMessage('Feedback sent. The student sees it under Feedback.');
      openStudent({ student_id: student.student.id });
    } catch (err) {
      setError(readError(err));
    }
  };

  if (!rows) return <Loading label="Loading the class" />;

  return (
    <ScrollView style={{ backgroundColor: colors.canvas }} contentContainerStyle={styles.page}>
      <Text style={type.title}>Student progress</Text>
      <Text style={[type.small, { marginBottom: spacing(2) }]}>
        Who is where, what they answered, and your written feedback.
      </Text>
      <Notice text={message} tone="good" />
      <Notice text={error} tone="error" />

      <View style={styles.filterRow}>
        {courses.map((item) => (
          <Pressable
            key={item.id}
            onPress={() => { setCourse(item.id); setStudent(null); }}
            style={[styles.filter, course === item.id && styles.filterActive]}
          >
            <Text style={[styles.filterText, course === item.id && { color: colors.tabActiveText }]}>
              {item.code}
            </Text>
          </Pressable>
        ))}
      </View>

      {rows.length === 0 ? (
        <Empty title="Nobody enrolled" body="Grant access from Access provision first." />
      ) : rows.map((row) => (
        <Pressable key={row.student_id} onPress={() => openStudent(row)}>
          <Surface>
            <View style={styles.head}>
              <Text style={styles.listTitle}>{row.student_name}</Text>
              <Text style={styles.points}>
                {row.rubric_progress && row.rubric_progress.percentage !== null
                  ? `${row.rubric_progress.percentage}% on your rubric`
                  : row.percentage === null ? '—' : `${row.percentage}% on quizzes`}
              </Text>
            </View>
            <Text style={type.small}>{row.student_email}</Text>
            <Text style={type.small}>
              {row.attempts} attempts · {row.marks || 'no marks yet'} ·{' '}
              {row.chapters_touched} of {row.chapters_published} chapters ·{' '}
              {row.evaluations} evaluations
            </Text>
            {row.rubric_progress ? (
              <Text style={styles.rubricLine}>
                {row.rubric_progress.awarded} of {row.rubric_progress.possible} points
                {row.rubric_progress.waiting_on.length
                  ? ` · waiting on ${row.rubric_progress.waiting_on.length} term`
                    + (row.rubric_progress.waiting_on.length === 1 ? '' : 's')
                  : ''}
              </Text>
            ) : null}
          </Surface>
        </Pressable>
      ))}

      {student ? (
        <Surface>
          <Text style={type.heading}>{student.student.name}</Text>
          <Text style={type.small}>
            {student.marks || 'No quizzes yet'} ·{' '}
            {student.percentage === null ? 'no average' : `${student.percentage}%`}
          </Text>

          {student.rubric_progress ? (
            <>
              <Text style={[styles.label, { marginTop: 12 }]}>
                {student.rubric_progress.rubric.title}
              </Text>
              {student.rubric_progress.criteria.map((item) => (
                <View key={item.name} style={styles.criterion}>
                  <View style={{ flex: 1, paddingRight: 10 }}>
                    <Text style={styles.criterionName}>
                      {item.name}
                      <Text style={styles.termKind}>
                        {'  '}{item.source === 'measured' ? 'measured' : 'you mark it'}
                      </Text>
                    </Text>
                    {item.note ? <Text style={styles.termNote}>{item.note}</Text> : null}
                  </View>
                  <Text style={styles.rowValue}>
                    {item.awarded === null ? `— / ${item.points}`
                      : `${item.awarded} / ${item.points}`}
                  </Text>
                </View>
              ))}
              <Text style={styles.rubricTotal}>
                {student.rubric_progress.awarded} of {student.rubric_progress.possible} points
                {student.rubric_progress.percentage !== null
                  ? ` (${student.rubric_progress.percentage}%)` : ''}
              </Text>
            </>
          ) : null}

          {student.skills.length ? (
            <>
              <Text style={[styles.label, { marginTop: 12 }]}>Skill by skill</Text>
              {student.skills.map((skill) => (
                <View key={skill.skill} style={styles.criterion}>
                  <Text style={styles.criterionName}>{skill.skill}</Text>
                  <Text style={styles.rowValue}>
                    {skill.correct}/{skill.asked} ({skill.accuracy}%)
                  </Text>
                </View>
              ))}
            </>
          ) : null}

          {student.attempts.map((attempt) => (
            <View key={attempt.attempt_id} style={styles.attempt}>
              <Text style={styles.listTitle}>{attempt.label}</Text>
              <Text style={type.small}>
                {attempt.score}/{attempt.total} ({attempt.percentage}%)
              </Text>
              {attempt.questions.map((question) => (
                <Text key={question.id} style={styles.answerLine}>
                  Q{question.order} {question.is_correct ? '✓' : '✗'} {question.skill} — they
                  answered {question.your_answer}
                  {question.is_correct ? '' : `, correct was ${question.correct_answer}`}
                </Text>
              ))}
            </View>
          ))}

          <Text style={[styles.label, { marginTop: 14 }]}>Written feedback</Text>
          <TextInput
            value={comment}
            onChangeText={setComment}
            multiline
            style={styles.editor}
            placeholder="What went well, and the one thing to fix next"
            placeholderTextColor={colors.muted}
          />
          <Button label="Send feedback" onPress={() => sendFeedback(null)} style={{ marginBottom: 8 }} />
          {rubrics.map((rubric) => (
            <Button
              key={rubric.id}
              tone="quiet"
              label={`Mark against ${rubric.title}`}
              onPress={() => sendFeedback(rubric.id)}
              style={{ marginBottom: 8 }}
            />
          ))}

          {student.evaluations.map((evaluation) => (
            <View key={evaluation.id} style={styles.attempt}>
              <Text style={styles.listTitle}>
                {evaluation.rubric_title || 'Written feedback'}
                {evaluation.possible ? ` — ${evaluation.awarded}/${evaluation.possible}` : ''}
              </Text>
              <Text style={type.small}>{evaluation.comment}</Text>
            </View>
          ))}
        </Surface>
      ) : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: {
    padding: spacing(2.5),
    paddingBottom: spacing(6),
    width: '100%',
    maxWidth: 1140,
    alignSelf: 'center',
  },
  head: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  chip: {
    fontSize: 11.5,
    fontWeight: '700',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    overflow: 'hidden',
  },
  label: { fontSize: 13, fontWeight: '600', color: colors.inkSoft, marginBottom: 6 },
  editor: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    borderRadius: radius.control,
    minHeight: 120,
    padding: 12,
    marginBottom: 12,
    fontSize: 14.5,
    lineHeight: 21,
    color: colors.ink,
    textAlignVertical: 'top',
  },
  smallInput: {
    borderWidth: 1,
    borderColor: colors.gridStrong,
    borderRadius: radius.control,
    paddingHorizontal: 12,
    paddingVertical: 11,
    marginRight: 8,
    width: 190,
    fontSize: 14,
    color: colors.ink,
  },
  moduleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    paddingHorizontal: 8,
    borderRadius: radius.control,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
  },
  moduleRowActive: { backgroundColor: colors.accentSoft },
  moduleNumber: { fontFamily: mono, fontSize: 12, color: colors.muted, width: 40 },
  moduleTitle: { flex: 1, fontSize: 14.5, color: colors.ink },
  remove: { color: colors.red, fontSize: 13, fontWeight: '600', paddingLeft: 10 },
  splitRow: { flexDirection: 'row', alignItems: 'center', marginTop: 12 },
  listRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    marginTop: 8,
  },
  listTitle: { fontSize: 15, fontWeight: '700', color: colors.ink },
  points: { fontFamily: mono, fontSize: 13, color: colors.accent },
  criterion: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 7,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
    marginTop: 6,
  },
  criterionName: { fontSize: 14, color: colors.inkSoft, flex: 1, paddingRight: 10 },
  rowValue: { fontFamily: mono, fontSize: 13, color: colors.ink },
  attempt: { borderTopWidth: 1, borderTopColor: colors.grid, paddingTop: 10, marginTop: 12 },
  answerLine: { fontSize: 12.5, color: colors.inkSoft, lineHeight: 19, marginTop: 4 },
  filterRow: { flexDirection: 'row', flexWrap: 'wrap', marginBottom: spacing(1.5) },
  filter: {
    borderWidth: 1,
    borderColor: colors.grid,
    backgroundColor: colors.paper,
    borderRadius: radius.control,
    paddingHorizontal: 12,
    paddingVertical: 9,
    marginRight: 8,
    marginBottom: 8,
  },
  filterActive: { backgroundColor: colors.tabActive, borderColor: colors.tabActive },
  filterText: { fontSize: 13.5, fontWeight: '600', color: colors.inkSoft },
  hint: { fontSize: 11.5, color: colors.muted, marginTop: 8 },
  termRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: colors.grid,
  },
  termName: { fontSize: 14.5, fontWeight: '600', color: colors.ink },
  termKind: { fontSize: 11.5, fontWeight: '400', color: colors.accent },
  termNote: { fontSize: 12.5, color: colors.muted, marginTop: 2, lineHeight: 18 },
  stepper: { flexDirection: 'row', alignItems: 'center' },
  stepButton: {
    width: 32,
    height: 32,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.gridStrong,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepText: { fontSize: 17, color: colors.inkSoft },
  total: { fontSize: 13.5, color: colors.inkSoft, marginTop: 12, marginBottom: 10 },
  rubricLine: { fontSize: 12.5, color: colors.accent, marginTop: 6 },
  rubricTotal: { fontSize: 14, fontWeight: '700', color: colors.ink, marginTop: 10 },
});
